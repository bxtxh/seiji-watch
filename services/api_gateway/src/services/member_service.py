"""Member service with enhanced data collection and caching."""

import asyncio
import logging
from datetime import datetime
from typing import Any

from shared.clients.airtable import AirtableClient

from ..cache.redis_client import MemberCache, RedisCache

logger = logging.getLogger(__name__)


class MemberService:
    """Service for managing member data with enhanced collection and caching."""

    def __init__(self, airtable_client: AirtableClient, redis_cache: RedisCache):
        self.airtable = airtable_client
        self.redis = redis_cache
        self.member_cache = MemberCache(redis_cache)

        # Official Diet member roster URLs
        self.member_urls = {
            "house_of_representatives": "https://www.shugiin.go.jp/internet/itdb_annai.nsf/html/statics/shiryo/kaiha_m.htm",
            "house_of_councillors": "https://www.sangiin.go.jp/japanese/joho1/kousei/giin/212/giin.htm",
        }

    async def collect_member_profiles(self, house: str = "both") -> dict[str, Any]:
        """Collect comprehensive member profiles from official sources."""
        results = {"collected": 0, "updated": 0, "errors": [], "new_members": []}

        try:
            if house in ["both", "house_of_representatives"]:
                hr_results = await self._collect_house_members(
                    "house_of_representatives"
                )
                results["collected"] += hr_results["collected"]
                results["updated"] += hr_results["updated"]
                results["errors"].extend(hr_results["errors"])
                results["new_members"].extend(hr_results["new_members"])

            if house in ["both", "house_of_councillors"]:
                hc_results = await self._collect_house_members("house_of_councillors")
                results["collected"] += hc_results["collected"]
                results["updated"] += hc_results["updated"]
                results["errors"].extend(hc_results["errors"])
                results["new_members"].extend(hc_results["new_members"])

        except Exception as e:
            logger.error(f"Member profile collection failed: {e}")
            results["errors"].append(f"Collection failed: {str(e)}")

        return results

    async def _collect_house_members(self, house: str) -> dict[str, Any]:
        """Collect member data from specific house."""
        results = {"collected": 0, "updated": 0, "errors": [], "new_members": []}

        try:
            # Simulate member data collection (in real implementation, scrape from official sites)
            # For now, we'll use a mock implementation to demonstrate the structure
            mock_members = await self._get_mock_member_data(house)

            for member_data in mock_members:
                try:
                    # Check if member already exists
                    existing_member = await self.airtable.find_member_by_name(
                        member_data["name"], member_data.get("party_name")
                    )

                    if existing_member:
                        # Update existing member
                        await self.airtable.update_member(
                            existing_member["id"], member_data
                        )
                        results["updated"] += 1
                    else:
                        # Create new member
                        new_member = await self.airtable.create_member(member_data)
                        results["new_members"].append(new_member)
                        results["collected"] += 1

                    # Invalidate cache for this member
                    member_id = (
                        existing_member["id"] if existing_member else new_member["id"]
                    )
                    await self.member_cache.invalidate_member(member_id)

                except Exception as e:
                    logger.error(
                        f"Failed to process member {member_data.get('name', 'Unknown')}: {e}"
                    )
                    results["errors"].append(
                        f"Member {member_data.get('name', 'Unknown')}: {str(e)}"
                    )

        except Exception as e:
            logger.error(f"House {house} member collection failed: {e}")
            results["errors"].append(f"House {house}: {str(e)}")

        return results

    async def _get_mock_member_data(self, house: str) -> list[dict[str, Any]]:
        """Mock member data for demonstration (replace with actual scraping)."""
        # In real implementation, this would scrape from official Diet websites
        mock_data = [
            {
                "name": "田中太郎",
                "name_kana": "たなか　たろう",
                "house": house,
                "constituency": (
                    "東京都第1区" if house == "house_of_representatives" else "東京都"
                ),
                "party_name": "自由民主党",
                "birth_date": "1970-01-01",
                "first_elected": "2009-08-30",
                "terms_served": 5,
                "education": "東京大学法学部",
                "previous_occupations": ["弁護士", "会社員"],
                "website_url": "https://example.com/tanaka",
                "status": "active",
            },
            {
                "name": "佐藤花子",
                "name_kana": "さとう　はなこ",
                "house": house,
                "constituency": (
                    "大阪府第2区" if house == "house_of_representatives" else "大阪府"
                ),
                "party_name": "立憲民主党",
                "birth_date": "1975-03-15",
                "first_elected": "2017-10-22",
                "terms_served": 2,
                "education": "京都大学経済学部",
                "previous_occupations": ["記者", "市議会議員"],
                "website_url": "https://example.com/sato",
                "status": "active",
            },
        ]

        return mock_data

    async def get_member_with_cache(
        self, member_id: str, force_refresh: bool = False
    ) -> dict[str, Any] | None:
        """Get member data with intelligent caching."""
        cache_key = f"member:{member_id}"

        # Check cache first unless force refresh
        if not force_refresh:
            cached_member = await self.member_cache.get_member(member_id)
            if cached_member:
                # Check if cache is stale (older than 6 hours)
                if not await self.member_cache.is_stale(cache_key):
                    return cached_member

                # If stale, return cached data but trigger background refresh
                asyncio.create_task(self._refresh_member_data(member_id))
                return cached_member

        # Fetch from Airtable
        try:
            member = await self.airtable.get_member(member_id)
            if member:
                # Cache the result
                await self.member_cache.set_member(member_id, member)
                return member
        except Exception as e:
            logger.error(f"Failed to fetch member {member_id}: {e}")

        return None

    async def _refresh_member_data(self, member_id: str) -> None:
        """Background refresh of member data."""
        try:
            member = await self.airtable.get_member(member_id)
            if member:
                await self.member_cache.set_member(member_id, member)
                logger.info(f"Background refreshed member {member_id}")
        except Exception as e:
            logger.error(f"Background refresh failed for member {member_id}: {e}")

    async def get_members_list(
        self, filters: dict[str, Any] | None = None, force_refresh: bool = False
    ) -> list[dict[str, Any]]:
        """Get members list with caching and filtering."""
        filter_key = self._build_filter_key(filters or {})

        # Check cache first
        if not force_refresh:
            cached_list = await self.member_cache.get_members_list(filter_key)
            if cached_list:
                return cached_list

        # Build Airtable filter formula
        filter_formula = self._build_airtable_filter(filters or {})

        try:
            # Fetch from Airtable
            members = await self.airtable.list_members(
                filter_formula=filter_formula,
                max_records=1000,  # Adjust based on needs
            )

            # Process and enrich member data
            enriched_members = []
            for member in members:
                enriched_member = await self._enrich_member_data(member)
                enriched_members.append(enriched_member)

            # Cache the result
            await self.member_cache.set_members_list(filter_key, enriched_members)

            return enriched_members

        except Exception as e:
            logger.error(f"Failed to fetch members list: {e}")
            return []

    async def _enrich_member_data(self, member: dict[str, Any]) -> dict[str, Any]:
        """Enrich member data with additional computed fields."""
        enriched = member.copy()

        # Add computed fields
        if "fields" in enriched:
            fields = enriched["fields"]

            # Calculate age
            if "Birth_Date" in fields:
                try:
                    birth_date = datetime.fromisoformat(fields["Birth_Date"])
                    age = (datetime.now() - birth_date).days // 365
                    enriched["computed_age"] = age
                except Exception:
                    pass

            # Calculate tenure
            if "First_Elected" in fields:
                try:
                    first_elected = datetime.fromisoformat(fields["First_Elected"])
                    tenure_years = (datetime.now() - first_elected).days // 365
                    enriched["computed_tenure_years"] = tenure_years
                except Exception:
                    pass

            # Add display name with furigana
            name = fields.get("Name", "")
            name_kana = fields.get("Name_Kana", "")
            if name and name_kana:
                enriched["display_name"] = f"{name} ({name_kana})"
            else:
                enriched["display_name"] = name

        return enriched

    def _build_filter_key(self, filters: dict[str, Any]) -> str:
        """Build cache key from filters."""
        if not filters:
            return "all"

        key_parts = []
        for key, value in sorted(filters.items()):
            if isinstance(value, list):
                key_parts.append(f"{key}:{','.join(sorted(value))}")
            else:
                key_parts.append(f"{key}:{value}")

        return "|".join(key_parts)

    def _build_airtable_filter(self, filters: dict[str, Any]) -> str | None:
        """Build Airtable filter formula from filters."""
        if not filters:
            return None

        filter_parts = []

        if "house" in filters:
            filter_parts.append(f"{{House}} = '{filters['house']}'")

        if "party" in filters:
            filter_parts.append(f"{{Party_Name}} = '{filters['party']}'")

        if "constituency" in filters:
            filter_parts.append(f"{{Constituency}} = '{filters['constituency']}'")

        if "status" in filters:
            filter_parts.append(f"{{Status}} = '{filters['status']}'")

        if "is_active" in filters:
            filter_parts.append(f"{{Is_Active}} = {str(filters['is_active']).upper()}")

        if not filter_parts:
            return None

        if len(filter_parts) == 1:
            return filter_parts[0]

        return "AND(" + ", ".join(filter_parts) + ")"

    async def search_members(
        self, query: str, filters: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Search members by name or other criteria."""
        # Build search filter
        search_filters = filters or {}

        # For now, implement basic name search
        # In a real implementation, this would use more sophisticated search
        members = await self.get_members_list(search_filters)

        # Filter by query
        query_lower = query.lower()
        filtered_members = []

        for member in members:
            fields = member.get("fields", {})

            # Search in name, name_kana, and name_en
            searchable_fields = [
                fields.get("Name", ""),
                fields.get("Name_Kana", ""),
                fields.get("Name_EN", ""),
                fields.get("Constituency", ""),
                fields.get("Previous_Occupations", ""),
            ]

            if any(query_lower in str(field).lower() for field in searchable_fields):
                filtered_members.append(member)

        return filtered_members

    async def get_member_statistics(self, member_id: str) -> dict[str, Any]:
        """Get member statistics (voting patterns, etc.)."""
        # Check cache first
        cached_stats = await self.member_cache.get_member_stats(member_id)
        if cached_stats:
            return cached_stats

        # Calculate statistics
        stats = await self._calculate_member_stats(member_id)

        # Cache the result
        await self.member_cache.set_member_stats(member_id, stats)

        return stats

    async def _calculate_member_stats(self, member_id: str) -> dict[str, Any]:
        """Calculate member statistics from voting data."""
        # This is a placeholder - in real implementation,
        # this would analyze voting patterns, committee participation, etc.
        return {
            "total_votes": 0,
            "attendance_rate": 0.0,
            "party_alignment_rate": 0.0,
            "committee_participation": 0,
            "bills_sponsored": 0,
            "calculated_at": datetime.now().isoformat(),
        }

    async def warmup_member_cache(self) -> dict[str, Any]:
        """Warm up the member cache with all active members."""
        try:
            # Fetch all active members
            members = await self.airtable.list_members(
                filter_formula="{Is_Active} = TRUE", max_records=1000
            )

            # Enrich all members
            enriched_members = []
            for member in members:
                enriched_member = await self._enrich_member_data(member)
                enriched_members.append(enriched_member)

            # Warm up cache
            success = await self.member_cache.warmup_cache(enriched_members)

            return {
                "success": success,
                "cached_members": len(enriched_members),
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Cache warmup failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    async def get_cache_health(self) -> dict[str, Any]:
        """Get cache health and statistics."""
        cache_stats = await self.member_cache.get_cache_stats()
        redis_health = await self.redis.health_check()

        return {
            "redis_healthy": redis_health,
            "cache_stats": cache_stats,
            "timestamp": datetime.now().isoformat(),
        }
