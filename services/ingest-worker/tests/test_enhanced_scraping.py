"""
Tests for enhanced scraping functionality.
Tests the enhanced diet scraper, Shugiin scraper, data merger, and validator.
"""

from datetime import datetime
from unittest.mock import Mock, patch

import pytest
from bs4 import BeautifulSoup

from ..src.processor.bill_data_merger import (
    BillDataMerger,
    ConflictResolutionStrategy,
    MergeResult,
)
from ..src.processor.bill_data_validator import (
    BillDataValidator,
)
from ..src.scraper.enhanced_diet_scraper import EnhancedBillData, EnhancedDietScraper
from ..src.scraper.shugiin_scraper import ShugiinBillData, ShugiinScraper


class TestEnhancedDietScraper:
    """Test cases for EnhancedDietScraper"""

    @pytest.fixture
    def scraper(self):
        """Create test scraper instance"""
        return EnhancedDietScraper(delay_seconds=0.1, enable_resilience=False)

    @pytest.fixture
    def mock_html(self):
        """Mock HTML content for testing"""
        return """
        <html>
        <head><title>法案詳細</title></head>
        <body>
            <h1>デジタル社会形成基本法案</h1>
            <div class="gian-youshi">
                <p>議案要旨</p>
                <p>本法案は、デジタル社会の形成に関する基本理念を定め、デジタル社会の形成に関する施策を総合的かつ計画的に推進することを目的とする。</p>
            </div>
            <div class="teisyutsu-haikei">
                <p>提出背景</p>
                <p>近年の情報通信技術の発展により、デジタル社会の形成が急務となっている。</p>
            </div>
            <div class="koka">
                <p>期待される効果</p>
                <p>デジタル技術の活用により、行政サービスの向上と経済発展が期待される。</p>
            </div>
            <div class="teisyutusya">
                <p>提出者</p>
                <p>内閣総理大臣　菅義偉</p>
            </div>
            <div class="iinkai">
                <p>内閣委員会</p>
            </div>
            <p>施行日：令和3年9月1日</p>
        </body>
        </html>
        """

    @patch('requests.Session.get')
    def test_fetch_enhanced_bill_details(self, mock_get, scraper, mock_html):
        """Test enhanced bill details fetching"""
        # Mock response
        mock_response = Mock()
        mock_response.content = mock_html.encode('utf-8')
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Test fetching
        bill_data = scraper.fetch_enhanced_bill_details("http://example.com/bill/1")

        # Assertions
        assert bill_data.title == "デジタル社会形成基本法案"
        assert "デジタル社会の形成に関する基本理念" in bill_data.bill_outline
        assert "情報通信技術の発展" in bill_data.background_context
        assert "行政サービスの向上" in bill_data.expected_effects
        assert bill_data.sponsoring_ministry == "内閣総理大臣"
        assert bill_data.source_house == "参議院"
        assert bill_data.data_quality_score is not None

    def test_extract_bill_outline(self, scraper):
        """Test bill outline extraction"""
        html = """
        <div>
            <p>議案要旨</p>
            <p>本法案は重要な法律改正を行うものである。具体的には、以下の点について定める。第一に、基本理念の明確化。第二に、制度の見直し。第三に、施行体制の整備。</p>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')

        # Create mock bill data
        bill_data = EnhancedBillData(
            bill_id="test-1", title="テスト法案", submission_date=None,
            status="審議中", stage="審議中", submitter="政府", category="その他",
            url="http://example.com"
        )

        scraper._extract_bill_outline(soup, bill_data)

        assert bill_data.bill_outline is not None
        assert len(bill_data.bill_outline) > 50
        assert "基本理念" in bill_data.bill_outline

    def test_extract_key_provisions(self, scraper):
        """Test key provisions extraction"""
        html = """
        <div>
            <ul>
                <li>第一条　目的の明確化</li>
                <li>第二条　基本理念の設定</li>
                <li>第三条　国の責務</li>
            </ul>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')

        bill_data = EnhancedBillData(
            bill_id="test-1", title="テスト法案", submission_date=None,
            status="審議中", stage="審議中", submitter="政府", category="その他",
            url="http://example.com"
        )

        scraper._extract_key_provisions(soup, bill_data)

        assert bill_data.key_provisions is not None
        assert len(bill_data.key_provisions) == 3
        assert "第一条" in bill_data.key_provisions[0]

    def test_extract_related_laws(self, scraper):
        """Test related laws extraction"""
        html = """
        <div>
            <p>本法案は、個人情報保護法、行政手続法、電子政府法の一部を改正する。</p>
        </div>
        """
        soup = BeautifulSoup(html, 'html.parser')

        bill_data = EnhancedBillData(
            bill_id="test-1", title="テスト法案", submission_date=None,
            status="審議中", stage="審議中", submitter="政府", category="その他",
            url="http://example.com"
        )

        scraper._extract_related_laws(soup, bill_data)

        assert bill_data.related_laws is not None
        assert "個人情報保護法" in bill_data.related_laws
        assert "行政手続法" in bill_data.related_laws
        assert "電子政府法" in bill_data.related_laws

    def test_calculate_data_quality_score(self, scraper):
        """Test data quality score calculation"""
        # Complete bill data
        complete_bill = EnhancedBillData(
            bill_id="complete-1", title="完全な法案", submission_date=datetime.now(),
            status="審議中", stage="審議中", submitter="政府", category="その他",
            url="http://example.com",
            bill_outline="詳細な法案概要",
            background_context="提出背景",
            expected_effects="期待される効果",
            key_provisions=["第一条", "第二条"],
            related_laws=["関連法1", "関連法2"],
            submitting_members=["議員A", "議員B"],
            sponsoring_ministry="内閣府"
        )

        score = scraper._calculate_data_quality_score(complete_bill)
        assert score > 0.8

        # Incomplete bill data
        incomplete_bill = EnhancedBillData(
            bill_id="incomplete-1", title="不完全な法案", submission_date=None,
            status="審議中", stage="審議中", submitter="政府", category="その他",
            url="http://example.com"
        )

        score = scraper._calculate_data_quality_score(incomplete_bill)
        assert score < 0.5


