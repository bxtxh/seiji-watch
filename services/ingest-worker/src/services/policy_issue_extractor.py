"""
Policy Issue Extraction Service - Extract dual-level policy issues from bills using LLM.
Provides comprehensive issue extraction with validation for high school and general reader levels.
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import openai
from janome.tokenizer import Tokenizer
from pydantic import BaseModel, ValidationError, field_validator

logger = logging.getLogger(__name__)


@dataclass
class BillData:
    """Bill data structure for issue extraction."""

    id: str
    title: str
    outline: str | None = None
    background_context: str | None = None
    expected_effects: str | None = None
    key_provisions: list[str] | None = field(default_factory=list)
    submitter: str | None = None
    category: str | None = None


class DualLevelIssue(BaseModel):
    """Pydantic model for dual-level issue validation."""

    label_lv1: str
    label_lv2: str
    confidence: float

    @field_validator("label_lv1")
    def validate_lv1_label(self, v):
        # Length check
        if len(v) > 60:
            raise ValueError("label_lv1 must be ≤ 60 characters")

        # High school vocabulary check
        if not self._is_high_school_vocabulary(v):
            raise ValueError("label_lv1 contains advanced vocabulary")

        # Verb ending check
        if not self._ends_with_verb(v):
            raise ValueError("label_lv1 must end with a verb")

        return v

    @field_validator("label_lv2")
    def validate_lv2_label(self, v):
        # Length check
        if len(v) > 60:
            raise ValueError("label_lv2 must be ≤ 60 characters")

        # Verb ending check
        if not self._ends_with_verb(v):
            raise ValueError("label_lv2 must end with a verb")

        return v

    @field_validator("confidence")
    def validate_confidence(self, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return v

    @classmethod
    def _ends_with_verb(cls, text: str) -> bool:
        """Check if text ends with a verb using Janome POS tagging."""
        try:
            tokenizer = Tokenizer()
            tokens = list(tokenizer.tokenize(text))

            if not tokens:
                return False

            last_token = tokens[-1]
            pos = last_token.part_of_speech.split(",")[0]

            return pos == "動詞"
        except Exception as e:
            logger.warning(f"POS tagging failed for '{text}': {e}")
            # Fallback to simple pattern matching
            verb_endings = [
                "する",
                "される",
                "できる",
                "なる",
                "れる",
                "せる",
                "ける",
                "げる",
                "める",
                "える",
            ]
            return any(text.endswith(ending) for ending in verb_endings)

    @classmethod
    def _is_high_school_vocabulary(cls, text: str) -> bool:
        """Check if text uses only high school level vocabulary."""
        # Advanced terms that are too complex for high school level
        advanced_terms = [
            "施策",
            "方策",
            "措置",
            "制度設計",
            "政策立案",
            "実効性",
            "持続可能性",
            "包括的",
            "体系的",
            "戦略的",
            "抜本的",
            "根本的",
            "構造的",
            "包摂的",
            "多角的",
            "実証的",
            "効率的",
            "合理的",
            "恒久的",
            "暫定的",
            "予防的",
            "事後的",
            "総合的",
            "統合的",
            "段階的",
            "優遇措置",
            "特例措置",
            "緊急措置",
            "暫定措置",
            "施行",
            "実施",
            "運用",
            "執行",
            "適用",
            "改廃",
            "制定",
            "改正",
            "廃止",
            "見直し",
        ]

        return not any(term in text for term in advanced_terms)


@dataclass
class ValidationResult:
    """Validation result for extracted issues."""

    is_valid: bool
    validated_data: DualLevelIssue | None
    errors: list[str]
    quality_score: float


class IssueValidator:
    """Validator for extracted policy issues."""

    def __init__(self):
        self.tokenizer = Tokenizer()

    def validate_issue(self, issue: dict) -> ValidationResult:
        """Validate extracted issue data."""
        try:
            validated_issue = DualLevelIssue(**issue)
            quality_score = self._calculate_quality_score(validated_issue)

            return ValidationResult(
                is_valid=True,
                validated_data=validated_issue,
                errors=[],
                quality_score=quality_score,
            )
        except ValidationError as e:
            error_messages = [str(error) for error in e.errors()]
            return ValidationResult(
                is_valid=False,
                validated_data=None,
                errors=error_messages,
                quality_score=0.0,
            )

    def _calculate_quality_score(self, issue: DualLevelIssue) -> float:
        """Calculate quality score for validated issue."""
        score = 0.0

        # Base score for successful validation
        score += 0.5

        # Length appropriateness (prefer 20-50 characters)
        lv1_length_score = self._score_length(len(issue.label_lv1), 20, 50)
        lv2_length_score = self._score_length(len(issue.label_lv2), 25, 55)
        score += (lv1_length_score + lv2_length_score) * 0.1

        # Confidence bonus
        score += issue.confidence * 0.2

        # Vocabulary level differentiation bonus
        if self._has_vocabulary_differentiation(issue.label_lv1, issue.label_lv2):
            score += 0.1

        # Clarity and specificity bonus
        if self._is_clear_and_specific(issue.label_lv1) and self._is_clear_and_specific(
            issue.label_lv2
        ):
            score += 0.1

        return min(1.0, score)

    def _score_length(self, length: int, optimal_min: int, optimal_max: int) -> float:
        """Score length appropriateness."""
        if optimal_min <= length <= optimal_max:
            return 1.0
        elif length < optimal_min:
            return length / optimal_min
        else:
            return max(0.0, 1.0 - (length - optimal_max) / optimal_max)

    def _has_vocabulary_differentiation(self, lv1: str, lv2: str) -> bool:
        """Check if lv2 uses more sophisticated vocabulary than lv1."""
        # Simple heuristic: lv2 should have different wording or additional detail
        return lv1 != lv2 and (len(lv2) > len(lv1) or self._has_advanced_terms(lv2))

    def _has_advanced_terms(self, text: str) -> bool:
        """Check if text contains advanced terms appropriate for general readers."""
        advanced_terms = [
            "改善",
            "向上",
            "推進",
            "促進",
            "強化",
            "充実",
            "確保",
            "対策",
            "対応",
            "解決",
            "防止",
            "予防",
            "支援",
            "援助",
        ]
        return any(term in text for term in advanced_terms)

    def _is_clear_and_specific(self, text: str) -> bool:
        """Check if text is clear and specific."""
        # Avoid vague terms
        vague_terms = ["問題", "こと", "もの", "など", "について", "に関して"]
        return len(text) > 10 and not any(term in text for term in vague_terms[:3])


class PolicyIssueExtractor:
    """Main service for extracting dual-level policy issues from bills."""

    def __init__(self, api_key: str | None = None):
        self.client = openai.AsyncOpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        if not self.client.api_key:
            raise ValueError("OpenAI API key is required")

        self.validator = IssueValidator()
        self.logger = logger

        # Rate limiting settings
        self.max_retries = 3
        self.retry_delay = 2.0

    async def extract_dual_level_issues(
        self, bill_data: BillData
    ) -> list[DualLevelIssue]:
        """Extract issues at both high school and general reader levels."""

        prompt = self._build_dual_level_prompt(bill_data)

        for attempt in range(self.max_retries):
            try:
                response = await self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": self._get_system_prompt()},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,
                    max_tokens=800,
                )

                return await self._parse_and_validate_response(response)

            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    raise e

    def _build_dual_level_prompt(self, bill_data: BillData) -> str:
        """Build prompt for dual-level issue extraction."""

        # Prepare bill information
        bill_info = f"法案タイトル: {bill_data.title}"

        if bill_data.outline:
            bill_info += f"\n法案概要: {bill_data.outline}"

        if bill_data.background_context:
            bill_info += f"\n提出背景: {bill_data.background_context}"

        if bill_data.expected_effects:
            bill_info += f"\n期待される効果: {bill_data.expected_effects}"

        if bill_data.key_provisions:
            provisions_text = "、".join(
                bill_data.key_provisions[:3]
            )  # Limit to 3 for brevity
            bill_info += f"\n主要条項: {provisions_text}"

        return f"""
