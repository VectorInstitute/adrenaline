"""RAG for patients and cohort search."""

import asyncio
import logging
from typing import Any, Dict, List, Tuple

import httpx
from pymilvus import Collection, connections, utility


COLLECTION_NAME = "patient_notes"
MILVUS_HOST = "localhost"
MILVUS_PORT = 19530
EMBEDDING_SERVICE_URL = "http://localhost:8004/embeddings"
NER_SERVICE_URL = "http://clinical-ner-service-dev:8000/extract_entities"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmbeddingManager:
    """Manager for embedding service."""

    def __init__(self, embedding_service_url: str):
        self.embedding_service_url = embedding_service_url
        self.client = httpx.AsyncClient(timeout=60.0)

    async def get_embedding(self, text: str) -> List[float]:
        """Get the embedding for a text."""
        response = await self.client.post(
            self.embedding_service_url,
            json={"texts": [text], "instruction": "Represent the query for retrieval:"},
        )
        response.raise_for_status()
        return response.json()["embeddings"][0]

    async def close(self):
        """Close the client."""
        await self.client.aclose()


class NERManager:
    """Manager for NER service."""

    def __init__(self, ner_service_url: str):
        """Initialize the NER manager."""
        self.ner_service_url = ner_service_url
        self.client = httpx.AsyncClient(timeout=300.0)

    async def extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract entities from a text."""
        response = await self.client.post(
            self.ner_service_url,
            json={"text": text},
        )
        response.raise_for_status()
        return response.json()

    async def close(self):
        """Close the client."""
        await self.client.aclose()


class MilvusManager:
    """Manager for Milvus operations."""

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

    async def ensure_collection_loaded(self):
        """Ensure the collection is loaded."""
        collection = self.get_collection()
        await asyncio.to_thread(collection.load)

    async def search(
        self,
        query_vector: List[float],
        patient_id: int = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Retrieve the relevant notes directly from Milvus."""
        await self.ensure_collection_loaded()
        collection = self.get_collection()
        search_params = {
            "metric_type": "IP",
            "params": {"nprobe": 16, "ef": 64},
        }

        expr = f"patient_id == {patient_id}" if patient_id else None

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

        filtered_results.sort(key=lambda x: x["distance"], reverse=True)
        return filtered_results

    async def cohort_search(
        self, query_vector: List[float], top_k: int = 2
    ) -> List[Tuple[int, Dict[str, Any]]]:
        """Retrieve the cohort search results from Milvus."""
        search_results = await self.search(query_vector, top_k=top_k)

        # Group results by patient_id and keep only the top result for each patient
        patient_results = {}
        for result in search_results:
            patient_id = result["patient_id"]
            if (
                patient_id not in patient_results
                or result["distance"] > patient_results[patient_id]["distance"]
            ):
                patient_results[patient_id] = result

        cohort_results = list(patient_results.items())
        cohort_results.sort(key=lambda x: x[1]["distance"], reverse=True)
        return cohort_results[:top_k]


class RAGManager:
    """Manager for RAG operations."""

    def __init__(
        self,
        embedding_manager: EmbeddingManager,
        milvus_manager: MilvusManager,
        ner_manager: NERManager,
    ):
        """Initialize the RAG manager."""
        self.embedding_manager = embedding_manager
        self.milvus_manager = milvus_manager
        self.ner_manager = ner_manager

    async def retrieve_relevant_notes(
        self,
        user_query: str,
        patient_id: int,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Retrieve the relevant notes directly from Milvus."""
        query_embedding = await self.embedding_manager.get_embedding(user_query)
        search_results = await self.milvus_manager.search(
            query_embedding, patient_id, top_k
        )

        # Extract entities from the query
        query_entities = await self.ner_manager.extract_entities(user_query)

        # Extract entities from the retrieved notes and filter based on matched entities
        filtered_results = []
        for result in search_results:
            note_entities = await self.ner_manager.extract_entities(result["note_text"])
            matching_entities = set(query_entities.keys()) & set(note_entities.keys())
            if matching_entities:
                result["matching_entities"] = list(matching_entities)
                filtered_results.append(result)

        filtered_results.sort(
            key=lambda x: len(x.get("matching_entities", [])), reverse=True
        )

        logger.info(
            f"Retrieved {len(filtered_results)} relevant notes for patient {patient_id}"
        )
        for i, result in enumerate(filtered_results):
            logger.info(
                f"Result {i+1}: Distance = {result['distance']}, Matching Entities = {result.get('matching_entities', [])}"
            )

        return filtered_results[:top_k]

    async def cohort_search(
        self, user_query: str, top_k: int = 2
    ) -> List[Tuple[int, Dict[str, Any]]]:
        """Retrieve the cohort search results from Milvus."""
        query_embedding = await self.embedding_manager.get_embedding(user_query)
        cohort_results = await self.milvus_manager.cohort_search(query_embedding, top_k)

        # Extract entities from the query
        query_entities = await self.ner_manager.extract_entities(user_query)

        # Filter and sort results based on matching entities
        filtered_results = []
        for patient_id, note_details in cohort_results:
            note_entities = await self.ner_manager.extract_entities(
                note_details["note_text"]
            )
            matching_entities = set(query_entities.keys()) & set(note_entities.keys())
            if matching_entities:
                note_details["matching_entities"] = list(matching_entities)
                filtered_results.append((patient_id, note_details))

        filtered_results.sort(
            key=lambda x: len(x[1].get("matching_entities", [])), reverse=True
        )

        logger.info(
            f"Found {len(filtered_results)} patients matching the query: '{user_query}'"
        )
        for _, (patient_id, note_details) in enumerate(filtered_results[:5]):
            logger.info(
                f"Patient {patient_id}: Distance = {note_details['distance']}, "
                f"Note Type = {note_details['note_type']}, "
                f"Matching Entities = {note_details.get('matching_entities', [])}"
            )

        return filtered_results[:top_k]


async def retrieve_relevant_notes(
    user_query: str,
    embedding_manager: EmbeddingManager,
    milvus_manager: MilvusManager,
    patient_id: int,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """Retrieve the relevant notes directly from Milvus."""
    query_embedding = await embedding_manager.get_embedding(user_query)
    search_results = await milvus_manager.search(query_embedding, patient_id, top_k)
    logger.info(f"Retrieved {len(search_results)} relevant notes")
    for i, result in enumerate(search_results):
        logger.info(f"Result {i+1}: Distance = {result['distance']}")
    return search_results
