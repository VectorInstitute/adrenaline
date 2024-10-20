"""RAG for patients."""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List

import httpx
from pymilvus import Collection, connections, utility


COLLECTION_NAME = "patient_notes"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmbeddingManager:
    """Manager for embedding service."""

    def __init__(self, embedding_service_url: str):
        """Initialize the embedding manager."""
        self.embedding_service_url = embedding_service_url
        self.client = httpx.AsyncClient(timeout=60.0)

    async def get_embedding(self, text: str) -> List[float]:
        """Get the embedding for a given text."""
        response = await self.client.post(
            self.embedding_service_url,
            json={"texts": [text], "instruction": "Represent the query for retrieval:"},
        )
        response.raise_for_status()
        return response.json()["embeddings"][0]

    async def close(self):
        """Close the embedding manager."""
        await self.client.aclose()


class MilvusManager:
    """Manager for Milvus."""

    def __init__(self, host: str, port: int):
        """Initialize the Milvus manager."""
        self.host = host
        self.port = port
        self.collection_name = COLLECTION_NAME
        self.collection = None

    def connect(self):
        """Connect to Milvus."""
        connections.connect(host=self.host, port=self.port)
        if not utility.has_collection(self.collection_name):
            raise ValueError(
                f"Collection {self.collection_name} does not exist in Milvus"
            )

    def get_collection(self) -> Collection:
        """Get the collection."""
        if self.collection is None:
            self.collection = Collection(self.collection_name)
        return self.collection

    def load_collection(self):
        """Load the collection."""
        collection = self.get_collection()
        collection.load()

    async def ensure_collection_loaded(self):
        """Ensure the collection is loaded."""
        collection = self.get_collection()
        await asyncio.to_thread(collection.load)

    async def search(
        self,
        query_vector: List[float],
        patient_id: int,
        top_k: int,
        time_range: Dict[str, int] = None,
    ) -> List[Dict[str, Any]]:
        """Search for the nearest neighbors."""
        await self.ensure_collection_loaded()
        collection = self.get_collection()
        search_params = {"metric_type": "IP", "params": {"nprobe": 16, "ef": 64}}

        expr = f"patient_id == {patient_id}"
        if time_range:
            expr += f" && timestamp >= {time_range['start']} && timestamp <= {time_range['end']}"

        results = collection.search(
            data=[query_vector],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            expr=expr,
            output_fields=[
                "patient_id",
                "note_id",
                "note_text",
                "note_type",
                "timestamp",
                "encounter_id",
            ],
        )

        filtered_results = [
            {
                "patient_id": hit.entity.get("patient_id"),
                "note_id": hit.entity.get("note_id"),
                "note_text": hit.entity.get("note_text"),
                "note_type": hit.entity.get("note_type"),
                "timestamp": hit.entity.get("timestamp"),
                "encounter_id": hit.entity.get("encounter_id"),
                "distance": hit.distance,
            }
            for hit in results[0]
        ]

        # Sort by distance in descending order (higher IP score means more similar)
        filtered_results.sort(key=lambda x: x["distance"], reverse=True)

        return filtered_results


async def retrieve_relevant_notes(
    user_query: str,
    embedding_manager: EmbeddingManager,
    milvus_manager: MilvusManager,
    patient_id: int,
    top_k: int = 5,
    time_range: Dict[str, int] = None,
) -> List[Dict[str, Any]]:
    """Retrieve the relevant notes directly from Milvus."""
    query_embedding = await embedding_manager.get_embedding(user_query)
    search_results = await milvus_manager.search(
        query_embedding, patient_id, top_k, time_range
    )
    for result in search_results:
        print(result["note_type"])
    logger.info(f"Retrieved {len(search_results)} relevant notes")
    for i, result in enumerate(search_results):
        logger.info(
            f"Result {i+1}: Distance = {result['distance']}, Timestamp = {datetime.fromtimestamp(result['timestamp'])}"
        )
    return search_results
