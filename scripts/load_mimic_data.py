import asyncio

import cycquery.ops as qo
from cycquery import MIMICIVQuerier
from motor.motor_asyncio import AsyncIOMotorClient


querier = MIMICIVQuerier(
    dbms="postgresql",
    port=5432,
    host="localhost",
    database="mimiciv-2.0",
    user="postgres",
    password="pwd",
)
# List all schemas.
querier.list_schemas()
querier.list_tables("mimiciv_note")
ops = qo.Sequential(qo.DropEmpty("text"), qo.DropNulls("text"))
notes = querier.mimiciv_note.discharge().ops(ops).run(limit=100)


async def load_medical_notes(mongo_uri):
    client = AsyncIOMotorClient(mongo_uri)
    db = client.medical_db
    collection = db.medical_notes

    for _, note in notes.iterrows():
        await collection.update_one(
            {"note_id": note["note_id"]},
            {
                "$set": {
                    "subject_id": note["subject_id"],
                    "hadm_id": note["hadm_id"],
                    "text": note["text"],
                }
            },
            upsert=True,
        )

    print(f"Loaded {len(notes)} medical notes into the database.")


async def main():
    mongo_uri = "mongodb://root:password@cyclops.cluster.local:27017"
    await load_medical_notes(mongo_uri)


if __name__ == "__main__":
    asyncio.run(main())