class TestShugiinScraper:
    """Test cases for ShugiinScraper"""

    @pytest.fixture
    def scraper(self):
        """Create test scraper instance"""
        return ShugiinScraper(delay_seconds=0.1)

    @pytest.fixture
    def mock_bill_list_html(self):
        """Mock HTML for bill list"""
        return """
        <html>
        <table>
            <tr>
                <th>提出番号</th>
                <th>議案件名</th>
                <th>議案種類</th>
                <th>状況</th>
            </tr>
            <tr>
                <td>1</td>
                <td><a href="/bill/1">デジタル改革関連法案</a></td>
                <td>政府提出</td>
                <td>審議中</td>
            </tr>
            <tr>
                <td>2</td>
                <td><a href="/bill/2">個人情報保護法改正案</a></td>
                <td>議員提出</td>
                <td>可決</td>
            </tr>
        </table>
        </html>
        """

    def test_is_bills_table(self, scraper):
        """Test bills table detection"""
        # Valid bills table
        html = """
        <table>
            <tr><th>議案番号</th><th>議案件名</th><th>提出者</th></tr>
        </table>
        """
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table')

        assert scraper._is_bills_table(table) is True

        # Invalid table
        html = """
        <table>
            <tr><th>名前</th><th>年齢</th><th>住所</th></tr>
        </table>
        """
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table')

        assert scraper._is_bills_table(table) is False

    def test_parse_bill_row(self, scraper):
        """Test bill row parsing"""
        html = """
        <tr>
            <td>1</td>
            <td><a href="/bill/1">デジタル改革関連法案</a></td>
            <td>政府提出</td>
            <td>審議中</td>
        </tr>
        """
        soup = BeautifulSoup(html, 'html.parser')
        row = soup.find('tr')

        bill_data = scraper._parse_bill_row(row, "217")

        assert bill_data is not None
        assert bill_data.bill_id == "217-1"
        assert bill_data.title == "デジタル改革関連法案"
        assert bill_data.submitter == "政府"
        assert bill_data.status == "審議中"
        assert bill_data.source_house == "衆議院"

    def test_map_submitter_type(self, scraper):
        """Test submitter type mapping"""
        assert scraper._map_submitter_type("政府提出") == "政府"
        assert scraper._map_submitter_type("議員提出") == "議員"
        assert scraper._map_submitter_type("内閣提出") == "政府"
        assert scraper._map_submitter_type("議員発議") == "議員"
        assert scraper._map_submitter_type("その他") == "議員"  # Default

    def test_determine_category(self, scraper):
        """Test category determination"""
        assert scraper._determine_category("令和3年度予算案") == "予算・決算"
        assert scraper._determine_category("所得税法改正案") == "税制"
        assert scraper._determine_category("社会保障制度改革法案") == "社会保障"
        assert scraper._determine_category("未知の法案") == "その他"

    @patch('requests.Session.get')
    def test_fetch_bill_list(self, mock_get, scraper, mock_bill_list_html):
        """Test bill list fetching"""
        # Mock response
        mock_response = Mock()
        mock_response.content = mock_bill_list_html.encode('utf-8')
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        bills = scraper.fetch_bill_list("217")

        assert len(bills) == 2
        assert bills[0].title == "デジタル改革関連法案"
        assert bills[1].title == "個人情報保護法改正案"
        assert bills[0].submitter == "政府"
        assert bills[1].submitter == "議員"


