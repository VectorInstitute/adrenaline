"""RAG for patients and cohort search."""

import asyncio
import logging
from typing import Any, Dict, List, Tuple

import chromadb
import httpx


# Configuration
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


class ChromaManager:
    """Manager for ChromaDB operations."""

    def __init__(self, host: str, port: int, collection_name: str):
        """Initialize the ChromaDB manager."""
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.client = None
        self.collection = None

    def connect(self):
        """Connect to ChromaDB."""
        try:
            self.client = chromadb.HttpClient(
                host=self.host,
                port=self.port,
                settings=chromadb.Settings(
                    anonymized_telemetry=False,
                    allow_reset=True,
                ),
            )
            self.collection = self.client.get_collection(
                name=self.collection_name,
            )
            logger.info(f"Connected to ChromaDB collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error connecting to ChromaDB: {e}")
            raise

    async def search(
        self,
        query_vector: List[float],
        patient_id: int = None,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Retrieve the relevant notes from ChromaDB."""
        if not self.collection:
            raise RuntimeError("ChromaDB collection not initialized")

        try:
            where_clause = {"patient_id": str(patient_id)} if patient_id else None

            results = await asyncio.to_thread(
                self.collection.query,
                query_embeddings=[query_vector],
                n_results=top_k,
                where=where_clause,
                include=["metadatas", "distances", "documents"],
            )

            if not results["metadatas"][0]:
                return []

            filtered_results = []
            for metadata, distance, document in zip(
                results["metadatas"][0],
                results["distances"][0],
                results["documents"][0],
            ):
                result = {
                    "patient_id": int(metadata["patient_id"]),
                    "note_type": metadata["note_type"],
                    "note_text": document,  # Use the full document text
                    "timestamp": int(metadata["timestamp"]),
                    "encounter_id": metadata["encounter_id"],
                    "distance": float(
                        1 - distance
                    ),  # Convert distance to similarity score
                }
                filtered_results.append(result)

            # Sort by similarity score in descending order
            filtered_results.sort(key=lambda x: x["distance"], reverse=True)
            return filtered_results

        except Exception as e:
            logger.error(f"Error searching ChromaDB: {e}")
            raise


class RAGManager:
    """Manager for RAG operations."""

    def __init__(
        self,
        embedding_manager: EmbeddingManager,
        chroma_manager: ChromaManager,
        ner_manager: NERManager,
    ):
        """Initialize the RAG manager."""
        self.embedding_manager = embedding_manager
        self.chroma_manager = chroma_manager
        self.ner_manager = ner_manager

    async def retrieve_relevant_notes(
        self,
        user_query: str,
        patient_id: int,
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Retrieve the relevant notes from ChromaDB."""
        query_embedding = await self.embedding_manager.get_embedding(user_query)
        search_results = await self.chroma_manager.search(
            query_embedding, patient_id, top_k
        )
        logger.info(f"Retrieved {len(search_results)} relevant notes")

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
        """Retrieve the cohort search results from ChromaDB."""
        query_embedding = await self.embedding_manager.get_embedding(user_query)
        cohort_results = await self.chroma_manager.cohort_search(query_embedding, top_k)
        logger.info(f"Retrieved {len(cohort_results)} cohort search results")

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
    chroma_manager: ChromaManager,
    patient_id: int,
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    """Retrieve the relevant notes from ChromaDB."""
    try:
        query_embedding = await embedding_manager.get_embedding(user_query)
        search_results = await chroma_manager.search(
            query_vector=query_embedding, patient_id=patient_id, top_k=top_k
        )

        if not search_results:
            logger.warning(f"No relevant notes found for patient {patient_id}")
            return []

        logger.info(
            f"Retrieved {len(search_results)} relevant notes for patient {patient_id}"
        )
        for i, result in enumerate(search_results):
            logger.info(
                f"Result {i+1}: "
                f"Note Type: {result['note_type']}, "
                f"Similarity: {result['distance']:.3f}, "
                f"Text Length: {len(result['note_text'])} chars"
            )

        return search_results

    except Exception as e:
        logger.error(f"Error retrieving relevant notes: {e}")
        raise
