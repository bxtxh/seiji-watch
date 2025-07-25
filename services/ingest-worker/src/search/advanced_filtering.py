"""
Advanced filtering API for bills database.
Provides sophisticated filtering capabilities with multiple criteria and logical operators.
"""

import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Union

from sqlalchemy import and_, create_engine, func, not_, or_, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.sql import Select, select


class FilterOperator(Enum):
    """Filter operators for different data types"""

    EQUALS = "eq"
    NOT_EQUALS = "ne"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    IN = "in"
    NOT_IN = "not_in"
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"
    BETWEEN = "between"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"
    REGEX = "regex"
    FUZZY = "fuzzy"


class LogicalOperator(Enum):
    """Logical operators for combining filters"""

    AND = "and"
    OR = "or"
    NOT = "not"


class SortOrder(Enum):
    """Sort order options"""

    ASC = "asc"
    DESC = "desc"


@dataclass
class FilterCondition:
    """Individual filter condition"""

    field: str
    operator: FilterOperator
    value: Any
    case_sensitive: bool = False

    def __post_init__(self):
        # Validate operator-value compatibility
        if (
            self.operator in [FilterOperator.IS_NULL, FilterOperator.IS_NOT_NULL]
            and self.value is not None
        ):
            raise ValueError(f"Operator {self.operator.value} should not have a value")

        if (
            self.operator == FilterOperator.BETWEEN
            and not isinstance(self.value, list | tuple)
            or len(self.value) != 2
        ):
            raise ValueError(
                f"Operator {self.operator.value} requires a list/tuple of two values"
            )

        if self.operator in [
            FilterOperator.IN,
            FilterOperator.NOT_IN,
        ] and not isinstance(self.value, list | tuple):
            raise ValueError(
                f"Operator {self.operator.value} requires a list/tuple of values"
            )


@dataclass
class FilterGroup:
    """Group of filter conditions with logical operator"""

    conditions: list[Union[FilterCondition, "FilterGroup"]]
    operator: LogicalOperator = LogicalOperator.AND

    def __post_init__(self):
        if not self.conditions:
            raise ValueError("FilterGroup must have at least one condition")


@dataclass
class SortCriteria:
    """Sort criteria"""

    field: str
    order: SortOrder = SortOrder.ASC
    nulls_first: bool = False


@dataclass
class FilterQuery:
    """Complete filter query"""

    filters: FilterGroup | None = None
    sort: list[SortCriteria] = field(default_factory=list)
    limit: int | None = None
    offset: int = 0

    # Aggregation options
    group_by: list[str] = field(default_factory=list)
    having: FilterGroup | None = None

    # Additional options
    distinct: bool = False
    include_count: bool = False


@dataclass
class FilterResult:
    """Filter result with metadata"""

    data: list[dict[str, Any]]
    total_count: int | None = None
    query_time_ms: float = 0.0
    sql_query: str | None = None
    parameters: dict[str, Any] | None = None


