"""Input validation and sanitization utilities for API Gateway."""

import html
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class InputValidator:
    """Input validation and sanitization utilities."""

    # Security patterns to detect malicious input
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"vbscript:",
        r"on\w+\s*=",
        r"expression\s*\(",
        r"@import",
        r"<iframe[^>]*>",
        r"<object[^>]*>",
        r"<embed[^>]*>",
        r"<link[^>]*>",
        r"<meta[^>]*>",
    ]

    SQL_INJECTION_PATTERNS = [
        r"union\s+select",
        r"drop\s+table",
        r"delete\s+from",
        r"insert\s+into",
        r"update\s+\w+\s+set",
        r"exec\s*\(",
        r"sp_\w+",
        r"xp_\w+",
        r";\s*--",
        r"\'\s*or\s*\'\w*\'\s*=\s*\'\w*\'",
        r"\'\s*or\s*1\s*=\s*1",
        r"0x[0-9a-f]+",
    ]

    # Character limits
    MAX_SEARCH_QUERY_LENGTH = 200
    MAX_GENERAL_TEXT_LENGTH = 1000
    MAX_URL_LENGTH = 2000

    @classmethod
    def sanitize_html(cls, text: str) -> str:
        """Sanitize HTML content to prevent XSS."""
        if not isinstance(text, str):
            return str(text)

        # HTML escape
        sanitized = html.escape(text)

        # Remove any remaining dangerous patterns
        for pattern in cls.XSS_PATTERNS:
            sanitized = re.sub(pattern, "", sanitized, flags=re.IGNORECASE)

        return sanitized

    @classmethod
    def validate_search_query(cls, query: str) -> tuple[bool, str | None]:
        """Validate search query input."""
        if not isinstance(query, str):
            return False, "Search query must be a string"

        # Length check
        if len(query) > cls.MAX_SEARCH_QUERY_LENGTH:
            return (
                False,
                f"Search query too long (max {cls.MAX_SEARCH_QUERY_LENGTH} characters)",
            )

        # Empty query check
        if not query.strip():
            return False, "Search query cannot be empty"

        # Check for SQL injection patterns
        query_lower = query.lower()
        for pattern in cls.SQL_INJECTION_PATTERNS:
            if re.search(pattern, query_lower):
                logger.warning(f"SQL injection attempt detected: {query[:50]}...")
                return False, "Invalid characters detected in search query"

        # Check for XSS patterns
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, query_lower):
                logger.warning(f"XSS attempt detected: {query[:50]}...")
                return False, "Invalid characters detected in search query"

        # Check for control characters
        if re.search(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", query):
            return False, "Invalid control characters in search query"

        return True, None

    @classmethod
    def validate_pagination_params(
        cls, limit: int, offset: int
    ) -> tuple[bool, str | None]:
        """Validate pagination parameters."""
        if not isinstance(limit, int) or not isinstance(offset, int):
            return False, "Pagination parameters must be integers"

        if limit < 1 or limit > 100:
            return False, "Limit must be between 1 and 100"

        if offset < 0:
            return False, "Offset must be non-negative"

        return True, None

    @classmethod
    def validate_certainty_threshold(cls, threshold: float) -> tuple[bool, str | None]:
        """Validate certainty threshold parameter."""
        if not isinstance(threshold, int | float):
            return False, "Certainty threshold must be a number"

        if threshold < 0.0 or threshold > 1.0:
            return False, "Certainty threshold must be between 0.0 and 1.0"

        return True, None

    @classmethod
    def sanitize_string(cls, text: str, max_length: int = None) -> str:
        """Sanitize and truncate string input."""
        if not isinstance(text, str):
            text = str(text)

        # Remove null bytes and control characters
        text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text)

        # HTML escape
        text = html.escape(text)

        # Truncate if necessary
        if max_length and len(text) > max_length:
            text = text[:max_length]

        return text.strip()

    @classmethod
    def validate_request_body(cls, body: dict[str, Any]) -> tuple[bool, str | None]:
        """Validate request body structure and content."""
        if not isinstance(body, dict):
            return False, "Request body must be a JSON object"

        # Check for reasonable body size
        if len(str(body)) > 10000:  # 10KB limit
            return False, "Request body too large"

        # Validate individual fields based on their names
        for key, value in body.items():
            if "query" in key.lower():
                if isinstance(value, str):
                    is_valid, error = cls.validate_search_query(value)
                    if not is_valid:
                        return False, f"Invalid {key}: {error}"

            elif "limit" in key.lower():
                if isinstance(value, int):
                    is_valid, error = cls.validate_pagination_params(value, 0)
                    if not is_valid:
                        return False, f"Invalid {key}: {error}"

            elif "certainty" in key.lower() or "threshold" in key.lower():
                if isinstance(value, int | float):
                    is_valid, error = cls.validate_certainty_threshold(value)
                    if not is_valid:
                        return False, f"Invalid {key}: {error}"

            elif isinstance(value, str):
                # General string validation
                if len(value) > cls.MAX_GENERAL_TEXT_LENGTH:
                    return (
                        False,
                        f"Field '{key}' too long (max {cls.MAX_GENERAL_TEXT_LENGTH} characters)",
                    )

                # Check for obvious malicious content
                value_lower = value.lower()
                for pattern in cls.XSS_PATTERNS + cls.SQL_INJECTION_PATTERNS:
                    if re.search(pattern, value_lower):
                        logger.warning(
                            f"Malicious content detected in field '{key}': {value[:50]}..."
                        )
                        return False, f"Invalid content in field '{key}'"

        return True, None


