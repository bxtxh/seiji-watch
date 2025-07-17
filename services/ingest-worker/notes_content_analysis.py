#!/usr/bin/env python3
"""
Notesフィールド内容詳細分析
どのような形式のデータが格納されているかを詳しく調べる
"""

import os
import sys
import requests
import json
import re
from pathlib import Path
from collections import defaultdict, Counter
from datetime import datetime

def load_env_file(env_file_path):
    if not os.path.exists(env_file_path):
        return False
    
    with open(env_file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                value = value.strip('"\'')
                os.environ[key] = value
    return True

def get_all_bills_with_notes(pat, base_id):
    """Notesフィールドを含む全ての法案データを取得"""
    url = f"https://api.airtable.com/v0/{base_id}/Bills%20%28%E6%B3%95%E6%A1%88%29"
    headers = {"Authorization": f"Bearer {pat}"}
    
    all_records = []
    params = {"maxRecords": 100, "fields": ["Name", "Notes", "Bill_ID", "Data_Source", "Collection_Date"]}
    
    while True:
        response = requests.get(url, headers=headers, params=params)
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

def analyze_notes_patterns(records):
    """Notesフィールドのパターンを分析"""
    print("🔍 Notes フィールドパターン分析")
    print("=" * 60)
    
    notes_data = []
    pattern_types = defaultdict(list)
    
    for record in records:
        fields = record.get('fields', {})
        notes = fields.get('Notes', '')
        name = fields.get('Name', 'N/A')
        bill_id = fields.get('Bill_ID', 'N/A')
        data_source = fields.get('Data_Source', 'N/A')
        
        if notes:
            notes_data.append({
                'record_id': record['id'],
                'name': name,
                'bill_id': bill_id, 
                'data_source': data_source,
                'notes': notes,
                'notes_length': len(notes)
            })
    
    print(f"📊 Notes データありレコード: {len(notes_data)}件")
    
    # パターン分析
    for item in notes_data:
        notes = item['notes']
        
        # パターン分類
        if '【法案詳細】' in notes or '🏛️' in notes:
            pattern_types['structured_emoji'].append(item)
        elif '状態:' in notes and 'カテゴリ:' in notes and '\\n' in notes:
            pattern_types['detailed_newline'].append(item)
        elif ' | ' in notes:
            pattern_types['pipe_separated'].append(item)
        elif '\n' in notes and len(notes.split('\n')) > 3:
            pattern_types['multiline_detailed'].append(item)
        elif ':' in notes:
            pattern_types['colon_format'].append(item)
        else:
            pattern_types['other'].append(item)
    
    # パターン統計
    print("\n📈 パターン分類結果:")
    for pattern, items in pattern_types.items():
        print(f"  {pattern}: {len(items)}件")
    
    # 各パターンの代表例を表示
    print("\n🔬 各パターンの詳細分析:")
    for pattern, items in pattern_types.items():
        if items:
            print(f"\n--- {pattern.upper()} パターン ---")
            print(f"件数: {len(items)}件")
            
            # 代表例表示（最初の3件）
            for i, item in enumerate(items[:3]):
                print(f"\n例{i+1}: {item['name'][:50]}...")
                print(f"Notes内容: {item['notes'][:200]}...")
                if len(item['notes']) > 200:
                    print("  [省略...]")
    
    return pattern_types

def analyze_extractable_data(notes_data):
    """Notesから抽出可能な構造化データを分析"""
    print("\n🔧 構造化データ抽出可能性分析")
    print("=" * 60)
    
    extractable_fields = {
        'bill_id': 0,
        'status': 0, 
        'category': 0,
        'submitter': 0,
        'url': 0,
        'stage': 0,
        'house': 0,
        'bill_type': 0,
        'date': 0
    }
    
    for item in notes_data:
        notes = item['notes'].lower()
        
        # パターンマッチング
        if '法案id:' in notes or 'bill id:' in notes or '🏛️' in notes:
            extractable_fields['bill_id'] += 1
        if '状態:' in notes or 'ステータス:' in notes or '📋' in notes:
            extractable_fields['status'] += 1
        if 'カテゴリ:' in notes or 'category:' in notes:
            extractable_fields['category'] += 1
        if '提出者:' in notes or 'submitter:' in notes:
            extractable_fields['submitter'] += 1
        if 'url:' in notes or 'http' in notes:
            extractable_fields['url'] += 1
        if 'ステージ:' in notes or 'stage:' in notes:
            extractable_fields['stage'] += 1
        if '院:' in notes or 'house:' in notes:
            extractable_fields['house'] += 1
        if 'type:' in notes or 'タイプ:' in notes:
            extractable_fields['bill_type'] += 1
        if 'date:' in notes or '日付:' in notes or 'collected:' in notes:
            extractable_fields['date'] += 1
    
    print("抽出可能フィールド分析:")
    total_records = len(notes_data)
    for field, count in extractable_fields.items():
        percentage = (count / total_records * 100) if total_records > 0 else 0
        print(f"  {field}: {count}件 ({percentage:.1f}%)")
    
    return extractable_fields

def suggest_migration_strategy(pattern_types, extractable_fields):
    """マイグレーション戦略を提案"""
    print("\n🎯 マイグレーション戦略提案")
    print("=" * 60)
    
    total_notes = sum(len(items) for items in pattern_types.values())
    
    print("1. パターン別処理方針:")
    for pattern, items in pattern_types.items():
        count = len(items)
        percentage = (count / total_notes * 100) if total_notes > 0 else 0
        
        if pattern == 'structured_emoji':
            print(f"  📋 {pattern}: {count}件 ({percentage:.1f}%) → 構造化データ解析で完全移行可能")
        elif pattern == 'detailed_newline':
            print(f"  📝 {pattern}: {count}件 ({percentage:.1f}%) → 正規表現で部分移行可能")
        elif pattern == 'pipe_separated':
            print(f"  ⚡ {pattern}: {count}件 ({percentage:.1f}%) → パイプ分割で簡単移行")
        elif pattern == 'multiline_detailed':
            print(f"  📄 {pattern}: {count}件 ({percentage:.1f}%) → 行単位解析で移行可能")
        else:
            print(f"  ❓ {pattern}: {count}件 ({percentage:.1f}%) → 手動確認必要")
    
    print("\n2. 移行優先度:")
    if 'structured_emoji' in pattern_types:
        print("  🥇 高優先度: structured_emoji パターン（完全自動化可能）")
    if 'pipe_separated' in pattern_types:
        print("  🥈 中優先度: pipe_separated パターン（簡単な解析）")
    if 'detailed_newline' in pattern_types:
        print("  🥉 中優先度: detailed_newline パターン（正規表現解析）")
    
    print("\n3. 推奨アプローチ:")
    print("  ✅ Notes フィールドを段階的に構造化フィールドに移行")
    print("  ✅ パターン別の専用パーサーを作成")
    print("  ✅ 移行後は新しいデータ生成パイプラインで構造化フィールドに直接書き込み")
    print("  ⚠️  移行完了後にNotes フィールド削除")

def main():
    print("🔍 Notes フィールド内容詳細分析")
    print("=" * 60)
    
    env_file = Path(__file__).parent / ".env.local"
    load_env_file(env_file)
    
    pat = os.environ.get('AIRTABLE_PAT')
    base_id = os.environ.get('AIRTABLE_BASE_ID')
    
    if not pat or not base_id:
        print("❌ 環境変数不足")
        return 1
    
    # 1. Notes データ取得
    print("📄 Step 1: Notes フィールドデータ取得")
    all_records = get_all_bills_with_notes(pat, base_id)
    print(f"✅ {len(all_records)}件のレコードを取得")
    
    # 2. パターン分析
    pattern_types = analyze_notes_patterns(all_records)
    
    # 3. 抽出可能データ分析
    notes_data = [
        {
            'notes': record.get('fields', {}).get('Notes', ''),
            'name': record.get('fields', {}).get('Name', ''),
        } 
        for record in all_records 
        if record.get('fields', {}).get('Notes')
    ]
    extractable_fields = analyze_extractable_data(notes_data)
    
    # 4. マイグレーション戦略
    suggest_migration_strategy(pattern_types, extractable_fields)
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)