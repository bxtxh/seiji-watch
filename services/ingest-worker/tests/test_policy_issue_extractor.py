"""
Unit tests for Policy Issue Extractor Service.
Tests dual-level extraction, validation, and quality assessment.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import json

# Import the components to test
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from services.policy_issue_extractor import (
    PolicyIssueExtractor, 
    DualLevelIssue, 
    BillData,
    VocabularyLevelValidator,
    VerbEndingValidator
)


class TestDualLevelIssue:
    """Test the DualLevelIssue Pydantic model."""
    
    def test_valid_dual_level_issue(self):
        """Test creating a valid dual-level issue."""
        issue = DualLevelIssue(
            label_lv1="高校生向けの政策課題を説明する",
            label_lv2="一般読者向けの詳細な政策課題を詳しく説明する",
            confidence=0.85
        )
        
        assert issue.label_lv1 == "高校生向けの政策課題を説明する"
        assert issue.label_lv2 == "一般読者向けの詳細な政策課題を詳しく説明する"
        assert issue.confidence == 0.85
    
    def test_label_length_validation(self):
        """Test label length validation."""
        # Test label too short
        with pytest.raises(ValueError, match="Label_Lv1 must be between 10 and 60 characters"):
            DualLevelIssue(
                label_lv1="短い",
                label_lv2="一般読者向けの政策課題を説明する",
                confidence=0.8
            )
        
        # Test label too long
        with pytest.raises(ValueError, match="Label_Lv1 must be between 10 and 60 characters"):
            DualLevelIssue(
                label_lv1="非常に長いラベルで六十文字を超えてしまう可能性がある内容をテストするためのラベル",
                label_lv2="一般読者向けの政策課題を説明する",
                confidence=0.8
            )
    
    @patch('services.policy_issue_extractor.VerbEndingValidator.is_valid_verb_ending')
    def test_verb_ending_validation(self, mock_verb_validator):
        """Test verb ending validation."""
        mock_verb_validator.return_value = False
        
        with pytest.raises(ValueError, match="Label_Lv1 must end with a verb"):
            DualLevelIssue(
                label_lv1="高校生向けの政策課題",  # No verb ending
                label_lv2="一般読者向けの政策課題を説明する",
                confidence=0.8
            )
    
    @patch('services.policy_issue_extractor.VocabularyLevelValidator.is_high_school_appropriate')
    def test_vocabulary_level_validation(self, mock_vocab_validator):
        """Test vocabulary level validation."""
        mock_vocab_validator.return_value = False
        
        with pytest.raises(ValueError, match="Label_Lv1 contains vocabulary too advanced for high school level"):
            DualLevelIssue(
                label_lv1="高校生向けの複雑な政策課題を説明する",
                label_lv2="一般読者向けの政策課題を説明する",
                confidence=0.8
            )
    
    def test_confidence_validation(self):
        """Test confidence score validation."""
        # Test confidence too low
        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            DualLevelIssue(
                label_lv1="高校生向けの政策課題を説明する",
                label_lv2="一般読者向けの政策課題を説明する",
                confidence=-0.1
            )
        
        # Test confidence too high
        with pytest.raises(ValueError, match="Confidence must be between 0.0 and 1.0"):
            DualLevelIssue(
                label_lv1="高校生向けの政策課題を説明する",
                label_lv2="一般読者向けの政策課題を説明する",
                confidence=1.1
            )


class TestVerbEndingValidator:
    """Test the Japanese verb ending validator."""
    
    def test_valid_verb_endings(self):
        """Test recognition of valid verb endings."""
        validator = VerbEndingValidator()
        
        valid_endings = [
            "政策を説明する",
            "課題を解決する",
            "制度を改善する",
            "法案を検討する",
            "問題を対処する"
        ]
        
        for text in valid_endings:
            assert validator.is_valid_verb_ending(text), f"Should recognize '{text}' as valid verb ending"
    
    def test_invalid_verb_endings(self):
        """Test rejection of invalid verb endings."""
        validator = VerbEndingValidator()
        
        invalid_endings = [
            "政策課題",
            "重要な問題",
            "社会保障制度",
            "経済政策について",
            "環境問題の"
        ]
        
        for text in invalid_endings:
            assert not validator.is_valid_verb_ending(text), f"Should reject '{text}' as invalid verb ending"
    
    def test_compound_verb_handling(self):
        """Test handling of compound verbs."""
        validator = VerbEndingValidator()
        
        compound_verbs = [
            "制度を見直していく",
            "政策を検討していきたい",
            "課題に取り組んでいる"
        ]
        
        for text in compound_verbs:
            assert validator.is_valid_verb_ending(text), f"Should handle compound verb '{text}'"


class TestVocabularyLevelValidator:
    """Test the vocabulary level validator."""
    
    def test_high_school_appropriate_vocabulary(self):
        """Test recognition of high school appropriate vocabulary."""
        validator = VocabularyLevelValidator()
        
        appropriate_texts = [
            "学校の政策を説明する",
            "社会の問題を解決する",
            "環境を守る取り組み",
            "経済の仕組みを理解する"
        ]
        
        for text in appropriate_texts:
            assert validator.is_high_school_appropriate(text), f"Should accept '{text}' as high school appropriate"
    
    def test_advanced_vocabulary_detection(self):
        """Test detection of advanced vocabulary."""
        validator = VocabularyLevelValidator()
        
        advanced_texts = [
            "施策の実効性を検証する",
            "制度の包括的な見直し",
            "多面的なアプローチを検討",
            "法的枠組みの整備"
        ]
        
        for text in advanced_texts:
            assert not validator.is_high_school_appropriate(text), f"Should reject '{text}' as too advanced"


class TestBillData:
    """Test the BillData model."""
    
    def test_valid_bill_data(self):
        """Test creating valid bill data."""
        bill = BillData(
            id="bill_001",
            title="テスト法案",
            outline="法案の概要",
            background_context="背景説明",
            expected_effects="期待される効果",
            key_provisions=["主要条項1", "主要条項2"],
            submitter="提出者",
            category="社会保障"
        )
        
        assert bill.id == "bill_001"
        assert bill.title == "テスト法案"
        assert len(bill.key_provisions) == 2
    
    def test_bill_data_validation(self):
        """Test bill data validation."""
        with pytest.raises(ValueError):
            BillData(
                id="",  # Empty ID should fail
                title="テスト法案"
            )


class TestPolicyIssueExtractor:
    """Test the main PolicyIssueExtractor class."""
    
    @pytest.fixture
    def extractor(self):
        """Create a PolicyIssueExtractor instance for testing."""
        return PolicyIssueExtractor()
    
    @pytest.fixture
    def sample_bill_data(self):
        """Create sample bill data for testing."""
        return BillData(
            id="test_bill_001",
            title="介護保険制度改正法案",
            outline="高齢者の介護負担を軽減し、制度の持続可能性を確保する",
            background_context="高齢化社会の進展により介護需要が増加している",
            expected_effects="介護費用の削減と質の向上が期待される",
            key_provisions=["自己負担率の見直し", "サービス提供体制の強化"],
            submitter="厚生労働省",
            category="社会保障"
        )
    
    def test_extractor_initialization(self, extractor):
        """Test extractor initialization."""
        assert extractor.client is not None
        assert extractor.model_name == "gpt-4"
        assert extractor.max_tokens == 800
        assert extractor.temperature == 0.2
    
    def test_system_prompt_generation(self, extractor):
        """Test system prompt generation."""
        system_prompt = extractor._get_system_prompt()
        
        assert "政策イシュー抽出専門家" in system_prompt
        assert "高校生向け" in system_prompt
        assert "一般読者向け" in system_prompt
        assert "JSON形式" in system_prompt
    
    def test_dual_level_prompt_building(self, extractor, sample_bill_data):
        """Test dual-level prompt building."""
        prompt = extractor._build_dual_level_prompt(sample_bill_data)
        
        assert sample_bill_data.title in prompt
        assert sample_bill_data.outline in prompt
        assert "高校生レベル" in prompt
        assert "一般読者レベル" in prompt
    
    @patch('openai.AsyncOpenAI')
    async def test_successful_extraction(self, mock_openai_client, extractor, sample_bill_data):
        """Test successful issue extraction."""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "label_lv1": "介護制度の負担を軽くする",
            "label_lv2": "高齢者介護保険制度の持続可能性を確保する",
            "confidence": 0.85
        })
        
        mock_client_instance = AsyncMock()
        mock_client_instance.chat.completions.create.return_value = mock_response
        mock_openai_client.return_value = mock_client_instance
        
        extractor.client = mock_client_instance
        
        issues = await extractor.extract_dual_level_issues(sample_bill_data)
        
        assert len(issues) == 1
        assert issues[0].label_lv1 == "介護制度の負担を軽くする"
        assert issues[0].label_lv2 == "高齢者介護保険制度の持続可能性を確保する"
        assert issues[0].confidence == 0.85
    
    @patch('openai.AsyncOpenAI')
    async def test_malformed_response_handling(self, mock_openai_client, extractor, sample_bill_data):
        """Test handling of malformed LLM responses."""
        # Mock malformed response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Invalid JSON response"
        
        mock_client_instance = AsyncMock()
        mock_client_instance.chat.completions.create.return_value = mock_response
        mock_openai_client.return_value = mock_client_instance
        
        extractor.client = mock_client_instance
        
        issues = await extractor.extract_dual_level_issues(sample_bill_data)
        
        # Should return empty list for malformed responses
        assert len(issues) == 0
    
    @patch('openai.AsyncOpenAI')
    async def test_api_error_handling(self, mock_openai_client, extractor, sample_bill_data):
        """Test handling of API errors."""
        mock_client_instance = AsyncMock()
        mock_client_instance.chat.completions.create.side_effect = Exception("API Error")
        mock_openai_client.return_value = mock_client_instance
        
        extractor.client = mock_client_instance
        
        issues = await extractor.extract_dual_level_issues(sample_bill_data)
        
        # Should return empty list on API errors
        assert len(issues) == 0
    
    @patch('openai.AsyncOpenAI')
    async def test_extraction_with_metadata(self, mock_openai_client, extractor, sample_bill_data):
        """Test extraction with metadata collection."""
        # Mock successful response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "label_lv1": "介護制度を改善する",
            "label_lv2": "介護保険制度の包括的な見直しを実施する",
            "confidence": 0.9
        })
        
        mock_client_instance = AsyncMock()
        mock_client_instance.chat.completions.create.return_value = mock_response
        mock_openai_client.return_value = mock_client_instance
        
        extractor.client = mock_client_instance
        
        result = await extractor.extract_issues_with_metadata(sample_bill_data)
        
        assert result["status"] == "success"
        assert len(result["issues"]) == 1
        assert "metadata" in result
        assert "extraction_time_ms" in result["metadata"]
        assert "model_used" in result["metadata"]
    
    @patch('openai.AsyncOpenAI')
    async def test_batch_extraction(self, mock_openai_client, extractor):
        """Test batch extraction of multiple bills."""
        bills = [
            BillData(id="bill_1", title="法案1", outline="概要1"),
            BillData(id="bill_2", title="法案2", outline="概要2")
        ]
        
        # Mock responses for batch
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "label_lv1": "政策課題を解決する",
            "label_lv2": "包括的な政策課題の解決を図る",
            "confidence": 0.8
        })
        
        mock_client_instance = AsyncMock()
        mock_client_instance.chat.completions.create.return_value = mock_response
        mock_openai_client.return_value = mock_client_instance
        
        extractor.client = mock_client_instance
        
        results = await extractor.batch_extract_issues(bills)
        
        assert len(results) == 2
        for result in results:
            assert result["status"] == "success"
            assert len(result["issues"]) == 1
    
    async def test_quality_calculation(self, extractor):
        """Test quality score calculation."""
        issue = DualLevelIssue(
            label_lv1="高校生向けの政策課題を説明する",
            label_lv2="一般読者向けの詳細な政策課題を詳しく説明する",
            confidence=0.9
        )
        
        quality_score = extractor._calculate_quality_score(issue)
        
        assert 0.0 <= quality_score <= 1.0
        assert quality_score > 0.5  # Should be reasonably high for good issue
    
    async def test_health_check(self, extractor):
        """Test health check functionality."""
        # Mock successful API test
        with patch.object(extractor, 'extract_dual_level_issues') as mock_extract:
            mock_extract.return_value = [Mock()]
            
            is_healthy = await extractor.health_check()
            assert is_healthy is True
    
    async def test_health_check_failure(self, extractor):
        """Test health check failure handling."""
        # Mock API failure
        with patch.object(extractor, 'extract_dual_level_issues') as mock_extract:
            mock_extract.side_effect = Exception("API Error")
            
            is_healthy = await extractor.health_check()
            assert is_healthy is False


@pytest.mark.asyncio
class TestIntegration:
    """Integration tests for the complete extraction pipeline."""
    
    async def test_end_to_end_extraction_pipeline(self):
        """Test the complete extraction pipeline end-to-end."""
        # This test would require actual API keys and should be run in integration environment
        pass
    
    async def test_validation_pipeline(self):
        """Test the complete validation pipeline."""
        # Create issue that should pass all validations
        issue_data = {
            "label_lv1": "学校教育制度を改善する",
            "label_lv2": "義務教育制度の包括的な見直しを実施する",
            "confidence": 0.85
        }
        
        # Test creation with validation
        issue = DualLevelIssue(**issue_data)
        assert issue.label_lv1 == issue_data["label_lv1"]
        assert issue.confidence == issue_data["confidence"]


# Test configuration and fixtures
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Helper functions for testing
def create_mock_openai_response(content: str):
    """Create a mock OpenAI API response."""
    mock_response = Mock()
    mock_response.choices = [Mock()]
    mock_response.choices[0].message.content = content
    return mock_response


def create_test_bill_data(bill_id: str = "test_001", **kwargs):
    """Create test bill data with defaults."""
    defaults = {
        "id": bill_id,
        "title": "テスト法案",
        "outline": "法案の概要説明",
        "background_context": "背景コンテキスト",
        "expected_effects": "期待される効果",
        "key_provisions": ["条項1", "条項2"],
        "submitter": "提出者",
        "category": "テスト"
    }
    defaults.update(kwargs)
    return BillData(**defaults)


if __name__ == "__main__":
    # Run tests with: python -m pytest test_policy_issue_extractor.py -v
    pytest.main([__file__, "-v"])