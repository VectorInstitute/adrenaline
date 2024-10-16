import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from rich.console import Console
from rich.table import Table

console = Console()


async def get_database_statistics():
    # Connect to MongoDB
    client = AsyncIOMotorClient("mongodb://root:password@localhost:27017")
    db = client.clinical_data
    collection = db.umls_concepts

    # Get total number of documents
    total_docs = await collection.count_documents({})

    # Count documents with missing fields
    missing_definitions = await collection.count_documents(
        {"definitions": {"$size": 0}}
    )
    missing_preferred_term = await collection.count_documents({"preferred_term": ""})
    missing_semantic_types = await collection.count_documents(
        {"semantic_types": {"$size": 0}}
    )
    missing_synonyms = await collection.count_documents({"synonyms": {"$size": 0}})

    # Calculate percentages
    def percentage(count):
        return f"{count} ({count/total_docs*100:.2f}%)"

    # Create a table for output
    table = Table(title="UMLS Database Statistics")
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Count", style="magenta")
    table.add_column("Percentage", style="green")

    table.add_row("Total Documents", str(total_docs), "100%")
    table.add_row(
        "Missing Definitions", str(missing_definitions), percentage(missing_definitions)
    )
    table.add_row(
        "Missing Preferred Term",
        str(missing_preferred_term),
        percentage(missing_preferred_term),
    )
    table.add_row(
        "Missing Semantic Types",
        str(missing_semantic_types),
        percentage(missing_semantic_types),
    )
    table.add_row(
        "Missing Synonyms", str(missing_synonyms), percentage(missing_synonyms)
    )

    console.print(table)


async def main():
    await get_database_statistics()


if __name__ == "__main__":
    asyncio.run(main())