class AdvancedFilterEngine:
    """Advanced filtering engine for bills"""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )
        self.logger = logging.getLogger(__name__)

        # Field mappings and types
        self.field_mappings = {
            "bill_id": "bill_id",
            "title": "title",
            "outline": "bill_outline",
            "background": "background_context",
            "effects": "expected_effects",
            "summary": "summary",
            "submitter": "submitter",
            "category": "category",
            "status": "status",
            "stage": "stage",
            "session": "diet_session",
            "house": "house_of_origin",
            "source_house": "source_house",
            "submitted_date": "submitted_date",
            "vote_date": "final_vote_date",
            "implementation_date": "implementation_date",
            "quality_score": "data_quality_score",
            "submitter_type": "submitter_type",
            "promulgated_date": "promulgated_date",
        }

        # Field types for validation and conversion
        self.field_types = {
            "bill_id": str,
            "title": str,
            "bill_outline": str,
            "background_context": str,
            "expected_effects": str,
            "summary": str,
            "submitter": str,
            "category": str,
            "status": str,
            "stage": str,
            "diet_session": str,
            "house_of_origin": str,
            "source_house": str,
            "submitted_date": date,
            "final_vote_date": date,
            "implementation_date": date,
            "promulgated_date": date,
            "data_quality_score": float,
            "submitter_type": str,
        }

        # Valid values for enum-like fields
        self.valid_values = {
            "category": [
                "budget",
                "taxation",
                "social_security",
                "foreign_affairs",
                "economy",
                "education",
                "environment",
                "infrastructure",
                "defense",
                "judiciary",
                "administration",
                "other",
                "予算・決算",
                "税制",
                "社会保障",
                "外交・国際",
                "経済・産業",
                "教育・文化",
                "環境・エネルギー",
                "インフラ・交通",
                "防衛・安全保障",
                "司法・法務",
                "行政・公務員",
                "その他",
            ],
            "status": [
                "成立",
                "可決",
                "否決",
                "審議中",
                "委員会審議",
                "継続審議",
                "撤回",
                "廃案",
                "backlog",
                "under_review",
                "pending_vote",
                "passed",
                "rejected",
                "withdrawn",
                "expired",
            ],
            "stage": [
                "submitted",
                "committee_review",
                "plenary_debate",
                "voting",
                "passed",
                "rejected",
                "withdrawn",
                "提出",
                "委員会審議",
                "本会議",
                "採決",
                "成立",
                "否決",
                "撤回",
                "廃案",
            ],
            "submitter": ["政府", "議員", "government", "member"],
            "submitter_type": ["政府", "議員", "government", "member"],
            "house_of_origin": ["参議院", "衆議院", "upper", "lower"],
            "source_house": ["参議院", "衆議院", "両院", "upper", "lower", "both"],
        }

        # Searchable text fields
        self.text_fields = [
            "title",
            "bill_outline",
            "background_context",
            "expected_effects",
            "summary",
        ]

        # Date fields
        self.date_fields = [
            "submitted_date",
            "final_vote_date",
            "implementation_date",
            "promulgated_date",
        ]

        # Numeric fields
        self.numeric_fields = ["data_quality_score"]

    def apply_filters(self, query: FilterQuery) -> FilterResult:
        """Apply advanced filters to bills"""
        start_time = datetime.now()

        try:
            with self.SessionLocal() as session:
                # Build base query
                base_query = self._build_base_query(query)

                # Apply filters
                if query.filters:
                    filtered_query = self._apply_filter_group(
                        base_query, query.filters, session
                    )
                else:
                    filtered_query = base_query

                # Apply grouping
                if query.group_by:
                    grouped_query = self._apply_grouping(filtered_query, query.group_by)
                else:
                    grouped_query = filtered_query

                # Apply having clause
                if query.having:
                    having_query = self._apply_having(
                        grouped_query, query.having, session
                    )
                else:
                    having_query = grouped_query

                # Apply sorting
                if query.sort:
                    sorted_query = self._apply_sorting(having_query, query.sort)
                else:
                    sorted_query = having_query

                # Apply distinct
                if query.distinct:
                    distinct_query = sorted_query.distinct()
                else:
                    distinct_query = sorted_query

                # Get total count if requested
                total_count = None
                if query.include_count:
                    count_query = self._build_count_query(distinct_query)
                    total_count = session.execute(count_query).scalar()

                # Apply pagination
                if query.limit:
                    final_query = distinct_query.limit(query.limit).offset(query.offset)
                else:
                    final_query = distinct_query.offset(query.offset)

                # Execute query
                result = session.execute(final_query)
                rows = result.fetchall()

                # Convert to dictionaries
                data = [dict(row._mapping) for row in rows]

                # Calculate query time
                query_time_ms = (datetime.now() - start_time).total_seconds() * 1000

                return FilterResult(
                    data=data,
                    total_count=total_count,
                    query_time_ms=query_time_ms,
                    sql_query=str(final_query),
                    parameters=(
                        final_query.compile().params
                        if hasattr(final_query, "compile")
                        else None
                    ),
                )

        except Exception as e:
            self.logger.error(f"Filter error: {e}")
            query_time_ms = (datetime.now() - start_time).total_seconds() * 1000
            return FilterResult(
                data=[],
                total_count=0,
                query_time_ms=query_time_ms,
                sql_query=None,
                parameters={"error": str(e)},
            )

    def _build_base_query(self, query: FilterQuery) -> Select:
        """Build base SQLAlchemy query"""
        # Get table metadata
        with self.engine.connect() as connection:
            connection.execute(
                text(
                    """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'bills'
                ORDER BY ordinal_position
            """
                )
            ).fetchall()

        # Build select columns
        if query.group_by:
            # For grouped queries, select group columns and aggregates
            select_columns = []
            for col in query.group_by:
                if col in self.field_mappings:
                    select_columns.append(text(self.field_mappings[col]))
        else:
            # For regular queries, select all columns
            select_columns = [text("*")]

        return select(*select_columns).select_from(text("bills"))

    def _apply_filter_group(
        self, query: Select, filter_group: FilterGroup, session: Session
    ) -> Select:
        """Apply a filter group to the query"""
        conditions = []

        for condition in filter_group.conditions:
            if isinstance(condition, FilterCondition):
                sql_condition = self._build_filter_condition(condition)
                if sql_condition is not None:
                    conditions.append(sql_condition)
            elif isinstance(condition, FilterGroup):
                # Recursively handle nested filter groups
                nested_query = select(text("*")).select_from(text("bills"))
                nested_filtered = self._apply_filter_group(
                    nested_query, condition, session
                )
                # Extract the where clause from the nested query
                if nested_filtered.whereclause is not None:
                    conditions.append(nested_filtered.whereclause)

        if not conditions:
            return query

        # Combine conditions with logical operator
        if filter_group.operator == LogicalOperator.AND:
            combined_condition = and_(*conditions)
        elif filter_group.operator == LogicalOperator.OR:
            combined_condition = or_(*conditions)
        elif filter_group.operator == LogicalOperator.NOT:
            # For NOT, we negate the first condition (or combined AND condition)
            if len(conditions) == 1:
                combined_condition = not_(conditions[0])
            else:
                combined_condition = not_(and_(*conditions))
        else:
            combined_condition = and_(*conditions)

        return query.where(combined_condition)

    def _build_filter_condition(self, condition: FilterCondition) -> Any:
        """Build a single filter condition"""
        # Get actual column name
        column_name = self.field_mappings.get(condition.field, condition.field)
        column = text(column_name)

        # Convert value to appropriate type
        converted_value = self._convert_value(condition.field, condition.value)

        # Build condition based on operator
        if condition.operator == FilterOperator.EQUALS:
            return column == converted_value

        elif condition.operator == FilterOperator.NOT_EQUALS:
            return column != converted_value

        elif condition.operator == FilterOperator.CONTAINS:
            if condition.case_sensitive:
                return column.contains(converted_value)
            else:
                return func.lower(column).contains(func.lower(converted_value))

        elif condition.operator == FilterOperator.NOT_CONTAINS:
            if condition.case_sensitive:
                return not_(column.contains(converted_value))
            else:
                return not_(func.lower(column).contains(func.lower(converted_value)))

        elif condition.operator == FilterOperator.STARTS_WITH:
            if condition.case_sensitive:
                return column.startswith(converted_value)
            else:
                return func.lower(column).startswith(func.lower(converted_value))

        elif condition.operator == FilterOperator.ENDS_WITH:
            if condition.case_sensitive:
                return column.endswith(converted_value)
            else:
                return func.lower(column).endswith(func.lower(converted_value))

        elif condition.operator == FilterOperator.IN:
            converted_values = [
                self._convert_value(condition.field, v) for v in converted_value
            ]
            return column.in_(converted_values)

        elif condition.operator == FilterOperator.NOT_IN:
            converted_values = [
                self._convert_value(condition.field, v) for v in converted_value
            ]
            return column.notin_(converted_values)

        elif condition.operator == FilterOperator.GREATER_THAN:
            return column > converted_value

        elif condition.operator == FilterOperator.GREATER_THAN_OR_EQUAL:
            return column >= converted_value

        elif condition.operator == FilterOperator.LESS_THAN:
            return column < converted_value

        elif condition.operator == FilterOperator.LESS_THAN_OR_EQUAL:
            return column <= converted_value

        elif condition.operator == FilterOperator.BETWEEN:
            start_val = self._convert_value(condition.field, converted_value[0])
            end_val = self._convert_value(condition.field, converted_value[1])
            return column.between(start_val, end_val)

        elif condition.operator == FilterOperator.IS_NULL:
            return column.is_(None)

        elif condition.operator == FilterOperator.IS_NOT_NULL:
            return column.isnot(None)

        elif condition.operator == FilterOperator.REGEX:
            return column.op("~")(converted_value)

        elif condition.operator == FilterOperator.FUZZY:
            # Use PostgreSQL's similarity operator
            return column.op("%")(converted_value)

        else:
            self.logger.warning(f"Unsupported operator: {condition.operator}")
            return None

    def _convert_value(self, field: str, value: Any) -> Any:
        """Convert value to appropriate type for field"""
        if value is None:
            return None

        # Get actual column name
        column_name = self.field_mappings.get(field, field)
        field_type = self.field_types.get(column_name)

        if field_type == date:
            if isinstance(value, str):
                try:
                    return datetime.strptime(value, "%Y-%m-%d").date()
                except ValueError:
                    try:
                        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S").date()
                    except ValueError:
                        self.logger.warning(f"Invalid date format: {value}")
                        return value
            elif isinstance(value, datetime):
                return value.date()
            elif isinstance(value, date):
                return value

        elif field_type is float:
            try:
                return float(value)
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid float value: {value}")
                return value

        elif field_type is int:
            try:
                return int(value)
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid integer value: {value}")
                return value

        elif field_type is str:
            return str(value)

        return value

    def _apply_grouping(self, query: Select, group_by: list[str]) -> Select:
        """Apply GROUP BY clause"""
        group_columns = []
        for group_field in group_by:
            column_name = self.field_mappings.get(group_field, group_field)
            group_columns.append(text(column_name))

        return query.group_by(*group_columns)

    def _apply_having(
        self, query: Select, having: FilterGroup, session: Session
    ) -> Select:
        """Apply HAVING clause"""
        # Build having conditions similar to WHERE conditions
        conditions = []

        for condition in having.conditions:
            if isinstance(condition, FilterCondition):
                sql_condition = self._build_filter_condition(condition)
                if sql_condition is not None:
                    conditions.append(sql_condition)

        if not conditions:
            return query

        # Combine conditions with logical operator
        if having.operator == LogicalOperator.AND:
            combined_condition = and_(*conditions)
        elif having.operator == LogicalOperator.OR:
            combined_condition = or_(*conditions)
        elif having.operator == LogicalOperator.NOT:
            if len(conditions) == 1:
                combined_condition = not_(conditions[0])
            else:
                combined_condition = not_(and_(*conditions))
        else:
            combined_condition = and_(*conditions)

        return query.having(combined_condition)

    def _apply_sorting(
        self, query: Select, sort_criteria: list[SortCriteria]
    ) -> Select:
        """Apply ORDER BY clause"""
        order_columns = []

        for criteria in sort_criteria:
            column_name = self.field_mappings.get(criteria.field, criteria.field)
            column = text(column_name)

            if criteria.order == SortOrder.ASC:
                if criteria.nulls_first:
                    order_columns.append(column.asc().nullsfirst())
                else:
                    order_columns.append(column.asc().nullslast())
            else:
                if criteria.nulls_first:
                    order_columns.append(column.desc().nullsfirst())
                else:
                    order_columns.append(column.desc().nullslast())

        return query.order_by(*order_columns)

    def _build_count_query(self, query: Select) -> Select:
        """Build count query from filtered query"""
        # Create a subquery and count rows
        subquery = query.subquery()
        return select(func.count()).select_from(subquery)

    def validate_filter_query(self, query: FilterQuery) -> list[str]:
        """Validate filter query and return list of errors"""
        errors = []

        # Validate filters
        if query.filters:
            filter_errors = self._validate_filter_group(query.filters)
            errors.extend(filter_errors)

        # Validate sort criteria
        for criteria in query.sort:
            if criteria.field not in self.field_mappings:
                errors.append(f"Invalid sort field: {criteria.field}")

        # Validate group by fields
        for group_field in query.group_by:
            if group_field not in self.field_mappings:
                errors.append(f"Invalid group by field: {group_field}")

        # Validate having clause
        if query.having:
            having_errors = self._validate_filter_group(query.having)
            errors.extend([f"HAVING: {error}" for error in having_errors])

        # Validate pagination
        if query.limit is not None and query.limit <= 0:
            errors.append("Limit must be positive")

        if query.offset < 0:
            errors.append("Offset must be non-negative")

        return errors

    def _validate_filter_group(self, filter_group: FilterGroup) -> list[str]:
        """Validate filter group recursively"""
        errors = []

        for condition in filter_group.conditions:
            if isinstance(condition, FilterCondition):
                condition_errors = self._validate_filter_condition(condition)
                errors.extend(condition_errors)
            elif isinstance(condition, FilterGroup):
                nested_errors = self._validate_filter_group(condition)
                errors.extend(nested_errors)

        return errors

    def _validate_filter_condition(self, condition: FilterCondition) -> list[str]:
        """Validate a single filter condition"""
        errors = []

        # Check if field exists
        if condition.field not in self.field_mappings:
            errors.append(f"Invalid field: {condition.field}")
            return errors

        # Get actual column name and type
        column_name = self.field_mappings[condition.field]
        field_type = self.field_types.get(column_name)

        # Validate operator compatibility with field type
        if field_type == date:
            if condition.operator not in [
                FilterOperator.EQUALS,
                FilterOperator.NOT_EQUALS,
                FilterOperator.GREATER_THAN,
                FilterOperator.GREATER_THAN_OR_EQUAL,
                FilterOperator.LESS_THAN,
                FilterOperator.LESS_THAN_OR_EQUAL,
                FilterOperator.BETWEEN,
                FilterOperator.IN,
                FilterOperator.NOT_IN,
                FilterOperator.IS_NULL,
                FilterOperator.IS_NOT_NULL,
            ]:
                errors.append(
                    f"Operator {condition.operator.value} not supported for date field {condition.field}"
                )

        elif field_type is float:
            if condition.operator not in [
                FilterOperator.EQUALS,
                FilterOperator.NOT_EQUALS,
                FilterOperator.GREATER_THAN,
                FilterOperator.GREATER_THAN_OR_EQUAL,
                FilterOperator.LESS_THAN,
                FilterOperator.LESS_THAN_OR_EQUAL,
                FilterOperator.BETWEEN,
                FilterOperator.IN,
                FilterOperator.NOT_IN,
                FilterOperator.IS_NULL,
                FilterOperator.IS_NOT_NULL,
            ]:
                errors.append(
                    f"Operator {condition.operator.value} not supported for numeric field {condition.field}"
                )

        # Validate value format
        if condition.operator not in [
            FilterOperator.IS_NULL,
            FilterOperator.IS_NOT_NULL,
        ]:
            try:
                self._convert_value(condition.field, condition.value)
            except Exception as e:
                errors.append(f"Invalid value for field {condition.field}: {e}")

        # Validate enum values
        if column_name in self.valid_values:
            valid_vals = self.valid_values[column_name]
            if condition.operator in [FilterOperator.EQUALS, FilterOperator.NOT_EQUALS]:
                if condition.value not in valid_vals:
                    errors.append(
                        f"Invalid value '{condition.value}' for field {condition.field}. Valid values: {valid_vals}"
                    )
            elif condition.operator in [FilterOperator.IN, FilterOperator.NOT_IN]:
                for val in condition.value:
                    if val not in valid_vals:
                        errors.append(
                            f"Invalid value '{val}' for field {condition.field}. Valid values: {valid_vals}"
                        )

        return errors

    def get_filter_suggestions(
        self, field: str, partial_value: str = "", limit: int = 10
    ) -> list[str]:
        """Get filter value suggestions for a field"""
        suggestions = []

        try:
            with self.SessionLocal() as session:
                column_name = self.field_mappings.get(field, field)

                if column_name in self.valid_values:
                    # For enum fields, filter from valid values
                    valid_vals = self.valid_values[column_name]
                    if partial_value:
                        suggestions = [
                            val
                            for val in valid_vals
                            if partial_value.lower() in val.lower()
                        ]
                    else:
                        suggestions = valid_vals
                else:
                    # For other fields, query distinct values
                    query = text(
                        f"""
                        SELECT DISTINCT {column_name} as value
                        FROM bills
                        WHERE {column_name} IS NOT NULL
                        AND {column_name} ILIKE :partial_value
                        ORDER BY {column_name}
                        LIMIT :limit
                    """
                    )

                    result = session.execute(
                        query, {"partial_value": f"%{partial_value}%", "limit": limit}
                    )

                    suggestions = [row.value for row in result.fetchall()]

        except Exception as e:
            self.logger.error(f"Error getting filter suggestions: {e}")

        return suggestions[:limit]

    def get_field_statistics(self, field: str) -> dict[str, Any]:
        """Get statistics for a field"""
        try:
            with self.SessionLocal() as session:
                column_name = self.field_mappings.get(field, field)
                field_type = self.field_types.get(column_name)

                stats = {
                    "field": field,
                    "column_name": column_name,
                    "field_type": field_type.__name__ if field_type else "unknown",
                }

                # Count total and non-null values
                total_query = text(
                    f"SELECT COUNT(*) as total, COUNT({column_name}) as non_null FROM bills"
                )
                result = session.execute(total_query).fetchone()
                stats["total_count"] = result.total
                stats["non_null_count"] = result.non_null
                stats["null_count"] = result.total - result.non_null

                # Get distinct values count
                distinct_query = text(
                    f"SELECT COUNT(DISTINCT {column_name}) as distinct_count FROM bills WHERE {column_name} IS NOT NULL"
                )
                result = session.execute(distinct_query).fetchone()
                stats["distinct_count"] = result.distinct_count

                # Type-specific statistics
                if field_type == date:
                    date_stats_query = text(
                        f"""
                        SELECT
                            MIN({column_name}) as min_date,
                            MAX({column_name}) as max_date
                        FROM bills
                        WHERE {column_name} IS NOT NULL
                    """
                    )
                    result = session.execute(date_stats_query).fetchone()
                    if result:
                        stats["min_date"] = (
                            result.min_date.isoformat() if result.min_date else None
                        )
                        stats["max_date"] = (
                            result.max_date.isoformat() if result.max_date else None
                        )

                elif field_type is float:
                    numeric_stats_query = text(
                        f"""
                        SELECT
                            MIN({column_name}) as min_val,
                            MAX({column_name}) as max_val,
                            AVG({column_name}) as avg_val,
                            STDDEV({column_name}) as stddev_val
                        FROM bills
                        WHERE {column_name} IS NOT NULL
                    """
                    )
                    result = session.execute(numeric_stats_query).fetchone()
                    if result:
                        stats["min_value"] = (
                            float(result.min_val)
                            if result.min_val is not None
                            else None
                        )
                        stats["max_value"] = (
                            float(result.max_val)
                            if result.max_val is not None
                            else None
                        )
                        stats["avg_value"] = (
                            float(result.avg_val)
                            if result.avg_val is not None
                            else None
                        )
                        stats["stddev_value"] = (
                            float(result.stddev_val)
                            if result.stddev_val is not None
                            else None
                        )

                elif field_type is str:
                    text_stats_query = text(
                        f"""
                        SELECT
                            MIN(LENGTH({column_name})) as min_length,
                            MAX(LENGTH({column_name})) as max_length,
                            AVG(LENGTH({column_name})) as avg_length
                        FROM bills
                        WHERE {column_name} IS NOT NULL
                    """
                    )
                    result = session.execute(text_stats_query).fetchone()
                    if result:
                        stats["min_length"] = result.min_length
                        stats["max_length"] = result.max_length
                        stats["avg_length"] = (
                            float(result.avg_length) if result.avg_length else None
                        )

                # Get top values
                top_values_query = text(
                    f"""
                    SELECT {column_name} as value, COUNT(*) as count
                    FROM bills
                    WHERE {column_name} IS NOT NULL
                    GROUP BY {column_name}
                    ORDER BY count DESC
                    LIMIT 10
                """
                )
                result = session.execute(top_values_query).fetchall()
                stats["top_values"] = [
                    {"value": row.value, "count": row.count} for row in result
                ]

                return stats

        except Exception as e:
            self.logger.error(f"Error getting field statistics: {e}")
            return {"error": str(e)}
