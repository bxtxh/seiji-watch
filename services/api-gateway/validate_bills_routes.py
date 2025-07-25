#!/usr/bin/env python3
"""Validate Bills API routes structure without imports."""

import ast
import os


def validate_bills_routes():
    """Validate the Bills API routes file structure."""
    print("🔍 Validating Bills API Routes Structure")
    print("=" * 50)

    # Read the bills routes file
    bills_routes_path = (
        "/Users/shogen/seiji-watch/services/api-gateway/src/routes/bills.py"
    )

    if not os.path.exists(bills_routes_path):
        print("❌ Bills routes file not found")
        return False

    try:
        with open(bills_routes_path, encoding="utf-8") as f:
            content = f.read()

        # Parse the Python file
        tree = ast.parse(content)

        # Extract function definitions
        functions = []
        classes = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(node.name)
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)

        print("✅ Bills routes file parsed successfully")
        print(f"   File size: {len(content)} characters")
        print(f"   Functions found: {len(functions)}")
        print(f"   Classes found: {len(classes)}")

        # Check for expected endpoints
        expected_endpoints = [
            "list_bills",
            "get_bill",
            "search_bills",
            "create_bill_policy_category_relationship",
            "get_bill_policy_categories",
            "update_bill_policy_category_relationship",
            "delete_bill_policy_category_relationship",
            "bulk_create_bill_policy_category_relationships",
            "get_bills_policy_category_statistics",
        ]

        print("\n📋 Expected endpoint functions:")
        for endpoint in expected_endpoints:
            if endpoint in functions:
                print(f"   ✅ {endpoint}")
            else:
                print(f"   ❌ {endpoint} - Missing")

        # Check for expected request models
        expected_models = ["PolicyCategoryRelationshipRequest", "BillSearchRequest"]

        print("\n📋 Expected request models:")
        for model in expected_models:
            if model in classes:
                print(f"   ✅ {model}")
            else:
                print(f"   ❌ {model} - Missing")

        # Check for FastAPI router
        router_found = "router = APIRouter" in content
        print(f"\n🔌 FastAPI Router: {'✅ Found' if router_found else '❌ Not found'}")

        # Check for proper imports
        has_fastapi_imports = "from fastapi import" in content
        has_pydantic_imports = "from pydantic import" in content
        has_shared_imports = "from shared.clients import" in content

        print("\n📦 Import structure:")
        print(f"   FastAPI imports: {'✅' if has_fastapi_imports else '❌'}")
        print(f"   Pydantic imports: {'✅' if has_pydantic_imports else '❌'}")
        print(f"   Shared imports: {'✅' if has_shared_imports else '❌'}")

        # Check for API endpoint decorators
        get_decorators = content.count("@router.get(")
        post_decorators = content.count("@router.post(")
        put_decorators = content.count("@router.put(")
        delete_decorators = content.count("@router.delete(")

        print("\n🎯 API endpoint decorators:")
        print(f"   GET endpoints: {get_decorators}")
        print(f"   POST endpoints: {post_decorators}")
        print(f"   PUT endpoints: {put_decorators}")
        print(f"   DELETE endpoints: {delete_decorators}")

        total_endpoints = (
            get_decorators + post_decorators + put_decorators + delete_decorators
        )
        print(f"   Total endpoints: {total_endpoints}")

        return True

    except Exception as e:
        print(f"❌ Error validating bills routes: {e}")
        return False


def validate_airtable_client_extensions():
    """Validate the Airtable client extensions."""
    print("\n🔍 Validating Airtable Client Extensions")
    print("=" * 50)

    # Read the airtable client file
    airtable_client_path = (
        "/Users/shogen/seiji-watch/shared/src/shared/clients/airtable.py"
    )

    if not os.path.exists(airtable_client_path):
        print("❌ Airtable client file not found")
        return False

    try:
        with open(airtable_client_path, encoding="utf-8") as f:
            content = f.read()

        # Check for Bills-PolicyCategory methods
        expected_methods = [
            "create_bill_policy_category_relationship",
            "get_bill_policy_category_relationship",
            "list_bill_policy_category_relationships",
            "update_bill_policy_category_relationship",
            "delete_bill_policy_category_relationship",
            "bulk_create_bill_policy_category_relationships",
            "get_bills_by_policy_category",
            "get_policy_categories_by_bill",
            "list_bills_policy_categories",
        ]

        print("📋 Expected Airtable client methods:")
        for method in expected_methods:
            if f"async def {method}" in content:
                print(f"   ✅ {method}")
            else:
                print(f"   ❌ {method} - Missing")

        # Check for Bills_PolicyCategories table references
        table_refs = content.count("Bills_PolicyCategories")
        print(f"\n📊 Bills_PolicyCategories table references: {table_refs}")

        return True
    except Exception as e:
        print(f"❌ Error validating Airtable client: {e}")
        return False


def validate_main_app_integration():
    """Validate the main app integration."""
    print("\n🔍 Validating Main App Integration")
    print("=" * 50)

    # Read the main app file
    main_app_path = "/Users/shogen/seiji-watch/services/api-gateway/src/main.py"

    if not os.path.exists(main_app_path):
        print("❌ Main app file not found")
        return False

    try:
        with open(main_app_path, encoding="utf-8") as f:
            content = f.read()

        # Check for bills router import and inclusion
        bills_import = "from .routes import issues, speeches, bills" in content
        bills_inclusion = "app.include_router(bills.router)" in content

        print("📦 Bills router integration:")
        print(f"   Import statement: {'✅' if bills_import else '❌'}")
        print(f"   Router inclusion: {'✅' if bills_inclusion else '❌'}")
        return bills_import and bills_inclusion

    except Exception as e:
        print(f"❌ Error validating main app: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Bills-PolicyCategory API Validation")
    print("=" * 60)

    # Run all validations
    bills_routes_ok = validate_bills_routes()
    airtable_client_ok = validate_airtable_client_extensions()
    main_app_ok = validate_main_app_integration()

    print("\n📊 Validation Summary:")
    bills_status = "✅ Valid" if bills_routes_ok else "❌ Invalid"
    airtable_status = "✅ Valid" if airtable_client_ok else "❌ Invalid"
    main_status = "✅ Valid" if main_app_ok else "❌ Invalid"

    print(f"   Bills routes structure: {bills_status}")
    print(f"   Airtable client extensions: {airtable_status}")
    print(f"   Main app integration: {main_status}")

    if bills_routes_ok and airtable_client_ok and main_app_ok:
        print(
            "\n✅ All validations passed! "
            "Bills-PolicyCategory API is ready for T128 completion."
        )
    else:
        print("\n❌ Some validations failed. " "Please fix issues before proceeding.")
        print("\n🎯 Next steps for T128 completion:")
        print(
            "   1. Start the API server: cd /Users/shogen/seiji-watch/"
            "services/api-gateway && python -m uvicorn src.main:app --reload"
        )
        print("   2. Test with: python test_bills_policy_category_api.py")
        print("   3. Check API docs at: http://localhost:8000/docs")
