"""
This script loads medical notes from MIMIC-IV and eICU databases into a MongoDB database.
It uses the cycquery library for querying MIMIC-IV/eICU and motor for asynchronous MongoDB operations.
"""

import asyncio
import logging
import time
from typing import Any
from enum import Enum

import cycquery.ops as qo
import pandas as pd
from cycquery import MIMICIVQuerier
from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorDatabase,
    AsyncIOMotorCollection,
)
from pymongo import UpdateOne, IndexModel, ASCENDING
from pymongo.errors import BulkWriteError

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class DatabaseType(Enum):
    MIMICIV = "mimiciv"


class NoteType(Enum):
    DISCHARGE = "discharge"
    RADIOLOGY = "radiology"


def initialize_querier(db_type: DatabaseType) -> MIMICIVQuerier:
    common_params = {
        "dbms": "postgresql",
        "port": 5432,
        "host": "localhost",
        "user": "postgres",
        "password": "pwd",
    }
    if db_type == DatabaseType.MIMICIV:
        return MIMICIVQuerier(database="mimiciv-2.0", **common_params)
    else:
        raise ValueError(f"Unsupported database type: {db_type}")


def fetch_notes(
    querier: MIMICIVQuerier,
    note_type: NoteType,
    limit: int = 10000000,
) -> pd.DataFrame:
    if isinstance(querier, MIMICIVQuerier):
        ops = qo.Sequential(qo.DropEmpty("text"), qo.DropNulls("text"))
        if note_type == NoteType.DISCHARGE:
            return querier.mimiciv_note.discharge().ops(ops).run(limit=limit)
        elif note_type == NoteType.RADIOLOGY:
            return querier.mimiciv_note.radiology().ops(ops).run(limit=limit)

    raise ValueError(
        f"Unsupported combination of querier {type(querier)} and note type {note_type}"
    )


async def ensure_indexes(collection: AsyncIOMotorCollection[Any]) -> None:
    indexes = [
        IndexModel([("note_id", ASCENDING)], unique=True),
        IndexModel([("patient_id", ASCENDING)]),
        IndexModel([("encounter_id", ASCENDING)]),
    ]
    await collection.create_indexes(indexes)


async def load_medical_notes(
    mongo_uri: str, notes: pd.DataFrame, collection_name: str
) -> None:
    client: AsyncIOMotorClient[Any] = AsyncIOMotorClient(mongo_uri)
    db: AsyncIOMotorDatabase[Any] = client.clinical_notes
    collection: AsyncIOMotorCollection[Any] = db[collection_name]

    # Ensure indexes are in place
    await ensure_indexes(collection)

    batch_size = 10000
    total_notes = len(notes)
    notes_loaded = 0
    start_time = time.time()

    for i in range(0, total_notes, batch_size):
        batch = notes.iloc[i : i + batch_size]
        batch = batch.fillna(-1)
        operations = []
        for _, note in batch.iterrows():
            note_id = note.get("note_id")
            patient_id = note.get("subject_id")
            encounter_id = note.get("hadm_id")
            text = note.get("text")
            note_type = note.get("note_type") or ""

            if note_id and patient_id and encounter_id and text:
                operations.append(
                    UpdateOne(
                        {"note_id": note_id},
                        {
                            "$set": {
                                "patient_id": patient_id,
                                "encounter_id": encounter_id,
                                "text": text,
                                "note_type": note_type,
                            }
                        },
                        upsert=True,
                    )
                )
            else:
                logger.warning(
                    f"Skipping note due to missing required fields: {note_id}"
                )

        if operations:
            batch_start_time = time.time()
            try:
                result = await collection.bulk_write(operations, ordered=False)
                notes_loaded += result.upserted_count + result.modified_count
            except BulkWriteError as bwe:
                logger.error(f"Bulk write error: {bwe.details}")
                notes_loaded += bwe.details["nInserted"]
            batch_end_time = time.time()
            batch_duration = batch_end_time - batch_start_time
            logger.info(
                f"Batch {i//batch_size + 1}: Processed {len(operations)} notes in {batch_duration:.2f} seconds"
            )

        current_time = time.time()
        elapsed_time = current_time - start_time
        logger.info(
            f"Progress: {i + len(batch)} / {total_notes} notes. Elapsed time: {elapsed_time:.2f} seconds"
        )

    total_time = time.time() - start_time
    logger.info(
        f"Loaded {notes_loaded} medical notes into the {collection_name} collection in {total_time:.2f} seconds."
    )


async def main() -> None:
    mongo_uri = "mongodb://root:password@cyclops.cluster.local:27017"

    try:
        # MIMIC-IV processing
        mimiciv_querier = initialize_querier(DatabaseType.MIMICIV)
        mimiciv_discharge_notes = fetch_notes(mimiciv_querier, NoteType.DISCHARGE)
        await load_medical_notes(
            mongo_uri, mimiciv_discharge_notes, "mimiciv_discharge_notes"
        )
        mimiciv_radiology_notes = fetch_notes(mimiciv_querier, NoteType.RADIOLOGY)
        await load_medical_notes(
            mongo_uri, mimiciv_radiology_notes, "mimiciv_radiology_notes"
        )

    except Exception as e:
        logger.error(f"An error occurred during note loading: {str(e)}")


if __name__ == "__main__":
    asyncio.run(main())
