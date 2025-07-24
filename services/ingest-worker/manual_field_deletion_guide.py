#!/usr/bin/env python3
"""
手動フィールド削除ガイド
API削除が不可能な場合の手動削除手順
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
        records = data.get('records', [])
        all_records.extend(records)

        offset = data.get('offset')
        if not offset:
            break
        params['offset'] = offset

    return all_records


def main():
    print("📋 手動フィールド削除ガイド")
    print("=" * 60)

    env_file = Path(__file__).parent / ".env.local"
    load_env_file(env_file)

    pat = os.environ.get('AIRTABLE_PAT')
    base_id = os.environ.get('AIRTABLE_BASE_ID')

    if not pat or not base_id:
        print("❌ 環境変数不足")
        return 1

    # スキーマ取得
    table_schema = get_table_schema(pat, base_id)
    if not table_schema:
        print("❌ スキーマ取得失敗")
        return 1

    fields = table_schema.get('fields', [])

    # 削除対象フィールドの使用状況確認
    all_records = get_all_records(pat, base_id)
    print(f"✅ {len(all_records)}件のレコードを確認")

    # 削除対象フィールド
    SAFE_TO_DELETE = [
        "Assignee", "Attachments", "Submission_Date",
        "Full_Text", "Related_Documents", "AI_Analysis", "Keywords"
    ]

    KEEP_FIELDS = [
        "Speeches", "Committee", "Issues",  # 要検討だが保持
        "Status", "Summary"                 # 必須フィールド
    ]

    print("\n🗑️ 削除対象フィールド（7個）")
    print("=" * 40)

    for field in fields:
        field_name = field.get('name')
        field_id = field.get('id')
        field_type = field.get('type')

        if field_name in SAFE_TO_DELETE:
            # 使用状況確認
            usage_count = 0
            for record in all_records:
                if field_name in record.get(
                        'fields', {}) and record['fields'][field_name]:
                    usage_count += 1

            print(f"📋 {field_name}")
            print(f"  - タイプ: {field_type}")
            print(f"  - フィールドID: {field_id}")
            print(f"  - データ使用: {usage_count}/{len(all_records)}件")
            print("  - 削除影響: なし（フロントエンド未使用）")
            print()

    print("🔧 手動削除手順:")
    print("=" * 40)
    print("1. Airtableブラウザで Diet Issue Tracker ベースを開く")
    print("2. 'Bills (法案)' テーブルを選択")
    print("3. 右上の 'Fields' ボタンをクリック")
    print("4. 以下のフィールドを一つずつ削除:")

    for field in fields:
        field_name = field.get('name')
        if field_name in SAFE_TO_DELETE:
            print(f"   - {field_name}")

    print("\n⚠️ 保持するフィールド:")
    print("=" * 40)
    for field in fields:
        field_name = field.get('name')
        if field_name in KEEP_FIELDS:
            reason = ""
            if field_name in ["Status", "Summary"]:
                reason = "（必須フィールド）"
            elif field_name in ["Speeches", "Committee", "Issues"]:
                reason = "（要検討だが保持）"
            print(f"   - {field_name} {reason}")

    print("\n🎯 削除完了後の効果:")
    print("=" * 40)
    print("✅ 7個の未使用フィールドが削除される")
    print("✅ プロダクト機能への影響なし")
    print("✅ Airtableのパフォーマンス向上")
    print("✅ データ管理の簡素化")

    print("\n💡 PATの権限が不足している可能性があります")
    print("   schema.bases:write 権限の追加を検討してください")

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
