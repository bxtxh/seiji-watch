# Airtable to Supabase Migration - Requirements Document

## Introduction

現在のシステムはAirtableを管理者用データベースとして使用していますが、APIレート制限（5req/sec）によるパフォーマンスボトルネック、複雑なリレーションクエリの処理困難、スケーラビリティの限界という課題に直面しています。

本要求は、これらの課題を解決するためにSupabase（PostgreSQLベース）への段階的移行を実現し、パフォーマンス向上とスケーラビリティ確保を図ることを目的とします。現在のデータ規模（1000+ 法案、744+ 国会議員、8つの相互連携テーブル）と管理者の運用継続性を考慮したハイブリッド運用アプローチを採用します。

## Requirements

### Requirement 1: パフォーマンス向上のための読み取り専用Supabase導入

**User Story:** システム利用者として、法案や議員データの検索・表示が高速に行われることを期待するので、APIレート制限によるボトルネックを解消した高速なデータアクセスを実現したい

#### Acceptance Criteria

1. WHEN 複雑な関係データを取得する THEN システムは現在より50-80%高速にレスポンスを返す SHALL
2. WHEN 同時に複数のユーザーがアクセスする THEN システムは5req/secの制限なく数百同時接続を処理する SHALL
3. WHEN CAP準拠の階層的政策分類（L1→L2→L3）を検索する THEN システムは単一クエリで結果を返す SHALL
4. IF Airtable APIが利用不可能 THEN システムはSupabaseから代替データを提供する SHALL

### Requirement 2: データ整合性を保つハイブリッド運用

**User Story:** システム管理者として、データの一貫性を保ちながら段階的に移行したいので、AirtableとSupabaseの両方が同期された状態で運用できるようにしたい

#### Acceptance Criteria

1. WHEN Airtableでデータが更新される THEN システムは変更をSupabaseに自動同期する SHALL
2. WHEN データ同期エラーが発生する THEN システムは管理者に通知し、手動同期オプションを提供する SHALL
3. WHEN 読み取りクエリを実行する THEN システムはSupabaseを優先し、フォールバックでAirtableを使用する SHALL
4. IF データの不整合を検出する THEN システムは警告を表示し、修正手順を提案する SHALL

### Requirement 3: 管理者の運用継続性確保

**User Story:** 非技術者の管理者として、慣れ親しんだAirtableインターフェースで日常的なデータメンテナンスを継続したいので、移行期間中も既存の操作方法を維持したい

#### Acceptance Criteria

1. WHEN 管理者がAirtableでデータを編集する THEN システムは従来通りの操作性を提供する SHALL
2. WHEN 新しい法案や議員データを追加する THEN システムは既存のワークフローを維持する SHALL
3. WHEN データの一括更新を行う THEN システムはAirtableの既存機能を活用できる SHALL
4. IF 管理者が移行の影響を受ける THEN システムは明確な操作ガイドを提供する SHALL

### Requirement 4: 段階的移行による影響最小化

**User Story:** プロジェクトマネージャーとして、システムの安定性を保ちながら移行を進めたいので、段階的なアプローチでリスクを最小化したい

#### Acceptance Criteria

1. WHEN Phase 1（読み取り専用移行）を実行する THEN システムは2-3週間で完了する SHALL
2. WHEN Phase 2（段階的機能移行）を実行する THEN システムは更新頻度の低いマスタデータから順次移行する SHALL
3. WHEN 各フェーズを完了する THEN システムは前フェーズへのロールバック機能を提供する SHALL
4. IF 移行中に問題が発生する THEN システムは即座に前の状態に復旧できる SHALL

### Requirement 5: 複雑なデータ構造の適切な移行

**User Story:** データアーキテクトとして、現在のAirtableの複雑なリレーションとJSONフィールドを適切にPostgreSQLに移行したいので、データの整合性と機能性を保持した設計を実現したい

#### Acceptance Criteria

1. WHEN 多対多リレーション（Bills_PolicyCategories）を移行する THEN システムは適切な中間テーブルを作成する SHALL
2. WHEN JSONフィールドの構造化データを移行する THEN システムはPostgreSQLのJSONB型を活用する SHALL
3. WHEN CAP準拠の階層的分類を移行する THEN システムは階層構造を効率的にクエリできる設計を採用する SHALL
4. IF 既存のクエリパターンがある THEN システムは同等以上のパフォーマンスを提供する SHALL

### Requirement 6: 運用監視とメンテナンス機能

**User Story:** システム運用者として、移行後のシステムの健全性を監視し、必要に応じてメンテナンスを実行したいので、包括的な監視とメンテナンス機能を利用したい

#### Acceptance Criteria

1. WHEN システムを監視する THEN システムはAirtableとSupabaseの同期状況をダッシュボードで表示する SHALL
2. WHEN パフォーマンス問題を検出する THEN システムは自動的にアラートを発信する SHALL
3. WHEN データベースメンテナンスが必要 THEN システムは自動バックアップと復旧機能を提供する SHALL
4. IF システム負荷が高い THEN システムは負荷分散とキャッシュ最適化を自動実行する SHALL

### Requirement 7: 移行評価とロールバック機能

**User Story:** 技術責任者として、移行の成功を客観的に評価し、必要に応じて安全にロールバックしたいので、定量的な評価指標と確実なロールバック機能を利用したい

#### Acceptance Criteria

1. WHEN 移行効果を測定する THEN システムはAPI応答時間、同時接続数、エラー率を定量的に報告する SHALL
2. WHEN ロールバックを実行する THEN システムは5分以内に前の状態に復旧する SHALL
3. WHEN 移行判定を行う THEN システムは事前定義された成功基準に基づいて評価する SHALL
4. IF 移行が失敗と判定される THEN システムは自動的にロールバック手順を開始する SHALL