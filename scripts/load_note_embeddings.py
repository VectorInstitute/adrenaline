import asyncio
import json
import traceback
import logging
import re
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
import spacy
from spacy.language import Language
from spacy.tokens import Doc
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
BATCH_SIZE = 1
MAX_PATIENTS = 2
EMBEDDING_INSTRUCTION = (
    "Represent the clinical note for retrieval, to provide context for a search query."
)
VECTOR_DIM = 4096

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load spaCy model
try:
    nlp = spacy.load("en_core_web_md")
except OSError:
    logger.error("Required spaCy model 'en_core_web_md' is not installed.")
    logger.info("Attempting to download 'en_core_web_md'...")
    spacy.cli.download("en_core_web_md")
    logger.info("Download completed. Retrying model load.")
    nlp = spacy.load("en_core_web_md")


@Language.component("split_on_newlines")
def split_on_newlines(doc: Doc) -> Doc:
    text = doc.text
    lines = [line for line in text.split("\n") if line.strip()]
    words = []
    spaces = []
    for i, line in enumerate(lines):
        line_words = line.split()
        words.extend(line_words)
        spaces.extend([True] * (len(line_words) - 1) + [False])
        if i < len(lines) - 1:
            words.append("\n")
            spaces.append(True)
    return Doc(doc.vocab, words=words, spaces=spaces)


nlp.add_pipe("split_on_newlines", before="parser")


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

    def create_collection(self, dim: int):
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="patient_id", dtype=DataType.INT64),
            FieldSchema(name="note_id", dtype=DataType.VARCHAR, max_length=64),
            FieldSchema(name="chunk_id", dtype=DataType.INT64),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
            FieldSchema(name="chunk_text", dtype=DataType.VARCHAR, max_length=65535),
        ]
        schema = CollectionSchema(fields, "Patient notes collection")
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
        patient_ids: List[int],
        note_ids: List[str],
        chunk_ids: List[int],
        embeddings: List[List[float]],
        chunk_texts: List[str],
    ):
        try:
            entities = [
                {
                    "patient_id": pid,
                    "note_id": nid,
                    "chunk_id": cid,
                    "embedding": emb,
                    "chunk_text": txt,
                }
                for pid, nid, cid, emb, txt in zip(
                    patient_ids, note_ids, chunk_ids, embeddings, chunk_texts
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


def chunk_discharge_summary(note_text: str) -> List[str]:
    note_text = re.sub(r"\n\s*\n", "\n", note_text.strip())
    section_headers = [
        "Name:",
        "Admission Date:",
        "Date of Birth:",
        "Service:",
        "Allergies:",
        "Attending:",
        "Chief Complaint:",
        "Major Surgical or Invasive Procedure:",
        "History of Present Illness:",
        "Past Medical History:",
        "Social History:",
        "Family History:",
        "Physical Exam:",
        "Pertinent Results:",
        "Brief Hospital Course:",
        "Medications on Admission:",
        "Discharge Medications:",
        "Discharge Disposition:",
        "Discharge Diagnosis:",
        "Discharge Condition:",
        "Discharge Instructions:",
        "Followup Instructions:",
        "Physical Therapy:",
        "Treatments Frequency:",
    ]

    def is_section_header(line: str) -> bool:
        return any(line.strip().startswith(header) for header in section_headers)

    lines = note_text.split("\n")
    chunks = []
    current_chunk = []
    current_header = ""

    for line in lines:
        if is_section_header(line):
            if current_chunk:
                chunks.append((current_header, "\n".join(current_chunk)))
            current_header = line.strip()
            current_chunk = [line]
        else:
            current_chunk.append(line)

    if current_chunk:
        chunks.append((current_header, "\n".join(current_chunk)))

    combined_chunks = []
    for i, (header, content) in enumerate(chunks):
        if i > 0 and len(content.split()) < 20:
            prev_header, prev_content = combined_chunks[-1]
            combined_chunks[-1] = (
                prev_header,
                f"{prev_content}\n\n{header}\n{content}",
            )
        else:
            combined_chunks.append((header, content))

    formatted_chunks = [
        f"{header}\n{content}" for header, content in combined_chunks if content.strip()
    ]

    logger.info(f"Number of chunks: {len(formatted_chunks)}")
    # for i, chunk in enumerate(formatted_chunks):
    #     logger.info(f"Chunk {i + 1} (first 100 characters): {chunk[:100]}...")

    return formatted_chunks


async def process_batch(
    patient_id: int,
    batch_notes: List[Dict],
    milvus_manager: MilvusManager,
    embedding_manager: EmbeddingManager,
) -> int:
    try:
        all_texts = []
        all_note_ids = []
        all_chunk_ids = []

        for note in batch_notes:
            if note["note_type"] == "DS":
                chunks = chunk_discharge_summary(note["text"])
                for i, chunk in enumerate(chunks):
                    all_texts.append(chunk)
                    all_note_ids.append(note["note_id"])
                    all_chunk_ids.append(i)
            else:
                all_texts.append(note["text"])
                all_note_ids.append(note["note_id"])
                all_chunk_ids.append(0)

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
            f"Sample data - Patient ID: {patient_ids[0]}, Note ID: {all_note_ids[0]}, Chunk ID: {all_chunk_ids[0]}"
        )

        milvus_manager.insert_vectors(
            patient_ids, all_note_ids, all_chunk_ids, embeddings, all_texts
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
