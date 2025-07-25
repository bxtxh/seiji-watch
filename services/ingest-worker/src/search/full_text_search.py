"""
Full-text search implementation for bills database.
Provides comprehensive search capabilities across bill content with Japanese text optimization.
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import MeCab
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker


class SearchMode(Enum):
    """Search modes for different use cases"""

    SIMPLE = "simple"  # Basic keyword search
    ADVANCED = "advanced"  # Advanced search with operators
    SEMANTIC = "semantic"  # Semantic search using embeddings
    EXACT = "exact"  # Exact phrase search


class SearchField(Enum):
    """Searchable fields"""

    ALL = "all"
    TITLE = "title"
    OUTLINE = "bill_outline"
    BACKGROUND = "background_context"
    EFFECTS = "expected_effects"
    PROVISIONS = "key_provisions"
    SUMMARY = "summary"
    SUBMITTER = "submitter"
    CATEGORY = "category"


@dataclass
class SearchQuery:
    """Search query configuration"""

    query: str
    mode: SearchMode = SearchMode.SIMPLE
    fields: list[SearchField] = field(default_factory=lambda: [SearchField.ALL])
    filters: dict[str, Any] = field(default_factory=dict)
    limit: int = 50
    offset: int = 0
    sort_by: str = "relevance"
    sort_order: str = "desc"

    # Advanced search options
    exact_phrase: bool = False
    fuzzy_match: bool = True
    include_synonyms: bool = True
    date_range: tuple[datetime, datetime] | None = None

    # Japanese-specific options
    use_morphological_analysis: bool = True
    enable_reading_search: bool = True  # Allow searching by reading (hiragana)


@dataclass
class SearchResult:
    """Search result item"""

    bill_id: str
    title: str
    relevance_score: float
    matched_fields: list[str]
    snippet: str
    highlights: list[str]
    metadata: dict[str, Any]


@dataclass
class SearchResponse:
    """Complete search response"""

    results: list[SearchResult]
    total_count: int
    query_time_ms: float
    suggestions: list[str] = field(default_factory=list)
    facets: dict[str, dict[str, int]] = field(default_factory=dict)
    debug_info: dict[str, Any] = field(default_factory=dict)


class JapaneseTextProcessor:
    """Japanese text processing utilities"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Initialize MeCab for morphological analysis
        try:
            self.mecab = MeCab.Tagger("-Owakati")
            self.mecab_features = MeCab.Tagger("-Ochasen")
        except Exception as e:
            self.logger.warning(f"MeCab initialization failed: {e}")
            self.mecab = None
            self.mecab_features = None

        # Initialize SudachiPy for more advanced Japanese processing
        try:
            from sudachipy import dictionary, tokenizer

            self.sudachi = dictionary.Dictionary().create()
            self.sudachi_mode = tokenizer.Tokenizer.SplitMode.C
        except Exception as e:
            self.logger.warning(f"SudachiPy initialization failed: {e}")
            self.sudachi = None

    def tokenize_japanese(self, text: str) -> list[str]:
        """Tokenize Japanese text into words"""
        if not text:
            return []

        tokens = []

        # Try SudachiPy first for better accuracy
        if self.sudachi:
            try:
                sudachi_tokens = self.sudachi.tokenize(text, self.sudachi_mode)
                tokens.extend(
                    [t.surface() for t in sudachi_tokens if len(t.surface()) > 1]
                )
            except Exception as e:
                self.logger.debug(f"SudachiPy tokenization failed: {e}")

        # Fallback to MeCab
        if not tokens and self.mecab:
            try:
                mecab_result = self.mecab.parse(text)
                tokens = [token for token in mecab_result.split() if len(token) > 1]
            except Exception as e:
                self.logger.debug(f"MeCab tokenization failed: {e}")

        # Final fallback to character-based splitting
        if not tokens:
            # Simple Japanese text splitting
            tokens = re.findall(r"[一-龯ひらがなカタカナ]+", text)

        return tokens

    def extract_readings(self, text: str) -> list[str]:
        """Extract hiragana readings from text"""
        if not text or not self.mecab_features:
            return []

        readings = []
        try:
            lines = self.mecab_features.parse(text).split("\n")
            for line in lines:
                if line and line != "EOS":
                    parts = line.split("\t")
                    if len(parts) >= 2:
                        features = parts[1].split(",")
                        if len(features) >= 8 and features[7] != "*":
                            readings.append(features[7])  # Reading field
        except Exception as e:
            self.logger.debug(f"Reading extraction failed: {e}")

        return readings

    def normalize_text(self, text: str) -> str:
        """Normalize Japanese text for search"""
        if not text:
            return ""

        # Convert full-width to half-width
        text = text.translate(
            str.maketrans(
                "ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ"
                "ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ"
                "０１２３４５６７８９",
                "abcdefghijklmnopqrstuvwxyz" "ABCDEFGHIJKLMNOPQRSTUVWXYZ" "0123456789",
            )
        )

        # Convert katakana to hiragana for better matching
        text = text.translate(
            str.maketrans(
                "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン",
                "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん",
            )
        )

        # Remove extra whitespace
        text = re.sub(r"\s+", " ", text).strip()

        return text


