"""Script to load note embeddings into ChromaDB."""

import asyncio
import logging
from typing import List, Dict, Any
import argparse
from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorDatabase,
    AsyncIOMotorCollection,
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
import sys
from pymongo import IndexModel, ASCENDING

try:
    import pysqlite3  # noqa: F401

    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except ImportError:
    pass
import chromadb
from chromadb.config import Settings

# Configuration
MONGO_URI = "mongodb://root:password@cyclops.cluster.local:27017"
MONGO_DB_NAME = "clinical_data"
CHROMA_HOST = "localhost"
CHROMA_PORT = 8000
EMBEDDING_SERVICE_URL = "http://localhost:8004/embeddings"
BATCH_SIZE = 100
MAX_PATIENTS = 16
EMBEDDING_INSTRUCTION = (
    "Represent the clinical note for retrieval, to provide context for a search query."
)
VECTOR_DIM = 768

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DatabaseManager:
    def __init__(self, mongo_uri: str, db_name: str):
        self.client: AsyncIOMotorClient[Any] = AsyncIOMotorClient(mongo_uri)
        self.db: AsyncIOMotorDatabase[Any] = self.client[db_name]
        self.patients_collection: AsyncIOMotorCollection[Any] = self.db.patients

    async def ensure_indexes(self) -> None:
        """Check and create indexes only if they don't exist"""
        existing_indexes = await self.patients_collection.index_information()
        indexes = [
            IndexModel([("patient_id", ASCENDING)], unique=True),
            IndexModel([("notes.note_id", ASCENDING)]),
        ]

        # Check and create indexes if they don't exist
        for index in indexes:
            index_name = f"{index.document['key'][0][0]}_{index.document['key'][0][1]}"
            if index_name not in existing_indexes:
                await self.patients_collection.create_index(
                    index.document["key"], unique=index.document.get("unique", False)
                )
                logger.info(f"Created index: {index_name}")
            else:
                logger.info(f"Index '{index_name}' already exists, skipping creation.")

    async def get_patients_batch(
        self, skip: int, limit: int, query: dict
    ) -> List[Dict]:
        """Get a batch of patients from MongoDB"""
        try:
            cursor = self.patients_collection.find(query).skip(skip).limit(limit)
            return await cursor.to_list(length=limit)
        except Exception as e:
            logger.error(f"Error fetching patients batch: {e}")
            raise

    async def close(self):
        """Close the MongoDB connection"""
        self.client.close()


class EmbeddingManager:
    def __init__(self, embedding_service_url: str):
        self.embedding_service_url = embedding_service_url
        self.client = httpx.AsyncClient(
            timeout=60.0,
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=50),
            http2=True,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError)),
    )
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        try:
            response = await self.client.post(
                self.embedding_service_url,
                json={"texts": texts, "instruction": EMBEDDING_INSTRUCTION},
            )
            response.raise_for_status()
            return response.json()["embeddings"]
        except Exception as e:
            logger.error(f"Error getting embeddings: {e}")
            raise

    async def close(self):
        await self.client.aclose()


class ChromaManager:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.collection_name = "patient_notes"
        self.client = None
        self.collection = None

    def connect(self):
        self.client = chromadb.HttpClient(
            host=self.host, port=self.port, settings=Settings(allow_reset=True)
        )
        logger.info(f"Connected to ChromaDB at {self.host}:{self.port}")

    def get_or_create_collection(self):
        try:
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "Patient notes collection"},
            )
            return self.collection
        except Exception as e:
            logger.error(f"Error creating/getting collection: {e}")
            raise

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
            metadatas = [
                {
                    "patient_id": str(pid),
                    "note_type": nt,
                    "timestamp": ts,
                    "encounter_id": str(eid),
                    "note_text": txt,
                }
                for pid, nt, ts, eid, txt in zip(
                    patient_ids, note_types, timestamps, encounter_ids, note_texts
                )
            ]

            self.collection.add(
                ids=note_ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=note_texts,
            )
        except Exception as e:
            logger.error(f"Error inserting vectors into ChromaDB: {e}")
            raise

    def patient_exists(self, patient_id: int) -> bool:
        try:
            results = self.collection.get(
                where={"patient_id": str(patient_id)}, limit=1
            )
            return len(results["ids"]) > 0
        except Exception:
            return False

    def reset_collection(self):
        if self.client:
            self.client.reset()
            logger.info("Reset ChromaDB collections")


async def process_batch(
    patient_id: int,
    batch_notes: List[Dict],
    chroma_manager: ChromaManager,
    embedding_manager: EmbeddingManager,
) -> int:
    try:
        texts = [note["text"] for note in batch_notes]
        embeddings = await embedding_manager.get_embeddings(texts)

        note_ids = [note["note_id"] for note in batch_notes]
        note_types = [note["note_type"] for note in batch_notes]
        timestamps = [int(note["timestamp"].timestamp()) for note in batch_notes]
        encounter_ids = [note["encounter_id"] for note in batch_notes]
        patient_ids = [patient_id] * len(texts)

        chroma_manager.insert_vectors(
            patient_ids,
            note_ids,
            embeddings,
            texts,
            note_types,
            timestamps,
            encounter_ids,
        )
        return len(texts)
    except Exception as e:
        logger.error(f"Error processing batch for patient {patient_id}: {e}")
        return 0


async def process_patients(
    db_manager: DatabaseManager,
    chroma_manager: ChromaManager,
    embedding_manager: EmbeddingManager,
    recreate_collection: bool,
):
    query = {} if recreate_collection else {"processed": {"$ne": True}}
    total_patients = await db_manager.patients_collection.count_documents(query)
    total_patients = min(MAX_PATIENTS, total_patients)

    patients_processed = 0
    total_notes_processed = 0
    start_time = time.time()

    async for patient in tqdm(
        db_manager.patients_collection.find(query).limit(MAX_PATIENTS),
        total=total_patients,
        desc="Processing patients",
    ):
        patient_id = patient["patient_id"]
        notes = patient.get("notes", [])

        if not notes:
            continue

        for i in range(0, len(notes), BATCH_SIZE):
            batch_notes = notes[i : i + BATCH_SIZE]
            notes_processed = await process_batch(
                patient_id, batch_notes, chroma_manager, embedding_manager
            )
            total_notes_processed += notes_processed

        await db_manager.patients_collection.update_one(
            {"patient_id": patient_id}, {"$set": {"processed": True}}
        )

        patients_processed += 1

    end_time = time.time()
    logger.info(
        f"Processed {patients_processed} patients and {total_notes_processed} "
        f"notes in {end_time - start_time:.2f} seconds"
    )


async def main(recreate_collection: bool):
    db_manager = DatabaseManager(MONGO_URI, MONGO_DB_NAME)
    chroma_manager = ChromaManager(CHROMA_HOST, CHROMA_PORT)
    embedding_manager = EmbeddingManager(EMBEDDING_SERVICE_URL)

    try:
        chroma_manager.connect()
        if recreate_collection:
            chroma_manager.reset_collection()
        chroma_manager.get_or_create_collection()

        # Ensure indexes exist
        await db_manager.ensure_indexes()

        await process_patients(
            db_manager, chroma_manager, embedding_manager, recreate_collection
        )
    except Exception as e:
        logger.error(f"An error occurred during processing: {e}")
        raise
    finally:
        await embedding_manager.close()
        await db_manager.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process patient notes and create embeddings in ChromaDB."
    )
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Recreate the entire collection in ChromaDB",
    )
    args = parser.parse_args()

    asyncio.run(main(args.recreate))
