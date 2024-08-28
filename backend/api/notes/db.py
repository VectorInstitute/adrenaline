"""Database module for medical notes."""

import logging
import os
from typing import AsyncGenerator

from motor.motor_asyncio import AsyncIOMotorClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MONGO_USERNAME = os.getenv("MONGO_USERNAME")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD")
MONGO_HOST = os.getenv("MONGO_HOST", "mongodb")
MONGO_PORT = os.getenv("MONGO_PORT", "27017")
MONGO_URL = f"mongodb://{MONGO_USERNAME}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}"
DB_NAME = "medical_db"

async def get_database() -> AsyncGenerator[AsyncIOMotorClient, None]:
    """
    Create and yield a database client.

    Yields
    ------
    AsyncIOMotorClient
        An asynchronous MongoDB client.

    Raises
    ------
    ConnectionError
        If unable to connect to the database.
    """
    client = AsyncIOMotorClient(MONGO_URL)
    try:
        # Check the connection
        await client.admin.command("ismaster")
        logger.info("Successfully connected to the database")
        yield client
    except Exception as e:
        logger.error(f"Unable to connect to the database: {str(e)}")
        raise ConnectionError(f"Database connection failed: {str(e)}")
    finally:
        client.close()
        logger.info("Database connection closed")

async def check_database_connection():
    """
    Check the database connection on startup.

    Raises
    ------
    ConnectionError
        If unable to connect to the database.
    """
    client = AsyncIOMotorClient(MONGO_URL)
    try:
        await client.admin.command("ismaster")
        db = client[DB_NAME]
        collections = await db.list_collection_names()
        if "medical_notes" in collections:
            logger.info(
                f"Database connection check passed. Found 'medical_notes' collection in {DB_NAME}"
            )
        else:
            logger.warning(f"'medical_notes' collection not found in {DB_NAME}")
        logger.info("Database connection check passed")
    except Exception as e:
        logger.error(f"Database connection check failed: {str(e)}")
        raise ConnectionError(f"Database connection check failed: {str(e)}")
    finally:
        client.close()