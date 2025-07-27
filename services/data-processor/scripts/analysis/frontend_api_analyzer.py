#!/usr/bin/env python3
"""
フロントエンドAPI使用状況分析
Bills関連のAPIエンドポイントとフィールド使用を調査
"""

import re
from collections import defaultdict
from pathlib import Path


def analyze_api_usage():
    """フロントエンドのAPI使用状況を分析"""

    web_frontend_path = (
        Path(__file__).parent.parent.parent / "services" / "web-frontend"
    )

    results = {
        "api_endpoints": [],
        "field_usage": defaultdict(list),
        "api_files": [],
        "component_usage": defaultdict(list),
    }

    # 検索対象ファイル
    search_patterns = ["*.ts", "*.tsx", "*.js", "*.jsx"]

    for pattern in search_patterns:
        for file_path in web_frontend_path.rglob(pattern):
            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()
                    rel_path = file_path.relative_to(web_frontend_path)

                    # API エンドポイント検索
                    api_patterns = [
                        r'/api/bills[^\s"\']*',
                        r'/api/issues[^\s"\']*',
                        r'bills[^/\s"\']*',
                        r'issues[^/\s"\']*',
                    ]

                    for pattern in api_patterns:
                        matches = re.findall(pattern, content, re.IGNORECASE)
                        for match in matches:
                            results["api_endpoints"].append(
                                {
                                    "file": str(rel_path),
                                    "endpoint": match,
                                    "line_context": "",
                                }
                            )

                    # フィールド使用検索
                    bills_fields = [
                        "Status",
                        "Summary",
                        "Assignee",
                        "Attachments",
                        "Speeches",
                        "Issues",
                        "Submission_Date",
                        "Committee",
                        "Full_Text",
                        "Related_Documents",
                        "AI_Analysis",
                        "Keywords",
                        "Bill_ID",
                        "Title",
                        "Diet_Session",
                        "Category",
                        "Bill_Number",
                    ]

                    for field in bills_fields:
                        # より厳密なパターンでフィールド使用を検索
                        patterns = [
                            f'"{field}"',
                            f"'{field}'",
                            rf"\.{field}",
                            f"{field}:",
                            rf"{field}\s*=",
                            rf"{field}\s*\?",
                        ]

                        for pattern in patterns:
                            if re.search(pattern, content):
                                # 行番号を取得
                                lines = content.split("\n")
                                for i, line in enumerate(lines):
                                    if re.search(pattern, line):
                                        results["field_usage"][field].append(
                                            {
                                                "file": str(rel_path),
                                                "line": i + 1,
                                                "context": line.strip(),
                                            }
                                        )
                                        break

                    # API関連ファイルの特定
                    if any(
                        keyword in content.lower()
                        for keyword in ["api", "fetch", "axios", "bills", "issues"]
                    ):
                        results["api_files"].append(str(rel_path))

            except Exception:
                continue

    return results


def main():
    print("🔍 フロントエンドAPI使用状況分析")
    print("=" * 60)

    results = analyze_api_usage()

    # 1. API関連ファイル一覧
    print("\n📁 API関連ファイル一覧")
    print("-" * 40)
    for file_path in sorted(set(results["api_files"])):
        print(f"  {file_path}")

    # 2. APIエンドポイント一覧
    print(f"\n🌐 検出されたAPIエンドポイント ({len(results['api_endpoints'])}件)")
    print("-" * 40)
    endpoints = {}
    for endpoint_info in results["api_endpoints"]:
        endpoint = endpoint_info["endpoint"]
        if endpoint not in endpoints:
            endpoints[endpoint] = []
        endpoints[endpoint].append(endpoint_info["file"])

    for endpoint, files in sorted(endpoints.items()):
        print(f"  {endpoint}")
        for file in sorted(set(files)):
            print(f"    └── {file}")

    # 3. 削除候補フィールドの使用状況
    print("\n🗑️ 削除候補フィールドの使用状況")
    print("-" * 40)

    deletion_candidates = [
        "Assignee",
        "Attachments",
        "Submission_Date",
        "Full_Text",
        "Related_Documents",
        "AI_Analysis",
        "Keywords",
    ]

    for field in deletion_candidates:
        usage = results["field_usage"][field]
        if usage:
            print(f"  ⚠️  {field} - {len(usage)}箇所で使用")
            for use in usage[:3]:  # 最大3件表示
                print(f"    └── {use['file']}:{use['line']} - {use['context'][:50]}...")
        else:
            print(f"  ✅ {field} - 未使用")

    # 4. 要検討フィールドの使用状況
    print("\n⚠️ 要検討フィールドの使用状況")
    print("-" * 40)

    review_fields = ["Status", "Summary", "Speeches", "Committee", "Issues"]

    for field in review_fields:
        usage = results["field_usage"][field]
        if usage:
            print(f"  🔍 {field} - {len(usage)}箇所で使用")
            for use in usage[:3]:  # 最大3件表示
                print(f"    └── {use['file']}:{use['line']} - {use['context'][:50]}...")
        else:
            print(f"  ❌ {field} - 未使用")

    # 5. 調査すべきファイル
    print("\n📋 詳細調査推奨ファイル")
    print("-" * 40)

    key_files = [
        "src/lib/api.ts",
        "src/types/index.ts",
        "src/components/BillDetailModal.tsx",
        "src/components/BillCard.tsx",
        "src/pages/issues/index.tsx",
        "src/pages/issues/[id].tsx",
    ]

    for file in key_files:
        web_frontend_path = (
            Path(__file__).parent.parent.parent / "services" / "web-frontend"
        )
        full_path = web_frontend_path / file
        if full_path.exists():
            print(f"  ✅ {file} - 存在")
        else:
            print(f"  ❌ {file} - 存在しない")

    print("\n🎯 次のステップ")
    print("-" * 40)
    print("1. 上記のkey_filesを直接確認")
    print("2. 削除候補フィールドの使用箇所を詳細確認")
    print("3. APIエンドポイントでの実際のフィールド使用を確認")
    print("4. 型定義ファイル(src/types/index.ts)でのフィールド定義確認")

    return 0


if __name__ == "__main__":
    main()
