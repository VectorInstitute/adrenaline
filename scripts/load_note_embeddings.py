"""Script to load note embeddings into Milvus."""

import asyncio
import json
import traceback
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
MONGO_URI = "mongodb://root:password@cyclops.cluster.local:27017"
MONGO_DB_NAME = "clinical_data"
MILVUS_HOST = "localhost"
MILVUS_PORT = 19530
EMBEDDING_SERVICE_URL = "http://localhost:8004/embeddings"
BATCH_SIZE = 32
MAX_PATIENTS = 16
EMBEDDING_INSTRUCTION = (
    "Represent the clinical note for retrieval, to provide context for a search query."
)
VECTOR_DIM = 768  # S-PubMedBert-MS-MARCO output dimension

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

            return embeddings
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error occurred: {e}")
            logger.error(f"Response content: {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error occurred: {e}")
            raise
        except KeyError as e:
            logger.error(
                f"KeyError: {e}. Response JSON: {json.dumps(response_json, indent=2)}"
            )
            raise
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}. Response text: {response.text}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error occurred: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            logger.error(f"Error traceback: {traceback.format_exc()}")
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

    def get_or_create_collection(self, dim: int) -> Collection:
        if not utility.has_collection(self.collection_name):
            self.collection = self.create_collection(dim)
        else:
            self.collection = Collection(self.collection_name)
            self.collection.load()
        return self.collection

    def create_collection(self, dim: int):
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="patient_id", dtype=DataType.INT64),
            FieldSchema(name="note_id", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
            FieldSchema(name="note_text", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="note_type", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="timestamp", dtype=DataType.INT64),
            FieldSchema(name="encounter_id", dtype=DataType.INT64),
        ]
        schema = CollectionSchema(fields, "Patient notes collection")
        collection = Collection(self.collection_name, schema)
        index_params = {
            "metric_type": "IP",
            "index_type": "HNSW",
            "params": {"M": 16, "efConstruction": 500},
        }
        collection.create_index(field_name="embedding", index_params=index_params)
        logger.info(f"Created Milvus collection: {self.collection_name}")
        return collection

    def insert_vectors(
        self,
        patient_ids: List[int],
        note_ids: List[str],
        embeddings: List[List[float]],
        note_texts: List[str],
        note_types: List[str],
        timestamps: List[int],
        encounter_ids: List[int],
    ):
        try:
            entities = [
                {
                    "patient_id": pid,
                    "note_id": nid,
                    "embedding": emb,
                    "note_text": txt,
                    "note_type": nt,
                    "timestamp": ts,
                    "encounter_id": eid,
                }
                for pid, nid, emb, txt, nt, ts, eid in zip(
                    patient_ids,
                    note_ids,
                    embeddings,
                    note_texts,
                    note_types,
                    timestamps,
                    encounter_ids,
                )
            ]
            self.collection.insert(entities)
            self.collection.flush()
            logger.info(f"Successfully inserted {len(entities)} entities into Milvus")
        except Exception as e:
            logger.error(f"Error inserting vectors into Milvus: {e}")
            raise

    def patient_exists(self, patient_id: int) -> bool:
        return self.collection.query(
            expr=f"patient_id == {patient_id}", output_fields=["patient_id"]
        )


async def process_batch(
    patient_id: int,
    batch_notes: List[Dict],
    milvus_manager: MilvusManager,
    embedding_manager: EmbeddingManager,
) -> int:
    try:
        all_texts = [note["text"] for note in batch_notes]
        all_note_ids = [note["note_id"] for note in batch_notes]
        all_note_types = [note["note_type"] for note in batch_notes]
        all_timestamps = [int(note["timestamp"].timestamp()) for note in batch_notes]
        all_encounter_ids = [note["encounter_id"] for note in batch_notes]
        embeddings = await embedding_manager.get_embeddings(all_texts)

        if not all(
            isinstance(emb, list) and all(isinstance(x, float) for x in emb)
            for emb in embeddings
        ):
            raise ValueError(
                "Embeddings are not in the correct format (list of float lists)"
            )

        patient_ids = [int(patient_id)] * len(all_texts)

        logger.info(f"Inserting {len(patient_ids)} vectors into Milvus")
        logger.info(
            f"Sample data - Patient ID: {patient_ids[0]}, Note ID: {all_note_ids[0]}"
        )

        milvus_manager.insert_vectors(
            patient_ids,
            all_note_ids,
            embeddings,
            all_texts,
            all_note_types,
            all_timestamps,
            all_encounter_ids,
        )
        return len(all_texts)
    except Exception as e:
        logger.error(f"Error processing batch for patient {patient_id}: {e}")
        return 0


async def process_patients(
    mongo_client: AsyncIOMotorClient,
    milvus_manager: MilvusManager,
    embedding_manager: EmbeddingManager,
    recreate_collection: bool,
):
    db = mongo_client[MONGO_DB_NAME]
    patients_collection = db.patients

    patients_processed = 0
    total_notes_processed = 0
    start_time = time.time()

    async with await mongo_client.start_session() as session:
        query = {} if recreate_collection else {"processed": {"$ne": True}}
        cursor = patients_collection.find(
            query, no_cursor_timeout=True, session=session
        ).limit(MAX_PATIENTS)

        patient_count = await patients_collection.count_documents(
            query, session=session
        )
        total = min(MAX_PATIENTS, patient_count)

        async for patient in tqdm(cursor, total=total, desc="Processing patients"):
            patient_id = patient["patient_id"]

            if not recreate_collection and milvus_manager.patient_exists(patient_id):
                logger.info(f"Patient {patient_id} already exists in Milvus. Skipping.")
                continue

            notes = patient.get("notes", [])

            if not notes:
                logger.warning(f"Patient {patient_id} has no notes. Skipping.")
                continue

            patient_notes_processed = 0

            for i in range(0, len(notes), BATCH_SIZE):
                batch_notes = notes[i : i + BATCH_SIZE]
                notes_processed = await process_batch(
                    patient_id, batch_notes, milvus_manager, embedding_manager
                )
                patient_notes_processed += notes_processed
                total_notes_processed += notes_processed

            patients_processed += 1
            logger.info(
                f"Processed patient {patient_id}: {patient_notes_processed} notes embedded"
            )

            await patients_collection.update_one(
                {"patient_id": patient_id},
                {"$set": {"processed": True}},
                session=session,
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
        await process_patients(
            mongo_client, milvus_manager, embedding_manager, recreate_collection
        )
    except Exception as e:
        logger.error(f"An error occurred during processing: {e}")
    finally:
        await embedding_manager.close()
        connections.disconnect(MILVUS_HOST)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process patient notes and create embeddings in Milvus."
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Recreate the entire collection in Milvus",
    )
    args = parser.parse_args()

    asyncio.run(main(args.recreate))