class TestBillDataMerger:
    """Test cases for BillDataMerger"""

    @pytest.fixture
    def merger(self):
        """Create test merger instance"""
        return BillDataMerger(
            conflict_strategy=ConflictResolutionStrategy.MOST_COMPLETE,
            similarity_threshold=0.7
        )

    @pytest.fixture
    def sample_sangiin_bill(self):
        """Sample Sangiin bill"""
        return EnhancedBillData(
            bill_id="sangiin-1",
            title="デジタル社会形成基本法案",
            submission_date=datetime(2021, 2, 9),
            status="審議中",
            stage="審議中",
            submitter="政府",
            category="行政・公務員",
            url="http://sangiin.go.jp/bill/1",
            bill_outline="デジタル社会形成に関する基本的な法案",
            diet_session="204",
            house_of_origin="参議院",
            source_house="参議院",
            data_quality_score=0.8
        )

    @pytest.fixture
    def sample_shugiin_bill(self):
        """Sample Shugiin bill"""
        return ShugiinBillData(
            bill_id="shugiin-1",
            title="デジタル社会形成基本法案",
            submission_date=datetime(2021, 2, 9),
            status="審議中",
            stage="審議中",
            submitter="政府",
            category="行政・公務員",
            url="http://shugiin.go.jp/bill/1",
            supporting_members=["議員A", "議員B", "議員C"],
            diet_session="204",
            house_of_origin="衆議院",
            source_house="衆議院",
            data_quality_score=0.7
        )

    def test_calculate_similarity_score(self, merger, sample_sangiin_bill, sample_shugiin_bill):
        """Test similarity score calculation"""
        score = merger._calculate_similarity_score(sample_sangiin_bill, sample_shugiin_bill)

        assert score > 0.8  # Should be high similarity
        assert score <= 1.0

    def test_find_matching_bills(self, merger, sample_sangiin_bill, sample_shugiin_bill):
        """Test bill matching"""
        sangiin_bills = [sample_sangiin_bill]
        shugiin_bills = [sample_shugiin_bill]

        matches = merger._find_matching_bills(sangiin_bills, shugiin_bills)

        assert len(matches) == 1
        assert matches[sample_sangiin_bill.bill_id] == sample_shugiin_bill

    def test_merge_bill_pair(self, merger, sample_sangiin_bill, sample_shugiin_bill):
        """Test bill pair merging"""
        result = merger._merge_bill_pair(sample_sangiin_bill, sample_shugiin_bill)

        assert isinstance(result, MergeResult)
        assert result.merged_bill.bill_id == sample_sangiin_bill.bill_id
        assert result.merged_bill.title == sample_sangiin_bill.title
        assert result.merged_bill.source_house == "両院"
        assert result.merged_bill.supporting_members == sample_shugiin_bill.supporting_members
        assert result.merge_quality_score > 0.0

    def test_resolve_field_conflict(self, merger):
        """Test field conflict resolution"""
        # Test no conflict
        merged_value, conflict = merger._resolve_field_conflict(
            "title", "同じタイトル", "同じタイトル"
        )
        assert merged_value == "同じタイトル"
        assert conflict is None

        # Test conflict with different values
        merged_value, conflict = merger._resolve_field_conflict(
            "bill_outline", "短い説明", "より長い詳細な説明文"
        )
        assert merged_value == "より長い詳細な説明文"  # Should choose longer text
        assert conflict is not None
        assert conflict.field_name == "bill_outline"

    def test_merge_bills(self, merger, sample_sangiin_bill, sample_shugiin_bill):
        """Test complete bill merging"""
        sangiin_bills = [sample_sangiin_bill]
        shugiin_bills = [sample_shugiin_bill]

        results = merger.merge_bills(sangiin_bills, shugiin_bills)

        assert len(results) == 1
        assert results[0].merged_bill.source_house == "両院"
        assert len(results[0].source_info['sources']) == 2
        assert results[0].merge_quality_score > 0.0

    def test_get_merge_statistics(self, merger):
        """Test merge statistics"""
        # Mock merge results
        mock_results = [
            MergeResult(
                merged_bill=EnhancedBillData(
                    bill_id="1", title="法案1", submission_date=None,
                    status="審議中", stage="審議中", submitter="政府",
                    category="その他", url="http://example.com"
                ),
                conflicts=[],
                merge_quality_score=0.9,
                source_info={'sources': ['sangiin', 'shugiin'], 'primary_source': 'sangiin'}
            ),
            MergeResult(
                merged_bill=EnhancedBillData(
                    bill_id="2", title="法案2", submission_date=None,
                    status="審議中", stage="審議中", submitter="政府",
                    category="その他", url="http://example.com"
                ),
                conflicts=[],
                merge_quality_score=0.8,
                source_info={'sources': ['sangiin'], 'primary_source': 'sangiin'}
            )
        ]

        stats = merger.get_merge_statistics(mock_results)

        assert stats['total_bills'] == 2
        assert stats['both_houses'] == 1
        assert stats['sangiin_only'] == 1
        assert stats['shugiin_only'] == 0
        assert stats['avg_quality_score'] == 0.85


