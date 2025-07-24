"""
Speech-to-Text client using OpenAI Whisper API for Japanese transcription.
"""
import logging
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

import requests
import yt_dlp

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    """Result of speech-to-text transcription"""
    text: str
    language: str
    duration: float
    confidence: float | None = None
    segments: list[dict] | None = None


class WhisperClient:
    """OpenAI Whisper API client for Japanese speech recognition"""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required")

        self.base_url = "https://api.openai.com/v1/audio/transcriptions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}"
        }

        # yt-dlp configuration for audio extraction
        self.yt_dlp_opts = {
            'format': 'bestaudio/best',
            'extractaudio': True,
            'audioformat': 'mp3',
            'outtmpl': '%(title)s.%(ext)s',
            'quiet': True,
            'no_warnings': True
        }

    def transcribe_audio_file(
        self,
        audio_file_path: str,
        language: str = "ja",
        model: str = "whisper-1"
    ) -> TranscriptionResult:
        """
        Transcribe audio file using OpenAI Whisper API

        Args:
            audio_file_path: Path to audio file
            language: Language code (default: "ja" for Japanese)
            model: Whisper model to use (default: "whisper-1")

        Returns:
            TranscriptionResult with transcribed text and metadata
        """
        if not os.path.exists(audio_file_path):
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        try:
            # Prepare the request
            with open(audio_file_path, 'rb') as audio_file:
                files = {
                    'file': audio_file,
                    'model': (None, model),
                    'language': (None, language),
                    'response_format': (None, 'verbose_json'),
                    'temperature': (None, '0')
                }

                logger.info(f"Transcribing audio file: {audio_file_path}")
                response = requests.post(
                    self.base_url,
                    headers=self.headers,
                    files=files,
                    timeout=300  # 5 minutes timeout for large files
                )

                response.raise_for_status()
                result = response.json()

                return TranscriptionResult(
                    text=result.get('text', ''),
                    language=result.get('language', language),
                    duration=result.get('duration', 0.0),
                    segments=result.get('segments', [])
                )

        except requests.RequestException as e:
            logger.error(f"API request failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise

    def download_and_transcribe_video(
        self,
        video_url: str,
        output_dir: str | None = None
    ) -> tuple[TranscriptionResult, str]:
        """
        Download video from URL and transcribe its audio

        Args:
            video_url: URL to video (supports YouTube, Diet TV, etc.)
            output_dir: Directory to save temporary files

        Returns:
            Tuple of (TranscriptionResult, audio_file_path)
        """
        if not output_dir:
            output_dir = tempfile.mkdtemp()

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        try:
            # Configure yt-dlp for this download
            yt_opts = self.yt_dlp_opts.copy()
            yt_opts['outtmpl'] = str(output_path / '%(title)s.%(ext)s')

            # Download and extract audio
            with yt_dlp.YoutubeDL(yt_opts) as ydl:
                logger.info(f"Downloading audio from: {video_url}")
                ydl.extract_info(video_url, download=True)

                # Find the downloaded audio file
                audio_file = None
                for file_path in output_path.glob("*"):
                    if file_path.is_file() and file_path.suffix in ['.mp3', '.wav', '.m4a']:
                        audio_file = str(file_path)
                        break

                if not audio_file:
                    raise RuntimeError("Could not find downloaded audio file")

                logger.info(f"Audio downloaded to: {audio_file}")

                # Transcribe the audio
                transcription = self.transcribe_audio_file(audio_file)

                return transcription, audio_file

        except Exception as e:
            logger.error(f"Video download and transcription failed: {e}")
            raise

    def calculate_wer(self, reference: str, hypothesis: str) -> float:
        """
        Calculate Word Error Rate (WER) between reference and hypothesis text

        Args:
            reference: Reference (ground truth) text
            hypothesis: Hypothesis (transcribed) text

        Returns:
            WER as a float between 0.0 and 1.0
        """
        # Simple WER calculation - can be improved with proper alignment
        ref_words = reference.split()
        hyp_words = hypothesis.split()

        if len(ref_words) == 0:
            return 1.0 if len(hyp_words) > 0 else 0.0

        # Use Levenshtein distance for word-level comparison
        distances = [[0] * (len(hyp_words) + 1) for _ in range(len(ref_words) + 1)]

        # Initialize first row and column
        for i in range(len(ref_words) + 1):
            distances[i][0] = i
        for j in range(len(hyp_words) + 1):
            distances[0][j] = j

        # Fill the distance matrix
        for i in range(1, len(ref_words) + 1):
            for j in range(1, len(hyp_words) + 1):
                if ref_words[i-1] == hyp_words[j-1]:
                    distances[i][j] = distances[i-1][j-1]
                else:
                    distances[i][j] = min(
                        distances[i-1][j] + 1,      # deletion
                        distances[i][j-1] + 1,      # insertion
                        distances[i-1][j-1] + 1     # substitution
                    )

        wer = distances[len(ref_words)][len(hyp_words)] / len(ref_words)
        return min(wer, 1.0)

    def validate_transcription_quality(
        self,
        transcription: TranscriptionResult,
        max_wer: float = 0.15
    ) -> bool:
        """
        Validate transcription quality based on WER threshold

        Args:
            transcription: TranscriptionResult to validate
            max_wer: Maximum acceptable WER (default: 0.15 as per requirements)

        Returns:
            True if transcription meets quality standards
        """
        # For now, we'll use heuristics since we don't have reference text
        # In production, this would compare against known reference transcripts

        # Check if text is not empty and has reasonable length
        if not transcription.text or len(transcription.text.strip()) < 10:
            logger.warning("Transcription too short or empty")
            return False

        # Check for excessive repetition (indicates poor transcription)
        words = transcription.text.split()
        if len(words) > 10:
            unique_words = set(words)
            repetition_rate = 1.0 - (len(unique_words) / len(words))
            if repetition_rate > 0.5:  # More than 50% repetition
                logger.warning(f"High repetition rate: {repetition_rate:.2f}")
                return False

        # Check for reasonable Japanese content (basic check)
        # This is a simplified check - can be improved with proper Japanese text analysis
        japanese_chars = sum(1 for c in transcription.text if ord(c) > 127)
        if japanese_chars < len(transcription.text) * 0.3:  # At least 30% non-ASCII
            logger.warning("Low Japanese character ratio")
            return False

        logger.info("Transcription quality validation passed")
        return True


# Example usage and testing
if __name__ == "__main__":
    # Test the WhisperClient
    logging.basicConfig(level=logging.INFO)

    # Test WER calculation (doesn't require API key)
    try:
        # Create a dummy client for testing WER calculation only
        import os
        os.environ["OPENAI_API_KEY"] = "test_key"  # Temporary for testing
        client = WhisperClient()

        # Test WER calculation
        ref = "これは日本語のテストです"
        hyp = "これは日本語のテストです"
        wer = client.calculate_wer(ref, hyp)
        logger.info(f"WER test (identical): {wer}")

        hyp2 = "これは英語のテストです"
        wer2 = client.calculate_wer(ref, hyp2)
        logger.info(f"WER test (1 word diff): {wer2}")

        # Test transcription quality validation
        from dataclasses import dataclass

        # Test good transcription
        good_result = TranscriptionResult(
            text="これは国会での審議についての議事録です。法案について詳細に議論されました。",
            language="ja",
            duration=60.0
        )
        is_valid = client.validate_transcription_quality(good_result)
        logger.info(f"Quality validation (good): {is_valid}")

        # Test poor transcription
        poor_result = TranscriptionResult(
            text="abc abc abc abc abc",
            language="ja",
            duration=60.0
        )
        is_valid2 = client.validate_transcription_quality(poor_result)
        logger.info(f"Quality validation (poor): {is_valid2}")

        logger.info("WhisperClient tests completed successfully")

    except Exception as e:
        logger.error(f"WhisperClient test failed: {e}")
    finally:
        # Clean up test environment variable
        if "OPENAI_API_KEY" in os.environ and os.environ["OPENAI_API_KEY"] == "test_key":
            del os.environ["OPENAI_API_KEY"]
