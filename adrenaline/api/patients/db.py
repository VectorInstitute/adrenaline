"""Database module for medical notes."""

import logging
import os
from typing import Any

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MONGO_USERNAME = os.getenv("MONGO_USERNAME")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
MONGO_HOST = os.getenv("MONGO_HOST", "mongodb-dev")
MONGO_PORT = os.getenv("MONGO_PORT", "27017")
MONGO_URL = f"mongodb://{MONGO_USERNAME}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}"
DB_NAME = "clinical_data"


async def get_database() -> AsyncIOMotorDatabase[Any]:
    """
    Create and return a database client.

    Returns
    -------
    AsyncIOMotorClient
        An asynchronous MongoDB client.

    Raises
    ------
    ConnectionError
        If unable to connect to the database.
    """
    client: AsyncIOMotorClient[Any] = AsyncIOMotorClient(MONGO_URL)
    try:
        await client.admin.command("ismaster")
        db = client[DB_NAME]
        logger.info(f"Successfully connected to the database: {DB_NAME}")
        return db
    except Exception as e:
        logger.error(f"Unable to connect to the database: {str(e)}")
        raise ConnectionError(f"Database connection failed: {str(e)}") from e


async def check_database_connection() -> None:
    """
    Check the database connection on startup.

    Raises
    ------
    ConnectionError
        If unable to connect to the database.
    """
    client: AsyncIOMotorClient[Any] = AsyncIOMotorClient(MONGO_URL)
    try:
        await client.admin.command("ismaster")
        db = client[DB_NAME]
        collections = await db.list_collection_names()
        logger.info(f"Available collections: {collections}")
        logger.info("Database connection check passed")
    except Exception as e:
        logger.error(f"Database connection check failed: {str(e)}")
        raise ConnectionError(f"Database connection check failed: {str(e)}") from e
    finally:
        client.close()
