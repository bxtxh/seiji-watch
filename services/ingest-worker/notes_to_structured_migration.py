#!/usr/bin/env python3
"""
Notes フィールドから構造化フィールドへのデータマイグレーション
各パターンに対応した専用パーサーでデータを移行
"""

import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import requests


@dataclass
class BillData:
    """法案データ構造"""
    bill_id: str | None = None
    status: str | None = None
    category: str | None = None
    submitter: str | None = None
    url: str | None = None
    stage: str | None = None
    house: str | None = None
    bill_type: str | None = None
    date: str | None = None
    data_source: str | None = None


class NotesPatternParser:
    """Notesフィールドのパターン解析クラス"""

    def __init__(self):
        self.patterns = {
            'structured_emoji': self._parse_structured_emoji,
            'pipe_separated': self._parse_pipe_separated,
            'detailed_newline': self._parse_detailed_newline
        }

    def detect_pattern(self, notes: str) -> str:
        """Notesフィールドのパターンを検出"""
        if '【法案詳細】' in notes or '🏛️' in notes:
            return 'structured_emoji'
        elif '状態:' in notes and 'カテゴリ:' in notes and '\\n' in notes:
            return 'detailed_newline'
        elif ' | ' in notes:
            return 'pipe_separated'
        elif '\n' in notes and len(notes.split('\n')) > 3:
            return 'multiline_detailed'
        else:
            return 'unknown'

    def parse(self, notes: str) -> BillData:
        """パターンに応じてNotesを解析"""
        pattern = self.detect_pattern(notes)

        if pattern in self.patterns:
            return self.patterns[pattern](notes)
        else:
            return BillData()  # 空のデータを返す

    def _parse_structured_emoji(self, notes: str) -> BillData:
        """構造化絵文字パターンの解析"""
        data = BillData()

        # 法案ID (🏛️ 法案ID: 217-58)
        bill_id_match = re.search(r'🏛️ 法案ID[:\s]*([^\n]+)', notes)
        if bill_id_match:
            data.bill_id = bill_id_match.group(1).strip()

        # ステータス (📋 ステータス: 議案要旨)
        status_match = re.search(r'📋 ステータス[:\s]*([^\n]+)', notes)
        if status_match:
            status_value = status_match.group(1).strip()
            # 絵文字や段階情報が混入している場合はクリーンアップ
            if '🔄 段階:' in status_value:
                status_value = status_value.split('🔄 段階:')[0].strip()
            # 引用符をクリーンアップ
            status_value = status_value.strip('"\'')
            data.status = status_value

        # 段階 (🔄 段階: Backlog)
        stage_match = re.search(r'🔄 段階[:\s]*([^\n]+)', notes)
        if stage_match:
            data.stage = stage_match.group(1).strip()

        # 提出者 (👤 提出者: 議員)
        submitter_match = re.search(r'👤 提出者[:\s]*([^\n]+)', notes)
        if submitter_match:
            data.submitter = submitter_match.group(1).strip()

        # カテゴリ (🏷️ カテゴリ: その他)
        category_match = re.search(r'🏷️ カテゴリ[:\s]*([^\n]+)', notes)
        if category_match:
            data.category = category_match.group(1).strip()

        # URL (🔗 URL: https://...)
        url_match = re.search(r'🔗 URL[:\s]*([^\n]+)', notes)
        if url_match:
            data.url = url_match.group(1).strip()

        # 収集日時 (📅 収集日時: 2025-07-09T03:22:37.753052)
        date_match = re.search(r'📅 収集日時[:\s]*([^\n]+)', notes)
        if date_match:
            data.date = date_match.group(1).strip()

        # データソース
        if 'データソース: 参議院公式サイト' in notes:
            data.data_source = '参議院公式サイト'

        return data

    def _parse_pipe_separated(self, notes: str) -> BillData:
        """パイプ区切りパターンの解析"""
        data = BillData()

        # " | " で分割
        parts = notes.split(' | ')

        for part in parts:
            part = part.strip()

            if '状態:' in part:
                data.status = part.replace('状態:', '').strip().strip('"\'')
            elif 'カテゴリ:' in part:
                data.category = part.replace('カテゴリ:', '').strip().strip('"\'')
            elif '提出者:' in part:
                data.submitter = part.replace('提出者:', '').strip().strip('"\'')
            elif part.startswith('http'):
                data.url = part.strip()

        return data

    def _parse_detailed_newline(self, notes: str) -> BillData:
        """詳細改行パターンの解析"""
        data = BillData()

        # \\n を実際の改行に変換
        notes = notes.replace('\\n', '\n')
        lines = notes.split('\n')

        for line in lines:
            line = line.strip()

            if line.startswith('状態:'):
                data.status = line.replace('状態:', '').strip().strip('"\'')
            elif line.startswith('カテゴリ:'):
                data.category = line.replace('カテゴリ:', '').strip().strip('"\'')
            elif line.startswith('提出者:'):
                data.submitter = line.replace('提出者:', '').strip().strip('"\'')
            elif line.startswith('URL:'):
                data.url = line.replace('URL:', '').strip()
            elif line.startswith('http'):
                data.url = line.strip()

        return data


