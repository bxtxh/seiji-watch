#!/usr/bin/env python3
"""
フィールド削除エラーの詳細調査
"""

import os
import sys
from pathlib import Path

import requests


def load_env_file(env_file_path):
    if not os.path.exists(env_file_path):
        return False

    with open(env_file_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                value = value.strip('"\'')
                os.environ[key] = value
    return True


def get_table_schema(pat, base_id):
    """テーブルスキーマ取得"""
    url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables"
    headers = {"Authorization": f"Bearer {pat}"}

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        for table in data.get('tables', []):
            if table.get('name') == "Bills (法案)":
                return table
    return None


def debug_field_deletion(pat, base_id, table_id, field_id, field_name):
    """フィールド削除のデバッグ"""
    url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables/{table_id}/fields/{field_id}"
    headers = {"Authorization": f"Bearer {pat}"}

    print(f"\n🔍 {field_name} 削除試行")
    print(f"  URL: {url}")

    response = requests.delete(url, headers=headers)

    print(f"  Status: {response.status_code}")
    print(f"  Response: {response.text}")

    return response.status_code == 200


def main():
    print("🔍 フィールド削除エラー調査")
    print("=" * 50)

    env_file = Path(__file__).parent / ".env.local"
    load_env_file(env_file)

    pat = os.environ.get('AIRTABLE_PAT')
    base_id = os.environ.get('AIRTABLE_BASE_ID')

    if not pat or not base_id:
        print("❌ 環境変数不足")
        return 1

    # PAT権限確認
    print("📋 PAT権限確認")
    print(f"  Base ID: {base_id}")
    print(f"  PAT: {pat[:15]}...")

    # スキーマ取得
    table_schema = get_table_schema(pat, base_id)
    if not table_schema:
        print("❌ スキーマ取得失敗")
        return 1

    table_id = table_schema.get('id')
    fields = table_schema.get('fields', [])

    print(f"✅ テーブルID: {table_id}")
    print(f"✅ フィールド数: {len(fields)}")

    # 削除対象フィールドの詳細調査
    SAFE_TO_DELETE = ["Assignee", "Attachments", "Submission_Date",
                      "Full_Text", "Related_Documents", "AI_Analysis", "Keywords"]

    for field in fields:
        field_name = field.get('name')
        field_id = field.get('id')
        field_type = field.get('type')

        if field_name in SAFE_TO_DELETE:
            print(f"\n📋 {field_name} ({field_type})")
            print(f"  Field ID: {field_id}")

            # 削除テスト
            result = debug_field_deletion(pat, base_id, table_id, field_id, field_name)
            if result:
                print("  ✅ 削除成功")
            else:
                print("  ❌ 削除失敗")

    # 権限確認
    print("\n🔧 権限確認:")
    print("  schema.bases:write 権限が必要です")
    print("  現在のPAT権限を確認してください")

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