以下の法案から、解決を目指す政策課題を2レベルで抽出してください。

{bill_info}

以下のJSON形式で回答してください：

{{
  "issues": [
    {{
      "label_lv1": "高校生でも理解できる簡潔な課題表現（60文字以内、動詞終わり）",
      "label_lv2": "一般読者向けの詳細な課題表現（60文字以内、動詞終わり）",
      "confidence": 0.0-1.0の信頼度スコア
    }}
  ]
}}

重要な制約条件:
- label_lv1: 高校生レベルの語彙のみ使用（基本的な日本語）
- label_lv2: 新聞読者レベルの語彙使用可（専門用語可）
- 両方とも必ず動詞で終わる（〜する、〜できる、〜される、〜を守る等）
- 各ラベル60文字以内
- 1-3個の主要課題を抽出
- 政治的中立性を保持
- 具体的で実行可能な課題表現を心がける

例:
- label_lv1: "環境を守る"
- label_lv2: "地球温暖化対策を推進する"
"""

    def _get_system_prompt(self) -> str:
        """Get system prompt for LLM."""
        return """
あなたは日本の政策分析専門家です。法案から解決を目指す政策課題を2つの理解レベルで抽出してください。

重要な区別:
- 政策カテゴリ（分野分類）≠ 政策イシュー（解決すべき課題）
- イシューは「何を解決するか」「何を改善するか」に焦点を当てる
- 具体的で実行可能な課題表現を心がける

レベル別要件:
- Level 1 (高校生向け): 基本語彙、簡潔、分かりやすい表現
- Level 2 (一般向け): 専門用語可、詳細、正確性重視

