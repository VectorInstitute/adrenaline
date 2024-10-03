import asyncio
import logging
from typing import List, Dict
import argparse
from motor.motor_asyncio import AsyncIOMotorClient
from pymilvus import (
    connections,
    Collection,
    FieldSchema,
    CollectionSchema,
    DataType,
    utility,
)
import httpx
import time
from tqdm.asyncio import tqdm
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

# Configuration
MONGO_URI = "mongodb://root:password@localhost:27017"
MONGO_DB_NAME = "clinical_data"
MILVUS_HOST = "localhost"
MILVUS_PORT = 19530
EMBEDDING_SERVICE_URL = "http://localhost:8004/embeddings"
BATCH_SIZE = 100
MAX_CONCEPTS = 10000000  # Adjust as needed
EMBEDDING_INSTRUCTION = (
    "Represent the UMLS concept for retrieval, to provide context for a search query."
)
VECTOR_DIM = 4096

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class EmbeddingManager:
    def __init__(self, embedding_service_url: str):
        self.embedding_service_url = embedding_service_url
        self.client = httpx.AsyncClient(
            timeout=60.0,
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
    )
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        try:
            logger.info(f"Sending request to embedding service with {len(texts)} texts")
            response = await self.client.post(
                self.embedding_service_url,
                json={"texts": texts, "instruction": EMBEDDING_INSTRUCTION},
            )
            logger.info(
                f"Received response from embedding service. Status code: {response.status_code}"
            )

            response.raise_for_status()

            response_json = response.json()
            logger.info("Successfully parsed response JSON")

            embeddings = response_json["embeddings"]
            logger.info(f"Retrieved {len(embeddings)} embeddings from response")

            processed_embeddings = [
                [float(value) for value in embedding.split(",")]
                if isinstance(embedding, str)
                else embedding
                for embedding in embeddings
            ]
            logger.info(f"Processed {len(processed_embeddings)} embeddings")

            return processed_embeddings
        except Exception as e:
            logger.error(f"Error in get_embeddings: {e}")
            raise

    async def close(self):
        await self.client.aclose()


class MilvusManager:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.collection_name = "umls_concepts"
        self.collection = None

    def connect(self):
        connections.connect(host=self.host, port=self.port)
        logger.info(f"Connected to Milvus at {self.host}:{self.port}")

    def create_collection(self, dim: int):
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="cui", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="preferred_term", dtype=DataType.VARCHAR, max_length=256),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
        ]
        schema = CollectionSchema(fields, "UMLS concepts collection")
        collection = Collection(self.collection_name, schema)
        index_params = {
            "metric_type": "COSINE",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 1024},
        }
        collection.create_index(field_name="embedding", index_params=index_params)
        logger.info(f"Created Milvus collection: {self.collection_name}")
        return collection

    def get_or_create_collection(self, dim: int) -> Collection:
        if not utility.has_collection(self.collection_name):
            self.collection = self.create_collection(dim)
        else:
            self.collection = Collection(self.collection_name)
            self.collection.load()
        return self.collection

    def insert_vectors(
        self,
        cuis: List[str],
        preferred_terms: List[str],
        embeddings: List[List[float]],
    ):
        try:
            entities = [
                {
                    "cui": cui,
                    "preferred_term": term,
                    "embedding": emb,
                }
                for cui, term, emb in zip(cuis, preferred_terms, embeddings)
            ]
            self.collection.insert(entities)
            self.collection.flush()
            logger.info(f"Successfully inserted {len(entities)} entities into Milvus")
        except Exception as e:
            logger.error(f"Error inserting vectors into Milvus: {e}")
            raise

    def concept_exists(self, cui: str) -> bool:
        return self.collection.query(expr=f'cui == "{cui}"', output_fields=["cui"])


async def process_batch(
    batch_concepts: List[Dict],
    milvus_manager: MilvusManager,
    embedding_manager: EmbeddingManager,
) -> int:
    try:
        cuis = []
        preferred_terms = []
        texts = []

        for concept in batch_concepts:
            cuis.append(concept["cui"])
            preferred_terms.append(concept["preferred_term"])
            texts.append(concept["combined_text"])

        embeddings = await embedding_manager.get_embeddings(texts)

        if not all(
            isinstance(emb, list) and all(isinstance(x, float) for x in emb)
            for emb in embeddings
        ):
            raise ValueError(
                "Embeddings are not in the correct format (list of float lists)"
            )

        logger.info(f"Inserting {len(cuis)} vectors into Milvus")
        logger.info(
            f"Sample data - CUI: {cuis[0]}, Preferred Term: {preferred_terms[0]}"
        )

        milvus_manager.insert_vectors(cuis, preferred_terms, embeddings)
        return len(cuis)
    except Exception as e:
        logger.error(f"Error processing batch: {e}")
        return 0


async def process_concepts(
    mongo_client: AsyncIOMotorClient,
    milvus_manager: MilvusManager,
    embedding_manager: EmbeddingManager,
    recreate_collection: bool,
):
    db = mongo_client[MONGO_DB_NAME]
    umls_collection = db.umls_concepts

    concepts_processed = 0
    start_time = time.time()

    async with await mongo_client.start_session() as session:
        query = {} if recreate_collection else {"processed": {"$ne": True}}
        total = await umls_collection.count_documents(query, session=session)
        total = min(MAX_CONCEPTS, total)

        async for batch in tqdm(
            AsyncBatchIterator(
                umls_collection.find(query, no_cursor_timeout=True, session=session),
                BATCH_SIZE,
            ),
            total=(total + BATCH_SIZE - 1) // BATCH_SIZE,
            desc="Processing concepts",
        ):
            concepts_processed += await process_batch(
                batch, milvus_manager, embedding_manager
            )

            cuis = [concept["cui"] for concept in batch]
            await umls_collection.update_many(
                {"cui": {"$in": cuis}},
                {"$set": {"processed": True}},
                session=session,
            )

            if concepts_processed >= MAX_CONCEPTS:
                break

    end_time = time.time()
    total_time = end_time - start_time
    logger.info(
        f"Finished processing {concepts_processed} concepts in {total_time:.2f} seconds"
    )
    if concepts_processed > 0:
        logger.info(
            f"Average processing time per concept: {total_time/concepts_processed:.4f} seconds"
        )


class AsyncBatchIterator:
    def __init__(self, cursor, batch_size):
        self.cursor = cursor
        self.batch_size = batch_size

    def __aiter__(self):
        return self

    async def __anext__(self):
        batch = await self.cursor.to_list(length=self.batch_size)
        if not batch:
            raise StopAsyncIteration
        return batch


async def main(recreate_collection: bool):
    mongo_client = AsyncIOMotorClient(MONGO_URI)
    milvus_manager = MilvusManager(MILVUS_HOST, MILVUS_PORT)
    embedding_manager = EmbeddingManager(EMBEDDING_SERVICE_URL)

    milvus_manager.connect()

    try:
        if recreate_collection:
            utility.drop_collection(milvus_manager.collection_name)
            logger.info(
                f"Dropped existing collection: {milvus_manager.collection_name}"
            )

        milvus_manager.collection = milvus_manager.get_or_create_collection(
            dim=VECTOR_DIM
        )
        await process_concepts(
            mongo_client, milvus_manager, embedding_manager, recreate_collection
        )
    except Exception as e:
        logger.error(f"An error occurred during processing: {e}")
    finally:
        await embedding_manager.close()
        connections.disconnect(MILVUS_HOST)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process UMLS concepts and create embeddings in Milvus."
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Recreate the entire collection in Milvus",
    )
    args = parser.parse_args()

    asyncio.run(main(args.recreate))
