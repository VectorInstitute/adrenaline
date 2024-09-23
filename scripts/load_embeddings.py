import asyncio
import logging
from typing import List
from motor.motor_asyncio import AsyncIOMotorClient
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType
import httpx
import time
from tqdm.asyncio import tqdm
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
MONGO_URI = "mongodb://root:password@cyclops.cluster.local:27017"
MONGO_DB_NAME = "clinical_data"
MILVUS_HOST = "localhost"
MILVUS_PORT = 19530
EMBEDDING_SERVICE_URL = "http://localhost:8004/embeddings"
BATCH_SIZE = 1
MAX_PATIENTS = 100
EMBEDDING_INSTRUCTION = "Represent the clinical note for retrieval:"
MAX_RETRIES = 3
RETRY_WAIT_MULTIPLIER = 1
RETRY_WAIT_MAX = 10


class EmbeddingManager:
    def __init__(self, embedding_service_url: str):
        self.embedding_service_url = embedding_service_url
        self.client = httpx.AsyncClient(
            timeout=60.0,
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        )

    @retry(
        stop=stop_after_attempt(MAX_RETRIES),
        wait=wait_exponential(multiplier=RETRY_WAIT_MULTIPLIER, max=RETRY_WAIT_MAX),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
        reraise=True,
    )
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        try:
            response = await self.client.post(
                self.embedding_service_url,
                json={"texts": texts, "instruction": EMBEDDING_INSTRUCTION},
            )
            response.raise_for_status()
            return response.json()["embeddings"]
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e}")
            logger.error(f"Response content: {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error occurred: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error occurred: {e}")
            raise

    async def close(self):
        await self.client.aclose()


class MilvusManager:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.collection_name = "patient_notes"
        self.collection = None

    def connect(self):
        connections.connect(host=self.host, port=self.port)
        logger.info(f"Connected to Milvus at {self.host}:{self.port}")

    def create_collection(self, dim: int):
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="patient_id", dtype=DataType.INT64),
            FieldSchema(name="note_id", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
        ]
        schema = CollectionSchema(fields, "Patient notes collection")
        collection = Collection(self.collection_name, schema)

        index_params = {
            "metric_type": "L2",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 1024},
        }
        collection.create_index(field_name="embedding", index_params=index_params)
        logger.info(f"Created Milvus collection: {self.collection_name}")
        return collection

    def recreate_collection(self, dim: int):
        try:
            Collection(self.collection_name).drop()
            logger.info(f"Dropped existing Milvus collection: {self.collection_name}")
        except Exception:
            logger.info(f"No existing collection to drop: {self.collection_name}")
        return self.create_collection(dim)

    def get_or_create_collection(self, dim: int) -> Collection:
        if self.collection is None:
            self.collection = self.recreate_collection(dim)
        return self.collection

    def insert_vectors(
        self, patient_ids: List[int], note_ids: List[str], embeddings: List[List[float]]
    ):
        entities = [patient_ids, note_ids, embeddings]
        try:
            self.collection.insert(entities)
        except Exception as e:
            logger.error(f"Error inserting vectors into Milvus: {e}")
            raise


async def process_batch(
    patient_id: int,
    batch_texts: List[str],
    batch_note_ids: List[str],
    milvus_manager: MilvusManager,
    embedding_manager: EmbeddingManager,
) -> int:
    try:
        embeddings = await embedding_manager.get_embeddings(batch_texts)
        patient_ids = [int(patient_id)] * len(batch_texts)
        milvus_manager.insert_vectors(patient_ids, batch_note_ids, embeddings)
        return len(batch_texts)
    except Exception as e:
        logger.error(f"Error processing batch for patient {patient_id}: {e}")
        return 0


async def process_patients(
    mongo_client: AsyncIOMotorClient,
    milvus_manager: MilvusManager,
    embedding_manager: EmbeddingManager,
):
    db = mongo_client[MONGO_DB_NAME]
    patients_collection = db.patients

    patients_processed = 0
    total_notes_processed = 0
    start_time = time.time()

    cursor = patients_collection.find().limit(MAX_PATIENTS)
    patient_count = await patients_collection.count_documents({})
    total = min(MAX_PATIENTS, patient_count)

    async for patient in tqdm(cursor, total=total, desc="Processing patients"):
        patient_id = patient["patient_id"]
        notes = patient.get("notes", [])

        if not notes:
            logger.warning(f"Patient {patient_id} has no notes. Skipping.")
            continue

        note_texts = [note["text"] for note in notes]
        note_ids = [note["note_id"] for note in notes]
        patient_notes_processed = 0

        # Process notes in batches
        for i in range(0, len(note_texts), BATCH_SIZE):
            batch_texts = note_texts[i : i + BATCH_SIZE]
            batch_note_ids = note_ids[i : i + BATCH_SIZE]

            notes_processed = await process_batch(
                patient_id,
                batch_texts,
                batch_note_ids,
                milvus_manager,
                embedding_manager,
            )
            patient_notes_processed += notes_processed
            total_notes_processed += notes_processed

        patients_processed += 1
        logger.info(
            f"Processed patient {patient_id}: {patient_notes_processed} notes embedded"
        )

        if patients_processed >= MAX_PATIENTS:
            break

    end_time = time.time()
    total_time = end_time - start_time
    logger.info(
        f"Finished processing {patients_processed} patients and {total_notes_processed} notes in {total_time:.2f} seconds"
    )
    if total_notes_processed > 0:
        logger.info(
            f"Average processing time per note: {total_time/total_notes_processed:.4f} seconds"
        )


async def main():
    mongo_client = AsyncIOMotorClient(MONGO_URI)
    milvus_manager = MilvusManager(MILVUS_HOST, MILVUS_PORT)
    embedding_manager = EmbeddingManager(EMBEDDING_SERVICE_URL)

    milvus_manager.connect()

    try:
        await process_patients(mongo_client, milvus_manager, embedding_manager)
    except Exception as e:
        logger.error(f"An error occurred during processing: {e}")
    finally:
        mongo_client.close()
        connections.disconnect(MILVUS_HOST)
        await embedding_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
