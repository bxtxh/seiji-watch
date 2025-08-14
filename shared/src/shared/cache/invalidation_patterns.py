"""Cache invalidation patterns for different data types."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from shared.cache.cache_manager import CacheManager, InvalidationPattern

logger = logging.getLogger(__name__)


class DataType(Enum):
    """Data types in the system."""
    PARTY = "party"
    MEMBER = "member"
    BILL = "bill"
    POLICY_CATEGORY = "policy_category"
    MEETING = "meeting"
    SPEECH = "speech"
    VOTE = "vote"
    ISSUE = "issue"
    ISSUE_TAG = "issue_tag"
    STATISTIC = "statistic"
    SEARCH_RESULT = "search_result"
    AGGREGATION = "aggregation"


class ChangeType(Enum):
    """Types of data changes."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    BULK_UPDATE = "bulk_update"
    RELATIONSHIP_CHANGE = "relationship_change"


@dataclass
class InvalidationRule:
    """Rule for cache invalidation."""
    data_type: DataType
    change_type: ChangeType
    patterns: List[str]  # Cache key patterns to invalidate
    cascade: bool = False  # Whether to cascade invalidation
    tags: List[str] = None  # Tags to invalidate
    delay_seconds: float = 0  # Delay before invalidation
    condition: Optional[callable] = None  # Condition for invalidation


