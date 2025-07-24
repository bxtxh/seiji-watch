#!/usr/bin/env python3
"""
ingest-worker内でのNotesフィールド使用箇所を特定
修正が必要なファイルとその優先度を分析
"""

import re
from pathlib import Path


def analyze_notes_usage():
    """Notesフィールド使用状況の分析"""

    print("🔍 ingest-worker内 Notes フィールド使用状況分析")
    print("=" * 60)

    ingest_worker_path = Path(__file__).parent
    python_files = list(ingest_worker_path.glob("*.py"))

    analysis_results = {
        'active_usage': [],      # 現在アクティブに使用中
        'legacy_usage': [],      # 過去の実装（非アクティブ）
        'test_files': [],        # テストファイル
        'analysis_files': []     # 分析ファイル
    }

    notes_patterns = [
        r'"Notes":\s*',           # "Notes": の直接代入
        r"'Notes':\s*",           # 'Notes': の直接代入
        r'\.get\(["\']Notes["\']',  # .get('Notes') のアクセス
        r'\["Notes"\]',           # ["Notes"] のアクセス
        r"\['Notes'\]",           # ['Notes'] のアクセス
        r'fields\.Notes',         # fields.Notes のアクセス
        r'Notes.*=.*f["\']',      # Notes = f"..." の代入
    ]

    for py_file in python_files:
        if py_file.name.startswith('.'):
            continue

        try:
            with open(py_file, encoding='utf-8') as f:
                content = f.read()

            notes_usage = []
            line_numbers = []

            # パターンマッチング
            for pattern in notes_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    # マッチした行番号を取得
                    line_num = content[:match.start()].count('\n') + 1
                    line_content = content.split('\n')[line_num - 1].strip()

                    notes_usage.append({
                        'pattern': pattern,
                        'line': line_num,
                        'content': line_content[:100] + ('...' if len(line_content) > 100 else '')
                    })
                    line_numbers.append(line_num)

            if notes_usage:
                file_info = {
                    'file': py_file.name,
                    'path': str(py_file),
                    'usage_count': len(notes_usage),
                    'usages': notes_usage,
                    'line_numbers': sorted(set(line_numbers))
                }

                # ファイルタイプ分類
                if 'test' in py_file.name.lower():
                    analysis_results['test_files'].append(file_info)
                elif 'analysis' in py_file.name.lower() or 'analyze' in py_file.name.lower():
                    analysis_results['analysis_files'].append(file_info)
                elif any(keyword in py_file.name for keyword in ['epic11', 'minimal', 'batch', 'integration']):
                    # 最近のデータ統合関連ファイル
                    analysis_results['active_usage'].append(file_info)
                else:
                    analysis_results['legacy_usage'].append(file_info)

        except Exception as e:
            print(f"⚠️ ファイル読み込みエラー {py_file.name}: {str(e)}")

    return analysis_results


def generate_fix_priority(analysis_results):
    """修正優先度の提案"""

    print("\n🎯 修正優先度とアクション計画")
    print("=" * 60)

    priority_plan = []

    # 高優先度: アクティブ使用ファイル
    if analysis_results['active_usage']:
        print("\n🔴 【高優先度】現在アクティブなファイル:")
        for file_info in analysis_results['active_usage']:
            print(f"  📁 {file_info['file']}: {file_info['usage_count']}箇所")
            for usage in file_info['usages'][:3]:  # 最初の3件のみ表示
                print(f"    L{usage['line']}: {usage['content']}")
            if len(file_info['usages']) > 3:
                print(f"    ... 他{len(file_info['usages'])-3}件")

            priority_plan.append({
                'priority': 'HIGH',
                'file': file_info['file'],
                'reason': 'アクティブなデータ統合処理',
                'action': 'Notesフィールド生成を構造化フィールドに変更'
            })

    # 中優先度: レガシーファイル
    if analysis_results['legacy_usage']:
        print("\n🟡 【中優先度】レガシーファイル:")
        for file_info in analysis_results['legacy_usage']:
            print(f"  📁 {file_info['file']}: {file_info['usage_count']}箇所")

            priority_plan.append({
                'priority': 'MEDIUM',
                'file': file_info['file'],
                'reason': 'レガシーコード（使用頻度低）',
                'action': '構造化フィールド使用に更新または削除検討'
            })

    # 低優先度: テストファイル
    if analysis_results['test_files']:
        print("\n🟢 【低優先度】テストファイル:")
        for file_info in analysis_results['test_files']:
            print(f"  📁 {file_info['file']}: {file_info['usage_count']}箇所")

            priority_plan.append({
                'priority': 'LOW',
                'file': file_info['file'],
                'reason': 'テストファイル',
                'action': 'テストデータ更新'
            })

    # 分析ファイルは対象外
    if analysis_results['analysis_files']:
        print("\n⚪ 【対象外】分析ファイル:")
        for file_info in analysis_results['analysis_files']:
            print(f"  📁 {file_info['file']}: {file_info['usage_count']}箇所（分析目的のため対象外）")

    return priority_plan


def suggest_replacement_strategy():
    """置換戦略の提案"""

    print("\n🔧 Notes フィールド置換戦略")
    print("=" * 60)

    strategies = [
        {
            'pattern': '"Notes": f"..."',
            'replacement': '構造化フィールドへの個別設定',
            'example': '''
# 変更前:
"Notes": f"状態: {bill.status} | カテゴリ: {bill.category}"

# 変更後:
"Bill_Status": bill.status,
"Category": bill.category,
"Submitter": bill.submitter_type
'''
        },
        {
            'pattern': '構造化絵文字形式',
            'replacement': '構造化フィールドマッピング',
            'example': '''
# 変更前:
"Notes": f"""【法案詳細】
🏛️ 法案ID: {bill.bill_id}
📋 ステータス: {bill.status}
..."""

# 変更後:
"Bill_Number": bill.bill_id,
"Bill_Status": bill.status,
"Stage": bill.stage,
"Bill_URL": bill.url
'''
        }
    ]

    for i, strategy in enumerate(strategies, 1):
        print(f"\n戦略 {i}: {strategy['pattern']} → {strategy['replacement']}")
        print(strategy['example'])

    print("\n✅ 置換後の利点:")
    print("  - 構造化された検索・フィルタリング")
    print("  - データの整合性向上")
    print("  - API レスポンスの最適化")
    print("  - 将来の機能拡張の容易性")


def main():
    # Notes使用状況分析
    analysis_results = analyze_notes_usage()

    # 統計表示
    total_files = sum(len(files) for files in analysis_results.values())
    total_usage = sum(len(file_info['usages'])
                      for files in analysis_results.values() for file_info in files)

    print("\n📊 使用状況サマリー")
    print(f"  対象ファイル数: {total_files}件")
    print(f"  総使用箇所: {total_usage}箇所")
    print(f"  アクティブファイル: {len(analysis_results['active_usage'])}件")
    print(f"  レガシーファイル: {len(analysis_results['legacy_usage'])}件")
    print(f"  テストファイル: {len(analysis_results['test_files'])}件")
    print(f"  分析ファイル: {len(analysis_results['analysis_files'])}件")

    # 修正優先度提案
    generate_fix_priority(analysis_results)

    # 置換戦略提案
    suggest_replacement_strategy()

    return 0


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)
