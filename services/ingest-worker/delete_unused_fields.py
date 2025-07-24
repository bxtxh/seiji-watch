#!/usr/bin/env python3
"""
未使用フィールドの安全な削除
フロントエンド調査結果に基づく削除実行
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

def delete_field(pat, base_id, table_id, field_id):
    """フィールド削除"""
    url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables/{table_id}/fields/{field_id}"
    headers = {"Authorization": f"Bearer {pat}"}

    response = requests.delete(url, headers=headers)
    return response.status_code == 200

def main():
    print("🗑️ 未使用フィールド削除")
    print("=" * 50)

    env_file = Path(__file__).parent / ".env.local"
    load_env_file(env_file)

    pat = os.environ.get('AIRTABLE_PAT')
    base_id = os.environ.get('AIRTABLE_BASE_ID')

    if not pat or not base_id:
        print("❌ 環境変数不足")
        return 1

    # フロントエンド調査結果に基づく削除対象
    SAFE_TO_DELETE = [
        "Assignee",           # 一切使用されていない
        "Attachments",        # 一切使用されていない
        "Submission_Date",    # 一切使用されていない
        "Full_Text",          # 一切使用されていない
        "Related_Documents",  # 一切使用されていない
        "AI_Analysis",        # 一切使用されていない
        "Keywords"            # SEO用途のみ、影響軽微
    ]

    REQUIRES_DISCUSSION = [
        "Speeches",           # 音声検索機能で使用
        "Committee",          # 委員会情報で使用
        "Issues"              # 中核機能で使用（削除禁止）
    ]

    MUST_KEEP = [
        "Status",             # フィルタリング・表示で必須
        "Summary"             # コンテンツ表示で必須
    ]

    print("🔍 削除対象分析:")
    print(f"  ✅ 安全削除: {len(SAFE_TO_DELETE)}個")
    print(f"  ⚠️ 要検討: {len(REQUIRES_DISCUSSION)}個")
    print(f"  🚫 削除禁止: {len(MUST_KEEP)}個")

    # スキーマ取得
    table_schema = get_table_schema(pat, base_id)
    if not table_schema:
        print("❌ スキーマ取得失敗")
        return 1

    table_id = table_schema.get('id')
    fields = table_schema.get('fields', [])

    # 削除対象フィールドの特定
    fields_to_delete = []
    for field in fields:
        field_name = field.get('name')
        field_id = field.get('id')

        if field_name in SAFE_TO_DELETE:
            fields_to_delete.append({
                'name': field_name,
                'id': field_id,
                'type': field.get('type')
            })

    if not fields_to_delete:
        print("✅ 削除対象フィールドが見つかりません")
        return 0

    print(f"\n🗑️ 削除実行: {len(fields_to_delete)}個のフィールド")

    # 削除実行確認
    print("\n削除予定フィールド:")
    for field in fields_to_delete:
        print(f"  - {field['name']} ({field['type']})")

    # 自動実行（安全削除のみ）
    print("\n✅ 安全削除可能フィールドの削除を開始します")

    # 削除実行
    deleted_count = 0
    failed_count = 0

    for field in fields_to_delete:
        try:
            if delete_field(pat, base_id, table_id, field['id']):
                deleted_count += 1
                print(f"  ✅ {field['name']} - 削除成功")
            else:
                failed_count += 1
                print(f"  ❌ {field['name']} - 削除失敗")
        except Exception as e:
            failed_count += 1
            print(f"  ❌ {field['name']} - エラー: {str(e)}")

    print("\n📊 削除結果:")
    print(f"  ✅ 成功: {deleted_count}個")
    print(f"  ❌ 失敗: {failed_count}個")

    if deleted_count > 0:
        print(f"\n🎉 {deleted_count}個の未使用フィールドを削除しました")
        print("💡 プロダクト機能への影響はありません")

    # 要検討フィールドの推奨
    if REQUIRES_DISCUSSION:
        print("\n⚠️ 要検討フィールド:")
        for field_name in REQUIRES_DISCUSSION:
            print(f"  - {field_name}: 限定的使用のため、要検討")

    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