class FullTextSearchEngine:
    """Full-text search engine for bills"""

    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )
        self.logger = logging.getLogger(__name__)

        # Initialize Japanese text processor
        self.text_processor = JapaneseTextProcessor()

        # Search configuration
        self.search_config = {
            "default_language": "japanese",
            "max_results": 1000,
            "snippet_length": 200,
            "highlight_fragments": 3,
            "fuzzy_distance": 2,
        }

        # Field weights for relevance scoring
        self.field_weights = {
            "title": 3.0,
            "bill_outline": 2.0,
            "background_context": 1.5,
            "expected_effects": 1.5,
            "key_provisions": 1.8,
            "summary": 1.3,
            "submitter": 1.0,
            "category": 1.2,
        }

    def create_search_indexes(self):
        """Create full-text search indexes"""
        try:
            with self.engine.connect() as connection:
                # Create compound tsvector index for multiple fields
                connection.execute(
                    text(
                        """
                    CREATE INDEX IF NOT EXISTS idx_bills_fulltext_search
                    ON bills USING GIN((
                        setweight(to_tsvector('japanese', COALESCE(title, '')), 'A') ||
                        setweight(to_tsvector('japanese', COALESCE(bill_outline, '')), 'B') ||
                        setweight(to_tsvector('japanese', COALESCE(background_context, '')), 'C') ||
                        setweight(to_tsvector('japanese', COALESCE(expected_effects, '')), 'C') ||
                        setweight(to_tsvector('japanese', COALESCE(summary, '')), 'D')
                    ))
                """
                    )
                )

                # Create separate indexes for specific fields
                connection.execute(
                    text(
                        """
                    CREATE INDEX IF NOT EXISTS idx_bills_title_search
                    ON bills USING GIN(to_tsvector('japanese', title))
                """
                    )
                )

                connection.execute(
                    text(
                        """
                    CREATE INDEX IF NOT EXISTS idx_bills_outline_search
                    ON bills USING GIN(to_tsvector('japanese', bill_outline))
                """
                    )
                )

                # Create trigram index for fuzzy matching
                connection.execute(
                    text(
                        """
                    CREATE EXTENSION IF NOT EXISTS pg_trgm
                """
                    )
                )

                connection.execute(
                    text(
                        """
                    CREATE INDEX IF NOT EXISTS idx_bills_title_trigram
                    ON bills USING GIN(title gin_trgm_ops)
                """
                    )
                )

                connection.execute(
                    text(
                        """
                    CREATE INDEX IF NOT EXISTS idx_bills_outline_trigram
                    ON bills USING GIN(bill_outline gin_trgm_ops)
                """
                    )
                )

                # Create indexes for filtering
                connection.execute(
                    text(
                        """
                    CREATE INDEX IF NOT EXISTS idx_bills_category_status
                    ON bills (category, status)
                """
                    )
                )

                connection.execute(
                    text(
                        """
                    CREATE INDEX IF NOT EXISTS idx_bills_submitter_session
                    ON bills (submitter, diet_session)
                """
                    )
                )

                connection.execute(
                    text(
                        """
                    CREATE INDEX IF NOT EXISTS idx_bills_dates
                    ON bills (submitted_date, final_vote_date)
                """
                    )
                )

                connection.commit()
                self.logger.info("Created full-text search indexes successfully")

        except Exception as e:
            self.logger.error(f"Error creating search indexes: {e}")
            raise

    def search(self, query: SearchQuery) -> SearchResponse:
        """Perform full-text search"""
        start_time = datetime.now()

        try:
            with self.SessionLocal() as session:
                # Build search query
                sql_query, params = self._build_search_query(query)

                # Execute search
                result = session.execute(text(sql_query), params)
                rows = result.fetchall()

                # Get total count
                count_query, count_params = self._build_count_query(query)
                count_result = session.execute(text(count_query), count_params)
                total_count = count_result.fetchone()[0]

                # Process results
                search_results = []
                for row in rows:
                    search_result = self._process_search_result(row, query)
                    search_results.append(search_result)

                # Calculate query time
                query_time_ms = (datetime.now() - start_time).total_seconds() * 1000

                # Get suggestions if no results
                suggestions = []
                if not search_results:
                    suggestions = self._get_search_suggestions(query, session)

                # Get facets
                facets = self._get_search_facets(query, session)

                return SearchResponse(
                    results=search_results,
                    total_count=total_count,
                    query_time_ms=query_time_ms,
                    suggestions=suggestions,
                    facets=facets,
                    debug_info={"sql_query": sql_query, "params": params},
                )

        except Exception as e:
            self.logger.error(f"Search error: {e}")
            return SearchResponse(
                results=[],
                total_count=0,
                query_time_ms=(datetime.now() - start_time).total_seconds() * 1000,
                debug_info={"error": str(e)},
            )

    def _build_search_query(self, query: SearchQuery) -> tuple[str, dict[str, Any]]:
        """Build SQL search query"""
        # Normalize and process query text
        normalized_query = self.text_processor.normalize_text(query.query)

        # Build search conditions
        search_conditions = []
        params = {}

        if query.mode == SearchMode.SIMPLE:
            # Simple full-text search
            search_vector = self._build_search_vector(query.fields)
            search_conditions.append(
                f"{search_vector} @@ plainto_tsquery('japanese', :query)"
            )
            params["query"] = normalized_query

        elif query.mode == SearchMode.ADVANCED:
            # Advanced search with operators
            search_vector = self._build_search_vector(query.fields)
            processed_query = self._process_advanced_query(normalized_query)
            search_conditions.append(
                f"{search_vector} @@ to_tsquery('japanese', :query)"
            )
            params["query"] = processed_query

        elif query.mode == SearchMode.EXACT:
            # Exact phrase search
            if SearchField.ALL in query.fields:
                exact_conditions = []
                for field in [
                    "title",
                    "bill_outline",
                    "background_context",
                    "expected_effects",
                    "summary",
                ]:
                    exact_conditions.append(f"{field} ILIKE :exact_query")
                search_conditions.append(f"({' OR '.join(exact_conditions)})")
            else:
                field_conditions = []
                for field in query.fields:
                    if field != SearchField.ALL:
                        field_conditions.append(f"{field.value} ILIKE :exact_query")
                search_conditions.append(f"({' OR '.join(field_conditions)})")
            params["exact_query"] = f"%{normalized_query}%"

        # Add filters
        filter_conditions = []
        if query.filters:
            for key, value in query.filters.items():
                if key == "category" and value:
                    filter_conditions.append("category = :filter_category")
                    params["filter_category"] = value
                elif key == "status" and value:
                    filter_conditions.append("status = :filter_status")
                    params["filter_status"] = value
                elif key == "submitter" and value:
                    filter_conditions.append("submitter = :filter_submitter")
                    params["filter_submitter"] = value
                elif key == "diet_session" and value:
                    filter_conditions.append("diet_session = :filter_session")
                    params["filter_session"] = value
                elif key == "house_of_origin" and value:
                    filter_conditions.append("house_of_origin = :filter_house")
                    params["filter_house"] = value

        # Add date range filter
        if query.date_range:
            start_date, end_date = query.date_range
            filter_conditions.append("submitted_date BETWEEN :start_date AND :end_date")
            params["start_date"] = start_date
            params["end_date"] = end_date

        # Combine conditions
        where_conditions = []
        if search_conditions:
            where_conditions.extend(search_conditions)
        if filter_conditions:
            where_conditions.extend(filter_conditions)

        where_clause = " AND ".join(where_conditions) if where_conditions else "TRUE"

        # Build ranking/scoring
        if query.mode in [SearchMode.SIMPLE, SearchMode.ADVANCED]:
            search_vector = self._build_search_vector(query.fields)
            ts_query = (
                "plainto_tsquery('japanese', :query)"
                if query.mode == SearchMode.SIMPLE
                else "to_tsquery('japanese', :query)"
            )
            rank_expression = f"ts_rank_cd({search_vector}, {ts_query})"
        else:
            rank_expression = "1.0"

        # Build ORDER BY clause
        if query.sort_by == "relevance":
            order_by = f"{rank_expression} DESC"
        elif query.sort_by == "date":
            order_by = (
                f"submitted_date {'DESC' if query.sort_order == 'desc' else 'ASC'}"
            )
        elif query.sort_by == "title":
            order_by = f"title {'DESC' if query.sort_order == 'desc' else 'ASC'}"
        else:
            order_by = f"{rank_expression} DESC"

        # Build complete query
        sql_query = f"""
            SELECT
                bill_id,
                title,
                bill_outline,
                background_context,
                expected_effects,
                summary,
                submitter,
                category,
                status,
                diet_session,
                house_of_origin,
                submitted_date,
                {rank_expression} as relevance_score,
                ts_headline('japanese', COALESCE(title, ''), {ts_query if query.mode != SearchMode.EXACT else 'plainto_tsquery(:query)'}) as title_highlight,
                ts_headline('japanese', COALESCE(bill_outline, ''), {ts_query if query.mode != SearchMode.EXACT else 'plainto_tsquery(:query)'}) as outline_highlight
            FROM bills
            WHERE {where_clause}
            ORDER BY {order_by}
            LIMIT :limit OFFSET :offset
        """

        params["limit"] = query.limit
        params["offset"] = query.offset

        return sql_query, params

    def _build_count_query(self, query: SearchQuery) -> tuple[str, dict[str, Any]]:
        """Build count query"""
        # This is a simplified version of the search query for counting
        normalized_query = self.text_processor.normalize_text(query.query)

        search_conditions = []
        params = {}

        if query.mode == SearchMode.SIMPLE:
            search_vector = self._build_search_vector(query.fields)
            search_conditions.append(
                f"{search_vector} @@ plainto_tsquery('japanese', :query)"
            )
            params["query"] = normalized_query
        elif query.mode == SearchMode.ADVANCED:
            search_vector = self._build_search_vector(query.fields)
            processed_query = self._process_advanced_query(normalized_query)
            search_conditions.append(
                f"{search_vector} @@ to_tsquery('japanese', :query)"
            )
            params["query"] = processed_query
        elif query.mode == SearchMode.EXACT:
            if SearchField.ALL in query.fields:
                exact_conditions = []
                for field in [
                    "title",
                    "bill_outline",
                    "background_context",
                    "expected_effects",
                    "summary",
                ]:
                    exact_conditions.append(f"{field} ILIKE :exact_query")
                search_conditions.append(f"({' OR '.join(exact_conditions)})")
            else:
                field_conditions = []
                for field in query.fields:
                    if field != SearchField.ALL:
                        field_conditions.append(f"{field.value} ILIKE :exact_query")
                search_conditions.append(f"({' OR '.join(field_conditions)})")
            params["exact_query"] = f"%{normalized_query}%"

        # Add filters (same as search query)
        filter_conditions = []
        if query.filters:
            for key, value in query.filters.items():
                if key == "category" and value:
                    filter_conditions.append("category = :filter_category")
                    params["filter_category"] = value
                elif key == "status" and value:
                    filter_conditions.append("status = :filter_status")
                    params["filter_status"] = value
                elif key == "submitter" and value:
                    filter_conditions.append("submitter = :filter_submitter")
                    params["filter_submitter"] = value
                elif key == "diet_session" and value:
                    filter_conditions.append("diet_session = :filter_session")
                    params["filter_session"] = value
                elif key == "house_of_origin" and value:
                    filter_conditions.append("house_of_origin = :filter_house")
                    params["filter_house"] = value

        if query.date_range:
            start_date, end_date = query.date_range
            filter_conditions.append("submitted_date BETWEEN :start_date AND :end_date")
            params["start_date"] = start_date
            params["end_date"] = end_date

        where_conditions = []
        if search_conditions:
            where_conditions.extend(search_conditions)
        if filter_conditions:
            where_conditions.extend(filter_conditions)

        where_clause = " AND ".join(where_conditions) if where_conditions else "TRUE"

        count_query = f"""
            SELECT COUNT(*) as total_count
            FROM bills
            WHERE {where_clause}
        """

        return count_query, params

    def _build_search_vector(self, fields: list[SearchField]) -> str:
        """Build tsvector expression for search fields"""
        if SearchField.ALL in fields:
            return """(
                setweight(to_tsvector('japanese', COALESCE(title, '')), 'A') ||
                setweight(to_tsvector('japanese', COALESCE(bill_outline, '')), 'B') ||
                setweight(to_tsvector('japanese', COALESCE(background_context, '')), 'C') ||
                setweight(to_tsvector('japanese', COALESCE(expected_effects, '')), 'C') ||
                setweight(to_tsvector('japanese', COALESCE(summary, '')), 'D')
            )"""
        else:
            field_vectors = []
            for field in fields:
                if field != SearchField.ALL:
                    weight = (
                        "A"
                        if field == SearchField.TITLE
                        else "B" if field == SearchField.OUTLINE else "C"
                    )
                    field_vectors.append(
                        f"setweight(to_tsvector('japanese', COALESCE({field.value}, '')), '{weight}')"
                    )

            return (
                f"({' || '.join(field_vectors)})"
                if field_vectors
                else "to_tsvector('japanese', '')"
            )

    def _process_advanced_query(self, query: str) -> str:
        """Process advanced search query with operators"""
        # Convert simple operators to PostgreSQL tsquery format
        query = query.replace(" AND ", " & ")
        query = query.replace(" OR ", " | ")
        query = query.replace(" NOT ", " !")

        # Handle phrase queries
        query = re.sub(r'"([^"]+)"', r"\1", query)

        # Tokenize Japanese text for better matching
        tokens = self.text_processor.tokenize_japanese(query)
        if tokens:
            # Join tokens with AND operator
            query = " & ".join(tokens)

        return query

    def _process_search_result(self, row, query: SearchQuery) -> SearchResult:
        """Process a single search result"""
        # Extract matched fields
        matched_fields = []
        query_terms = self.text_processor.tokenize_japanese(query.query)

        for field in [
            "title",
            "bill_outline",
            "background_context",
            "expected_effects",
            "summary",
        ]:
            field_value = getattr(row, field, "")
            if field_value and any(term in field_value for term in query_terms):
                matched_fields.append(field)

        # Generate snippet
        snippet = self._generate_snippet(row, query)

        # Generate highlights
        highlights = self._generate_highlights(row, query)

        # Prepare metadata
        metadata = {
            "submitter": row.submitter,
            "category": row.category,
            "status": row.status,
            "diet_session": row.diet_session,
            "house_of_origin": row.house_of_origin,
            "submitted_date": (
                row.submitted_date.isoformat() if row.submitted_date else None
            ),
        }

        return SearchResult(
            bill_id=row.bill_id,
            title=row.title,
            relevance_score=float(row.relevance_score),
            matched_fields=matched_fields,
            snippet=snippet,
            highlights=highlights,
            metadata=metadata,
        )

    def _generate_snippet(self, row, query: SearchQuery) -> str:
        """Generate search result snippet"""
        # Prioritize bill_outline for snippet
        if row.bill_outline:
            text = row.bill_outline
        elif row.background_context:
            text = row.background_context
        elif row.expected_effects:
            text = row.expected_effects
        else:
            text = row.title

        # Truncate to snippet length
        if len(text) > self.search_config["snippet_length"]:
            text = text[: self.search_config["snippet_length"]] + "..."

        return text

    def _generate_highlights(self, row, query: SearchQuery) -> list[str]:
        """Generate highlighted text fragments"""
        highlights = []

        # Use PostgreSQL's ts_headline results when available
        if hasattr(row, "title_highlight") and row.title_highlight:
            highlights.append(row.title_highlight)

        if hasattr(row, "outline_highlight") and row.outline_highlight:
            highlights.append(row.outline_highlight)

        return highlights[: self.search_config["highlight_fragments"]]

    def _get_search_suggestions(
        self, query: SearchQuery, session: Session
    ) -> list[str]:
        """Get search suggestions when no results found"""
        suggestions = []

        try:
            # Get similar terms using trigram similarity
            similar_query = text(
                """
                SELECT DISTINCT title
                FROM bills
                WHERE title % :query
                ORDER BY similarity(title, :query) DESC
                LIMIT 5
            """
            )

            result = session.execute(similar_query, {"query": query.query})
            suggestions = [row.title for row in result.fetchall()]

        except Exception as e:
            self.logger.debug(f"Error getting suggestions: {e}")

        return suggestions

    def _get_search_facets(
        self, query: SearchQuery, session: Session
    ) -> dict[str, dict[str, int]]:
        """Get search facets for filtering"""
        facets = {}

        try:
            # Get category facets
            category_query = text(
                """
                SELECT category, COUNT(*) as count
                FROM bills
                WHERE category IS NOT NULL
                GROUP BY category
                ORDER BY count DESC
                LIMIT 10
            """
            )

            result = session.execute(category_query)
            facets["category"] = {row.category: row.count for row in result.fetchall()}

            # Get status facets
            status_query = text(
                """
                SELECT status, COUNT(*) as count
                FROM bills
                WHERE status IS NOT NULL
                GROUP BY status
                ORDER BY count DESC
                LIMIT 10
            """
            )

            result = session.execute(status_query)
            facets["status"] = {row.status: row.count for row in result.fetchall()}

            # Get submitter facets
            submitter_query = text(
                """
                SELECT submitter, COUNT(*) as count
                FROM bills
                WHERE submitter IS NOT NULL
                GROUP BY submitter
                ORDER BY count DESC
                LIMIT 10
            """
            )

            result = session.execute(submitter_query)
            facets["submitter"] = {
                row.submitter: row.count for row in result.fetchall()
            }

        except Exception as e:
            self.logger.debug(f"Error getting facets: {e}")

        return facets

    async def reindex_bills(self, session: Session, bill_ids: list[str] | None = None):
        """Reindex bills for search (if needed for custom search vectors)"""
        try:
            # PostgreSQL automatically maintains tsvector indexes
            # This method is for any custom indexing logic

            if bill_ids:
                # Reindex specific bills
                self.logger.info(f"Reindexing {len(bill_ids)} bills")
                # Custom reindexing logic here if needed
            else:
                # Reindex all bills
                self.logger.info("Reindexing all bills")
                # Full reindex logic here if needed

            # For now, just refresh the search statistics
            with self.engine.connect() as connection:
                connection.execute(text("ANALYZE bills"))
                connection.commit()

        except Exception as e:
            self.logger.error(f"Error reindexing bills: {e}")
            raise

    def get_search_statistics(self) -> dict[str, Any]:
        """Get search engine statistics"""
        try:
            with self.SessionLocal() as session:
                # Get total bill count
                total_bills = session.execute(
                    text("SELECT COUNT(*) FROM bills")
                ).fetchone()[0]

                # Get index sizes
                index_sizes = session.execute(
                    text(
                        """
                    SELECT schemaname, tablename, indexname, pg_size_pretty(pg_relation_size(indexrelid)) as size
                    FROM pg_stat_user_indexes
                    WHERE tablename = 'bills'
                    ORDER BY pg_relation_size(indexrelid) DESC
                """
                    )
                ).fetchall()

                # Get most recent indexing time
                last_analyze = session.execute(
                    text(
                        """
                    SELECT last_analyze, last_autoanalyze
                    FROM pg_stat_user_tables
                    WHERE relname = 'bills'
                """
                    )
                ).fetchone()

                return {
                    "total_bills": total_bills,
                    "index_sizes": [
                        {"name": row.indexname, "size": row.size} for row in index_sizes
                    ],
                    "last_analyze": (
                        last_analyze.last_analyze.isoformat()
                        if last_analyze and last_analyze.last_analyze
                        else None
                    ),
                    "last_autoanalyze": (
                        last_analyze.last_autoanalyze.isoformat()
                        if last_analyze and last_analyze.last_autoanalyze
                        else None
                    ),
                    "search_config": self.search_config,
                }

        except Exception as e:
            self.logger.error(f"Error getting search statistics: {e}")
            return {"error": str(e)}
