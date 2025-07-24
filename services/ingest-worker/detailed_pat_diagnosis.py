#!/usr/bin/env python3
"""
PATの詳細診断スクリプト
余分なスペース、改行文字、Base IDの問題を特定
"""

import os
from pathlib import Path

import requests


def load_env_file(env_file_path):
    """Load environment variables from .env file"""
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


def detailed_pat_analysis():
    """PATの詳細分析"""
    print("🔬 PAT詳細分析")
    print("=" * 50)

    pat = os.environ.get('AIRTABLE_PAT')
    base_id = os.environ.get('AIRTABLE_BASE_ID')

    if not pat:
        print("❌ AIRTABLE_PAT環境変数なし")
        return None, None

    if not base_id:
        print("❌ AIRTABLE_BASE_ID環境変数なし")
        return None, None

    print("📝 PAT詳細:")
    print(f"  生の長さ: {len(pat)}文字")
    print(f"  先頭文字: '{pat[0]}' (ASCII: {ord(pat[0])})")
    print(f"  末尾文字: '{pat[-1]}' (ASCII: {ord(pat[-1])})")
    print(f"  前後3文字: '[{pat[:3]}...{pat[-3:]}]'")

    # バイト表現で隠れた文字を確認
    pat_bytes = pat.encode('utf-8')
    print(f"  バイト長: {len(pat_bytes)} bytes")
    print(f"  先頭5バイト: {pat_bytes[:5]}")
    print(f"  末尾5バイト: {pat_bytes[-5:]}")

    # 空白文字チェック
    leading_spaces = len(pat) - len(pat.lstrip())
    trailing_spaces = len(pat) - len(pat.rstrip())
    print(f"  先頭空白: {leading_spaces}文字")
    print(f"  末尾空白: {trailing_spaces}文字")

    # 改行文字チェック
    has_newlines = '\n' in pat or '\r' in pat
    print(f"  改行文字含有: {has_newlines}")

    if has_newlines:
        newline_positions = [i for i, c in enumerate(pat) if c == '\n']
        carriage_positions = [i for i, c in enumerate(pat) if c == '\r']
        print(f"  \\n位置: {newline_positions}")
        print(f"  \\r位置: {carriage_positions}")

    print("\n📝 Base ID詳細:")
    print(f"  長さ: {len(base_id)}文字")
    print(f"  値: '{base_id}'")
    print(f"  app形式: {base_id.startswith('app')}")

    # クリーンなPATを生成
    clean_pat = pat.strip()
    clean_base_id = base_id.strip()

    print("\n🧹 クリーン後:")
    print(f"  PAT長さ変化: {len(pat)} → {len(clean_pat)}")
    print(f"  Base ID長さ変化: {len(base_id)} → {len(clean_base_id)}")

    return clean_pat, clean_base_id


def test_clean_authentication(clean_pat, clean_base_id):
    """クリーンなPATでテスト"""
    print("\n🧪 クリーンPAT認証テスト")
    print("=" * 50)

    if not clean_pat or not clean_base_id:
        print("❌ クリーンなPATまたはBase IDが取得できません")
        return False

    # Airtableメタデータエンドポイントでテスト（テーブル名不要）
    url = f"https://api.airtable.com/v0/meta/bases/{clean_base_id}/tables"

    headers = {
        "Authorization": f"Bearer {clean_pat}",
        "Content-Type": "application/json"
    }

    print("🌐 リクエスト詳細:")
    print(f"  URL: {url}")
    print(f"  Authorization: Bearer {clean_pat[:15]}...{clean_pat[-10:]}")
    print("  Content-Type: application/json")

    try:
        response = requests.get(url, headers=headers, timeout=10)

        print("\n📡 レスポンス詳細:")
        print(f"  Status Code: {response.status_code}")
        print(f"  Headers: {dict(response.headers)}")

        if response.status_code == 200:
            data = response.json()
            tables = data.get('tables', [])
            print("  ✅ 認証成功!")
            print(f"  テーブル数: {len(tables)}")

            print("\n📋 利用可能テーブル:")
            for table in tables:
                table_id = table.get('id', 'Unknown')
                table_name = table.get('name', 'Unknown')
                print(f"    - {table_name} (ID: {table_id})")

            return True

        elif response.status_code == 401:
            print("  ❌ 401認証エラー")
            print(f"  エラー詳細: {response.text}")

        elif response.status_code == 404:
            print("  ❌ 404 Base ID不正の可能性")
            print(f"  エラー詳細: {response.text}")

        else:
            print(f"  ❌ その他エラー: {response.status_code}")
            print(f"  エラー詳細: {response.text}")

    except Exception as e:
        print(f"  ❌ リクエスト例外: {str(e)}")

    return False


def test_direct_curl_equivalent(clean_pat, clean_base_id):
    """curl相当の最小テスト"""
    print("\n🔧 最小curl相当テスト")
    print("=" * 50)

    # 最もシンプルなエンドポイント
    url = f"https://api.airtable.com/v0/{clean_base_id}/Bills?maxRecords=1"

    headers = {"Authorization": f"Bearer {clean_pat}"}

    print(f"curl -H 'Authorization: Bearer {clean_pat[:15]}...' \\")
    print(f"     '{url}'")
    print()

    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            print("✅ 基本認証 SUCCESS!")
            return True
        else:
            print(f"❌ レスポンス: {response.text}")

    except Exception as e:
        print(f"❌ エラー: {str(e)}")

    return False


def main():
    """メイン診断プロセス"""
    print("🔬 Airtable PAT詳細診断スクリプト")
    print("=" * 60)

    # 環境変数読み込み
    env_file = Path(__file__).parent / ".env.local"
    if load_env_file(env_file):
        print("✅ .env.local読み込み完了")
    else:
        print("❌ .env.localファイルが見つかりません")
        return 1

    # PAT詳細分析
    clean_pat, clean_base_id = detailed_pat_analysis()

    if not clean_pat or not clean_base_id:
        return 1

    # メタデータAPIテスト
    meta_success = test_clean_authentication(clean_pat, clean_base_id)

    # 基本curl相当テスト
    basic_success = test_direct_curl_equivalent(clean_pat, clean_base_id)

    print("\n" + "=" * 60)
    print("🏁 診断結果")
    print("=" * 60)

    if meta_success:
        print("✅ Airtable認証: 成功")
        print("🎯 自動統合可能")
        return 0
    elif basic_success:
        print("✅ 基本認証: 成功")
        print("⚠️  メタデータ権限要確認")
        return 0
    else:
        print("❌ 認証: 失敗")
        print("🔧 PAT再生成推奨")
        return 1


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
