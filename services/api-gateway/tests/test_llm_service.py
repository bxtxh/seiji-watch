"""Tests for LLM service."""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from services.llm_service import LLMService


class TestLLMService:
    """Test cases for LLM service."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_openai_response = AsyncMock()
        self.mock_openai_response.choices = [
            AsyncMock(message=AsyncMock(content="テスト要約です。"))
        ]
    
    @pytest.mark.asyncio
    async def test_generate_speech_summary_success(self):
        """Test successful speech summary generation."""
        with patch("services.llm_service.openai.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create.return_value = self.mock_openai_response
            mock_openai.return_value = mock_client
            
            llm_service = LLMService(api_key="test-key")
            
            result = await llm_service.generate_speech_summary(
                "これは国会での発言のテストです。重要な政策について議論しています。",
                "テスト議員"
            )
            
            assert result == "テスト要約です。"
            mock_client.chat.completions.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_speech_summary_short_text(self):
        """Test speech summary with short text."""
        llm_service = LLMService(api_key="test-key")
        
        result = await llm_service.generate_speech_summary("短い", "テスト議員")
        
        assert result == "発言内容が短すぎるため要約できません。"
    
    @pytest.mark.asyncio
    async def test_generate_speech_summary_api_error(self):
        """Test speech summary with API error."""
        with patch("services.llm_service.openai.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create.side_effect = Exception("API Error")
            mock_openai.return_value = mock_client
            
            llm_service = LLMService(api_key="test-key")
            
            long_text = "これは国会での発言のテストです。" * 10
            result = await llm_service.generate_speech_summary(long_text, "テスト議員")
            
            # Should return fallback (truncated text)
            assert result.startswith("これは国会での発言のテストです。")
            assert result.endswith("...")
    
    @pytest.mark.asyncio
    async def test_extract_speech_topics_success(self):
        """Test successful topic extraction."""
        mock_topics_response = AsyncMock()
        mock_topics_response.choices = [
            AsyncMock(message=AsyncMock(content="予算・決算、社会保障、その他"))
        ]
        
        with patch("services.llm_service.openai.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create.return_value = mock_topics_response
            mock_openai.return_value = mock_client
            
            llm_service = LLMService(api_key="test-key")
            
            result = await llm_service.extract_speech_topics(
                "予算について議論し、社会保障制度の改革を提案します。",
                "テスト議員"
            )
            
            assert result == ["予算・決算", "社会保障", "その他"]
    
    @pytest.mark.asyncio
    async def test_extract_speech_topics_short_text(self):
        """Test topic extraction with short text."""
        llm_service = LLMService(api_key="test-key")
        
        result = await llm_service.extract_speech_topics("短い", "テスト議員")
        
        assert result == ["短い発言"]
    
    @pytest.mark.asyncio
    async def test_batch_process_speeches(self):
        """Test batch processing of speeches."""
        mock_summary_response = AsyncMock()
        mock_summary_response.choices = [
            AsyncMock(message=AsyncMock(content="要約1です。"))
        ]
        
        mock_topics_response = AsyncMock()
        mock_topics_response.choices = [
            AsyncMock(message=AsyncMock(content="トピック1、トピック2、トピック3"))
        ]
        
        with patch("services.llm_service.openai.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create.side_effect = [
                mock_summary_response, mock_topics_response
            ]
            mock_openai.return_value = mock_client
            
            llm_service = LLMService(api_key="test-key")
            
            speeches = [
                {
                    "original_text": "テスト発言です。" * 10,
                    "speaker_name": "テスト議員"
                }
            ]
            
            result = await llm_service.batch_process_speeches(
                speeches, 
                generate_summaries=True, 
                extract_topics=True
            )
            
            assert len(result) == 1
            assert result[0]["summary"] == "要約1です。"
            assert result[0]["topics"] == ["トピック1", "トピック2", "トピック3"]
    
    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check."""
        with patch("services.llm_service.openai.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create.return_value = self.mock_openai_response
            mock_openai.return_value = mock_client
            
            llm_service = LLMService(api_key="test-key")
            
            result = await llm_service.health_check()
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test health check failure."""
        with patch("services.llm_service.openai.AsyncOpenAI") as mock_openai:
            mock_client = AsyncMock()
            mock_client.chat.completions.create.side_effect = Exception("API Error")
            mock_openai.return_value = mock_client
            
            llm_service = LLMService(api_key="test-key")
            
            result = await llm_service.health_check()
            
            assert result is False