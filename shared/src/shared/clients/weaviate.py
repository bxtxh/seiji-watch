"""Weaviate client for Diet Issue Tracker vector data."""

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Weaviate search result with similarity score."""

    id: str
    airtable_record_id: str
    content: str
    metadata: Dict[str, Any]
    similarity: float


class WeaviateClient:
    """Async Weaviate client for Diet Issue Tracker vector operations."""

    def __init__(
        self, api_key: Optional[str] = None, cluster_url: Optional[str] = None
    ):
        self.api_key = api_key or os.getenv("WEAVIATE_API_KEY")
        self.cluster_url = cluster_url or os.getenv("WEAVIATE_CLUSTER_URL")

        if not self.api_key or not self.cluster_url:
            raise ValueError("Weaviate API key and cluster URL are required")

        # Ensure cluster URL format
        if not self.cluster_url.startswith("https://"):
            self.cluster_url = f"https://{self.cluster_url}"

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # Class names for different content types
        self.SPEECH_CLASS = "DietSpeech"
        self.BILL_CLASS = "DietBill"

    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make request to Weaviate API."""
        url = f"{self.cluster_url}/v1/{endpoint}"

        async with aiohttp.ClientSession() as session:
            async with session.request(
                method, url, headers=self.headers, **kwargs
            ) as response:
                if response.status >= 400:
                    error_text = await response.text()
                    raise Exception(
                        f"Weaviate API error {response.status}: {error_text}"
                    )

                return await response.json()

    async def initialize_schema(self) -> None:
        """Initialize Weaviate schema with Diet Issue Tracker classes."""

        # Speech class for storing speech embeddings
        speech_class = {
            "class": self.SPEECH_CLASS,
            "description": "Diet speech content with embeddings",
            "properties": [
                {
                    "name": "airtableRecordId",
                    "dataType": ["text"],
                    "description": "Airtable record ID for the speech",
                },
                {
                    "name": "content",
                    "dataType": ["text"],
                    "description": "Speech text content",
                },
                {
                    "name": "speakerName",
                    "dataType": ["text"],
                    "description": "Name of the speaker",
                },
                {
                    "name": "meetingId",
                    "dataType": ["text"],
                    "description": "Airtable meeting record ID",
                },
                {
                    "name": "speechType",
                    "dataType": ["text"],
                    "description": (
                        "Type of speech (question, answer, discussion, etc.)"
                    ),
                },
                {
                    "name": "sentiment",
                    "dataType": ["text"],
                    "description": "Sentiment analysis result",
                },
                {
                    "name": "topics",
                    "dataType": ["text[]"],
                    "description": "Topic tags extracted from speech",
                },
                {
                    "name": "createdAt",
                    "dataType": ["date"],
                    "description": "Creation timestamp",
                },
            ],
            "vectorizer": "none",  # We'll provide embeddings manually
            "vectorIndexConfig": {"distance": "cosine"},
        }

        # Bill class for storing bill embeddings
        bill_class = {
            "class": self.BILL_CLASS,
            "description": "Diet bill content with embeddings",
            "properties": [
                {
                    "name": "airtableRecordId",
                    "dataType": ["text"],
                    "description": "Airtable record ID for the bill",
                },
                {
                    "name": "billNumber",
                    "dataType": ["text"],
                    "description": "Official bill number",
                },
                {"name": "title", "dataType": ["text"], "description": "Bill title"},
                {
                    "name": "content",
                    "dataType": ["text"],
                    "description": "Bill text content for embedding",
                },
                {
                    "name": "category",
                    "dataType": ["text"],
                    "description": "Bill category",
                },
                {
                    "name": "status",
                    "dataType": ["text"],
                    "description": "Current status of the bill",
                },
                {
                    "name": "dietSession",
                    "dataType": ["text"],
                    "description": "Diet session number",
                },
                {
                    "name": "tags",
                    "dataType": ["text[]"],
                    "description": "Tags associated with the bill",
                },
                {
                    "name": "createdAt",
                    "dataType": ["date"],
                    "description": "Creation timestamp",
                },
            ],
            "vectorizer": "none",
            "vectorIndexConfig": {"distance": "cosine"},
        }

        try:
            # Create classes if they don't exist
            await self._request("POST", "schema", json=speech_class)
            logger.info(f"Created {self.SPEECH_CLASS} class")
        except Exception as e:
            if "already exists" not in str(e):
                logger.error(f"Failed to create {self.SPEECH_CLASS} class: {e}")

        try:
            await self._request("POST", "schema", json=bill_class)
            logger.info(f"Created {self.BILL_CLASS} class")
        except Exception as e:
            if "already exists" not in str(e):
                logger.error(f"Failed to create {self.BILL_CLASS} class: {e}")

    async def add_speech_embedding(
        self,
        airtable_record_id: str,
        content: str,
        embedding: List[float],
        metadata: Dict[str, Any],
    ) -> str:
        """Add speech embedding to Weaviate."""

        object_data = {
            "class": self.SPEECH_CLASS,
            "properties": {
                "airtableRecordId": airtable_record_id,
                "content": content,
                "speakerName": metadata.get("speaker_name", ""),
                "meetingId": metadata.get("meeting_id", ""),
                "speechType": metadata.get("speech_type", ""),
                "sentiment": metadata.get("sentiment", ""),
                "topics": metadata.get("topics", []),
                "createdAt": metadata.get("created_at", ""),
            },
            "vector": embedding,
        }

        response = await self._request("POST", "objects", json=object_data)
        return response["id"]

    async def add_bill_embedding(
        self,
        airtable_record_id: str,
        content: str,
        embedding: List[float],
        metadata: Dict[str, Any],
    ) -> str:
        """Add bill embedding to Weaviate."""

        object_data = {
            "class": self.BILL_CLASS,
            "properties": {
                "airtableRecordId": airtable_record_id,
                "billNumber": metadata.get("bill_number", ""),
                "title": metadata.get("title", ""),
                "content": content,
                "category": metadata.get("category", ""),
                "status": metadata.get("status", ""),
                "dietSession": metadata.get("diet_session", ""),
                "tags": metadata.get("tags", []),
                "createdAt": metadata.get("created_at", ""),
            },
            "vector": embedding,
        }

        response = await self._request("POST", "objects", json=object_data)
        return response["id"]

    async def search_speeches(
        self,
        query_vector: List[float],
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Search for similar speeches using vector similarity."""

        where_filter = {}
        if filters:
            # Convert filters to Weaviate where format
            conditions = []
            for key, value in filters.items():
                if isinstance(value, list):
                    # Multiple values - use OR
                    or_conditions = [
                        {"path": [key], "operator": "Equal", "valueText": v}
                        for v in value
                    ]
                    conditions.append({"operator": "Or", "operands": or_conditions})
                else:
                    conditions.append(
                        {"path": [key], "operator": "Equal", "valueText": value}
                    )

            if len(conditions) == 1:
                where_filter = conditions[0]
            elif len(conditions) > 1:
                where_filter = {"operator": "And", "operands": conditions}

        query = {
            "query": f"""
            {{
                Get {{
                    {self.SPEECH_CLASS}(
                        nearVector: {{vector: {query_vector}}}
                        limit: {limit}
                        {(f"where: {json.dumps(where_filter)}" if where_filter else "")}
                    ) {{
                        airtableRecordId
                        content
                        speakerName
                        meetingId
                        speechType
                        sentiment
                        topics
                        _additional {{
                            id
                            distance
                        }}
                    }}
                }}
            }}
            """
        }

        response = await self._request("POST", "graphql", json=query)

        results = []
        if "data" in response and "Get" in response["data"]:
            for item in response["data"]["Get"][self.SPEECH_CLASS]:
                results.append(
                    SearchResult(
                        id=item["_additional"]["id"],
                        airtable_record_id=item["airtableRecordId"],
                        content=item["content"],
                        metadata={
                            "speaker_name": item.get("speakerName", ""),
                            "meeting_id": item.get("meetingId", ""),
                            "speech_type": item.get("speechType", ""),
                            "sentiment": item.get("sentiment", ""),
                            "topics": item.get("topics", []),
                        },
                        similarity=(
                            1.0 - item["_additional"]["distance"]
                        ),  # Convert distance to similarity
                    )
                )

        return results

    async def search_bills(
        self,
        query_vector: List[float],
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[SearchResult]:
        """Search for similar bills using vector similarity."""

        where_filter = {}
        if filters:
            conditions = []
            for key, value in filters.items():
                if isinstance(value, list):
                    or_conditions = [
                        {"path": [key], "operator": "Equal", "valueText": v}
                        for v in value
                    ]
                    conditions.append({"operator": "Or", "operands": or_conditions})
                else:
                    conditions.append(
                        {"path": [key], "operator": "Equal", "valueText": value}
                    )

            if len(conditions) == 1:
                where_filter = conditions[0]
            elif len(conditions) > 1:
                where_filter = {"operator": "And", "operands": conditions}

        query = {
            "query": f"""
            {{
                Get {{
                    {self.BILL_CLASS}(
                        nearVector: {{vector: {query_vector}}}
                        limit: {limit}
                        {(f"where: {json.dumps(where_filter)}" if where_filter else "")}
                    ) {{
                        airtableRecordId
                        billNumber
                        title
                        content
                        category
                        status
                        dietSession
                        tags
                        _additional {{
                            id
                            distance
                        }}
                    }}
                }}
            }}
            """
        }

        response = await self._request("POST", "graphql", json=query)

        results = []
        if "data" in response and "Get" in response["data"]:
            for item in response["data"]["Get"][self.BILL_CLASS]:
                results.append(
                    SearchResult(
                        id=item["_additional"]["id"],
                        airtable_record_id=item["airtableRecordId"],
                        content=item["content"],
                        metadata={
                            "bill_number": item.get("billNumber", ""),
                            "title": item.get("title", ""),
                            "category": item.get("category", ""),
                            "status": item.get("status", ""),
                            "diet_session": item.get("dietSession", ""),
                            "tags": item.get("tags", []),
                        },
                        similarity=1.0 - item["_additional"]["distance"],
                    )
                )

        return results

    async def hybrid_search(
        self,
        query_text: str,
        query_vector: List[float],
        content_type: str = "speech",
        limit: int = 10,
        alpha: float = 0.7,
    ) -> List[SearchResult]:
        """Perform hybrid search combining text and vector similarity."""

        class_name = self.SPEECH_CLASS if content_type == "speech" else self.BILL_CLASS

        query = {
            "query": f"""
            {{
                Get {{
                    {class_name}(
                        hybrid: {{
                            query: "{query_text}"
                            vector: {query_vector}
                            alpha: {alpha}
                        }}
                        limit: {limit}
                    ) {{
                        airtableRecordId
                        content
                        {
                (
                    "speakerName meetingId speechType sentiment topics"
                    if content_type == "speech"
                    else "billNumber title category status dietSession tags"
                )
            }
                        _additional {{
                            id
                            score
                        }}
                    }}
                }}
            }}
            """
        }

        response = await self._request("POST", "graphql", json=query)

        results = []
        if "data" in response and "Get" in response["data"]:
            for item in response["data"]["Get"][class_name]:
                if content_type == "speech":
                    metadata = {
                        "speaker_name": item.get("speakerName", ""),
                        "meeting_id": item.get("meetingId", ""),
                        "speech_type": item.get("speechType", ""),
                        "sentiment": item.get("sentiment", ""),
                        "topics": item.get("topics", []),
                    }
                else:
                    metadata = {
                        "bill_number": item.get("billNumber", ""),
                        "title": item.get("title", ""),
                        "category": item.get("category", ""),
                        "status": item.get("status", ""),
                        "diet_session": item.get("dietSession", ""),
                        "tags": item.get("tags", []),
                    }

                results.append(
                    SearchResult(
                        id=item["_additional"]["id"],
                        airtable_record_id=item["airtableRecordId"],
                        content=item["content"],
                        metadata=metadata,
                        similarity=item["_additional"]["score"],
                    )
                )

        return results

    async def update_object(self, object_id: str, properties: Dict[str, Any]) -> None:
        """Update an existing object in Weaviate."""
        await self._request(
            "PATCH", f"objects/{object_id}", json={"properties": properties}
        )

    async def delete_object(self, object_id: str) -> None:
        """Delete an object from Weaviate."""
        await self._request("DELETE", f"objects/{object_id}")

    async def get_object_by_airtable_id(
        self,
        airtable_record_id: str,
        content_type: str = "speech",
    ) -> Optional[Dict[str, Any]]:
        """Get Weaviate object by Airtable record ID."""

        class_name = self.SPEECH_CLASS if content_type == "speech" else self.BILL_CLASS

        query = {
            "query": f"""
            {{
                Get {{
                    {class_name}(
                        where: {{
                            path: ["airtableRecordId"]
                            operator: Equal
                            valueText: "{airtable_record_id}"
                        }}
                        limit: 1
                    ) {{
                        airtableRecordId
                        content
                        _additional {{
                            id
                        }}
                    }}
                }}
            }}
            """
        }

        response = await self._request("POST", "graphql", json=query)

        if "data" in response and "Get" in response["data"]:
            objects = response["data"]["Get"][class_name]
            return objects[0] if objects else None

        return None

    async def health_check(self) -> bool:
        """Check if Weaviate connection is healthy."""
        try:
            response = await self._request("GET", "meta")
            return "hostname" in response
        except Exception as e:
            logger.error(f"Weaviate health check failed: {e}")
            return False

    async def get_schema_info(self) -> Dict[str, Any]:
        """Get current schema information."""
        return await self._request("GET", "schema")

    async def get_object_count(
        self, class_name: Optional[str] = None
    ) -> Dict[str, int]:
        """Get object count for classes."""
        counts = {}

        classes = [class_name] if class_name else [self.SPEECH_CLASS, self.BILL_CLASS]

        for cls in classes:
            query = {
                "query": f"""
                {{
                    Aggregate {{
                        {cls} {{
                            meta {{
                                count
                            }}
                        }}
                    }}
                }}
                """
            }

            try:
                response = await self._request("POST", "graphql", json=query)
                if "data" in response and "Aggregate" in response["data"]:
                    count_data = response["data"]["Aggregate"][cls]
                    counts[cls] = count_data[0]["meta"]["count"] if count_data else 0
                else:
                    counts[cls] = 0
            except Exception as e:
                logger.error(f"Failed to get count for {cls}: {e}")
                counts[cls] = 0

        return counts
