#!/usr/bin/env python3
"""
Check current member data in the database
"""

import asyncio
import aiohttp
import os
from dotenv import load_dotenv

load_dotenv('/Users/shogen/seiji-watch/.env.local')

async def check_member_data():
    """Check current member data quality"""
    
    pat = os.getenv("AIRTABLE_PAT")
    base_id = os.getenv("AIRTABLE_BASE_ID")
    
    headers = {
        "Authorization": f"Bearer {pat}",
        "Content-Type": "application/json"
    }
    
    base_url = f"https://api.airtable.com/v0/{base_id}"
    
    async with aiohttp.ClientSession() as session:
        print("🔍 議員データベース確認")
        print("=" * 60)
        
        # Get member data
        members_url = f"{base_url}/Members (議員)"
        async with session.get(members_url, headers=headers, params={"maxRecords": 50}) as response:
            if response.status == 200:
                data = await response.json()
                records = data.get("records", [])
                
                print(f"📊 総議員数: {len(records)}件")
                print("\n🔍 データサンプル:")
                
                dummy_count = 0
                real_count = 0
                
                for i, record in enumerate(records[:10], 1):
                    fields = record["fields"]
                    name = fields.get("Name", "N/A")
                    name_kana = fields.get("Name_Kana", "N/A")
                    house = fields.get("House", "N/A")
                    constituency = fields.get("Constituency", "N/A")
                    
                    # Check if this looks like dummy data
                    is_dummy = (
                        name.startswith("議員") or 
                        name in ["山田太郎", "田中花子", "佐藤次郎", "鈴木三郎", "高橋美咲"] or
                        name_kana and name_kana.startswith("ぎいん")
                    )
                    
                    status = "🤖 ダミー" if is_dummy else "👤 実データ"
                    
                    if is_dummy:
                        dummy_count += 1
                    else:
                        real_count += 1
                    
                    print(f"  {i:2d}. {status} | {name} ({name_kana}) | {house} | {constituency}")
                
                print(f"\n📊 データ分析 (サンプル10件):")
                print(f"  🤖 ダミーデータ: {dummy_count}件")
                print(f"  👤 実データ: {real_count}件")
                
                # Check all records for dummy data
                print(f"\n🔍 全データ分析...")
                total_dummy = 0
                for record in records:
                    name = record["fields"].get("Name", "")
                    name_kana = record["fields"].get("Name_Kana", "")
                    
                    is_dummy = (
                        name.startswith("議員") or 
                        name in ["山田太郎", "田中花子", "佐藤次郎", "鈴木三郎", "高橋美咲"] or
                        name_kana and name_kana.startswith("ぎいん")
                    )
                    
                    if is_dummy:
                        total_dummy += 1
                
                total_real = len(records) - total_dummy
                
                print(f"📊 全体統計:")
                print(f"  🤖 ダミーデータ: {total_dummy}件 ({total_dummy/len(records)*100:.1f}%)")
                print(f"  👤 実データ: {total_real}件 ({total_real/len(records)*100:.1f}%)")
                
                if total_dummy > total_real:
                    print(f"\n❌ 問題発見!")
                    print(f"  議員テーブルの大部分がダミーデータです")
                    print(f"  実際の国会議員データに置き換える必要があります")
                    print(f"\n💡 推奨対応:")
                    print(f"  1. 参議院・衆議院の公式議員リストをスクレイピング")
                    print(f"  2. 実際の議員名、選挙区、所属政党データを収集")
                    print(f"  3. ダミーデータを実データで置換")
                else:
                    print(f"\n✅ データ品質良好")
                    print(f"  実データが多数を占めています")
                
            else:
                print(f"❌ 議員データ取得失敗: {response.status}")

if __name__ == "__main__":
    asyncio.run(check_member_data())