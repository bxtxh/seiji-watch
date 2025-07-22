"""
Airtable Security Utilities
Provides secure query escaping and validation for Airtable formulas.
"""

import logging
import re

logger = logging.getLogger(__name__)


class AirtableQueryEscaper:
    """Secure query escaping for Airtable formulas."""

    # Characters that need escaping in Airtable formulas
    ESCAPE_CHARS = {
        "'": "\\'",
        '"': '\\"',
        "\\": "\\\\",
        "\n": "\\n",
        "\r": "\\r",
        "\t": "\\t",
    }

    # Dangerous patterns that should be blocked
    DANGEROUS_PATTERNS = [
        r"';.*--",  # SQL injection patterns
        r"'.*OR.*'.*=.*'",  # OR injection
        r"'.*UNION.*",  # UNION injection
        r"'.*DROP.*",  # DROP statements
        r"'.*DELETE.*",  # DELETE statements
        r"'.*UPDATE.*",  # UPDATE statements
        r"'.*INSERT.*",  # INSERT statements
        r"javascript:",  # JavaScript injection
        r"<script",  # XSS attempts
        r"eval\(",  # Code execution
        r"function\s*\(",  # Function definitions
    ]

    @classmethod
    def escape_string(cls, text: str) -> str:
        """Safely escape a string for use in Airtable formulas."""
        if not isinstance(text, str):
            text = str(text)

        # Check for dangerous patterns
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning(
                    f"Potentially dangerous query pattern detected: {pattern}"
                )
                # Replace with safe placeholder
                text = re.sub(pattern, "[FILTERED]", text, flags=re.IGNORECASE)

        # Escape special characters
        for char, escaped in cls.ESCAPE_CHARS.items():
            text = text.replace(char, escaped)

        # Limit length to prevent DoS
        if len(text) > 200:
            text = text[:200] + "..."
            logger.warning("Query truncated due to length limit")

        return text

    @classmethod
    def build_search_formula(cls, query: str, fields: list[str]) -> str:
        """Build a safe search formula for multiple fields."""
        escaped_query = cls.escape_string(query)

        # Build OR condition for searching across multiple fields
        search_conditions = []
        for field in fields:
            # Validate field name (only allow alphanumeric and underscores)
            if not re.match(r"^[a-zA-Z0-9_]+$", field):
                logger.error(f"Invalid field name: {field}")
                continue

            search_conditions.append(f"FIND('{escaped_query}', {{{field}}}) > 0")

        if not search_conditions:
            return "FALSE()"  # No valid fields

        return "OR(" + ", ".join(search_conditions) + ")"

    @classmethod
    def build_filter_formula(cls, conditions: list[str]) -> str:
        """Build a safe filter formula from multiple conditions."""
        # Validate each condition
        safe_conditions = []
        for condition in conditions:
            # Basic validation - must contain field reference and operator
            if not re.match(r"^{[a-zA-Z0-9_]+}\s*(=|!=|>|<|>=|<=)\s*", condition):
                logger.error(f"Invalid condition format: {condition}")
                continue
            safe_conditions.append(condition)

        if not safe_conditions:
            return "TRUE()"  # No conditions means no filtering

        return "AND(" + ", ".join(safe_conditions) + ")"


class AirtableInputValidator:
    """Validates inputs for Airtable operations."""

    @staticmethod
    def validate_record_id(record_id: str) -> bool:
        """Validate Airtable record ID format."""
        pattern = r"^rec[a-zA-Z0-9]{14}$"
        return bool(re.match(pattern, record_id))

    @staticmethod
    def validate_field_name(field_name: str) -> bool:
        """Validate field name contains only safe characters."""
        pattern = r"^[a-zA-Z0-9_]+$"
        return bool(re.match(pattern, field_name)) and len(field_name) <= 50

    @staticmethod
    def validate_status_value(status: str) -> bool:
        """Validate status value is in allowed list."""
        allowed_statuses = {"pending", "approved", "rejected", "failed_validation"}
        return status in allowed_statuses

    @staticmethod
    def sanitize_text_input(text: str, max_length: int = 1000) -> str:
        """Sanitize text input for storage."""
        if not isinstance(text, str):
            text = str(text)

        # Remove or escape dangerous characters
        text = re.sub(r'[<>"\']', "", text)  # Remove HTML/quote chars
        text = re.sub(
            r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", text
        )  # Remove control chars

        # Limit length
        if len(text) > max_length:
            text = text[:max_length]

        return text.strip()


# Global instances
query_escaper = AirtableQueryEscaper()
input_validator = AirtableInputValidator()