class AirtableMigrator:
    """Airtableデータマイグレーションクラス"""

    def __init__(self, pat: str, base_id: str):
        self.pat = pat
        self.base_id = base_id
        self.base_url = f"https://api.airtable.com/v0/{base_id}"
        self.headers = {
            "Authorization": f"Bearer {pat}",
            "Content-Type": "application/json"}
        self.parser = NotesPatternParser()
        self.rate_limit_delay = 0.3  # 300ms between requests

    def _rate_limit(self):
        """レート制限対応"""
        time.sleep(self.rate_limit_delay)

    def get_all_bills(self) -> list[dict]:
        """全ての法案レコードを取得"""
        url = f"{self.base_url}/Bills%20%28%E6%B3%95%E6%A1%88%29"
        all_records = []
        params = {"maxRecords": 100}

        while True:
            self._rate_limit()
            response = requests.get(url, headers=self.headers, params=params)

            if response.status_code != 200:
                print(f"❌ API エラー: {response.status_code}")
                break

            data = response.json()
            records = data.get('records', [])
            all_records.extend(records)

            offset = data.get('offset')
            if not offset:
                break
            params['offset'] = offset

        return all_records

    def analyze_migration_scope(self, records: list[dict]) -> dict:
        """マイグレーション範囲の分析"""
        analysis = {
            'total_records': len(records),
            'notes_records': 0,
            'patterns': {
                'structured_emoji': 0,
                'pipe_separated': 0,
                'detailed_newline': 0,
                'other': 0},
            'extractable_fields': {
                'bill_id': 0,
                'status': 0,
                'category': 0,
                'submitter': 0,
                'url': 0},
            'records_to_migrate': []}

        for record in records:
            fields = record.get('fields', {})
            notes = fields.get('Notes', '')

            if notes:
                analysis['notes_records'] += 1
                pattern = self.parser.detect_pattern(notes)

                if pattern in analysis['patterns']:
                    analysis['patterns'][pattern] += 1
                else:
                    analysis['patterns']['other'] += 1

                # パース結果をチェック
                parsed_data = self.parser.parse(notes)

                if parsed_data.bill_id:
                    analysis['extractable_fields']['bill_id'] += 1
                if parsed_data.status:
                    analysis['extractable_fields']['status'] += 1
                if parsed_data.category:
                    analysis['extractable_fields']['category'] += 1
                if parsed_data.submitter:
                    analysis['extractable_fields']['submitter'] += 1
                if parsed_data.url:
                    analysis['extractable_fields']['url'] += 1

                analysis['records_to_migrate'].append({
                    'record_id': record['id'],
                    'name': fields.get('Name', 'N/A'),
                    'pattern': pattern,
                    'parsed_data': parsed_data
                })

        return analysis

    def update_record(
            self,
            record_id: str,
            fields_to_update: dict,
            dry_run: bool = True) -> bool:
        """レコードを更新（ドライラン対応）"""
        if dry_run:
            print(f"  [DRY RUN] レコード {record_id} を更新予定: {fields_to_update}")
            return True

        url = f"{self.base_url}/Bills%20%28%E6%B3%95%E6%A1%88%29/{record_id}"
        data = {"fields": fields_to_update}

        self._rate_limit()
        response = requests.patch(url, headers=self.headers, json=data)

        if response.status_code == 200:
            return True
        else:
            print(f"❌ レコード更新失敗 {record_id}: {response.status_code}")
            print(f"   エラー詳細: {response.text}")
            return False

    def migrate_record(self, record_info: dict, dry_run: bool = True) -> bool:
        """個別レコードのマイグレーション（権限エラー対応）"""
        parsed_data = record_info['parsed_data']
        fields_to_update = {}

        # マッピング設定（権限問題が起きやすいフィールドを除外）
        safe_field_mapping = {
            'category': 'Category',
            'submitter': 'Submitter',
            'url': 'Bill_URL',
            'stage': 'Stage',
            'house': 'House',
            'bill_type': 'Bill_Type'
        }

        # 更新するフィールドを準備（安全なフィールドのみ）
        for field_name, airtable_field in safe_field_mapping.items():
            value = getattr(parsed_data, field_name)
            if value and value != 'N/A':
                fields_to_update[airtable_field] = value

        # bill_idは特別処理（Bill_NumberまたはBill_IDフィールドに）
        if parsed_data.bill_id and parsed_data.bill_id != 'N/A':
            fields_to_update['Bill_Number'] = parsed_data.bill_id

        # data_sourceがある場合
        if parsed_data.data_source:
            fields_to_update['Data_Source'] = parsed_data.data_source

        # Bill_Statusは権限エラーが起きやすいため、別途処理
        # まず安全なフィールドで更新を試み、その後必要に応じてBill_Statusを追加
        if fields_to_update:
            return self.update_record(
                record_info['record_id'], fields_to_update, dry_run)

        return True

    def execute_migration(self, dry_run: bool = True) -> dict:
        """マイグレーション実行"""
        print("🚀 Notes → 構造化フィールド マイグレーション開始")
        print("=" * 60)

        # 1. データ取得
        print("📄 Step 1: データ取得")
        records = self.get_all_bills()
        print(f"✅ {len(records)}件のレコードを取得")

        # 2. 分析
        print("\n🔍 Step 2: マイグレーション範囲分析")
        analysis = self.analyze_migration_scope(records)

        print(f"  総レコード数: {analysis['total_records']}件")
        print(f"  Notesありレコード: {analysis['notes_records']}件")
        print("  パターン分布:")
        for pattern, count in analysis['patterns'].items():
            print(f"    {pattern}: {count}件")
        print("  抽出可能フィールド:")
        for field, count in analysis['extractable_fields'].items():
            print(f"    {field}: {count}件")

        # 3. マイグレーション実行
        mode = "ドライラン" if dry_run else "本実行"
        print(f"\n⚡ Step 3: マイグレーション{mode}")

        success_count = 0
        error_count = 0

        for record_info in analysis['records_to_migrate']:
            pattern = record_info['pattern']
            name = record_info['name'][:50]

            print(f"  処理中: {name}... ({pattern})")

            if self.migrate_record(record_info, dry_run):
                success_count += 1
            else:
                error_count += 1

        # 4. 結果サマリー
        print("\n📊 マイグレーション結果")
        print(f"  成功: {success_count}件")
        print(f"  失敗: {error_count}件")

        if dry_run:
            print("\n⚠️  これはドライランです。実際のデータは変更されていません。")
            print("    実行するには --execute フラグを使用してください。")

        return {
            'success_count': success_count,
            'error_count': error_count,
            'analysis': analysis
        }


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


def main():
    import argparse

    parser = argparse.ArgumentParser(description='Notes フィールドから構造化フィールドへのマイグレーション')
    parser.add_argument(
        '--execute',
        action='store_true',
        help='実際にマイグレーションを実行（デフォルトはドライラン）')
    parser.add_argument(
        '--pattern',
        choices=[
            'structured_emoji',
            'pipe_separated',
            'detailed_newline',
            'all'],
        default='all',
        help='処理するパターンを指定')

    args = parser.parse_args()

    # 環境変数読み込み
    env_file = Path(__file__).parent / ".env.local"
    load_env_file(env_file)

    pat = os.environ.get('AIRTABLE_PAT')
    base_id = os.environ.get('AIRTABLE_BASE_ID')

    if not pat or not base_id:
        print("❌ 環境変数不足: AIRTABLE_PAT, AIRTABLE_BASE_ID が必要です")
        return 1

    # マイグレーション実行
    migrator = AirtableMigrator(pat, base_id)

    try:
        result = migrator.execute_migration(dry_run=not args.execute)
        return 0 if result['error_count'] == 0 else 1

    except Exception as e:
        print(f"❌ マイグレーション実行エラー: {str(e)}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
