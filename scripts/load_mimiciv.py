"""
This script loads the MIMIC-IV notes and QA pairs into a MongoDB database.
"""

import os
import asyncio
import logging
import time
from typing import Any, List
from enum import Enum
import json
import gzip
import pandas as pd
from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorDatabase,
    AsyncIOMotorCollection,
)
from pymongo import UpdateOne, IndexModel, ASCENDING
from pymongo.errors import BulkWriteError
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
NOTE_PATH = "/Volumes/clinical-data/physionet.org/files/mimic-iv-note/2.2/note"


class NoteType(Enum):
    DISCHARGE = "discharge"
    RADIOLOGY = "radiology"


def read_notes(file_path: Path) -> pd.DataFrame:
    """Read notes from compressed CSV file."""
    logger.info(f"Reading notes from {file_path}")
    
    df = pd.read_csv(file_path, compression='gzip')
    
    # Drop rows with empty or null text
    df = df.dropna(subset=['text'])
    df = df[df['text'].str.strip() != '']
    
    return df


def handle_nas(df: pd.DataFrame) -> pd.DataFrame:
    return df.assign(
        note_id=df["note_id"].fillna(-1),
        subject_id=df["subject_id"].fillna(-1),
        hadm_id=df["hadm_id"].fillna(-1),
        category=df["category"].fillna("unknown"),
    )


class DatabaseManager:
    def __init__(self, mongo_uri: str, db_name: str):
        self.client: AsyncIOMotorClient[Any] = AsyncIOMotorClient(mongo_uri)
        self.db: AsyncIOMotorDatabase[Any] = self.client[db_name]
        self.patients_collection: AsyncIOMotorCollection[Any] = self.db.patients

    async def ensure_indexes(self) -> None:
        indexes = [
            IndexModel([("patient_id", ASCENDING)], unique=True),
            IndexModel([("notes.note_id", ASCENDING)]),
        ]
        await self.patients_collection.create_indexes(indexes)

    async def bulk_upsert_patients(self, operations: List[UpdateOne]) -> None:
        try:
            result = await self.patients_collection.bulk_write(
                operations, ordered=False
            )
            logger.info(
                f"Bulk upsert: {result.upserted_count} upserted, {result.modified_count} modified"
            )
        except BulkWriteError as bwe:
            logger.error(f"Bulk write error: {bwe.details}")
            logger.info(
                f"Bulk upsert: {bwe.details.get('nUpserted', 0)} upserted, {bwe.details.get('nModified', 0)} modified"
            )

    async def load_notes(self, notes: pd.DataFrame, note_type: NoteType) -> None:
        notes = handle_nas(notes)
        batch_size = 10000
        total_notes = len(notes)
        operations = []

        for i, note in notes.iterrows():
            operation = UpdateOne(
                {"patient_id": note["subject_id"]},
                {
                    "$push": {
                        "notes": {
                            "note_id": note["note_id"],
                            "encounter_id": note["hadm_id"],
                            "timestamp": note["charttime"],
                            "text": note["text"],
                            "note_type": note_type.value,
                        }
                    }
                },
                upsert=True,
            )
            operations.append(operation)

            if len(operations) >= batch_size or i == total_notes - 1:
                await self.bulk_upsert_patients(operations)
                operations = []
                logger.info(f"Processed {i+1}/{total_notes} notes")

    async def load_qa_pairs(self, file_path: str) -> None:
        batch_size = 1000
        operations = []
        total_pairs = 0

        with open(file_path, "r") as file:
            for i, line in enumerate(file):
                data = json.loads(line)
                qa_pair = {
                    "question": data["question"],
                    "answer": data[f"choice_{data['answer']}"],
                }
                operation = UpdateOne(
                    {"patient_id": data["patient_id"]},
                    {"$push": {"qa_pairs": qa_pair}},
                    upsert=True,
                )
                operations.append(operation)
                total_pairs += 1

                if len(operations) >= batch_size:
                    await self.bulk_upsert_patients(operations)
                    operations = []
                    logger.info(f"Processed {total_pairs} QA pairs")

        if operations:
            await self.bulk_upsert_patients(operations)
            logger.info(f"Processed {total_pairs} QA pairs")


async def main() -> None:
    # Configuration
    mongo_uri = "mongodb://root:password@localhost:27017"
    db_name = "clinical_data"
    discharge_file = os.path.join(NOTE_PATH, "discharge.csv.gz")
    radiology_file = os.path.join(NOTE_PATH, "radiology.csv.gz")
    db_manager = DatabaseManager(mongo_uri, db_name)
    start_time = time.time()

    await db_manager.ensure_indexes()

    try:
        logger.info("Loading MIMIC-IV discharge notes...")
        discharge_notes = read_notes(discharge_file)
        await db_manager.load_notes(discharge_notes, NoteType.DISCHARGE)

        logger.info("Loading MIMIC-IV radiology notes...")
        radiology_notes = read_notes(radiology_file)
        await db_manager.load_notes(radiology_notes, NoteType.RADIOLOGY)

        logger.info("Loading EHRNoteQA data...")
        ehrnoteqa_file_path = "/Volumes/clinical-data/physionet.org/files/ehr-notes-qa-llms/1.0.1/1.0.1/EHRNoteQA.jsonl"
        await db_manager.load_qa_pairs(ehrnoteqa_file_path)

    except Exception as e:
        logger.error(f"An error occurred during data loading: {str(e)}")
        raise

    end_time = time.time()
    logger.info(
        f"Data loading completed successfully in {end_time - start_time:.2f} seconds."
    )


if __name__ == "__main__":
    asyncio.run(main())
