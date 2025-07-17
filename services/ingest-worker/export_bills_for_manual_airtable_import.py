#!/usr/bin/env python3
"""
第217回国会法案データ手動Airtableインポート用エクスポート

PATの認証問題を回避し、手動インポート可能なCSVファイルを生成
"""

import csv
import sys
import json
from datetime import datetime
from pathlib import Path

def load_bills_data():
    """既存の法案データを読み込み"""
    print("📄 法案データ読み込み")
    sys.path.insert(0, 'src')
    from scraper.diet_scraper import DietScraper
    
    scraper = DietScraper(enable_resilience=False)
    bills = scraper.fetch_current_bills()
    print(f"✅ {len(bills)}件の法案データを収集")
    return bills

def bill_to_airtable_row(bill):
    """法案データをAirtableインポート用行に変換"""
    
    # カテゴリマッピング
    category_mapping = {
        "税制": "taxation",
        "社会保障": "social_security", 
        "外交・国際": "foreign_affairs",
        "予算・決算": "budget",
        "経済・産業": "economy",
        "その他": "other"
    }
    
    # ステータスマッピング
    status_mapping = {
        "議案要旨": "backlog",
        "審議中": "under_review", 
        "採決待ち": "pending_vote",
        "成立": "passed",
        "否決": "rejected",
        "": "backlog"
    }
    
    return {
        "Bill_Number": bill.bill_id,
        "Title": bill.title,
        "Status": status_mapping.get(bill.status, "backlog"),
        "Category": category_mapping.get(bill.category, "other"),
        "Diet_Session": "217",
        "House_Of_Origin": "参議院",
        "Bill_Type": bill.submitter or "議員",
        "Diet_URL": bill.url or "",
        "Summary": bill.summary or "",
        "Submitted_Date": bill.submission_date.isoformat() if bill.submission_date else "",
        "Created_At": datetime.now().isoformat(),
        "Updated_At": datetime.now().isoformat()
    }

def export_bills_to_csv(bills, output_path):
    """法案データをCSVファイルにエクスポート"""
    
    # CSVフィールド定義（Airtableフィールド名に対応）
    fieldnames = [
        "Bill_Number",
        "Title", 
        "Status",
        "Category",
        "Diet_Session",
        "House_Of_Origin",
        "Bill_Type",
        "Diet_URL",
        "Summary",
        "Submitted_Date",
        "Created_At",
        "Updated_At"
    ]
    
    with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        # ヘッダー行を書き込み
        writer.writeheader()
        
        # データ行を書き込み
        for bill in bills:
            row = bill_to_airtable_row(bill)
            writer.writerow(row)
    
    print(f"✅ CSVファイル作成完了: {output_path}")

def export_bills_to_json(bills, output_path):
    """法案データをJSONファイルにエクスポート（バックアップ用）"""
    
    bills_data = []
    for bill in bills:
        bill_dict = {
            'bill_id': bill.bill_id,
            'title': bill.title,
            'status': bill.status,
            'stage': bill.stage,
            'submitter': bill.submitter,
            'category': bill.category,
            'url': bill.url,
            'summary': bill.summary,
            'submission_date': bill.submission_date.isoformat() if bill.submission_date else None,
            'collected_at': datetime.now().isoformat()
        }
        bills_data.append(bill_dict)
    
    export_data = {
        "export_info": {
            "timestamp": datetime.now().isoformat(),
            "total_bills": len(bills_data),
            "diet_session": "217",
            "source": "参議院",
            "purpose": "MVP manual Airtable import"
        },
        "bills": bills_data
    }
    
    with open(output_path, 'w', encoding='utf-8') as jsonfile:
        json.dump(export_data, jsonfile, ensure_ascii=False, indent=2)
    
    print(f"✅ JSONファイル作成完了: {output_path}")

def main():
    """メイン実行"""
    print("📤 第217回国会法案データ手動インポート用エクスポート")
    print(f"📅 実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    try:
        # 1. 法案データ収集
        bills = load_bills_data()
        
        if not bills:
            print("❌ 法案データが収集できませんでした")
            return 1
        
        # 2. ファイル名生成
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_filename = f"diet_bills_217_for_airtable_{timestamp}.csv"
        json_filename = f"diet_bills_217_backup_{timestamp}.json"
        
        # 3. CSVエクスポート（Airtable手動インポート用）
        print("\n📊 CSVファイル生成（Airtable手動インポート用）")
        export_bills_to_csv(bills, csv_filename)
        
        # 4. JSONエクスポート（バックアップ用）
        print("\n💾 JSONファイル生成（バックアップ用）")
        export_bills_to_json(bills, json_filename)
        
        print("\n" + "=" * 60)
        print("✅ エクスポート完了!")
        print(f"📄 Airtable用CSVファイル: {csv_filename}")
        print(f"💾 バックアップJSONファイル: {json_filename}")
        print("\n📋 手動インポート手順:")
        print("1. Airtableベースの「Bills (法案)」テーブルを開く")
        print(f"2. CSVファイル ({csv_filename}) をインポート")
        print("3. フィールドマッピングを確認してインポート実行")
        print("4. 226件の法案データがAirtableに追加される")
        print("\n🎯 MVP用法案データベース準備完了!")
        
        return 0
        
    except Exception as e:
        print(f"❌ エクスポートエラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)