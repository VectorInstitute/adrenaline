import asyncio
import logging
from typing import Any, List, Dict
from datetime import datetime
import argparse

import httpx
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import IndexModel, ASCENDING, TEXT
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, TaskID
from pydantic import BaseModel, Field

# Configure logging with rich
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger("rich")
console = Console()

# MongoDB configuration
MONGO_URI = "mongodb://root:password@cyclops.cluster.local:27017"
DB_NAME = "clinical_data"

# NER service configuration
NER_SERVICE_URL = "http://localhost:8003/extract_entities"
NER_SERVICE_TIMEOUT = 300  # 5 minutes

class Entity(BaseModel):
    pretty_name: str
    cui: str
    type_ids: List[str]
    types: List[str]
    source_value: str
    detected_name: str
    acc: float
    context_similarity: float
    start: int
    end: int
    icd10: List[Dict[str, str]]
    ontologies: List[str]
    snomed: List[str]
    id: int
    meta_anns: Dict[str, Any]

class NERResponse(BaseModel):
    note_id: str
    text: str
    entities: List[Entity]

class DatabaseManager:
    def __init__(self, mongo_uri: str, db_name: str):
        self.client: AsyncIOMotorClient = AsyncIOMotorClient(mongo_uri)
        self.db: AsyncIOMotorDatabase = self.client[db_name]
        self.patients_collection = self.db.patients

    async def ensure_indexes(self) -> None:
        indexes = [
            IndexModel([("patient_id", ASCENDING)], unique=True),
            IndexModel([("notes.note_id", ASCENDING)]),
            IndexModel([("notes.entities.pretty_name", TEXT)]),
            IndexModel([("notes.entities.cui", ASCENDING)]),
            IndexModel([("notes.entities.types", ASCENDING)]),
        ]
        await self.patients_collection.create_indexes(indexes)

    async def get_all_notes(self) -> List[Dict[str, Any]]:
        cursor = self.patients_collection.aggregate([
            {"$unwind": "$notes"},
            {"$project": {
                "patient_id": 1,
                "note_id": "$notes.note_id",
                "text": "$notes.text",
                "entities_exist": {"$ifNull": ["$notes.entities", False]}
            }}
        ])
        return await cursor.to_list(length=None)

    async def update_note_with_entities(self, patient_id: int, note_id: str, entities: List[Entity]) -> None:
        await self.patients_collection.update_one(
            {"patient_id": patient_id, "notes.note_id": note_id},
            {"$set": {"notes.$.entities": [entity.dict() for entity in entities]}}
        )

async def extract_entities(note_text: str, note_id: str) -> NERResponse:
    async with httpx.AsyncClient(timeout=httpx.Timeout(NER_SERVICE_TIMEOUT)) as client:
        try:
            response = await client.post(NER_SERVICE_URL, json={"text": note_text})
            response.raise_for_status()
            ner_response = response.json()
            ner_response["note_id"] = note_id
            return NERResponse(**ner_response)
        except httpx.HTTPStatusError as exc:
            logger.error(f"HTTP error occurred: {exc}")
            raise
        except httpx.RequestError as exc:
            logger.error(f"An error occurred while requesting {exc.request.url!r}.")
            raise
        except asyncio.TimeoutError:
            logger.error("Request to clinical NER service timed out")
            raise

async def process_notes(db_manager: DatabaseManager, progress: Progress, task: TaskID, recreate: bool) -> None:
    notes = await db_manager.get_all_notes()
    total_notes = len(notes)
    progress.update(task, total=total_notes)

    for i, note in enumerate(notes):
        if not recreate and note["entities_exist"]:
            logger.info(f"Skipping note {note['note_id']} as entities already exist")
            progress.update(task, advance=1, description=f"Skipped note {i+1}/{total_notes}")
            continue

        try:
            ner_response = await extract_entities(note["text"], note["note_id"])
            await db_manager.update_note_with_entities(note["patient_id"], note["note_id"], ner_response.entities)
            progress.update(task, advance=1, description=f"Processed note {i+1}/{total_notes}")
        except Exception as e:
            logger.error(f"Error processing note {note['note_id']}: {str(e)}")
            progress.update(task, advance=1, description=f"Error on note {i+1}/{total_notes}")

async def main(recreate: bool) -> None:
    start_time = datetime.now()
    console.print("[bold green]Starting NER processing and database update...[/bold green]")

    db_manager = DatabaseManager(MONGO_URI, DB_NAME)
    
    with Progress() as progress:
        index_task = progress.add_task("[cyan]Ensuring database indexes...", total=1)
        await db_manager.ensure_indexes()
        progress.update(index_task, advance=1)

        process_task = progress.add_task("[cyan]Processing notes...", total=None)
        await process_notes(db_manager, progress, process_task, recreate)

    end_time = datetime.now()
    duration = end_time - start_time
    console.print(f"[bold green]NER processing and database update completed in {duration}[/bold green]")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process clinical notes with NER")
    parser.add_argument("--recreate", action="store_true", help="Recreate entities for all notes")
    args = parser.parse_args()

    asyncio.run(main(args.recreate))