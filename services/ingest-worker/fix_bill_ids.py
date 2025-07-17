#!/usr/bin/env python3
"""
Bill ID 欠損データ修正スクリプト

Billsテーブルの空白・欠損Bill_IDを分析し、適切なIDを生成して埋め込みます。
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# Airtable client setup
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from shared.src.shared.clients.airtable import AirtableClient


@dataclass
class BillRecord:
    """法案レコード構造"""
    record_id: str
    bill_id: Optional[str]
    title: str
    submission_date: Optional[str]
    status: str
    stage: str
    submitter: str
    category: str
    diet_session: Optional[str]
    house: Optional[str]


class BillIDGenerator:
    """Bill ID生成器"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.used_ids = set()
        
        # 法案ID命名規則
        self.HOUSE_CODES = {
            "衆議院": "H",
            "参議院": "S",
            "両院": "B",
            "": "G"  # 政府提出法案
        }
        
        self.CATEGORY_CODES = {
            "内閣提出": "C",
            "議員提出": "M", 
            "予算関連": "B",
            "条約": "T",
            "承認": "A",
            "その他": "O"
        }
    
    def analyze_existing_patterns(self, bills: List[BillRecord]) -> Dict[str, Any]:
        """既存のBill_IDパターンを分析"""
        patterns = {
            "total_bills": len(bills),
            "has_bill_id": 0,
            "missing_bill_id": 0,
            "id_patterns": {},
            "existing_ids": set()
        }
        
        for bill in bills:
            if bill.bill_id and bill.bill_id.strip():
                patterns["has_bill_id"] += 1
                patterns["existing_ids"].add(bill.bill_id)
                
                # パターン分析
                if re.match(r'^[HSB][CM][0-9]{3}$', bill.bill_id):
                    patterns["id_patterns"]["standard"] = patterns["id_patterns"].get("standard", 0) + 1
                elif re.match(r'^[0-9]+$', bill.bill_id):
                    patterns["id_patterns"]["numeric"] = patterns["id_patterns"].get("numeric", 0) + 1
                else:
                    patterns["id_patterns"]["other"] = patterns["id_patterns"].get("other", 0) + 1
            else:
                patterns["missing_bill_id"] += 1
        
        self.used_ids = patterns["existing_ids"]
        return patterns
    
    def generate_bill_id(self, bill: BillRecord, session: str = "217") -> str:
        """法案に対してBill_IDを生成"""
        
        # 提出者・カテゴリからコード決定
        category_code = self._get_category_code(bill.submitter, bill.category)
        
        # 議院コード決定
        house_code = self._get_house_code(bill.house, bill.submitter)
        
        # 連番生成
        sequence = self._generate_sequence(house_code, category_code, session)
        
        # 最終ID
        bill_id = f"{house_code}{category_code}{sequence:03d}"
        
        # 重複チェック
        if bill_id in self.used_ids:
            # 重複する場合は連番を増やす
            for i in range(1, 1000):
                alternative_id = f"{house_code}{category_code}{(sequence + i):03d}"
                if alternative_id not in self.used_ids:
                    bill_id = alternative_id
                    break
        
        self.used_ids.add(bill_id)
        return bill_id
    
    def _get_category_code(self, submitter: str, category: str) -> str:
        """カテゴリコードを決定"""
        if not submitter:
            return "O"
        
        submitter_lower = submitter.lower()
        category_lower = category.lower() if category else ""
        
        if "内閣" in submitter or "政府" in submitter:
            return "C"
        elif "議員" in submitter or "member" in submitter_lower:
            return "M"
        elif "予算" in category_lower or "budget" in category_lower:
            return "B"
        elif "条約" in category_lower or "treaty" in category_lower:
            return "T"
        elif "承認" in category_lower or "approval" in category_lower:
            return "A"
        else:
            return "O"
    
    def _get_house_code(self, house: str, submitter: str) -> str:
        """議院コードを決定"""
        if not house:
            if submitter and "内閣" in submitter:
                return "G"  # 政府提出
            return "B"  # 両院
        
        return self.HOUSE_CODES.get(house, "B")
    
    def _generate_sequence(self, house_code: str, category_code: str, session: str) -> int:
        """連番を生成"""
        # 既存IDから同じパターンの最大連番を取得
        pattern = f"{house_code}{category_code}"
        max_sequence = 0
        
        for existing_id in self.used_ids:
            if existing_id.startswith(pattern) and len(existing_id) == 6:
                try:
                    sequence = int(existing_id[2:5])
                    max_sequence = max(max_sequence, sequence)
                except ValueError:
                    continue
        
        return max_sequence + 1


