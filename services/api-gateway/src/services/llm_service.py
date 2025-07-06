"""LLM service for speech summarization and topic extraction."""

import os
import logging
from typing import List, Optional, Dict, Any
import openai
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)


class LLMService:
    """Service for LLM-powered intelligence features."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.client = openai.AsyncOpenAI(
            api_key=api_key or os.getenv("OPENAI_API_KEY")
        )
        if not self.client.api_key:
            raise ValueError("OpenAI API key is required")
    
    async def generate_speech_summary(self, text: str, speaker_name: Optional[str] = None) -> str:
        """Generate a one-sentence summary of a speech.
        
        Args:
            text: The speech text to summarize
            speaker_name: Optional speaker name for context
            
        Returns:
            A one-sentence summary of the speech
        """
        if not text or len(text.strip()) < 10:
            return "発言内容が短すぎるため要約できません。"
        
        # Truncate very long speeches to avoid token limits
        if len(text) > 3000:
            text = text[:3000] + "..."
        
        speaker_context = f"発言者：{speaker_name}\n" if speaker_name else ""
        
        prompt = f"""以下の国会での発言を、1文で要約してください。要約は簡潔で分かりやすく、発言の核心的な内容を捉えるようにしてください。

{speaker_context}発言内容：
{text}

要約（1文）："""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system", 
                        "content": "あなたは国会議事録の専門要約者です。発言内容を1文で簡潔かつ正確に要約してください。政治的偏向を避け、客観的な要約を心がけてください。"
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=100,
                temperature=0.3
            )
            
            summary = response.choices[0].message.content.strip()
            
            # Ensure the summary is not too long
            if len(summary) > 150:
                summary = summary[:147] + "..."
            
            return summary
            
        except Exception as e:
            logger.error(f"Failed to generate speech summary: {e}")
            # Fallback to truncated text
            fallback = text[:100].strip()
            if len(text) > 100:
                fallback += "..."
            return fallback
    
    async def extract_speech_topics(self, text: str, speaker_name: Optional[str] = None) -> List[str]:
        """Extract 3 key topics/tags from a speech.
        
        Args:
            text: The speech text to analyze
            speaker_name: Optional speaker name for context
            
        Returns:
            List of 3 topic tags
        """
        if not text or len(text.strip()) < 20:
            return ["短い発言"]
        
        # Truncate very long speeches
        if len(text) > 3000:
            text = text[:3000] + "..."
        
        speaker_context = f"発言者：{speaker_name}\n" if speaker_name else ""
        
        # Predefined categories for consistency
        categories = [
            "予算・決算", "税制", "社会保障", "外交・国際", "経済・産業", "教育", 
            "環境", "防衛", "法務", "労働", "農業", "医療・健康", "科学技術",
            "地方自治", "選挙制度", "憲法", "災害対策", "交通・インフラ",
            "文化・スポーツ", "その他"
        ]
        
        categories_str = "、".join(categories)
        
        prompt = f"""以下の国会での発言から、3つの主要なトピック・テーマを抽出してください。

利用可能なカテゴリ：
{categories_str}

上記のカテゴリから最も適切なものを選んで3つ挙げてください。上記にない場合は、適切な日本語のキーワードを使用してください。

{speaker_context}発言内容：
{text}

トピック（3つ、カンマ区切り）："""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "あなたは国会議事録の専門分析者です。発言内容から主要なトピックを正確に抽出してください。政治的偏向を避け、客観的な分析を心がけてください。"
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=50,
                temperature=0.3
            )
            
            topics_text = response.choices[0].message.content.strip()
            
            # Parse the response into a list
            topics = [topic.strip() for topic in topics_text.split("、") if topic.strip()]
            if len(topics) == 1:
                # Try comma separation
                topics = [topic.strip() for topic in topics_text.split(",") if topic.strip()]
            
            # Ensure we have exactly 3 topics
            if len(topics) > 3:
                topics = topics[:3]
            elif len(topics) < 3:
                # Add default topics if needed
                while len(topics) < 3:
                    topics.append("その他")
            
            return topics
            
        except Exception as e:
            logger.error(f"Failed to extract speech topics: {e}")
            # Fallback topics
            return ["一般議論", "国会質疑", "その他"]
    
    async def batch_process_speeches(self, speeches: List[Dict[str, Any]], 
                                   generate_summaries: bool = True,
                                   extract_topics: bool = True) -> List[Dict[str, Any]]:
        """Process multiple speeches in batch for efficiency.
        
        Args:
            speeches: List of speech dictionaries with 'original_text' and optional 'speaker_name'
            generate_summaries: Whether to generate summaries
            extract_topics: Whether to extract topics
            
        Returns:
            List of speech dictionaries with added 'summary' and/or 'topics' fields
        """
        tasks = []
        
        for speech in speeches:
            text = speech.get("original_text", "")
            speaker_name = speech.get("speaker_name")
            
            speech_tasks = []
            if generate_summaries:
                speech_tasks.append(self.generate_speech_summary(text, speaker_name))
            if extract_topics:
                speech_tasks.append(self.extract_speech_topics(text, speaker_name))
            
            if speech_tasks:
                tasks.append(speech_tasks)
        
        if not tasks:
            return speeches
        
        # Process in batches to avoid rate limiting
        batch_size = 5
        results = []
        
        for i in range(0, len(tasks), batch_size):
            batch_tasks = tasks[i:i + batch_size]
            
            # Flatten tasks for this batch
            flat_tasks = []
            for speech_tasks in batch_tasks:
                flat_tasks.extend(speech_tasks)
            
            # Process batch
            batch_results = await asyncio.gather(*flat_tasks, return_exceptions=True)
            
            # Reorganize results back to speeches
            batch_speeches = speeches[i:i + batch_size]
            result_idx = 0
            
            for j, speech in enumerate(batch_speeches):
                processed_speech = speech.copy()
                
                if generate_summaries:
                    summary_result = batch_results[result_idx]
                    if isinstance(summary_result, Exception):
                        logger.error(f"Summary generation failed: {summary_result}")
                        processed_speech["summary"] = "要約生成に失敗しました。"
                    else:
                        processed_speech["summary"] = summary_result
                    result_idx += 1
                
                if extract_topics:
                    topics_result = batch_results[result_idx]
                    if isinstance(topics_result, Exception):
                        logger.error(f"Topic extraction failed: {topics_result}")
                        processed_speech["topics"] = ["処理失敗"]
                    else:
                        processed_speech["topics"] = topics_result
                    result_idx += 1
                
                results.append(processed_speech)
            
            # Rate limiting: wait between batches
            if i + batch_size < len(tasks):
                await asyncio.sleep(1)
        
        return results
    
    async def health_check(self) -> bool:
        """Check if OpenAI API is accessible."""
        try:
            response = await self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "健康チェック"}],
                max_tokens=5
            )
            return True
        except Exception as e:
            logger.error(f"LLM service health check failed: {e}")
            return False