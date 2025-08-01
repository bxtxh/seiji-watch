#!/usr/bin/env python3
"""
Airtable Schema Inspector
Airtableテーブルのスキーマとフィールド制約を調査
"""

import asyncio
import json
import os
from datetime import datetime

import aiohttp
from dotenv import load_dotenv

load_dotenv("/Users/shogen/seiji-watch/.env.local")


class AirtableSchemaInspector:
    """Airtable schema and field constraint inspector"""

    def __init__(self):
        self.pat = os.getenv("AIRTABLE_PAT")
        self.base_id = os.getenv("AIRTABLE_BASE_ID")
        self.base_url = f"https://api.airtable.com/v0/{self.base_id}"

        if not self.pat or not self.base_id:
            raise ValueError("Airtable PAT and base ID are required")

        self.headers = {
            "Authorization": f"Bearer {self.pat}",
            "Content-Type": "application/json",
        }

    async def get_base_schema(self, session: aiohttp.ClientSession) -> dict:
        """Get base schema information"""
        try:
            # Note: Airtable doesn't provide direct schema API in the standard API
            # We'll need to inspect through record structure
            url = f"https://api.airtable.com/v0/meta/bases/{self.base_id}/tables"

            async with session.get(url, headers=self.headers) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    print(f"⚠️ Schema API not available: {response.status}")
                    return {}
        except Exception as e:
            print(f"⚠️ Error fetching base schema: {e}")
            return {}

    async def inspect_table_fields(
        self, session: aiohttp.ClientSession, table_name: str
    ) -> dict:
        """Inspect table fields by examining existing records"""
        try:
            url = f"{self.base_url}/{table_name}"
            # Just need a few records to understand structure
            params = {"maxRecords": 5}

            async with session.get(
                url, headers=self.headers, params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    records = data.get("records", [])

                    if not records:
                        return {"fields": {}, "analysis": "No records found"}

                    # Analyze field types and values
                    field_analysis = {}
                    all_fields = set()

                    for record in records:
                        fields = record.get("fields", {})
                        all_fields.update(fields.keys())

                    for field_name in all_fields:
                        field_analysis[field_name] = {
                            "appears_in_records": 0,
                            "sample_values": [],
                            "value_types": set(),
                            "is_empty_count": 0,
                            "max_length": 0,
                        }

                    # Analyze each record
                    for record in records:
                        fields = record.get("fields", {})

                        for field_name in all_fields:
                            if field_name in fields:
                                value = fields[field_name]
                                field_analysis[field_name]["appears_in_records"] += 1

                                if value is None or value == "":
                                    field_analysis[field_name]["is_empty_count"] += 1
                                else:
                                    # Store sample values (max 3)
                                    if (
                                        len(field_analysis[field_name]["sample_values"])
                                        < 3
                                    ):
                                        field_analysis[field_name][
                                            "sample_values"
                                        ].append(value)

                                    # Track value types
                                    if isinstance(value, list):
                                        field_analysis[field_name]["value_types"].add(
                                            "array"
                                        )
                                        if value and isinstance(value[0], dict):
                                            field_analysis[field_name][
                                                "value_types"
                                            ].add("linked_record")
                                        elif value and isinstance(value[0], str):
                                            field_analysis[field_name][
                                                "value_types"
                                            ].add("attachment")
                                    elif isinstance(value, dict):
                                        field_analysis[field_name]["value_types"].add(
                                            "object"
                                        )
                                    elif isinstance(value, str):
                                        field_analysis[field_name]["value_types"].add(
                                            "string"
                                        )
                                        field_analysis[field_name]["max_length"] = max(
                                            field_analysis[field_name]["max_length"],
                                            len(value),
                                        )
                                    elif isinstance(value, int | float):
                                        field_analysis[field_name]["value_types"].add(
                                            "number"
                                        )
                                    elif isinstance(value, bool):
                                        field_analysis[field_name]["value_types"].add(
                                            "boolean"
                                        )
                                    else:
                                        field_analysis[field_name]["value_types"].add(
                                            type(value).__name__
                                        )

                    # Convert sets to lists for JSON serialization
                    for field_name in field_analysis:
                        field_analysis[field_name]["value_types"] = list(
                            field_analysis[field_name]["value_types"]
                        )

                    return {
                        "total_records_analyzed": len(records),
                        "total_fields": len(all_fields),
                        "fields": field_analysis,
                    }
                else:
                    print(f"❌ Error fetching {table_name}: {response.status}")
                    return {"error": f"HTTP {response.status}"}

        except Exception as e:
            print(f"❌ Error inspecting {table_name}: {e}")
            return {"error": str(e)}

    async def test_field_updates(
        self, session: aiohttp.ClientSession, table_name: str
    ) -> dict:
        """Test different field update patterns to identify constraints"""
        try:
            # Get a sample record first
            url = f"{self.base_url}/{table_name}"
            params = {"maxRecords": 1}

            async with session.get(
                url, headers=self.headers, params=params
            ) as response:
                if response.status != 200:
                    return {"error": f"Cannot fetch test record: {response.status}"}

                data = await response.json()
                records = data.get("records", [])

                if not records:
                    return {"error": "No records available for testing"}

                test_record = records[0]
                original_fields = test_record.get("fields", {})
                record_id = test_record["id"]

                test_results = {}

                # Test 1: Update only basic text fields
                basic_fields = {}
                for field_name, value in original_fields.items():
                    if (
                        isinstance(value, str) and len(field_name) < 20
                    ):  # Simple field names
                        basic_fields[field_name] = value  # Keep original value
                        break  # Test with just one field first

                if basic_fields:
                    test_results["basic_field_update"] = await self.test_single_update(
                        session, table_name, record_id, basic_fields
                    )

                # Test 2: Update with minimal required fields only
                required_test_fields = {
                    "Title": "Test Title",
                    "Bill_Number": "Test123",
                    "Status": "提出",
                    "Session": "Test Session",
                }

                # Only include fields that exist in the original record
                minimal_fields = {}
                for field_name, value in required_test_fields.items():
                    if field_name in original_fields:
                        minimal_fields[field_name] = value

                if minimal_fields:
                    test_results["minimal_update"] = await self.test_single_update(
                        session, table_name, record_id, minimal_fields
                    )

                # Test 3: Try to identify problematic fields
                problematic_fields = {}
                for field_name, value in original_fields.items():
                    if (
                        "attachment" in field_name.lower()
                        or "summary" in field_name.lower()
                    ):
                        problematic_fields[field_name] = value

                if problematic_fields:
                    test_results["problematic_fields_test"] = (
                        await self.test_single_update(
                            session, table_name, record_id, problematic_fields
                        )
                    )

                return test_results

        except Exception as e:
            return {"error": f"Test failed: {e}"}

    async def test_single_update(
        self,
        session: aiohttp.ClientSession,
        table_name: str,
        record_id: str,
        test_fields: dict,
    ) -> dict:
        """Test a single update operation"""
        try:
            update_data = {"fields": test_fields}

            async with session.patch(
                f"{self.base_url}/{table_name}/{record_id}",
                headers=self.headers,
                json=update_data,
            ) as response:
                if response.status == 200:
                    return {
                        "status": "SUCCESS",
                        "fields_tested": list(test_fields.keys()),
                        "message": "Update successful",
                    }
                else:
                    error_text = await response.text()
                    return {
                        "status": "ERROR",
                        "fields_tested": list(test_fields.keys()),
                        "error_code": response.status,
                        "error_message": error_text,
                    }
        except Exception as e:
            return {
                "status": "EXCEPTION",
                "fields_tested": list(test_fields.keys()),
                "error_message": str(e),
            }

    def print_schema_report(self, table_name: str, schema_info: dict):
        """Print detailed schema report"""
        print(f"\n{'=' * 70}")
        print(f"📋 AIRTABLE SCHEMA ANALYSIS: {table_name}")
        print(f"{'=' * 70}")

        if "error" in schema_info:
            print(f"❌ Error: {schema_info['error']}")
            return

        print(
            f"📊 Total Records Analyzed: {schema_info.get('total_records_analyzed', 0)}"
        )
        print(f"📊 Total Fields: {schema_info.get('total_fields', 0)}")

        fields = schema_info.get("fields", {})

        print("\n📋 FIELD ANALYSIS:")
        print(f"{'-' * 70}")

        for field_name, analysis in fields.items():
            print(f"\n🔍 {field_name}")
            print(f"   📈 Appears in: {analysis['appears_in_records']} records")
            print(f"   🔢 Value types: {', '.join(analysis['value_types'])}")
            print(f"   ❌ Empty count: {analysis['is_empty_count']}")

            if analysis["max_length"] > 0:
                print(f"   📏 Max length: {analysis['max_length']}")

            if analysis["sample_values"]:
                print(f"   📝 Sample values: {analysis['sample_values'][:2]}")

            # Identify potential constraint issues
            warnings = []
            if "attachment" in analysis["value_types"]:
                warnings.append("⚠️ Attachment field - may have special constraints")
            if "linked_record" in analysis["value_types"]:
                warnings.append("⚠️ Linked record - requires valid reference IDs")
            if analysis["is_empty_count"] == 0 and analysis["appears_in_records"] > 0:
                warnings.append("🔒 Potentially required field (never empty)")

            for warning in warnings:
                print(f"   {warning}")

    def print_test_results(self, test_results: dict):
        """Print field update test results"""
        print("\n🧪 FIELD UPDATE TESTS:")
        print(f"{'-' * 50}")

        for test_name, result in test_results.items():
            print(f"\n🔬 {test_name.replace('_', ' ').title()}")

            if result.get("status") == "SUCCESS":
                print(f"   ✅ Status: {result['status']}")
                print(f"   📝 Fields: {', '.join(result['fields_tested'])}")
            else:
                print(f"   ❌ Status: {result['status']}")
                print(f"   📝 Fields: {', '.join(result['fields_tested'])}")
                print(f"   🚨 Error: {result.get('error_message', 'Unknown error')}")

    async def run_comprehensive_inspection(self):
        """Run comprehensive schema inspection"""
        print("🔍 Starting Airtable schema inspection...")

        tables_to_inspect = [
            "Bills (法案)",
            "Members (議員)",
            "Parties (政党)",
            "Speeches (発言)",
        ]

        async with aiohttp.ClientSession() as session:
            for table_name in tables_to_inspect:
                print(f"\n🔍 Inspecting {table_name}...")

                # Get schema information
                schema_info = await self.inspect_table_fields(session, table_name)
                self.print_schema_report(table_name, schema_info)

                # Test field updates (only for Bills table to identify the issue)
                if table_name == "Bills (法案)":
                    print(f"\n🧪 Testing field updates for {table_name}...")
                    test_results = await self.test_field_updates(session, table_name)
                    self.print_test_results(test_results)

                # Save detailed report
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"airtable_schema_{table_name.replace(' ', '_').replace('(', '').replace(')', '')}_{timestamp}.json"

                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(
                        {
                            "table_name": table_name,
                            "inspection_date": datetime.now().isoformat(),
                            "schema_info": schema_info,
                            "test_results": (
                                test_results if table_name == "Bills (法案)" else {}
                            ),
                        },
                        f,
                        indent=2,
                        ensure_ascii=False,
                    )

                print(f"💾 Detailed report saved: {filename}")

                # Rate limiting
                await asyncio.sleep(2)


async def main():
    """Main entry point"""
    inspector = AirtableSchemaInspector()
    await inspector.run_comprehensive_inspection()

    print("\n✅ Airtable schema inspection completed!")


if __name__ == "__main__":
    asyncio.run(main())
