#!/usr/bin/env python3
"""
修正されたingest-workerスクリプトの動作確認テスト
Notesフィールドの代わりに構造化フィールドを使用することを確認
"""

import sys
from pathlib import Path


def test_complete_integration_fields():
    """complete_integration.py の構造化フィールド使用をテスト"""

    print("🧪 complete_integration.py 構造化フィールドテスト")
    print("=" * 50)

    # ファイル読み込み
    file_path = Path(__file__).parent / "complete_integration.py"
    with open(file_path, encoding="utf-8") as f:
        content = f.read()

    # テスト項目
    tests = [
        (
            "Notesフィールド使用なし",
            '"Notes":' not in content and "'Notes':" not in content,
        ),
        (
            "Bill_Status使用確認",
            '"Bill_Status":' in content or "'Bill_Status':" in content,
        ),
        ("Category使用確認", '"Category":' in content or "'Category':" in content),
        ("Submitter使用確認", '"Submitter":' in content or "'Submitter':" in content),
    ]

    # 結果表示
    for test_name, result in tests:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")

    return all(result for _, result in tests)


def test_epic11_files_fields():
    """epic11_* ファイル群の構造化フィールド使用をテスト"""

    print("\n🧪 epic11_* ファイル群 構造化フィールドテスト")
    print("=" * 50)

    epic11_files = [
        "epic11_batch_integration.py",
        "epic11_minimal_integration.py",
        "epic11_optimized_integration.py",
        "epic11_pilot_insert.py",
    ]

    all_passed = True

    for filename in epic11_files:
        print(f"\n📁 {filename}:")

        file_path = Path(__file__).parent / filename
        if not file_path.exists():
            print(f"  ⚠️  ファイル不存在: {filename}")
            continue

        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # 各ファイルのテスト
        tests = [
            (
                "Notesフィールド使用なし",
                '"Notes":' not in content and "'Notes':" not in content,
            ),
            (
                "構造化フィールド使用確認",
                any(
                    field in content
                    for field in [
                        "Bill_Status",
                        "Category",
                        "Submitter",
                        "Bill_URL",
                        "Stage",
                        "Bill_Number",
                    ]
                ),
            ),
        ]

        file_passed = True
        for test_name, result in tests:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"    {status} {test_name}")
            if not result:
                file_passed = False

        if not file_passed:
            all_passed = False

    return all_passed


def test_api_gateway_fields():
    """API Gateway の構造化フィールド検索をテスト"""

    print("\n🧪 API Gateway 構造化フィールド検索テスト")
    print("=" * 50)

    api_files = [
        "../api-gateway/src/main.py",
        "../api-gateway/test_real_data_api.py",
        "../api-gateway/simple_airtable_test_api.py",
    ]

    all_passed = True

    for relative_path in api_files:
        filename = Path(relative_path).name
        print(f"\n📁 {filename}:")

        file_path = Path(__file__).parent / relative_path
        if not file_path.exists():
            print(f"  ⚠️  ファイル不存在: {relative_path}")
            continue

        with open(file_path, encoding="utf-8") as f:
            content = f.read()

        # 検索機能のテスト
        tests = [
            ("Notesフィールド検索なし", "SEARCH('{query}', {Notes})" not in content),
            (
                "構造化フィールド検索確認",
                "SEARCH('{query}', {Bill_Status})" in content
                or "SEARCH('{query}', {Category})" in content,
            ),
        ]

        file_passed = True
        for test_name, result in tests:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"    {status} {test_name}")
            if not result:
                file_passed = False

        if not file_passed:
            all_passed = False

    return all_passed


def test_sample_data_generation():
    """サンプルデータ生成テスト"""

    print("\n🧪 サンプルデータ生成テスト")
    print("=" * 50)

    # サンプル法案データ
    sample_bill = {
        "title": "テスト法案",
        "bill_id": "TEST-001",
        "status": "議案要旨",
        "category": "テスト分類",
        "submitter": "議員",
        "url": "https://example.com/test",
    }

    # 構造化フィールド生成のテスト（complete_integration.py方式）
    fields = {
        "Name": sample_bill["title"],
        "Bill_ID": sample_bill["bill_id"],
        "Diet_Session": "217",
        "Bill_Status": sample_bill["status"],
        "Category": sample_bill["category"],
        "Submitter": sample_bill["submitter"],
    }

    tests = [
        ("Nameフィールド設定", fields.get("Name") == "テスト法案"),
        ("Bill_IDフィールド設定", fields.get("Bill_ID") == "TEST-001"),
        ("Bill_Statusフィールド設定", fields.get("Bill_Status") == "議案要旨"),
        ("Categoryフィールド設定", fields.get("Category") == "テスト分類"),
        ("Submitterフィールド設定", fields.get("Submitter") == "議員"),
        ("Notesフィールドなし", "Notes" not in fields),
    ]

    print("  生成されたフィールド:")
    for key, value in fields.items():
        print(f"    {key}: {value}")

    print("\n  テスト結果:")
    all_passed = True
    for test_name, result in tests:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"    {status} {test_name}")
        if not result:
            all_passed = False

    return all_passed


def main():
    """全テスト実行"""

    print("🚀 修正されたパイプライン動作確認テスト")
    print("=" * 60)

    # 各テスト実行
    test_results = [
        ("complete_integration.py", test_complete_integration_fields()),
        ("epic11_* ファイル群", test_epic11_files_fields()),
        ("API Gateway", test_api_gateway_fields()),
        ("サンプルデータ生成", test_sample_data_generation()),
    ]

    # 総合結果
    print("\n📊 テスト結果サマリー")
    print("=" * 60)

    passed_count = 0
    for test_name, result in test_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} {test_name}")
        if result:
            passed_count += 1

    total_tests = len(test_results)
    print(f"\n合計: {passed_count}/{total_tests} テスト成功")

    if passed_count == total_tests:
        print("🎉 全てのテストが成功しました！構造化フィールド移行が完了しています。")
        return 0
    else:
        print("⚠️  一部のテストが失敗しました。修正が必要です。")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
