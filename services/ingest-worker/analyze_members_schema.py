#!/usr/bin/env python3
"""
議員テーブル使用フィールド調査
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
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                value = value.strip('"\'')
                os.environ[key] = value
    return True

def get_table_schema(pat, base_id, table_name):
    """テーブルスキーマ取得"""
    url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables"
    headers = {"Authorization": f"Bearer {pat}"}

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        for table in data.get('tables', []):
            if table.get('name') == table_name:
                return table
    return None

def get_all_records(pat, base_id, table_name):
    """全レコード取得"""
    url = f"https://api.airtable.com/v0/{base_id}/{table_name}"
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

def analyze_field_usage(records, fields_schema):
    """フィールド使用状況分析"""
    field_usage = defaultdict(lambda: {"populated": 0, "empty": 0, "total": 0})

    for record in records:
        record_fields = record.get('fields', {})

        for field_schema in fields_schema:
            field_name = field_schema.get('name')
            field_schema.get('type')

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
    web_frontend_path = Path(__file__).parent.parent.parent / "services" / "web-frontend"

    used_fields = set()

    try:
        for ext in ["*.ts", "*.tsx", "*.js", "*.jsx"]:
            for file_path in web_frontend_path.rglob(ext):
                try:
                    with open(file_path, encoding='utf-8') as f:
                        content = f.read()

                        # 議員関連フィールド名を検索
                        potential_fields = [
                            "Name", "Name_Kana", "Name_EN", "House", "Constituency",
                            "Diet_Member_ID", "Birth_Date", "Gender", "First_Elected",
                            "Terms_Served", "Previous_Occupations", "Education",
                            "Website_URL", "Twitter_Handle", "Facebook_URL",
                            "Is_Active", "Status", "Party", "Created_At", "Updated_At",
                            "Profile_Image", "Bio", "Position", "Committee_Memberships",
                            "Voting_Record", "Speech_Count", "Bill_Sponsorship"
                        ]

                        for field in potential_fields:
                            if field in content:
                                used_fields.add(field)

                except Exception:
                    continue

    except Exception as e:
        print(f"⚠️ Web frontend検索エラー: {str(e)}")

    return used_fields

def check_database_model_usage():
    """データベースモデルでの定義確認"""
    models_path = Path(__file__).parent.parent.parent / "shared" / "src" / "shared" / "models"

    defined_fields = set()

    try:
        member_model_path = models_path / "member.py"
        if member_model_path.exists():
            with open(member_model_path, encoding='utf-8') as f:
                content = f.read()

                # SQLAlchemyカラム定義を検索
                import re
                column_pattern = r'(\w+)\s*=\s*Column'
                matches = re.findall(column_pattern, content)
                defined_fields.update(matches)

    except Exception as e:
        print(f"⚠️ データベースモデル検索エラー: {str(e)}")

    return defined_fields

def main():
    print("🔍 議員テーブル使用フィールド調査")
    print("=" * 70)

    env_file = Path(__file__).parent / ".env.local"
    load_env_file(env_file)

    pat = os.environ.get('AIRTABLE_PAT')
    base_id = os.environ.get('AIRTABLE_BASE_ID')

    if not pat or not base_id:
        print("❌ 環境変数不足")
        return 1

    table_name = "Members (議員)"

    # 1. スキーマ取得
    print("📋 Step 1: 議員テーブルスキーマ取得")
    table_schema = get_table_schema(pat, base_id, table_name)

    if not table_schema:
        print("❌ スキーマ取得失敗")
        return 1

    fields_schema = table_schema.get('fields', [])
    print(f"✅ {len(fields_schema)}個のフィールドを確認")

    # 2. 全レコード取得
    print("\n📄 Step 2: 全レコードデータ取得")
    all_records = get_all_records(pat, base_id, table_name)
    print(f"✅ {len(all_records)}件のレコードを取得")

    # 3. フィールド使用状況分析
    print("\n📊 Step 3: フィールド使用状況分析")
    field_usage = analyze_field_usage(all_records, fields_schema)

    # 4. Web frontend使用状況確認
    print("\n🌐 Step 4: Web frontend使用状況確認")
    frontend_used_fields = check_web_frontend_usage()
    print(f"✅ Frontend で {len(frontend_used_fields)}個のフィールドを発見")

    # 5. データベースモデル確認
    print("\n🗄️ Step 5: データベースモデル確認")
    db_defined_fields = check_database_model_usage()
    print(f"✅ データベースモデルで {len(db_defined_fields)}個のフィールドを発見")

    # 6. 結果分析
    print("\n📊 詳細分析結果")
    print("=" * 70)

    unused_fields = []
    barely_used_fields = []
    well_used_fields = []

    for field_schema in fields_schema:
        field_name = field_schema.get('name')
        field_type = field_schema.get('type')
        usage = field_usage[field_name]

        usage_rate = usage["populated"] / usage["total"] * 100 if usage["total"] > 0 else 0
        frontend_used = field_name in frontend_used_fields
        db_defined = field_name.lower() in {f.lower() for f in db_defined_fields}

        status = ""
        if usage_rate == 0:
            unused_fields.append((field_name, field_type, usage_rate, frontend_used, db_defined))
            status = "🔴 未使用"
        elif usage_rate < 10:
            barely_used_fields.append((field_name, field_type, usage_rate, frontend_used, db_defined))
            status = "🟡 ほぼ未使用"
        else:
            well_used_fields.append((field_name, field_type, usage_rate, frontend_used, db_defined))
            status = "🟢 使用中"

        frontend_status = "🌐" if frontend_used else "❌"
        db_status = "🗄️" if db_defined else "❌"

        print(f"{status} {field_name:25} | {field_type:15} | {usage_rate:5.1f}% | {frontend_status} | {db_status}")

    # 7. サマリー
    print("\n📋 サマリー")
    print("=" * 70)
    print(f"🔴 完全未使用フィールド: {len(unused_fields)}個")
    print(f"🟡 ほぼ未使用フィールド: {len(barely_used_fields)}個")
    print(f"🟢 活用中フィールド: {len(well_used_fields)}個")

    if unused_fields:
        print("\n🗑️ 削除候補フィールド:")
        for name, field_type, rate, frontend, db in unused_fields:
            notes = []
            if frontend:
                notes.append("Frontend参照あり")
            if db:
                notes.append("DB定義あり")
            note_str = f" ({', '.join(notes)})" if notes else ""
            print(f"  - {name} ({field_type}){note_str}")

    if barely_used_fields:
        print("\n⚠️ 要検討フィールド:")
        for name, field_type, rate, frontend, db in barely_used_fields:
            notes = []
            if frontend:
                notes.append("Frontend参照あり")
            if db:
                notes.append("DB定義あり")
            note_str = f" ({', '.join(notes)})" if notes else ""
            print(f"  - {name} ({field_type}) - {rate:.1f}%{note_str}")

    print("\n🎯 推奨アクション:")
    print("1. 🗑️ 完全未使用フィールドの削除検討")
    print("2. ⚠️ ほぼ未使用フィールドの活用方法検討")
    print("3. 🔧 データベースモデルとの整合性確認")
    print("4. 🌐 フロントエンド機能との連携強化")

    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
