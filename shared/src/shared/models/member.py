"""Models for Diet members and political parties."""


from pydantic import Field

from .base import BaseRecord


class Party(BaseRecord):
    """Political party model."""

    name: str = Field(..., description="Party name")
    name_en: str | None = Field(None, description="English name")
    abbreviation: str | None = Field(None, description="Party abbreviation")
    description: str | None = Field(None, description="Party description")
    website_url: str | None = Field(None, description="Official website URL")
    color_code: str | None = Field(None, description="Hex color code for UI")
    is_active: bool = Field(True, description="Whether the party is currently active")

    def __repr__(self) -> str:
        return f"<Party(name='{self.name}')>"


class Member(BaseRecord):
    """Diet member model."""

    # Basic information
    name: str = Field(..., description="Member name")
    name_kana: str | None = Field(None, description="Name in hiragana")
    name_en: str | None = Field(None, description="English name")

    # Political information
    party_id: str | None = Field(None, description="Airtable Party record ID")
    house: str = Field(..., description="House of Diet (衆議院/参議院)")
    constituency: str | None = Field(None, description="Electoral district")
    diet_member_id: str | None = Field(None, description="Official Diet member ID")

    # Personal information
    birth_date: str | None = Field(None, description="Birth date (YYYY-MM-DD)")
    gender: str | None = Field(None, description="Gender")

    # Career information
    first_elected: str | None = Field(None, description="Year first elected")
    terms_served: int | None = Field(None, description="Number of terms served")
    previous_occupations: str | None = Field(
        None, description="Previous occupations"
    )
    education: str | None = Field(None, description="Educational background")

    # Contact and web presence
    website_url: str | None = Field(None, description="Personal website URL")
    twitter_handle: str | None = Field(None, description="Twitter handle")
    facebook_url: str | None = Field(None, description="Facebook profile URL")

    # Status
    is_active: bool = Field(True, description="Whether the member is currently active")
    status: str = Field(
        "active", description="Member status (active, inactive, deceased)"
    )

    def __repr__(self) -> str:
        return f"<Member(name='{self.name}', house='{self.house}')>"

    @property
    def display_name(self) -> str:
        """Get display name with party affiliation."""
        # Note: To get party name, would need to fetch from Airtable using party_id
        return f"{self.name}"
