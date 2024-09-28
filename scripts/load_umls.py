"""Load UMLS data into MongoDB for RAG system."""

import os
import asyncio
from typing import Any, Dict, List
from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorDatabase,
    AsyncIOMotorCollection,
)
from pymongo import UpdateOne, IndexModel, ASCENDING
from pymongo.errors import BulkWriteError
from rich.console import Console
from rich.progress import Progress, TaskID
from rich.logging import RichHandler
import logging

# Configure logging with rich
logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)

logger = logging.getLogger("rich")
console = Console()

DATA_PATH = "/mnt/data/clinical_datasets/umls/2024AA/META"
BATCH_SIZE = 1000
ENGLISH_SOURCES = {"NCI", "MSH", "HPO"}  # English sources


class UMLSDatabaseManager:
    def __init__(self, mongo_uri: str, db_name: str):
        self.client: AsyncIOMotorClient[Any] = AsyncIOMotorClient(mongo_uri)
        self.db: AsyncIOMotorDatabase[Any] = self.client[db_name]
        self.umls_collection: AsyncIOMotorCollection[Any] = self.db.umls_concepts

    async def ensure_indexes(self) -> None:
        indexes = [
            IndexModel([("cui", ASCENDING)], unique=True),
            IndexModel([("preferred_term", ASCENDING)]),
            IndexModel([("synonyms", ASCENDING)]),
            IndexModel([("semantic_types", ASCENDING)]),
        ]
        await self.umls_collection.create_indexes(indexes)

    async def bulk_upsert_concepts(self, operations: List[UpdateOne]) -> None:
        try:
            result = await self.umls_collection.bulk_write(operations, ordered=False)
            logger.info(
                f"Bulk upsert: {result.upserted_count} upserted, {result.modified_count} modified"
            )
        except BulkWriteError as bwe:
            logger.error(f"Bulk write error: {bwe.details}")
            logger.info(
                f"Bulk upsert: {bwe.details.get('nUpserted', 0)} upserted, {bwe.details.get('nModified', 0)} modified"
            )


def read_mrconso(
    file_path: str, progress: Progress, task: TaskID
) -> Dict[str, Dict[str, Any]]:
    concepts = {}
    total_lines = sum(1 for _ in open(file_path, "r", encoding="utf-8"))
    progress.update(task, total=total_lines)

    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            parts = line.strip().split("|")
            if len(parts) != 19:
                logger.warning(
                    f"Skipping line with unexpected number of fields: {len(parts)}"
                )
                continue

            cui, lat, ts, _, _, _, ispref, _, _, _, _, sab, tty, _, str_, _, _, _, _ = (
                parts
            )

            if cui not in concepts:
                concepts[cui] = {
                    "cui": cui,
                    "preferred_term": "",
                    "synonyms": set(),
                    "definitions": [],
                    "semantic_types": set(),
                    "relationships": [],
                }

            if lat == "ENG" and ts == "P" and sab in ENGLISH_SOURCES:
                if tty == "PF" and not concepts[cui]["preferred_term"]:
                    concepts[cui]["preferred_term"] = str_
                concepts[cui]["synonyms"].add(str_)

            progress.update(task, advance=1)

    return concepts


def read_mrdef(
    file_path: str,
    concepts: Dict[str, Dict[str, Any]],
    progress: Progress,
    task: TaskID,
) -> None:
    total_lines = sum(1 for _ in open(file_path, "r", encoding="utf-8"))
    progress.update(task, total=total_lines)

    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            parts = line.strip().split("|")
            if len(parts) < 7:
                logger.warning(f"Skipping line with insufficient fields: {len(parts)}")
                continue

            cui, _, _, _, sab, def_, suppress = parts[:7]

            if cui in concepts and suppress != "Y" and sab in ENGLISH_SOURCES:
                concepts[cui]["definitions"].append({"definition": def_, "source": sab})

            progress.update(task, advance=1)


def read_mrsty(
    file_path: str,
    concepts: Dict[str, Dict[str, Any]],
    progress: Progress,
    task: TaskID,
) -> None:
    total_lines = sum(1 for _ in open(file_path, "r", encoding="utf-8"))
    progress.update(task, total=total_lines)

    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            parts = line.strip().split("|")
            if len(parts) != 7:
                logger.warning(
                    f"Skipping line with unexpected number of fields: {len(parts)}"
                )
                continue

            cui, tui, stn, sty, atui, cvf, _ = parts
            if cui in concepts:
                concepts[cui]["semantic_types"].add(sty)
            progress.update(task, advance=1)


