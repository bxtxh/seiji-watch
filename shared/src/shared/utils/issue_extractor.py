"""LLM-powered issue extraction utilities."""

import json
import logging
import os
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class IssueExtractor:
    """LLM-powered policy issue extraction from bill content."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        # Predefined categories for consistency
        self.issue_categories = [
            "環境・エネルギー",
            "経済・産業",
            "社会保障・福祉",
            "外交・安全保障",
            "教育・文化",
            "司法・法務",
            "行政・公務員",
            "インフラ・交通",
            "その他"
        ]

    async def extract_issues_from_bill(self, bill_content: str, bill_title: str = "") -> list[dict[str, Any]]:
        """Extract policy issues from bill content using OpenAI GPT."""

        if not bill_content.strip():
            return []

        # Limit content length to avoid token limits
        content_preview = bill_content[:2000] + "..." if len(bill_content) > 2000 else bill_content

        prompt = f"""
以下の法案内容から、政策上の重要なイシューを抽出してください。
各イシューについて、JSON形式で以下の情報を含めてください：

法案タイトル: {bill_title}
法案内容: {content_preview}

以下のJSON形式で1-3個のイシューを抽出してください：

{{
  "issues": [
    {{
      "title": "30文字以内の簡潔なイシュータイトル",
      "description": "100文字程度の詳細説明",
      "suggested_tags": ["関連するタグ候補1", "タグ候補2"],
      "category": "{'/'.join(self.issue_categories)}から選択",
      "priority": "high/medium/low",
      "confidence": 0.0-1.0の信頼度スコア
    }}
  ]
}}

注意事項:
- 具体的で実用的なイシューを抽出
- 政治的偏見を避け、中立的な表現を使用
- 既存の政策分野に当てはまるものを優先
- 重要度の高いイシューから順に抽出
"""

        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "model": "gpt-4",
                    "messages": [
                        {
                            "role": "system",
                            "content": "あなたは日本の政策分析専門家です。法案から重要な政策イシューを客観的に抽出してください。"
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "max_tokens": 1000,
                    "temperature": 0.3
                }

                async with session.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=self.headers,
                    json=payload
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"OpenAI API error {response.status}: {error_text}")
                        return []

                    result = await response.json()

                    if "choices" not in result or not result["choices"]:
                        logger.error("No choices in OpenAI response")
                        return []

                    content = result["choices"][0]["message"]["content"]

                    # Parse JSON response
                    try:
                        extracted_data = json.loads(content)
                        issues = extracted_data.get("issues", [])

                        # Validate and clean extracted issues
                        validated_issues = []
                        for issue in issues:
                            if self._validate_issue(issue):
                                issue["is_llm_generated"] = True
                                validated_issues.append(issue)

                        return validated_issues

                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse LLM response as JSON: {e}")
                        logger.error(f"Response content: {content}")
                        return []

        except Exception as e:
            logger.error(f"Failed to extract issues from bill: {e}")
            return []

    def _validate_issue(self, issue: dict[str, Any]) -> bool:
        """Validate extracted issue data."""
        required_fields = ["title", "description", "category", "priority"]

        for field in required_fields:
            if field not in issue or not issue[field]:
                logger.warning(f"Missing required field '{field}' in extracted issue")
                return False

        # Validate title length
        if len(issue["title"]) > 100:
            logger.warning(f"Issue title too long: {len(issue['title'])} chars")
            return False

        # Validate category
        if issue["category"] not in self.issue_categories:
            logger.warning(f"Invalid category: {issue['category']}")
            return False

        # Validate priority
        if issue["priority"] not in ["high", "medium", "low"]:
            logger.warning(f"Invalid priority: {issue['priority']}")
            return False

        return True

    async def suggest_issue_tags(self, issue_title: str, existing_tags: list[str]) -> list[str]:
        """Suggest relevant tags for an issue based on existing tags."""

        if not existing_tags:
            return []

        # Simple keyword matching approach for MVP
        # In the future, could use embeddings for better matching
        title_lower = issue_title.lower()
        suggestions = []

        for tag in existing_tags:
            tag_lower = tag.lower()
            # Check for partial matches or related terms
            if any(keyword in title_lower for keyword in tag_lower.split()):
                suggestions.append(tag)

        return suggestions[:5]  # Return top 5 suggestions

    def generate_default_tags(self, category: str) -> list[str]:
        """Generate default tag suggestions based on category."""

        category_tags = {
            "環境・エネルギー": ["カーボンニュートラル", "再生可能エネルギー", "環境保護", "気候変動"],
            "経済・産業": ["経済成長", "産業政策", "中小企業支援", "デジタル化"],
            "社会保障・福祉": ["年金制度", "医療保険", "介護", "子育て支援"],
            "外交・安全保障": ["日米同盟", "防衛政策", "国際協力", "外交政策"],
            "教育・文化": ["教育改革", "大学政策", "文化振興", "スポーツ政策"],
            "司法・法務": ["司法制度", "法改正", "人権保護", "犯罪対策"],
            "行政・公務員": ["行政改革", "公務員制度", "規制緩和", "地方自治"],
            "インフラ・交通": ["交通政策", "都市計画", "公共工事", "災害対策"],
            "その他": ["政治改革", "選挙制度", "情報公開", "市民参加"]
        }

        return category_tags.get(category, ["政策課題", "改革", "制度"])