class TestBillDataValidator:
    """Test cases for BillDataValidator"""

    @pytest.fixture
    def validator(self):
        """Create test validator instance"""
        return BillDataValidator(strict_mode=False, require_japanese=True)

    @pytest.fixture
    def valid_bill(self):
        """Valid bill data"""
        return EnhancedBillData(
            bill_id="valid-1",
            title="有効な法案",
            submission_date=datetime(2021, 2, 9),
            status="審議中",
            stage="審議中",
            submitter="政府",
            category="行政・公務員",
            url="http://example.com/bill/1",
            bill_outline="この法案は重要な改正を行うものである。",
            diet_session="204",
            house_of_origin="参議院",
            source_house="参議院",
            data_quality_score=0.8
        )

    @pytest.fixture
    def invalid_bill(self):
        """Invalid bill data"""
        return EnhancedBillData(
            bill_id="",  # Missing required field
            title="Invalid Bill",  # No Japanese
            submission_date=None,
            status="invalid_status",  # Invalid status
            stage="invalid_stage",  # Invalid stage
            submitter="invalid_submitter",  # Invalid submitter
            category="invalid_category",  # Invalid category
            url="http://example.com/bill/1",
            data_quality_score=1.5  # Out of range
        )

    def test_validate_required_fields(self, validator, valid_bill, invalid_bill):
        """Test required field validation"""
        # Valid bill
        result = validator.validate_bill(valid_bill, 'standard')
        required_issues = [issue for issue in result.issues if issue.issue_type == 'missing_required_field']
        assert len(required_issues) == 0

        # Invalid bill
        result = validator.validate_bill(invalid_bill, 'standard')
        required_issues = [issue for issue in result.issues if issue.issue_type == 'missing_required_field']
        assert len(required_issues) > 0

    def test_validate_field_formats(self, validator, invalid_bill):
        """Test field format validation"""
        result = validator.validate_bill(invalid_bill, 'standard')

        format_issues = [issue for issue in result.issues if issue.issue_type == 'invalid_format']
        assert len(format_issues) > 0

    def test_validate_data_consistency(self, validator, invalid_bill):
        """Test data consistency validation"""
        result = validator.validate_bill(invalid_bill, 'standard')

        consistency_issues = [
            issue for issue in result.issues
            if issue.issue_type in ['invalid_value', 'out_of_range']
        ]
        assert len(consistency_issues) > 0

    def test_validate_japanese_content(self, validator, valid_bill):
        """Test Japanese content validation"""
        result = validator.validate_bill(valid_bill, 'standard')

        japanese_issues = [
            issue for issue in result.issues
            if issue.issue_type == 'missing_japanese_text'
        ]
        # Should have no issues for valid Japanese content
        assert len(japanese_issues) == 0

    def test_calculate_completeness_score(self, validator, valid_bill, invalid_bill):
        """Test completeness score calculation"""
        # Valid bill should have high completeness
        valid_score = validator._calculate_completeness_score(valid_bill, 'standard')
        assert valid_score > 0.7

        # Invalid bill should have low completeness
        invalid_score = validator._calculate_completeness_score(invalid_bill, 'standard')
        assert invalid_score < 0.5

    def test_validate_bills(self, validator, valid_bill, invalid_bill):
        """Test multiple bills validation"""
        bills = [valid_bill, invalid_bill]
        results = validator.validate_bills(bills, 'standard')

        assert len(results) == 2
        assert results[0].is_valid is True
        assert results[1].is_valid is False

    def test_get_validation_summary(self, validator, valid_bill, invalid_bill):
        """Test validation summary"""
        bills = [valid_bill, invalid_bill]
        results = validator.validate_bills(bills, 'standard')
        summary = validator.get_validation_summary(results)

        assert summary['total_bills'] == 2
        assert summary['valid_bills'] == 1
        assert summary['invalid_bills'] == 1
        assert summary['validation_rate'] == 0.5
        assert 'avg_quality_score' in summary
        assert 'common_issues' in summary


