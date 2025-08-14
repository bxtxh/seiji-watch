"""Tests for schema mapping and data transformation."""

import json
import unittest
from datetime import datetime, date
from unittest.mock import Mock, patch

from shared.migration.schema_mapper import SchemaMapper


class TestSchemaMapper(unittest.TestCase):
    """Test schema mapping functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mapper = SchemaMapper()
        
    def test_simple_field_mapping(self):
        """Test basic field mapping from Airtable to Supabase."""
        airtable_record = {
            "id": "rec123",
            "fields": {
                "Name": "自由民主党",
                "Name_EN": "Liberal Democratic Party",
                "Abbreviation": "LDP",
                "Color_Code": "#FF0000",
                "Is_Active": True,
            }
        }
        
        result = self.mapper.airtable_to_supabase("Parties", airtable_record)
        
        self.assertEqual(result["airtable_id"], "rec123")
        self.assertEqual(result["name"], "自由民主党")
        self.assertEqual(result["name_en"], "Liberal Democratic Party")
        self.assertEqual(result["abbreviation"], "LDP")
        self.assertEqual(result["color_code"], "#FF0000")
        self.assertTrue(result["is_active"])
        
    def test_type_conversion(self):
        """Test type conversion for different field types."""
        airtable_record = {
            "id": "rec456",
            "fields": {
                "Name": "Test Member",
                "House": "参議院",
                "Terms_Served": "5",
                "Birth_Date": "1970-01-15",
                "Is_Active": "true",
                "Created_At": "2024-01-15T09:30:00.000Z",
            }
        }
        
        result = self.mapper.airtable_to_supabase("Members", airtable_record)
        
        self.assertEqual(result["terms_served"], 5)
        self.assertTrue(result["is_active"])
        self.assertEqual(result["birth_date"], "1970-01-15")
        self.assertEqual(result["created_at"], "2024-01-15T09:30:00.000Z")
        
    def test_json_field_conversion(self):
        """Test conversion of JSON fields."""
        airtable_record = {
            "id": "rec789",
            "fields": {
                "Bill_Number": "第123号",
                "Title": "Test Bill",
                "Submitting_Members": ["Member1", "Member2"],
                "Key_Points": {"point1": "value1", "point2": "value2"},
                "Tags": "tag1, tag2, tag3",
            }
        }
        
        result = self.mapper.airtable_to_supabase("Bills (法案)", airtable_record)
        
        self.assertEqual(result["bill_number"], "第123号")
        self.assertEqual(
            json.loads(result["submitting_members"]),
            ["Member1", "Member2"]
        )
        self.assertEqual(
            json.loads(result["key_points"]),
            {"point1": "value1", "point2": "value2"}
        )
        self.assertEqual(
            json.loads(result["tags"]),
            ["tag1, tag2, tag3"]
        )
        
    def test_foreign_key_resolution(self):
        """Test foreign key resolution with ID mappings."""
        id_mappings = {
            "parties": {
                "recParty1": "uuid-party-1",
                "recParty2": "uuid-party-2",
            },
            "bills": {
                "recBill1": "uuid-bill-1",
            }
        }
        
        airtable_record = {
            "id": "recMember1",
            "fields": {
                "Name": "Test Member",
                "House": "衆議院",
                "Party": ["recParty1"],
            }
        }
        
        result = self.mapper.airtable_to_supabase(
            "Members", airtable_record, id_mappings
        )
        
        self.assertEqual(result["party_id"], ["uuid-party-1"])
        
    def test_date_conversion_formats(self):
        """Test conversion of various date formats."""
        test_dates = [
            ("2024-01-15", "2024-01-15"),
            ("2024/01/15", "2024-01-15"),
            ("15/01/2024", "2024-01-15"),
            ("2024年1月15日", "2024-01-15"),
        ]
        
        for input_date, expected in test_dates:
            result = self.mapper._convert_date(input_date)
            self.assertEqual(
                result, expected,
                f"Failed to convert {input_date}"
            )
            
    def test_boolean_conversion(self):
        """Test boolean conversion from various formats."""
        test_cases = [
            (True, True),
            (False, False),
            ("true", True),
            ("false", False),
            ("yes", True),
            ("no", False),
            ("1", True),
            ("0", False),
            (1, True),
            (0, False),
        ]
        
        for input_val, expected in test_cases:
            result = self.mapper._convert_boolean(input_val)
            self.assertEqual(
                result, expected,
                f"Failed to convert {input_val}"
            )
            
    def test_decimal_conversion(self):
        """Test decimal number conversion."""
        test_cases = [
            ("123.45", 123.45),
            (123.45, 123.45),
            ("0.95", 0.95),
            (None, None),
            ("", None),
        ]
        
        for input_val, expected in test_cases:
            result = self.mapper._convert_decimal(input_val)
            self.assertEqual(
                result, expected,
                f"Failed to convert {input_val}"
            )
            
    def test_array_conversion(self):
        """Test array conversion from various formats."""
        test_cases = [
            (["a", "b", "c"], ["a", "b", "c"]),
            ("a, b, c", ["a", "b", "c"]),
            ('["a", "b", "c"]', ["a", "b", "c"]),
            ("single", ["single"]),
            (None, []),
            ("", []),
        ]
        
        for input_val, expected in test_cases:
            result = self.mapper._convert_array(input_val)
            self.assertEqual(
                result, expected,
                f"Failed to convert {input_val}"
            )
            
    def test_time_conversion(self):
        """Test time string conversion."""
        test_cases = [
            ("14:30", "14:30:00"),
            ("14:30:45", "14:30:45"),
            ("2:30", "2:30"),  # Invalid format, returned as-is
        ]
        
        for input_val, expected in test_cases:
            result = self.mapper._convert_time(input_val)
            self.assertEqual(
                result, expected,
                f"Failed to convert {input_val}"
            )
            
    def test_get_supabase_table_name(self):
        """Test Airtable to Supabase table name mapping."""
        test_cases = [
            ("Parties", "parties"),
            ("Members", "members"),
            ("Bills (法案)", "bills"),
            ("IssueCategories", "policy_categories"),
            ("Votes (投票)", "votes"),
            ("UnknownTable", "unknowntable"),
        ]
        
        for airtable_name, expected in test_cases:
            result = self.mapper.get_supabase_table_name(airtable_name)
            self.assertEqual(
                result, expected,
                f"Failed to map {airtable_name}"
            )
            
    def test_validate_record_required_fields(self):
        """Test record validation for required fields."""
        # Valid record
        valid_record = {
            "airtable_id": "rec123",
            "name": "Test Party",
        }
        errors = self.mapper.validate_record("parties", valid_record)
        self.assertEqual(len(errors), 0)
        
        # Missing required field
        invalid_record = {
            "airtable_id": "rec123",
        }
        errors = self.mapper.validate_record("parties", invalid_record)
        self.assertIn("Missing required field: name", errors)
        
    def test_validate_record_constraints(self):
        """Test record validation for specific constraints."""
        # Invalid house value
        record = {
            "airtable_id": "rec123",
            "name": "Test Member",
            "house": "Invalid House",
        }
        errors = self.mapper.validate_record("members", record)
        self.assertIn("Invalid house value: Invalid House", errors)
        
        # Invalid layer value
        record = {
            "airtable_id": "rec456",
            "cap_code": "1.2.3",
            "layer": "L4",
            "title_ja": "Test Category",
        }
        errors = self.mapper.validate_record("policy_categories", record)
        self.assertIn("Invalid layer value: L4", errors)
        
        # Invalid color code
        record = {
            "airtable_id": "rec789",
            "name": "Test Party",
            "color_code": "not-a-color",
        }
        errors = self.mapper.validate_record("parties", record)
        self.assertIn("Invalid color code: not-a-color", errors)
        
    def test_complex_bill_mapping(self):
        """Test mapping of complex bill record with all fields."""
        airtable_record = {
            "id": "recBill123",
            "fields": {
                "Bill_Number": "第210回国会第45号",
                "Title": "消費税法改正案",
                "Title_EN": "Consumption Tax Law Amendment",
                "Short_Title": "消費税改正",
                "Summary": "消費税率の見直しに関する法案",
                "Status": "審議中",
                "Category": "taxation",
                "Diet_Session": "210",
                "House_Of_Origin": "衆議院",
                "Submitter_Type": "government",
                "Submitted_Date": "2024-01-15",
                "Estimated_Cost": "1000000000",
                "Is_Controversial": True,
                "Priority_Level": "high",
                "Submitting_Members": ["Member1", "Member2", "Member3"],
                "Key_Points": [
                    "税率の段階的引き上げ",
                    "低所得者への配慮",
                    "実施時期の検討"
                ],
                "Tags": ["税制", "経済", "社会保障"],
                "Created_At": "2024-01-15T10:00:00.000Z",
                "Updated_At": "2024-01-20T15:30:00.000Z",
            }
        }
        
        result = self.mapper.airtable_to_supabase("Bills (法案)", airtable_record)
        
        # Check all mapped fields
        self.assertEqual(result["airtable_id"], "recBill123")
        self.assertEqual(result["bill_number"], "第210回国会第45号")
        self.assertEqual(result["title"], "消費税法改正案")
        self.assertEqual(result["title_en"], "Consumption Tax Law Amendment")
        self.assertEqual(result["short_title"], "消費税改正")
        self.assertEqual(result["summary"], "消費税率の見直しに関する法案")
        self.assertEqual(result["status"], "審議中")
        self.assertEqual(result["category"], "taxation")
        self.assertEqual(result["diet_session"], "210")
        self.assertEqual(result["house_of_origin"], "衆議院")
        self.assertEqual(result["submitter_type"], "government")
        self.assertEqual(result["submitted_date"], "2024-01-15")
        self.assertEqual(result["estimated_cost"], 1000000000.0)
        self.assertTrue(result["is_controversial"])
        self.assertEqual(result["priority_level"], "high")
        
        # Check JSON fields
        submitting_members = json.loads(result["submitting_members"])
        self.assertEqual(len(submitting_members), 3)
        self.assertIn("Member1", submitting_members)
        
        key_points = json.loads(result["key_points"])
        self.assertEqual(len(key_points), 3)
        self.assertIn("税率の段階的引き上げ", key_points)
        
        tags = json.loads(result["tags"])
        self.assertEqual(len(tags), 3)
        self.assertIn("税制", tags)
        
        # Check timestamps
        self.assertEqual(result["created_at"], "2024-01-15T10:00:00.000Z")
        self.assertEqual(result["updated_at"], "2024-01-20T15:30:00.000Z")
        
        # Check sync version
        self.assertEqual(result["sync_version"], 1)


if __name__ == "__main__":
    unittest.main()