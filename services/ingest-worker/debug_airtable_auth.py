#!/usr/bin/env python3
"""
Airtable PAT認証デバッグスクリプト
段階的にAirtable接続問題を診断・解決
"""

import os
import requests
from pathlib import Path

def load_env_file(env_file_path):
    """Load environment variables from .env file"""
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

def debug_environment_variables():
    """環境変数の詳細確認"""
    print("🔍 Step 1: 環境変数の詳細確認")
    print("=" * 50)
    
    api_key = os.environ.get('AIRTABLE_PAT')
    base_id = os.environ.get('AIRTABLE_BASE_ID')
    
    print(f"AIRTABLE_PAT:")
    if api_key:
        print(f"  存在: はい")
        print(f"  長さ: {len(api_key)}文字")
        print(f"  先頭10文字: '{api_key[:10]}...'")
        print(f"  末尾10文字: '...{api_key[-10:]}'")
        print(f"  形式チェック: {'✅ pat...' if api_key.startswith('pat') else '❌ pat...ではない'}")
        print(f"  前後空白: '[{api_key}]'")
    else:
        print("  ❌ 環境変数が設定されていません")
    
    print(f"\nAIRTABLE_BASE_ID:")
    if base_id:
        print(f"  存在: はい")
        print(f"  値: '{base_id}'")
        print(f"  形式チェック: {'✅ app...' if base_id.startswith('app') else '❌ app...ではない'}")
    else:
        print("  ❌ 環境変数が設定されていません")
    
    return api_key, base_id

def test_curl_equivalent(api_key, base_id):
    """curl相当のテストをPythonで実行"""
    print("\n🌐 Step 2: Airtable API直接テスト")
    print("=" * 50)
    
    if not api_key or not base_id:
        print("❌ 必要な環境変数が不足しています")
        return False
    
    # テーブル名の候補
    table_candidates = [
        "Bills%20%28%E6%B3%95%E6%A1%88%29",  # URL エンコード済み
        "Bills (法案)",                       # 日本語そのまま
        "Bills",                            # シンプル版
        "tblBillsTableId"                   # もしテーブルIDがわかる場合
    ]
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    print(f"Base ID: {base_id}")
    print(f"Authorization Header: Bearer {api_key[:15]}...")
    print()
    
    for table_name in table_candidates:
        print(f"🔄 Testing table: '{table_name}'")
        url = f"https://api.airtable.com/v0/{base_id}/{table_name}?maxRecords=1"
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            
            print(f"  Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                records_count = len(data.get('records', []))
                print(f"  ✅ 成功! レコード数: {records_count}")
                print(f"  レスポンス例: {str(data)[:100]}...")
                return True
                
            elif response.status_code == 401:
                print(f"  ❌ 401 認証エラー: {response.text}")
                
            elif response.status_code == 404:
                print(f"  ❌ 404 テーブルが見つからない: {response.text}")
                
            else:
                print(f"  ❌ その他のエラー: {response.text}")
                
        except Exception as e:
            print(f"  ❌ リクエスト例外: {str(e)}")
        
        print()
    
    return False

def test_simple_base_access(api_key, base_id):
    """ベースのメタデータ取得テスト"""
    print("📋 Step 3: ベースメタデータ取得テスト")
    print("=" * 50)
    
    # Airtable Metadata APIを使用
    url = f"https://api.airtable.com/v0/meta/bases/{base_id}/tables"
    headers = {
        "Authorization": f"Bearer {api_key}",
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            tables = data.get('tables', [])
            print(f"✅ ベースアクセス成功! テーブル数: {len(tables)}")
            
            print("\n📋 利用可能なテーブル:")
            for table in tables:
                table_id = table.get('id', 'Unknown')
                table_name = table.get('name', 'Unknown')
                print(f"  - {table_name} (ID: {table_id})")
            
            return True
            
        elif response.status_code == 401:
            print(f"❌ 401 認証エラー: {response.text}")
            
        elif response.status_code == 403:
            print(f"❌ 403 権限不足: schema.bases:read が必要")
            
        else:
            print(f"❌ その他のエラー ({response.status_code}): {response.text}")
            
    except Exception as e:
        print(f"❌ リクエスト例外: {str(e)}")
    
    return False

def main():
    """メイン診断プロセス"""
    print("🏥 Airtable PAT認証診断スクリプト")
    print("=" * 50)
    
    # 環境変数読み込み
    env_file = Path(__file__).parent / ".env.local"
    if load_env_file(env_file):
        print("✅ .env.local ファイルを読み込みました")
    else:
        print("⚠️  .env.local ファイルが見つかりません")
        return 1
    
    print()
    
    # 診断実行
    api_key, base_id = debug_environment_variables()
    
    if not api_key or not base_id:
        print("\n❌ 必要な環境変数が不足しています")
        return 1
    
    # Direct API test
    api_success = test_curl_equivalent(api_key, base_id)
    
    # Meta API test
    meta_success = test_simple_base_access(api_key, base_id)
    
    print("🏁 診断結果サマリー")
    print("=" * 50)
    
    if api_success:
        print("✅ Airtable API接続: 成功")
        print("🎯 法案データの統合が可能です")
        return 0
    elif meta_success:
        print("✅ ベースアクセス: 成功")
        print("⚠️  テーブル名の調整が必要です")
        return 0
    else:
        print("❌ Airtable接続: 失敗")
        print("🔧 PAT設定の見直しが必要です")
        print("\n推奨アクション:")
        print("1. Airtable PATの権限設定確認")
        print("   - data.records:read")
        print("   - data.records:write") 
        print("   - schema.bases:read")
        print("2. ベースアクセス権の確認")
        print("3. PAT の再生成・再設定")
        return 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)