def read_mrrel(
    file_path: str,
    concepts: Dict[str, Dict[str, Any]],
    progress: Progress,
    task: TaskID,
) -> None:
    total_lines = sum(1 for _ in open(file_path, "r", encoding="utf-8"))
    progress.update(task, total=total_lines)

    with open(file_path, "r", encoding="utf-8") as file:
        for line in file:
            parts = line.strip().split("|")
            if len(parts) < 16:
                logger.warning(f"Skipping line with insufficient fields: {len(parts)}")
                continue

            (
                cui1,
                aui1,
                stype1,
                rel,
                cui2,
                aui2,
                stype2,
                rela,
                rui,
                srui,
                sab,
                sl,
                rg,
                dir,
                suppress,
                cvf,
            ) = parts[:16]

            if cui1 in concepts and suppress != "Y":
                concepts[cui1]["relationships"].append(
                    {
                        "related_cui": cui2,
                        "relationship_type": rel,
                        "relationship_attribute": rela,
                        "source": sab,
                    }
                )

            progress.update(task, advance=1)


def process_concepts(concepts: Dict[str, Dict[str, Any]]) -> None:
    for concept in concepts.values():
        concept["synonyms"] = list(concept["synonyms"])
        concept["semantic_types"] = list(concept["semantic_types"])

        # Sort definitions by source preference
        concept["definitions"].sort(
            key=lambda x: x["source"] in ENGLISH_SOURCES, reverse=True
        )

        # Create a structured combined text field without codes and relationships
        combined_text = f"PREFERRED TERM: {concept['preferred_term']}\n"
        combined_text += "DEFINITIONS:\n"
        for def_ in concept["definitions"]:
            combined_text += f"- {def_['definition']} (Source: {def_['source']})\n"
        combined_text += "SYNONYMS:\n"
        combined_text += f"- {', '.join(concept['synonyms'])}\n"
        combined_text += "SEMANTIC TYPES:\n"
        combined_text += f"- {', '.join(concept['semantic_types'])}\n"
        concept["combined_text"] = combined_text.strip().lower()


async def process_umls_data(
    db_manager: UMLSDatabaseManager,
    concepts: Dict[str, Dict[str, Any]],
    progress: Progress,
    task: TaskID,
) -> None:
    operations = []
    total_concepts = len(concepts)
    progress.update(task, total=total_concepts)

    for i, (cui, concept) in enumerate(concepts.items(), 1):
        operation = UpdateOne({"cui": cui}, {"$set": concept}, upsert=True)
        operations.append(operation)

        if len(operations) >= BATCH_SIZE or i == total_concepts:
            await db_manager.bulk_upsert_concepts(operations)
            operations = []
            progress.update(task, advance=BATCH_SIZE)


async def main() -> None:
    mongo_uri = "mongodb://root:password@localhost:27017"
    db_name = "clinical_data"
    db_manager = UMLSDatabaseManager(mongo_uri, db_name)

    await db_manager.ensure_indexes()

    with Progress() as progress:
        try:
            mrconso_task = progress.add_task("[cyan]Reading MRCONSO.RRF...", total=None)
            concepts = read_mrconso(
                os.path.join(DATA_PATH, "MRCONSO.RRF"), progress, mrconso_task
            )
            progress.remove_task(mrconso_task)

            mrdef_task = progress.add_task("[magenta]Reading MRDEF.RRF...", total=None)
            read_mrdef(
                os.path.join(DATA_PATH, "MRDEF.RRF"), concepts, progress, mrdef_task
            )
            progress.remove_task(mrdef_task)

            mrsty_task = progress.add_task("[yellow]Reading MRSTY.RRF...", total=None)
            read_mrsty(
                os.path.join(DATA_PATH, "MRSTY.RRF"), concepts, progress, mrsty_task
            )
            progress.remove_task(mrsty_task)

            mrrel_task = progress.add_task("[blue]Reading MRREL.RRF...", total=None)
            read_mrrel(
                os.path.join(DATA_PATH, "MRREL.RRF"), concepts, progress, mrrel_task
            )
            progress.remove_task(mrrel_task)

            process_concepts(concepts)

            upload_task = progress.add_task(
                "[green]Processing and uploading UMLS data...", total=None
            )
            await process_umls_data(db_manager, concepts, progress, upload_task)
            progress.remove_task(upload_task)

        except Exception:
            logger.exception("An error occurred during data loading")

    console.print("[bold green]UMLS data loading completed successfully.[/bold green]")


if __name__ == "__main__":
    asyncio.run(main())
