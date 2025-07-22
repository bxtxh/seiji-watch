"""Policy analysis service with MVP implementation."""

import logging
import random
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from shared.clients.airtable import AirtableClient

from ..cache.redis_client import MemberCache, RedisCache

logger = logging.getLogger(__name__)


class PolicyStance(Enum):
    """Policy stance categories."""

    STRONG_SUPPORT = "strong_support"
    SUPPORT = "support"
    NEUTRAL = "neutral"
    OPPOSE = "oppose"
    STRONG_OPPOSE = "strong_oppose"
    UNKNOWN = "unknown"


@dataclass
class IssuePosition:
    """Member's position on a specific issue."""

    issue_tag: str
    stance: PolicyStance
    confidence: float
    vote_count: int
    supporting_evidence: list[str]
    last_updated: datetime


@dataclass
class PolicyAnalysisResult:
    """Result of policy analysis."""

    member_id: str
    issue_positions: list[IssuePosition]
    overall_activity_level: float
    party_alignment_rate: float
    analysis_timestamp: datetime
    data_completeness: float


class PolicyAnalysisService:
    """Service for analyzing member policy positions."""

    def __init__(self, airtable_client: AirtableClient, redis_cache: RedisCache):
        self.airtable = airtable_client
        self.redis = redis_cache
        self.member_cache = MemberCache(redis_cache)

        # Issue tag definitions for Japanese politics
        self.issue_tags = {
            "経済・産業": {
                "name": "経済・産業政策",
                "description": "経済成長、産業振興、雇用政策",
                "color": "#3B82F6",
            },
            "社会保障": {
                "name": "社会保障制度",
                "description": "年金、医療、介護、社会保険",
                "color": "#10B981",
            },
            "外交・国際": {
                "name": "外交・国際関係",
                "description": "外交政策、安全保障、国際協力",
                "color": "#F59E0B",
            },
            "環境・エネルギー": {
                "name": "環境・エネルギー",
                "description": "環境保護、エネルギー政策、気候変動",
                "color": "#22C55E",
            },
            "教育・文化": {
                "name": "教育・文化",
                "description": "教育制度、文化政策、科学技術",
                "color": "#8B5CF6",
            },
            "法務・人権": {
                "name": "法務・人権",
                "description": "司法制度、人権保護、法制度改革",
                "color": "#EC4899",
            },
            "地方・都市": {
                "name": "地方・都市政策",
                "description": "地方創生、都市計画、インフラ整備",
                "color": "#6B7280",
            },
            "農林水産": {
                "name": "農林水産業",
                "description": "農業政策、林業、水産業振興",
                "color": "#92400E",
            },
            "税制・財政": {
                "name": "税制・財政",
                "description": "税制改革、財政政策、予算配分",
                "color": "#DC2626",
            },
            "憲法・政治": {
                "name": "憲法・政治制度",
                "description": "憲法改正、政治制度改革、選挙制度",
                "color": "#1F2937",
            },
        }

    async def analyze_member_policy_positions(
        self, member_id: str, force_refresh: bool = False
    ) -> PolicyAnalysisResult:
        """Analyze member's policy positions across all issues."""
        cache_key = f"policy_analysis:{member_id}"

        # Check cache first
        if not force_refresh:
            cached_result = await self.redis.get(cache_key)
            if cached_result:
                return PolicyAnalysisResult(**cached_result)

        # Generate MVP analysis (mock data)
        analysis_result = await self._generate_mvp_analysis(member_id)

        # Cache the result
        await self.redis.set(
            cache_key, analysis_result.__dict__, ttl=3600
        )  # 1 hour TTL

        return analysis_result

    async def _generate_mvp_analysis(self, member_id: str) -> PolicyAnalysisResult:
        """Generate MVP policy analysis with mock data."""
        # Get member info for context
        member_info = await self.member_cache.get_member(member_id)
        party_name = "自由民主党"  # Default for mock

        if member_info and "fields" in member_info:
            party_name = member_info["fields"].get("Party_Name", "自由民主党")

        # Generate positions for each issue
        issue_positions = []

        for issue_tag, issue_info in self.issue_tags.items():
            position = self._generate_mock_position(issue_tag, party_name)
            issue_positions.append(position)

        # Calculate overall metrics
        overall_activity_level = random.uniform(0.6, 0.95)
        party_alignment_rate = random.uniform(0.7, 0.9)
        data_completeness = random.uniform(0.8, 0.95)

        return PolicyAnalysisResult(
            member_id=member_id,
            issue_positions=issue_positions,
            overall_activity_level=overall_activity_level,
            party_alignment_rate=party_alignment_rate,
            analysis_timestamp=datetime.now(),
            data_completeness=data_completeness,
        )

    def _generate_mock_position(self, issue_tag: str, party_name: str) -> IssuePosition:
        """Generate mock position based on issue and party."""
        # Simulate party-based tendencies
        party_tendencies = {
            "自由民主党": {
                "経済・産業": PolicyStance.STRONG_SUPPORT,
                "社会保障": PolicyStance.SUPPORT,
                "外交・国際": PolicyStance.STRONG_SUPPORT,
                "環境・エネルギー": PolicyStance.NEUTRAL,
                "教育・文化": PolicyStance.SUPPORT,
                "法務・人権": PolicyStance.NEUTRAL,
                "地方・都市": PolicyStance.SUPPORT,
                "農林水産": PolicyStance.SUPPORT,
                "税制・財政": PolicyStance.SUPPORT,
                "憲法・政治": PolicyStance.STRONG_SUPPORT,
            },
            "立憲民主党": {
                "経済・産業": PolicyStance.SUPPORT,
                "社会保障": PolicyStance.STRONG_SUPPORT,
                "外交・国際": PolicyStance.NEUTRAL,
                "環境・エネルギー": PolicyStance.STRONG_SUPPORT,
                "教育・文化": PolicyStance.STRONG_SUPPORT,
                "法務・人権": PolicyStance.STRONG_SUPPORT,
                "地方・都市": PolicyStance.SUPPORT,
                "農林水産": PolicyStance.SUPPORT,
                "税制・財政": PolicyStance.OPPOSE,
                "憲法・政治": PolicyStance.OPPOSE,
            },
            "日本維新の会": {
                "経済・産業": PolicyStance.STRONG_SUPPORT,
                "社会保障": PolicyStance.NEUTRAL,
                "外交・国際": PolicyStance.SUPPORT,
                "環境・エネルギー": PolicyStance.SUPPORT,
                "教育・文化": PolicyStance.SUPPORT,
                "法務・人権": PolicyStance.SUPPORT,
                "地方・都市": PolicyStance.STRONG_SUPPORT,
                "農林水産": PolicyStance.NEUTRAL,
                "税制・財政": PolicyStance.SUPPORT,
                "憲法・政治": PolicyStance.SUPPORT,
            },
        }

        # Default stance if party not found
        default_stance = PolicyStance.NEUTRAL
        stance = party_tendencies.get(party_name, {}).get(issue_tag, default_stance)

        # Add some randomness to avoid perfectly predictable results
        if random.random() < 0.2:  # 20% chance to deviate
            stance_values = list(PolicyStance)
            stance = random.choice(stance_values)

        # Generate confidence based on stance
        confidence_map = {
            PolicyStance.STRONG_SUPPORT: random.uniform(0.8, 0.95),
            PolicyStance.SUPPORT: random.uniform(0.7, 0.85),
            PolicyStance.NEUTRAL: random.uniform(0.5, 0.7),
            PolicyStance.OPPOSE: random.uniform(0.7, 0.85),
            PolicyStance.STRONG_OPPOSE: random.uniform(0.8, 0.95),
            PolicyStance.UNKNOWN: random.uniform(0.3, 0.5),
        }

        confidence = confidence_map.get(stance, 0.5)
        vote_count = random.randint(5, 25)

        # Generate supporting evidence
        evidence = self._generate_mock_evidence(issue_tag, stance)

        return IssuePosition(
            issue_tag=issue_tag,
            stance=stance,
            confidence=confidence,
            vote_count=vote_count,
            supporting_evidence=evidence,
            last_updated=datetime.now() - timedelta(days=random.randint(1, 30)),
        )

    def _generate_mock_evidence(
        self, issue_tag: str, stance: PolicyStance
    ) -> list[str]:
        """Generate mock evidence for a stance."""
        evidence_templates = {
            PolicyStance.STRONG_SUPPORT: [
                f"{issue_tag}に関する積極的な議員立法を提出",
                f"委員会で{issue_tag}の推進を強く主張",
                f"{issue_tag}関連の予算増額を要求",
            ],
            PolicyStance.SUPPORT: [
                f"{issue_tag}に関する賛成討論を実施",
                f"委員会質疑で{issue_tag}の必要性を指摘",
                f"{issue_tag}関連法案に賛成票を投じる",
            ],
            PolicyStance.NEUTRAL: [
                f"{issue_tag}について慎重な検討を求める発言",
                f"委員会で{issue_tag}の課題を指摘",
                f"{issue_tag}関連で条件付き賛成の立場",
            ],
            PolicyStance.OPPOSE: [
                f"{issue_tag}に関する反対討論を実施",
                f"委員会で{issue_tag}の問題点を指摘",
                f"{issue_tag}関連法案に反対票を投じる",
            ],
            PolicyStance.STRONG_OPPOSE: [
                f"{issue_tag}に関する強い反対意見を表明",
                f"委員会で{issue_tag}の廃止を主張",
                f"{issue_tag}関連の予算削減を要求",
            ],
        }

        templates = evidence_templates.get(stance, [f"{issue_tag}に関する発言"])
        return random.sample(templates, min(len(templates), 2))

    async def get_member_issue_stance(
        self, member_id: str, issue_tag: str
    ) -> IssuePosition | None:
        """Get member's stance on a specific issue."""
        analysis = await self.analyze_member_policy_positions(member_id)

        for position in analysis.issue_positions:
            if position.issue_tag == issue_tag:
                return position

        return None

    async def compare_members_on_issue(
        self, member_ids: list[str], issue_tag: str
    ) -> dict[str, Any]:
        """Compare multiple members on a specific issue."""
        comparisons = []

        for member_id in member_ids:
            position = await self.get_member_issue_stance(member_id, issue_tag)
            if position:
                comparisons.append(
                    {
                        "member_id": member_id,
                        "stance": position.stance.value,
                        "confidence": position.confidence,
                        "vote_count": position.vote_count,
                    }
                )

        # Calculate stance distribution
        stance_counts = {}
        for comp in comparisons:
            stance = comp["stance"]
            stance_counts[stance] = stance_counts.get(stance, 0) + 1

        return {
            "issue_tag": issue_tag,
            "issue_name": self.issue_tags.get(issue_tag, {}).get("name", issue_tag),
            "member_count": len(comparisons),
            "stance_distribution": stance_counts,
            "member_positions": comparisons,
            "analyzed_at": datetime.now().isoformat(),
        }

    async def get_similar_members(
        self, member_id: str, issue_tags: list[str] = None
    ) -> list[dict[str, Any]]:
        """Find members with similar policy positions."""
        await self.analyze_member_policy_positions(member_id)

        # For MVP, return mock similar members
        similar_members = [
            {
                "member_id": "member_001",
                "name": "佐藤花子",
                "party": "立憲民主党",
                "similarity_score": 0.87,
                "common_stances": 7,
                "different_stances": 3,
            },
            {
                "member_id": "member_002",
                "name": "鈴木一郎",
                "party": "自由民主党",
                "similarity_score": 0.72,
                "common_stances": 6,
                "different_stances": 4,
            },
            {
                "member_id": "member_003",
                "name": "高橋真由美",
                "party": "日本維新の会",
                "similarity_score": 0.65,
                "common_stances": 5,
                "different_stances": 5,
            },
        ]

        return similar_members

    async def get_policy_trends(
        self, issue_tag: str, time_range_days: int = 30
    ) -> dict[str, Any]:
        """Get policy trends for an issue over time."""
        # Mock trend data
        return {
            "issue_tag": issue_tag,
            "issue_name": self.issue_tags.get(issue_tag, {}).get("name", issue_tag),
            "time_range_days": time_range_days,
            "trend_direction": "increasing_support",
            "support_change": 0.12,
            "key_events": [
                {
                    "date": "2024-07-01",
                    "event": f"{issue_tag}に関する重要法案が委員会を通過",
                    "impact": "positive",
                },
                {
                    "date": "2024-07-05",
                    "event": f"{issue_tag}関連の予算増額が決定",
                    "impact": "positive",
                },
            ],
            "member_position_changes": [
                {
                    "member_id": "member_001",
                    "name": "田中太郎",
                    "previous_stance": "neutral",
                    "current_stance": "support",
                    "change_date": "2024-07-03",
                }
            ],
            "analyzed_at": datetime.now().isoformat(),
        }

    async def get_analysis_summary(self, member_id: str) -> dict[str, Any]:
        """Get summary of member's policy analysis."""
        analysis = await self.analyze_member_policy_positions(member_id)

        # Calculate stance distribution
        stance_counts = {}
        for position in analysis.issue_positions:
            stance = position.stance.value
            stance_counts[stance] = stance_counts.get(stance, 0) + 1

        # Find strongest positions
        strongest_positions = sorted(
            analysis.issue_positions, key=lambda p: p.confidence, reverse=True
        )[:5]

        return {
            "member_id": member_id,
            "analysis_timestamp": analysis.analysis_timestamp.isoformat(),
            "overall_activity_level": analysis.overall_activity_level,
            "party_alignment_rate": analysis.party_alignment_rate,
            "data_completeness": analysis.data_completeness,
            "stance_distribution": stance_counts,
            "strongest_positions": [
                {
                    "issue_tag": pos.issue_tag,
                    "issue_name": self.issue_tags.get(pos.issue_tag, {}).get(
                        "name", pos.issue_tag
                    ),
                    "stance": pos.stance.value,
                    "confidence": pos.confidence,
                    "vote_count": pos.vote_count,
                }
                for pos in strongest_positions
            ],
            "total_issues_analyzed": len(analysis.issue_positions),
        }

    async def get_available_issues(self) -> list[dict[str, Any]]:
        """Get list of available issue tags."""
        return [
            {
                "tag": tag,
                "name": info["name"],
                "description": info["description"],
                "color": info["color"],
            }
            for tag, info in self.issue_tags.items()
        ]
