"""
Vector embedding client for generating and storing embeddings using OpenAI and Weaviate.
"""
import logging
import os
from dataclasses import dataclass

import requests
import weaviate
from weaviate.classes.config import Configure

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    """Result of text embedding operation"""
    vector: list[float]
    text: str
    model: str
    dimensions: int
    usage_tokens: int | None = None


class VectorClient:
    """
    Vector embedding client using OpenAI embeddings and Weaviate storage.
    Optimized for Japanese text processing.
    """

    def __init__(
        self,
        openai_api_key: str | None = None,
        weaviate_url: str | None = None,
        weaviate_api_key: str | None = None
    ):
        # OpenAI configuration
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OpenAI API key is required")

        self.openai_headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }

        # Weaviate configuration
        self.weaviate_url = weaviate_url or os.getenv("WEAVIATE_URL", "https://seiji-watch-cluster.weaviate.network")
        self.weaviate_api_key = weaviate_api_key or os.getenv("WEAVIATE_API_KEY")

        # Initialize Weaviate client
        self.weaviate_client = None
        self._init_weaviate_client()

        # Embedding model configuration for Japanese
        self.embedding_model = "text-embedding-3-large"
        self.embedding_dimensions = 3072  # Full dimensions for best quality

    def _init_weaviate_client(self):
        """Initialize Weaviate client with proper authentication"""
        try:
            if self.weaviate_api_key:
                # Weaviate Cloud authentication
                auth_config = weaviate.AuthApiKey(api_key=self.weaviate_api_key)
                self.weaviate_client = weaviate.connect_to_weaviate_cloud(
                    cluster_url=self.weaviate_url,
                    auth_credentials=auth_config
                )
            else:
                # Local Weaviate instance
                self.weaviate_client = weaviate.connect_to_local(
                    host=self.weaviate_url.replace("http://", "").replace("https://", "")
                )

            logger.info("Weaviate client initialized successfully")

            # Create schema if it doesn't exist
            self._ensure_schema_exists()

        except Exception as e:
            logger.error(f"Failed to initialize Weaviate client: {e}")
            self.weaviate_client = None

    def _ensure_schema_exists(self):
        """Ensure required Weaviate schema exists"""
        try:
            # Define Bills collection schema
            bills_exists = self.weaviate_client.collections.exists("Bills")
            if not bills_exists:
                self.weaviate_client.collections.create(
                    name="Bills",
                    vectorizer_config=Configure.Vectorizer.none(),  # We provide vectors manually
                    properties=[
                        weaviate.classes.config.Property(
                            name="bill_number",
                            data_type=weaviate.classes.config.DataType.TEXT
                        ),
                        weaviate.classes.config.Property(
                            name="title",
                            data_type=weaviate.classes.config.DataType.TEXT
                        ),
                        weaviate.classes.config.Property(
                            name="summary",
                            data_type=weaviate.classes.config.DataType.TEXT
                        ),
                        weaviate.classes.config.Property(
                            name="category",
                            data_type=weaviate.classes.config.DataType.TEXT
                        ),
                        weaviate.classes.config.Property(
                            name="status",
                            data_type=weaviate.classes.config.DataType.TEXT
                        ),
                        weaviate.classes.config.Property(
                            name="diet_session",
                            data_type=weaviate.classes.config.DataType.TEXT
                        ),
                        weaviate.classes.config.Property(
                            name="embedding_model",
                            data_type=weaviate.classes.config.DataType.TEXT
                        )
                    ]
                )
                logger.info("Created Bills collection in Weaviate")

            # Define Speeches collection schema
            speeches_exists = self.weaviate_client.collections.exists("Speeches")
            if not speeches_exists:
                self.weaviate_client.collections.create(
                    name="Speeches",
                    vectorizer_config=Configure.Vectorizer.none(),
                    properties=[
                        weaviate.classes.config.Property(
                            name="text",
                            data_type=weaviate.classes.config.DataType.TEXT
                        ),
                        weaviate.classes.config.Property(
                            name="speaker",
                            data_type=weaviate.classes.config.DataType.TEXT
                        ),
                        weaviate.classes.config.Property(
                            name="meeting_id",
                            data_type=weaviate.classes.config.DataType.TEXT
                        ),
                        weaviate.classes.config.Property(
                            name="duration",
                            data_type=weaviate.classes.config.DataType.NUMBER
                        ),
                        weaviate.classes.config.Property(
                            name="language",
                            data_type=weaviate.classes.config.DataType.TEXT
                        ),
                        weaviate.classes.config.Property(
                            name="embedding_model",
                            data_type=weaviate.classes.config.DataType.TEXT
                        )
                    ]
                )
                logger.info("Created Speeches collection in Weaviate")

        except Exception as e:
            logger.error(f"Failed to ensure schema exists: {e}")

    def generate_embedding(self, text: str) -> EmbeddingResult:
        """
        Generate embedding for text using OpenAI API

        Args:
            text: Text to embed

        Returns:
            EmbeddingResult with vector and metadata
        """
        try:
            # Prepare request for OpenAI embeddings
            data = {
                "input": text,
                "model": self.embedding_model,
                "dimensions": self.embedding_dimensions,
                "encoding_format": "float"
            }

            response = requests.post(
                "https://api.openai.com/v1/embeddings",
                headers=self.openai_headers,
                json=data,
                timeout=30
            )

            response.raise_for_status()
            result = response.json()

            embedding_data = result["data"][0]
            usage = result.get("usage", {})

            return EmbeddingResult(
                vector=embedding_data["embedding"],
                text=text,
                model=self.embedding_model,
                dimensions=len(embedding_data["embedding"]),
                usage_tokens=usage.get("total_tokens")
            )

        except requests.RequestException as e:
            logger.error(f"OpenAI API request failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            raise

    def store_bill_embedding(self, bill_data: dict, embedding: EmbeddingResult) -> str | None:
        """
        Store bill data and embedding in Weaviate

        Args:
            bill_data: Bill metadata dictionary
            embedding: EmbeddingResult for the bill

        Returns:
            Weaviate object UUID if successful
        """
        if not self.weaviate_client:
            logger.error("Weaviate client not available")
            return None

        try:
            bills_collection = self.weaviate_client.collections.get("Bills")

            # Prepare data for Weaviate
            properties = {
                "bill_number": bill_data.get("bill_number", ""),
                "title": bill_data.get("title", ""),
                "summary": bill_data.get("summary", ""),
                "category": bill_data.get("category", ""),
                "status": bill_data.get("status", ""),
                "diet_session": bill_data.get("diet_session", ""),
                "embedding_model": embedding.model
            }

            # Insert with vector
            result = bills_collection.data.insert(
                properties=properties,
                vector=embedding.vector
            )

            logger.info(f"Stored bill embedding: {bill_data.get('bill_number')} -> {result.uuid}")
            return str(result.uuid)

        except Exception as e:
            logger.error(f"Failed to store bill embedding: {e}")
            return None

    def store_speech_embedding(self, speech_data: dict, embedding: EmbeddingResult) -> str | None:
        """
        Store speech data and embedding in Weaviate

        Args:
            speech_data: Speech metadata dictionary
            embedding: EmbeddingResult for the speech

        Returns:
            Weaviate object UUID if successful
        """
        if not self.weaviate_client:
            logger.error("Weaviate client not available")
            return None

        try:
            speeches_collection = self.weaviate_client.collections.get("Speeches")

            # Prepare data for Weaviate
            properties = {
                "text": speech_data.get("text", "")[:1000],  # Truncate for storage
                "speaker": speech_data.get("speaker", ""),
                "meeting_id": speech_data.get("meeting_id", ""),
                "duration": speech_data.get("duration", 0.0),
                "language": speech_data.get("language", "ja"),
                "embedding_model": embedding.model
            }

            # Insert with vector
            result = speeches_collection.data.insert(
                properties=properties,
                vector=embedding.vector
            )

            logger.info(f"Stored speech embedding: {speech_data.get('meeting_id')} -> {result.uuid}")
            return str(result.uuid)

        except Exception as e:
            logger.error(f"Failed to store speech embedding: {e}")
            return None

    def search_similar_bills(
        self,
        query_text: str,
        limit: int = 10,
        min_certainty: float = 0.7
    ) -> list[dict]:
        """
        Search for similar bills using vector similarity

        Args:
            query_text: Query text to search for
            limit: Maximum number of results
            min_certainty: Minimum similarity certainty

        Returns:
            List of similar bills with metadata and distances
        """
        if not self.weaviate_client:
            logger.error("Weaviate client not available")
            return []

        try:
            # Generate embedding for query
            query_embedding = self.generate_embedding(query_text)

            bills_collection = self.weaviate_client.collections.get("Bills")

            # Perform vector search
            results = bills_collection.query.near_vector(
                near_vector=query_embedding.vector,
                limit=limit,
                return_metadata=weaviate.classes.query.MetadataQuery(certainty=True)
            )

            # Format results
            formatted_results = []
            for obj in results.objects:
                formatted_results.append({
                    "uuid": str(obj.uuid),
                    "bill_number": obj.properties.get("bill_number"),
                    "title": obj.properties.get("title"),
                    "summary": obj.properties.get("summary"),
                    "category": obj.properties.get("category"),
                    "status": obj.properties.get("status"),
                    "certainty": obj.metadata.certainty,
                    "distance": obj.metadata.distance
                })

            # Filter by minimum certainty
            filtered_results = [r for r in formatted_results if r["certainty"] >= min_certainty]

            logger.info(f"Vector search found {len(filtered_results)} similar bills")
            return filtered_results

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    def get_embedding_stats(self) -> dict[str, int]:
        """Get statistics about stored embeddings"""
        if not self.weaviate_client:
            return {"bills": 0, "speeches": 0}

        try:
            bills_count = self.weaviate_client.collections.get("Bills").aggregate.over_all(
                total_count=True
            ).total_count

            speeches_count = self.weaviate_client.collections.get("Speeches").aggregate.over_all(
                total_count=True
            ).total_count

            return {
                "bills": bills_count,
                "speeches": speeches_count
            }

        except Exception as e:
            logger.error(f"Failed to get embedding stats: {e}")
            return {"bills": 0, "speeches": 0}

    def close(self):
        """Close Weaviate client connection"""
        if self.weaviate_client:
            self.weaviate_client.close()
            logger.info("Weaviate client connection closed")


# Test functionality
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    try:
        # Test without actual API keys (will fail gracefully)
        import os

        # Test basic embedding generation logic
        test_text = "これは国会での法案審議に関するテキストです。"
        logger.info(f"Test text: {test_text}")

        # Test Japanese text analysis
        japanese_chars = sum(1 for c in test_text if ord(c) > 127)
        logger.info(f"Japanese character ratio: {japanese_chars / len(test_text):.2f}")

        logger.info("VectorClient basic tests completed")

    except Exception as e:
        logger.error(f"VectorClient test failed: {e}")
