"""Base models and mixins for all Airtable-based models."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T", bound="BaseRecord")


class BaseRecord(BaseModel):
    """Base class for all Airtable record models."""

    airtable_record_id: Optional[str] = Field(None, description="Airtable record ID")
    created_at: Optional[datetime] = Field(None, description="Record creation timestamp")
    updated_at: Optional[datetime] = Field(
        None, description="Record last update timestamp"
    )

    def to_airtable_fields(self) -> Dict[str, Any]:
        """Convert model to Airtable fields format."""
        # Exclude None values and internal fields
        exclude_fields = {"airtable_record_id", "created_at", "updated_at"}
        fields = {}

        for field_name, field_value in self.model_dump().items():
            if field_name not in exclude_fields and field_value is not None:
                # Convert field name to Airtable format (Title_Case with underscores)
                airtable_field = field_name.replace("_", " ").title().replace(" ", "_")
                fields[airtable_field] = field_value

        return fields

    @classmethod
    def from_airtable_record(cls: Type[T], record: Dict[str, Any]) -> T:
        """Create model instance from Airtable record."""
        fields = record.get("fields", {})

        # Convert Airtable field names to snake_case
        converted_fields = {}
        for airtable_field, value in fields.items():
            field_name = airtable_field.lower().replace(" ", "_")
            converted_fields[field_name] = value

        # Add record metadata
        converted_fields["airtable_record_id"] = record.get("id")
        converted_fields["created_at"] = record.get("createdTime")

        return cls(**converted_fields)


class WeaviateEmbedding(BaseModel):
    """Model for Weaviate vector embeddings."""

    weaviate_object_id: Optional[str] = Field(None, description="Weaviate object ID")
    airtable_record_id: str = Field(..., description="Corresponding Airtable record ID")
    content: str = Field(..., description="Text content for embedding")
    embedding_vector: Optional[List[float]] = Field(None, description="Vector embedding")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    class Config:
        arbitrary_types_allowed = True