品質基準:
- 政治的中立性を保持
- 具体性と実用性を重視
- 動詞終わりの統一性
- 課題の本質を捉える

NGパターン:
- 抽象的すぎる表現（「問題を解決する」等）
- 政治的偏向のある表現
- 名詞で終わる表現
- 60文字を超える表現
"""

    async def _parse_and_validate_response(self, response) -> list[DualLevelIssue]:
        """Parse and validate LLM response."""
        try:
            content = response.choices[0].message.content.strip()

            # Handle potential markdown formatting
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]

            data = json.loads(content)
            issues_data = data.get("issues", [])

            if not issues_data:
                raise ValueError("No issues found in response")

            validated_issues = []
            for issue_data in issues_data:
                validation_result = self.validator.validate_issue(issue_data)

                if validation_result.is_valid:
                    validated_issues.append(validation_result.validated_data)
                    self.logger.info(
                        f"Issue validated with quality score: {validation_result.quality_score:.2f}"
                    )
                else:
                    self.logger.warning(
                        f"Issue validation failed: {validation_result.errors}"
                    )
                    # Store for manual review or retry
                    continue

            if not validated_issues:
                raise ValueError("No valid issues after validation")

            return validated_issues

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON response: {e}")
            self.logger.debug(f"Response content: {content}")
            raise ValueError(f"Invalid JSON response: {e}")

        except Exception as e:
            self.logger.error(f"Failed to parse and validate response: {e}")
            raise

    async def extract_issues_with_metadata(self, bill_data: BillData) -> dict[str, Any]:
        """Extract issues with comprehensive metadata."""

        start_time = datetime.now()

        try:
            issues = await self.extract_dual_level_issues(bill_data)

            processing_time = (datetime.now() - start_time).total_seconds()

            # Calculate overall quality metrics
            quality_scores = []
            for issue in issues:
                validation_result = self.validator.validate_issue(issue.dict())
                quality_scores.append(validation_result.quality_score)

            avg_quality = (
                sum(quality_scores) / len(quality_scores) if quality_scores else 0.0
            )

            return {
                "bill_id": bill_data.id,
                "issues": [issue.dict() for issue in issues],
                "metadata": {
                    "extraction_timestamp": start_time.isoformat(),
                    "processing_time_seconds": processing_time,
                    "issue_count": len(issues),
                    "average_quality_score": avg_quality,
                    "individual_quality_scores": quality_scores,
                    "model_used": "gpt-4",
                    "extractor_version": "1.0.0",
                },
                "status": "success",
            }

        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()

            return {
                "bill_id": bill_data.id,
                "issues": [],
                "metadata": {
                    "extraction_timestamp": start_time.isoformat(),
                    "processing_time_seconds": processing_time,
                    "issue_count": 0,
                    "error": str(e),
                    "model_used": "gpt-4",
                    "extractor_version": "1.0.0",
                },
                "status": "failed",
            }

    async def batch_extract_issues(
        self,
        bills: list[BillData],
        batch_size: int = 5,
        delay_between_batches: float = 2.0,
    ) -> list[dict[str, Any]]:
        """Extract issues from multiple bills in batches."""

        self.logger.info(f"Starting batch extraction for {len(bills)} bills")

        results = []

        for i in range(0, len(bills), batch_size):
            batch = bills[i : i + batch_size]

            self.logger.info(
                f"Processing batch {i // batch_size + 1}: {len(batch)} bills"
            )

            # Process batch concurrently
            tasks = [self.extract_issues_with_metadata(bill) for bill in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Handle results and exceptions
            for j, result in enumerate(batch_results):
                if isinstance(result, Exception):
                    self.logger.error(
                        f"Batch processing failed for bill {batch[j].id}: {result}"
                    )
                    error_result = {
                        "bill_id": batch[j].id,
                        "issues": [],
                        "metadata": {
                            "extraction_timestamp": datetime.now().isoformat(),
                            "error": str(result),
                            "model_used": "gpt-4",
                            "extractor_version": "1.0.0",
                        },
                        "status": "failed",
                    }
                    results.append(error_result)
                else:
                    results.append(result)

            # Rate limiting between batches
            if i + batch_size < len(bills):
                await asyncio.sleep(delay_between_batches)

        self.logger.info(f"Batch extraction completed: {len(results)} results")

        return results

    async def health_check(self) -> bool:
        """Check if the service is healthy."""
        try:
            test_bill = BillData(
                id="health_check",
                title="テスト法案",
                outline="健康チェック用のテスト法案です。",
            )

            issues = await self.extract_dual_level_issues(test_bill)
            return len(issues) > 0

        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False

    def get_statistics(self) -> dict[str, Any]:
        """Get service statistics."""
        return {
            "service_name": "PolicyIssueExtractor",
            "version": "1.0.0",
            "model": "gpt-4",
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "validator_class": "IssueValidator",
            "supported_levels": ["high_school", "general_reader"],
            "max_characters": 60,
            "language": "japanese",
        }
