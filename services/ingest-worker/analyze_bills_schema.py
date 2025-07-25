#!/usr/bin/env python3
"""
Billsテーブル未使用カラム調査
Airtableスキーマと実データを分析
"""

import os
import sys
from collections import defaultdict
from pathlib import Path

import requests


def load_env_file(env_file_path):
    if not os.path.exists(env_file_path):
        return False

    with open(env_file_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                value = value.strip("\"'")
                os.environ[key] = value
    return True


def get_table_schema(pat, base_id):
    """テーブルスキーマ取得"""
    url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables"
    headers = {"Authorization": f"Bearer {pat}"}

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        for table in data.get("tables", []):
            if table.get("name") == "Bills (法案)":
                return table
    return None


def get_all_records(pat, base_id):
    """全レコード取得"""
    url = f"https://api.airtable.com/v0/{base_id}/Bills%20%28%E6%B3%95%E6%A1%88%29"
    headers = {"Authorization": f"Bearer {pat}"}

    all_records = []
    params = {"maxRecords": 100}

    while True:
        response = requests.get(url, headers=headers, params=params)
        if response.status_code != 200:
            break

        data = response.json()
        records = data.get("records", [])
        all_records.extend(records)

        offset = data.get("offset")
        if not offset:
            break
        params["offset"] = offset

    return all_records


def analyze_field_usage(records, fields_schema):
    """フィールド使用状況分析"""
    field_usage = defaultdict(lambda: {"populated": 0, "empty": 0, "total": 0})

    for record in records:
        record_fields = record.get("fields", {})

        for field_schema in fields_schema:
            field_name = field_schema.get("name")
            field_schema.get("type")

            field_usage[field_name]["total"] += 1

            if field_name in record_fields:
                value = record_fields[field_name]

                # 値の存在チェック
                if value is not None and value != "" and value != []:
                    field_usage[field_name]["populated"] += 1
                else:
                    field_usage[field_name]["empty"] += 1
            else:
                field_usage[field_name]["empty"] += 1

    return field_usage


def check_web_frontend_usage():
    """Web frontend での使用状況確認"""
    web_frontend_path = (
        Path(__file__).parent.parent.parent / "services" / "web-frontend"
    )

    # 使用されているフィールド名を検索
    used_fields = set()

    try:
        # TypeScript/JavaScript ファイルを検索
        for ext in ["*.ts", "*.tsx", "*.js", "*.jsx"]:
            for file_path in web_frontend_path.rglob(ext):
                try:
                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()

                        # よくあるBillsフィールド名を検索
                        potential_fields = [
                            "Bill_Number",
                            "Bill_ID",
                            "Title",
                            "Status",
                            "Category",
                            "Diet_Session",
                            "House_Of_Origin",
                            "Bill_Type",
                            "Diet_URL",
                            "PDF_URL",
                            "Summary",
                            "Notes",
                            "Name",
                            "Assignee",
                            "Attachments",
                            "Created_At",
                            "Updated_At",
                            "Speeches",
                            "Issues",
                            "Submitter_Type",
                            "Sponsoring_Ministry",
                        ]

                        for field in potential_fields:
                            if field in content:
                                used_fields.add(field)

                except Exception:
                    continue

    except Exception as e:
        print(f"⚠️ Web frontend検索エラー: {str(e)}")

    return used_fields


def main():
    print("🔍 Billsテーブル未使用カラム調査")
    print("=" * 60)

    env_file = Path(__file__).parent / ".env.local"
    load_env_file(env_file)

    pat = os.environ.get("AIRTABLE_PAT")
    base_id = os.environ.get("AIRTABLE_BASE_ID")

    if not pat or not base_id:
        print("❌ 環境変数不足")
        return 1

    # 1. スキーマ取得
    print("📋 Step 1: Billsテーブルスキーマ取得")
    table_schema = get_table_schema(pat, base_id)

    if not table_schema:
        print("❌ スキーマ取得失敗")
        return 1

    fields_schema = table_schema.get("fields", [])
    print(f"✅ {len(fields_schema)}個のフィールドを確認")

    # 2. 全レコード取得
    print("\n📄 Step 2: 全レコードデータ取得")
    all_records = get_all_records(pat, base_id)
    print(f"✅ {len(all_records)}件のレコードを取得")

    # 3. フィールド使用状況分析
    print("\n📊 Step 3: フィールド使用状況分析")
    field_usage = analyze_field_usage(all_records, fields_schema)

    # 4. Web frontend使用状況確認
    print("\n🌐 Step 4: Web frontend使用状況確認")
    frontend_used_fields = check_web_frontend_usage()
    print(f"✅ Frontend で {len(frontend_used_fields)}個のフィールドを発見")

    # 5. 結果分析
    print("\n📊 分析結果")
    print("=" * 60)

    unused_fields = []
    barely_used_fields = []
    well_used_fields = []

    for field_schema in fields_schema:
        field_name = field_schema.get("name")
        field_type = field_schema.get("type")
        usage = field_usage[field_name]

        usage_rate = (
            usage["populated"] / usage["total"] * 100 if usage["total"] > 0 else 0
        )
        frontend_used = field_name in frontend_used_fields

        status = ""
        if usage_rate == 0:
            unused_fields.append((field_name, field_type, usage_rate, frontend_used))
            status = "🔴 未使用"
        elif usage_rate < 10:
            barely_used_fields.append(
                (field_name, field_type, usage_rate, frontend_used)
            )
            status = "🟡 ほぼ未使用"
        else:
            well_used_fields.append((field_name, field_type, usage_rate, frontend_used))
            status = "🟢 使用中"

        frontend_status = "🌐" if frontend_used else "❌"

        print(
            f"{status} {field_name:25} | {field_type:15} | {usage_rate:5.1f}% | {frontend_status}"
        )

    # 6. サマリー
    print("\n📋 サマリー")
    print("=" * 60)
    print(f"🔴 完全未使用フィールド: {len(unused_fields)}個")
    print(f"🟡 ほぼ未使用フィールド: {len(barely_used_fields)}個")
    print(f"🟢 活用中フィールド: {len(well_used_fields)}個")

    if unused_fields:
        print("\n🗑️ 削除候補フィールド:")
        for name, field_type, rate, frontend in unused_fields:
            frontend_note = " (Frontend参照あり)" if frontend else ""
            print(f"  - {name} ({field_type}){frontend_note}")

    if barely_used_fields:
        print("\n⚠️ 要検討フィールド:")
        for name, field_type, rate, frontend in barely_used_fields:
            frontend_note = " (Frontend参照あり)" if frontend else ""
            print(f"  - {name} ({field_type}) - {rate:.1f}%{frontend_note}")

    print("\n🎯 推奨アクション:")
    if unused_fields:
        print(f"1. 🗑️ 完全未使用の{len(unused_fields)}フィールドの削除検討")
    if barely_used_fields:
        print(f"2. ⚠️ ほぼ未使用の{len(barely_used_fields)}フィールドの活用方法検討")
    print("3. 🔧 プロダクト機能との整合性確認")

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