class SecurityValidator:
    """Security-focused validation utilities."""

    @staticmethod
    def validate_content_type(content_type: str | None) -> bool:
        """Validate Content-Type header."""
        if not content_type:
            return False

        allowed_types = [
            "application/json",
            "application/x-www-form-urlencoded",
            "multipart/form-data",
            "text/plain",
        ]

        # Check if content type is in allowed list
        for allowed_type in allowed_types:
            if content_type.startswith(allowed_type):
                return True

        return False

    @staticmethod
    def validate_user_agent(user_agent: str | None) -> bool:
        """Validate User-Agent header to detect bots/scanners."""
        if not user_agent:
            return True  # Allow requests without User-Agent

        # Common malicious user agents
        malicious_patterns = [
            r"sqlmap",
            r"nikto",
            r"nmap",
            r"masscan",
            r"zap",
            r"burp",
            r"acunetix",
            r"nessus",
            r"openvas",
        ]

        user_agent_lower = user_agent.lower()
        for pattern in malicious_patterns:
            if re.search(pattern, user_agent_lower):
                logger.warning(f"Malicious User-Agent detected: {user_agent}")
                return False

        return True

    @staticmethod
    def check_request_headers(headers: dict[str, str]) -> tuple[bool, str | None]:
        """Check request headers for security issues."""
        # Check Content-Type for POST requests
        content_type = headers.get("content-type", "").lower()
        if content_type and not SecurityValidator.validate_content_type(content_type):
            return False, "Invalid Content-Type header"

        # Check User-Agent
        user_agent = headers.get("user-agent", "")
        if not SecurityValidator.validate_user_agent(user_agent):
            return False, "Blocked User-Agent"

        # Check for suspicious headers
        suspicious_headers = ["x-forwarded-proto", "x-real-ip", "x-forwarded-for"]

        for header in suspicious_headers:
            value = headers.get(header, "")
            if value and len(value) > 100:  # Unusually long values
                return False, f"Suspicious {header} header"

        return True, None


def validate_and_sanitize_request(
    body: dict[str, Any] | None = None, headers: dict[str, str] | None = None
) -> tuple[bool, str | None, dict[str, Any] | None]:
    """
    Validate and sanitize incoming request.

    Returns:
        Tuple of (is_valid, error_message, sanitized_body)
    """
    # Validate headers
    if headers:
        is_valid, error = SecurityValidator.check_request_headers(headers)
        if not is_valid:
            return False, error, None

    # Validate and sanitize body
    if body:
        is_valid, error = InputValidator.validate_request_body(body)
        if not is_valid:
            return False, error, None

        # Sanitize string fields in body
        sanitized_body = {}
        for key, value in body.items():
            if isinstance(value, str):
                sanitized_body[key] = InputValidator.sanitize_string(
                    value,
                    max_length=InputValidator.MAX_SEARCH_QUERY_LENGTH
                    if "query" in key.lower()
                    else InputValidator.MAX_GENERAL_TEXT_LENGTH,
                )
            else:
                sanitized_body[key] = value

        return True, None, sanitized_body

    return True, None, body