class BillIDFixer:
    """Bill ID修正メインクラス"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.airtable_client = None
        self.generator = BillIDGenerator()
    
    async def __aenter__(self):
        self.airtable_client = AirtableClient()
        await self.airtable_client.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.airtable_client:
            await self.airtable_client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def analyze_bills_table(self) -> Dict[str, Any]:
        """Billsテーブルの現状を分析"""
        self.logger.info("Analyzing Bills table structure and data...")
        
        try:
            # 全法案データを取得
            bills_data = await self.airtable_client.get_all_bills()
            
            # BillRecordに変換
            bills = []
            for bill_data in bills_data:
                bills.append(BillRecord(
                    record_id=bill_data.get('id', ''),
                    bill_id=bill_data.get('bill_id', ''),
                    title=bill_data.get('title', ''),
                    submission_date=bill_data.get('submission_date', ''),
                    status=bill_data.get('status', ''),
                    stage=bill_data.get('stage', ''),
                    submitter=bill_data.get('submitter', ''),
                    category=bill_data.get('category', ''),
                    diet_session=bill_data.get('diet_session', ''),
                    house=bill_data.get('house', '')
                ))
            
            # パターン分析
            analysis = self.generator.analyze_existing_patterns(bills)
            
            # 詳細分析
            missing_bills = [bill for bill in bills if not bill.bill_id or not bill.bill_id.strip()]
            
            analysis.update({
                "missing_bills_details": [
                    {
                        "record_id": bill.record_id,
                        "title": bill.title[:100] + "..." if len(bill.title) > 100 else bill.title,
                        "submitter": bill.submitter,
                        "category": bill.category,
                        "house": bill.house,
                        "status": bill.status
                    }
                    for bill in missing_bills[:10]  # 最初の10件のみ
                ],
                "total_missing_shown": min(len(missing_bills), 10),
                "bills_to_fix": missing_bills
            })
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Failed to analyze bills table: {e}")
            raise
    
    async def fix_missing_bill_ids(self, bills_to_fix: List[BillRecord]) -> Dict[str, Any]:
        """欠損Bill_IDを修正"""
        self.logger.info(f"Starting Bill ID fixing for {len(bills_to_fix)} bills...")
        
        results = {
            "total_processed": 0,
            "successfully_updated": 0,
            "failed_updates": 0,
            "generated_ids": [],
            "errors": []
        }
        
        for bill in bills_to_fix:
            try:
                # Bill_IDを生成
                generated_id = self.generator.generate_bill_id(bill)
                
                # Airtableを更新
                update_data = {"bill_id": generated_id}
                await self.airtable_client.update_bill(bill.record_id, update_data)
                
                results["successfully_updated"] += 1
                results["generated_ids"].append({
                    "record_id": bill.record_id,
                    "title": bill.title[:50] + "..." if len(bill.title) > 50 else bill.title,
                    "generated_id": generated_id,
                    "submitter": bill.submitter,
                    "house": bill.house
                })
                
                self.logger.info(f"✅ Updated {bill.record_id}: {generated_id}")
                
            except Exception as e:
                results["failed_updates"] += 1
                error_msg = f"Failed to update {bill.record_id}: {str(e)}"
                results["errors"].append(error_msg)
                self.logger.error(error_msg)
            
            finally:
                results["total_processed"] += 1
        
        return results
    
    async def validate_bill_ids(self) -> Dict[str, Any]:
        """Bill_ID修正後の検証"""
        self.logger.info("Validating Bill IDs after fixing...")
        
        try:
            # 修正後の全データを取得
            bills_data = await self.airtable_client.get_all_bills()
            
            validation = {
                "total_bills": len(bills_data),
                "with_bill_id": 0,
                "still_missing": 0,
                "duplicate_ids": {},
                "format_violations": []
            }
            
            bill_ids = {}
            
            for bill_data in bills_data:
                bill_id = bill_data.get('bill_id', '')
                
                if bill_id and bill_id.strip():
                    validation["with_bill_id"] += 1
                    
                    # 重複チェック
                    if bill_id in bill_ids:
                        validation["duplicate_ids"][bill_id] = validation["duplicate_ids"].get(bill_id, 1) + 1
                    else:
                        bill_ids[bill_id] = 1
                    
                    # フォーマットチェック
                    if not re.match(r'^[HSBG][CMBTAO][0-9]{3}$', bill_id):
                        validation["format_violations"].append({
                            "record_id": bill_data.get('id', ''),
                            "bill_id": bill_id,
                            "title": bill_data.get('title', '')[:50]
                        })
                else:
                    validation["still_missing"] += 1
            
            # 成功率計算
            validation["completion_rate"] = (validation["with_bill_id"] / validation["total_bills"]) * 100
            
            return validation
            
        except Exception as e:
            self.logger.error(f"Failed to validate bill IDs: {e}")
            raise


async def main():
    """メイン処理"""
    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    logger = logging.getLogger(__name__)
    
    print("🔧 Bill ID 欠損データ修正システム")
    print("=" * 50)
    
    try:
        async with BillIDFixer() as fixer:
            # 1. 現状分析
            print("\n📊 Step 1: Bills テーブル分析")
            analysis = await fixer.analyze_bills_table()
            
            print(f"  総法案数: {analysis['total_bills']}")
            print(f"  Bill_ID有り: {analysis['has_bill_id']}")
            print(f"  Bill_ID無し: {analysis['missing_bill_id']}")
            print(f"  欠損率: {(analysis['missing_bill_id']/analysis['total_bills'])*100:.1f}%")
            
            if analysis['id_patterns']:
                print("\n  既存IDパターン:")
                for pattern, count in analysis['id_patterns'].items():
                    print(f"    {pattern}: {count}件")
            
            if analysis['missing_bill_id'] > 0:
                print(f"\n  欠損データ例 (先頭{analysis['total_missing_shown']}件):")
                for bill in analysis['missing_bills_details']:
                    print(f"    - {bill['title']}")
                    print(f"      提出者: {bill['submitter']}, 院: {bill['house']}")
            
            # 2. 修正実行
            if analysis['missing_bill_id'] > 0:
                print(f"\n🔨 Step 2: Bill_ID生成・修正 ({analysis['missing_bill_id']}件)")
                
                confirm = input("修正を実行しますか？ (y/N): ").lower().strip()
                if confirm != 'y':
                    print("修正をキャンセルしました。")
                    return 0
                
                results = await fixer.fix_missing_bill_ids(analysis['bills_to_fix'])
                
                print(f"  処理完了: {results['total_processed']}件")
                print(f"  成功: {results['successfully_updated']}件")
                print(f"  失敗: {results['failed_updates']}件")
                
                if results['failed_updates'] > 0:
                    print(f"\n  エラー詳細:")
                    for error in results['errors'][:5]:  # 最初の5件のみ
                        print(f"    - {error}")
                
                # 生成されたIDのサンプル表示
                if results['generated_ids']:
                    print(f"\n  生成されたID例:")
                    for generated in results['generated_ids'][:5]:
                        print(f"    {generated['generated_id']}: {generated['title']}")
            
            # 3. 検証
            print(f"\n✅ Step 3: 修正結果検証")
            validation = await fixer.validate_bill_ids()
            
            print(f"  総法案数: {validation['total_bills']}")
            print(f"  Bill_ID有り: {validation['with_bill_id']}")
            print(f"  まだ欠損: {validation['still_missing']}")
            print(f"  完了率: {validation['completion_rate']:.1f}%")
            
            if validation['duplicate_ids']:
                print(f"  ⚠️  重複ID検出: {len(validation['duplicate_ids'])}件")
                for dup_id, count in list(validation['duplicate_ids'].items())[:3]:
                    print(f"    {dup_id}: {count}回")
            
            if validation['format_violations']:
                print(f"  ⚠️  フォーマット違反: {len(validation['format_violations'])}件")
            
            # 4. 結果保存
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_file = f"bill_id_fix_report_{timestamp}.json"
            
            report = {
                "timestamp": timestamp,
                "analysis": analysis,
                "fix_results": results if 'results' in locals() else None,
                "validation": validation
            }
            
            # 循環参照を避けるため、bills_to_fixオブジェクトを削除
            if 'bills_to_fix' in report['analysis']:
                del report['analysis']['bills_to_fix']
            
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, ensure_ascii=False, indent=2)
            
            print(f"\n📄 詳細レポート保存: {report_file}")
            
            if validation['completion_rate'] >= 95:
                print("🎉 Bill ID修正が正常に完了しました！")
                return 0
            else:
                print("⚠️  一部の修正に失敗しました。レポートを確認してください。")
                return 1
                
    except Exception as e:
        logger.error(f"Bill ID修正処理でエラーが発生: {e}")
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))