class CacheInvalidator:
    """Service for intelligent cache invalidation based on data changes."""
    
    def __init__(self, cache_manager: CacheManager):
        """Initialize cache invalidator.
        
        Args:
            cache_manager: Cache manager instance
        """
        self.cache_manager = cache_manager
        self.invalidation_rules: Dict[str, List[InvalidationRule]] = {}
        self.invalidation_history: List[Dict[str, Any]] = []
        self.invalidation_stats: Dict[str, int] = {}
        
        # Register default invalidation rules
        self._register_default_rules()
        
    def _register_default_rules(self):
        """Register default invalidation rules for each data type."""
        
        # ===== Party Rules =====
        # Party changes affect members and statistics
        self.add_rule(
            InvalidationRule(
                data_type=DataType.PARTY,
                change_type=ChangeType.UPDATE,
                patterns=[
                    "cache:parties:*",
                    "cache:members:list*",  # Members list includes party info
                    "cache:statistics:*"
                ],
                cascade=True,
                tags=["parties", "members"]
            )
        )
        
        # ===== Member Rules =====
        # Member changes affect bills, speeches, votes
        self.add_rule(
            InvalidationRule(
                data_type=DataType.MEMBER,
                change_type=ChangeType.UPDATE,
                patterns=[
                    "cache:members:{id}",
                    "cache:members:list*",
                    "cache:bills:*:author:{id}",  # Bills by this member
                    "cache:speeches:*:member:{id}",  # Speeches by this member
                    "cache:votes:*:member:{id}"  # Votes by this member
                ],
                cascade=True,
                tags=["members"]
            )
        )
        
        # ===== Bill Rules =====
        # Bill changes affect issues, categories, and statistics
        self.add_rule(
            InvalidationRule(
                data_type=DataType.BILL,
                change_type=ChangeType.CREATE,
                patterns=[
                    "cache:bills:list*",
                    "cache:bills:recent*",
                    "cache:statistics:*",
                    "cache:issues:*"  # Issues may reference bills
                ],
                tags=["bills", "statistics"]
            )
        )
        
        self.add_rule(
            InvalidationRule(
                data_type=DataType.BILL,
                change_type=ChangeType.UPDATE,
                patterns=[
                    "cache:bills:{id}",
                    "cache:bills:list*",
                    "cache:bills:status:{old_status}",  # Old status list
                    "cache:bills:status:{new_status}",  # New status list
                    "cache:policy_categories:*:bills",  # Category bill lists
                    "cache:statistics:*"
                ],
                cascade=True,
                tags=["bills"]
            )
        )
        
        # ===== Policy Category Rules =====
        # Category changes affect bills and navigation
        self.add_rule(
            InvalidationRule(
                data_type=DataType.POLICY_CATEGORY,
                change_type=ChangeType.UPDATE,
                patterns=[
                    "cache:policy_categories:*",
                    "cache:policy_categories:tree*",
                    "cache:bills:category:{id}",
                    "cache:navigation:categories"
                ],
                cascade=True,
                tags=["categories", "navigation"]
            )
        )
        
        # ===== Meeting Rules =====
        # Meeting changes affect speeches and attendance
        self.add_rule(
            InvalidationRule(
                data_type=DataType.MEETING,
                change_type=ChangeType.CREATE,
                patterns=[
                    "cache:meetings:list*",
                    "cache:meetings:active*",
                    "cache:meetings:upcoming*",
                    "cache:calendar:*"
                ],
                tags=["meetings", "calendar"]
            )
        )
        
        self.add_rule(
            InvalidationRule(
                data_type=DataType.MEETING,
                change_type=ChangeType.UPDATE,
                patterns=[
                    "cache:meetings:{id}",
                    "cache:meetings:list*",
                    "cache:speeches:meeting:{id}",
                    "cache:calendar:*"
                ],
                cascade=True,
                tags=["meetings", "speeches"]
            )
        )
        
        # ===== Speech Rules =====
        # Speech changes affect member and meeting caches
        self.add_rule(
            InvalidationRule(
                data_type=DataType.SPEECH,
                change_type=ChangeType.CREATE,
                patterns=[
                    "cache:speeches:list*",
                    "cache:speeches:recent*",
                    "cache:meetings:{meeting_id}:speeches",
                    "cache:members:{member_id}:speeches",
                    "cache:search:speeches:*"  # Search results
                ],
                tags=["speeches", "search"]
            )
        )
        
        # ===== Vote Rules =====
        # Vote changes affect bill status and member records
        self.add_rule(
            InvalidationRule(
                data_type=DataType.VOTE,
                change_type=ChangeType.CREATE,
                patterns=[
                    "cache:votes:list*",
                    "cache:bills:{bill_id}:votes",
                    "cache:members:{member_id}:votes",
                    "cache:statistics:votes:*"
                ],
                tags=["votes", "statistics"]
            )
        )
        
        # ===== Issue Rules =====
        # Issue changes affect related bills and categories
        self.add_rule(
            InvalidationRule(
                data_type=DataType.ISSUE,
                change_type=ChangeType.UPDATE,
                patterns=[
                    "cache:issues:{id}",
                    "cache:issues:list*",
                    "cache:issues:popular*",
                    "cache:bills:issue:{id}",
                    "cache:policy_categories:{category_id}:issues"
                ],
                cascade=True,
                tags=["issues"]
            )
        )
        
        # ===== Search Result Rules =====
        # Search results have short TTL and specific invalidation
        self.add_rule(
            InvalidationRule(
                data_type=DataType.SEARCH_RESULT,
                change_type=ChangeType.UPDATE,
                patterns=[
                    "cache:search:*"
                ],
                tags=["search"],
                delay_seconds=5  # Delay to batch invalidations
            )
        )
        
        # ===== Aggregation Rules =====
        # Aggregations are invalidated when underlying data changes
        self.add_rule(
            InvalidationRule(
                data_type=DataType.AGGREGATION,
                change_type=ChangeType.UPDATE,
                patterns=[
                    "cache:statistics:*",
                    "cache:aggregations:*",
                    "cache:dashboard:*"
                ],
                tags=["statistics", "dashboard"]
            )
        )
        
    def add_rule(self, rule: InvalidationRule):
        """Add an invalidation rule.
        
        Args:
            rule: Invalidation rule to add
        """
        key = f"{rule.data_type.value}:{rule.change_type.value}"
        
        if key not in self.invalidation_rules:
            self.invalidation_rules[key] = []
            
        self.invalidation_rules[key].append(rule)
        
        logger.debug(f"Added invalidation rule for {key}")
        
    async def invalidate_on_change(
        self,
        data_type: DataType,
        change_type: ChangeType,
        entity_id: Optional[str] = None,
        old_data: Optional[Dict[str, Any]] = None,
        new_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Invalidate cache based on data change.
        
        Args:
            data_type: Type of data that changed
            change_type: Type of change
            entity_id: ID of the changed entity
            old_data: Previous data (for updates)
            new_data: New data
            metadata: Additional metadata
            
        Returns:
            Number of invalidated cache entries
        """
        key = f"{data_type.value}:{change_type.value}"
        rules = self.invalidation_rules.get(key, [])
        
        if not rules:
            logger.debug(f"No invalidation rules for {key}")
            return 0
            
        total_invalidated = 0
        
        for rule in rules:
            # Check condition if provided
            if rule.condition and not rule.condition(old_data, new_data, metadata):
                continue
                
            # Apply delay if specified
            if rule.delay_seconds > 0:
                import asyncio
                await asyncio.sleep(rule.delay_seconds)
                
            # Process each pattern
            for pattern in rule.patterns:
                # Replace placeholders in pattern
                resolved_pattern = self._resolve_pattern(
                    pattern, entity_id, old_data, new_data, metadata
                )
                
                # Invalidate by pattern
                count = await self.cache_manager.invalidate(
                    InvalidationPattern.PATTERN,
                    resolved_pattern,
                    cascade=rule.cascade
                )
                
                total_invalidated += count
                
            # Invalidate by tags
            if rule.tags:
                for tag in rule.tags:
                    count = await self.cache_manager.invalidate(
                        InvalidationPattern.TAG,
                        tag,
                        cascade=rule.cascade
                    )
                    total_invalidated += count
                    
        # Log invalidation
        self._log_invalidation(
            data_type, change_type, entity_id,
            total_invalidated, metadata
        )
        
        return total_invalidated
        
    def _resolve_pattern(
        self,
        pattern: str,
        entity_id: Optional[str],
        old_data: Optional[Dict[str, Any]],
        new_data: Optional[Dict[str, Any]],
        metadata: Optional[Dict[str, Any]]
    ) -> str:
        """Resolve placeholders in pattern.
        
        Args:
            pattern: Pattern with placeholders
            entity_id: Entity ID
            old_data: Previous data
            new_data: New data
            metadata: Additional metadata
            
        Returns:
            Resolved pattern
        """
        resolved = pattern
        
        # Replace {id} with entity ID
        if entity_id:
            resolved = resolved.replace("{id}", entity_id)
            
        # Replace old data placeholders
        if old_data:
            for key, value in old_data.items():
                resolved = resolved.replace(f"{{old_{key}}}", str(value))
                
        # Replace new data placeholders
        if new_data:
            for key, value in new_data.items():
                resolved = resolved.replace(f"{{new_{key}}}", str(value))
                resolved = resolved.replace(f"{{{key}}}", str(value))
                
        # Replace metadata placeholders
        if metadata:
            for key, value in metadata.items():
                resolved = resolved.replace(f"{{meta_{key}}}", str(value))
                
        return resolved
        
    def _log_invalidation(
        self,
        data_type: DataType,
        change_type: ChangeType,
        entity_id: Optional[str],
        count: int,
        metadata: Optional[Dict[str, Any]]
    ):
        """Log invalidation event.
        
        Args:
            data_type: Type of data
            change_type: Type of change
            entity_id: Entity ID
            count: Number of invalidated entries
            metadata: Additional metadata
        """
        event = {
            "timestamp": datetime.utcnow(),
            "data_type": data_type.value,
            "change_type": change_type.value,
            "entity_id": entity_id,
            "invalidated_count": count,
            "metadata": metadata
        }
        
        self.invalidation_history.append(event)
        
        # Update statistics
        key = f"{data_type.value}:{change_type.value}"
        self.invalidation_stats[key] = self.invalidation_stats.get(key, 0) + count
        
        logger.info(
            f"Invalidated {count} cache entries for {key} "
            f"(entity: {entity_id})"
        )
        
    async def invalidate_related(
        self,
        data_type: DataType,
        entity_id: str,
        relationship: str
    ) -> int:
        """Invalidate cache for related entities.
        
        Args:
            data_type: Type of primary entity
            entity_id: ID of primary entity
            relationship: Relationship name
            
        Returns:
            Number of invalidated entries
        """
        # Define relationship patterns
        relationship_patterns = {
            DataType.BILL: {
                "votes": ["cache:votes:bill:{id}:*"],
                "speeches": ["cache:speeches:bill:{id}:*"],
                "amendments": ["cache:amendments:bill:{id}:*"],
                "categories": ["cache:policy_categories:*:bills:*{id}*"]
            },
            DataType.MEMBER: {
                "bills": ["cache:bills:author:{id}:*"],
                "speeches": ["cache:speeches:member:{id}:*"],
                "votes": ["cache:votes:member:{id}:*"],
                "committees": ["cache:committees:member:{id}:*"]
            },
            DataType.MEETING: {
                "speeches": ["cache:speeches:meeting:{id}:*"],
                "attendance": ["cache:attendance:meeting:{id}:*"],
                "minutes": ["cache:minutes:meeting:{id}:*"]
            },
            DataType.POLICY_CATEGORY: {
                "bills": ["cache:bills:category:{id}:*"],
                "issues": ["cache:issues:category:{id}:*"],
                "subcategories": ["cache:policy_categories:parent:{id}:*"]
            }
        }
        
        patterns = relationship_patterns.get(data_type, {}).get(relationship, [])
        
        if not patterns:
            logger.warning(
                f"No relationship patterns defined for "
                f"{data_type.value}.{relationship}"
            )
            return 0
            
        total_invalidated = 0
        
        for pattern in patterns:
            resolved = pattern.replace("{id}", entity_id)
            count = await self.cache_manager.invalidate(
                InvalidationPattern.PATTERN,
                resolved,
                cascade=True
            )
            total_invalidated += count
            
        logger.info(
            f"Invalidated {total_invalidated} related cache entries "
            f"for {data_type.value}.{relationship} (ID: {entity_id})"
        )
        
        return total_invalidated
        
    async def invalidate_by_time(
        self,
        older_than_minutes: int,
        data_types: Optional[List[DataType]] = None
    ) -> int:
        """Invalidate cache entries older than specified time.
        
        Args:
            older_than_minutes: Age threshold in minutes
            data_types: Specific data types to invalidate (optional)
            
        Returns:
            Number of invalidated entries
        """
        patterns = []
        
        if data_types:
            for dt in data_types:
                patterns.append(f"cache:{dt.value}:*")
        else:
            patterns.append("cache:*")
            
        total_invalidated = 0
        
        for pattern in patterns:
            # Note: This requires storing timestamps in cache keys or metadata
            # For now, we'll invalidate all matching patterns
            count = await self.cache_manager.invalidate(
                InvalidationPattern.PATTERN,
                pattern,
                cascade=False
            )
            total_invalidated += count
            
        logger.info(
            f"Time-based invalidation: removed {total_invalidated} entries "
            f"older than {older_than_minutes} minutes"
        )
        
        return total_invalidated
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get invalidation statistics.
        
        Returns:
            Statistics dictionary
        """
        # Calculate top invalidated patterns
        top_patterns = sorted(
            self.invalidation_stats.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        # Recent invalidation events
        recent_events = self.invalidation_history[-20:] if self.invalidation_history else []
        
        return {
            "total_rules": sum(len(rules) for rules in self.invalidation_rules.values()),
            "total_invalidations": sum(self.invalidation_stats.values()),
            "invalidation_by_type": dict(self.invalidation_stats),
            "top_patterns": top_patterns,
            "recent_events": [
                {
                    "timestamp": e["timestamp"].isoformat(),
                    "data_type": e["data_type"],
                    "change_type": e["change_type"],
                    "entity_id": e["entity_id"],
                    "count": e["invalidated_count"]
                }
                for e in recent_events
            ],
            "history_size": len(self.invalidation_history)
        }
        
    def clear_history(self):
        """Clear invalidation history."""
        self.invalidation_history.clear()
        self.invalidation_stats.clear()
        logger.info("Invalidation history cleared")