class TestIntegration:
    """Integration tests for the complete pipeline"""

    @pytest.fixture
    def scraper(self):
        return EnhancedDietScraper(delay_seconds=0.1, enable_resilience=False)

    @pytest.fixture
    def shugiin_scraper(self):
        return ShugiinScraper(delay_seconds=0.1)

    @pytest.fixture
    def merger(self):
        return BillDataMerger(conflict_strategy=ConflictResolutionStrategy.MOST_COMPLETE)

    @pytest.fixture
    def validator(self):
        return BillDataValidator(strict_mode=False, require_japanese=True)

    def test_complete_pipeline(self, scraper, shugiin_scraper, merger, validator):
        """Test complete data processing pipeline"""
        # Mock data
        sangiin_bill = EnhancedBillData(
            bill_id="pipeline-1",
            title="パイプラインテスト法案",
            submission_date=datetime(2021, 2, 9),
            status="審議中",
            stage="審議中",
            submitter="政府",
            category="行政・公務員",
            url="http://sangiin.go.jp/bill/1",
            bill_outline="パイプラインテスト用の法案概要",
            diet_session="204",
            house_of_origin="参議院",
            source_house="参議院"
        )

        shugiin_bill = ShugiinBillData(
            bill_id="pipeline-2",
            title="パイプラインテスト法案",
            submission_date=datetime(2021, 2, 9),
            status="審議中",
            stage="審議中",
            submitter="政府",
            category="行政・公務員",
            url="http://shugiin.go.jp/bill/1",
            supporting_members=["議員A", "議員B"],
            diet_session="204",
            house_of_origin="衆議院",
            source_house="衆議院"
        )

        # Step 1: Merge bills
        merge_results = merger.merge_bills([sangiin_bill], [shugiin_bill])
        assert len(merge_results) == 1

        # Step 2: Validate merged bills
        validation_results = validator.validate_merge_results(merge_results)
        assert len(validation_results) == 1

        # Step 3: Check final result
        final_result = validation_results[0]
        assert final_result.is_valid is True
        assert final_result.quality_score > 0.7

        # Step 4: Get statistics
        merge_stats = merger.get_merge_statistics(merge_results)
        validation_summary = validator.get_validation_summary(validation_results)

        assert merge_stats['total_bills'] == 1
        assert merge_stats['both_houses'] == 1
        assert validation_summary['validation_rate'] == 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
