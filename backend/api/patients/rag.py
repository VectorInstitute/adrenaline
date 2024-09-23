"""RAG (Retrieval-Augmented Generation) API for patient data."""

import asyncio
from typing import Any, Dict, List

import httpx
from pymilvus import Collection, connections, utility


COLLECTION_NAME = "patient_notes"


class EmbeddingManager:
    """A class to manage embeddings."""

    def __init__(self, embedding_service_url: str):
        """Initialize the EmbeddingManager.

        Parameters
        ----------
        embedding_service_url : str
            The URL of the embedding service.
        """
        self.embedding_service_url = embedding_service_url
        self.client = httpx.AsyncClient(timeout=60.0)

    async def get_embedding(self, text: str) -> List[float]:
        """Get the embedding for a given text.

        Parameters
        ----------
        text : str
            The text to embed.

        Returns
        -------
        List[float]
            The embedding for the given text.
        """
        response = await self.client.post(
            self.embedding_service_url,
            json={"texts": [text], "instruction": "Represent the query for retrieval:"},
        )
        response.raise_for_status()
        return response.json()["embeddings"][0]

    async def close(self):
        """Close the client."""
        await self.client.aclose()


class MilvusManager:
    """A class to manage Milvus."""

    def __init__(self, host: str, port: int):
        """Initialize the MilvusManager.

        Parameters
        ----------
        host : str
            The host of the Milvus server.
        port : int
            The port of the Milvus server.
        """
        self.host = host
        self.port = port
        self.collection_name = COLLECTION_NAME
        self.collection = None

    def connect(self):
        """Connect to the Milvus server.

        Raises
        ------
        ValueError
            If the collection does not exist in Milvus.
        """
        connections.connect(host=self.host, port=self.port)
        if not utility.has_collection(self.collection_name):
            raise ValueError(
                f"Collection {self.collection_name} does not exist in Milvus"
            )

    def get_collection(self) -> Collection:
        """Get the collection from Milvus.

        Returns
        -------
        Collection
            The collection from Milvus.
        """
        if self.collection is None:
            self.collection = Collection(self.collection_name)
        return self.collection

    def load_collection(self):
        """Load the collection from Milvus.

        Raises
        ------
        ValueError
            If the collection is not loaded.
        """
        collection = self.get_collection()
        collection.load()

    async def ensure_collection_loaded(self):
        """Ensure the collection is loaded from Milvus.

        Raises
        ------
        ValueError
            If the collection is not loaded.
        """
        collection = self.get_collection()
        # The load() method is synchronous and blocks until the collection is loaded
        await asyncio.to_thread(collection.load)

    async def search(
        self, query_vector: List[float], top_k: int
    ) -> List[Dict[str, Any]]:
        """Search for the nearest neighbors in Milvus.

        Parameters
        ----------
        query_vector : List[float]
            The query vector.
        top_k : int
            The number of nearest neighbors to return.

        Returns
        -------
        List[Dict[str, Any]]
            The nearest neighbors.
        """
        await self.ensure_collection_loaded()
        collection = self.get_collection()
        search_params = {"metric_type": "L2", "params": {"nprobe": 10}}
        results = collection.search(
            data=[query_vector],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            output_fields=["patient_id", "note_id"],
        )
        return [
            {
                "patient_id": hit.entity.get("patient_id"),
                "note_id": hit.entity.get("note_id"),
                "distance": hit.distance,
            }
            for hit in results[0]
        ]
