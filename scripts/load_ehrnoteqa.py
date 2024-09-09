"""
This script loads EHRNoteQA data into a MongoDB database.
"""

import asyncio
import json
import logging
from typing import Any, Dict, List

from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorDatabase,
    AsyncIOMotorCollection,
)
from pymongo import IndexModel, ASCENDING
from pymongo.errors import BulkWriteError

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def ensure_indexes(collection: AsyncIOMotorCollection[Any]) -> None:
    indexes = [
        IndexModel([("patient_id", ASCENDING)], unique=True),
    ]
    await collection.create_indexes(indexes)


async def load_ehrnoteqa_data(
    file_path: str, mongo_uri: str, db_name: str, collection_name: str
) -> None:
    client: AsyncIOMotorClient[Any] = AsyncIOMotorClient(mongo_uri)
    db: AsyncIOMotorDatabase[Any] = client[db_name]
    collection: AsyncIOMotorCollection[Any] = db[collection_name]

    # Ensure indexes are in place
    await ensure_indexes(collection)

    batch_size = 1000
    operations: List[Dict[str, Any]] = []
    total_documents = 0
    documents_loaded = 0

    try:
        with open(file_path, "r") as file:
            for line in file:
                total_documents += 1
                data = json.loads(line)

                document = {
                    "patient_id": data["patient_id"],
                    "question": data["question"],
                    "answer": data[f"choice_{data['answer']}"],
                }

                operations.append(document)

                if len(operations) >= batch_size:
                    try:
                        result = await collection.insert_many(operations)
                        documents_loaded += len(result.inserted_ids)
                    except BulkWriteError as bwe:
                        logger.error(f"Bulk write error: {bwe.details}")
                        documents_loaded += bwe.details["nInserted"]

                    logger.info(
                        f"Processed {documents_loaded}/{total_documents} documents"
                    )
                    operations = []

        # Insert any remaining documents
        if operations:
            try:
                result = await collection.insert_many(operations)
                documents_loaded += len(result.inserted_ids)
            except BulkWriteError as bwe:
                logger.error(f"Bulk write error: {bwe.details}")
                documents_loaded += bwe.details["nInserted"]

        logger.info(
            f"Finished loading {documents_loaded}/{total_documents} documents into the {collection_name} collection."
        )

    except Exception as e:
        logger.error(f"An error occurred during data loading: {str(e)}")


async def main() -> None:
    mongo_uri = "mongodb://root:password@localhost:27017"
    db_name = "question_answers"
    collection_name = "ehrnoteqa"
    file_path = "/mnt/data/clinical_datasets/physionet.org/files/ehr-notes-qa-llms/1.0.1/1.0.1/EHRNoteQA.jsonl"

    await load_ehrnoteqa_data(file_path, mongo_uri, db_name, collection_name)


if __name__ == "__main__":
    asyncio.run(main())
