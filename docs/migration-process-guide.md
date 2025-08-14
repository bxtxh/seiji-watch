# Airtable to Supabase 移行プロセスガイド

## 目次
1. [移行概要](#移行概要)
2. [事前準備](#事前準備)
3. [Phase 1: Read-Only移行](#phase-1-read-only移行)
4. [Phase 2: Selective移行](#phase-2-selective移行)
5. [Phase 3: 完全移行](#phase-3-完全移行)
6. [ロールバック手順](#ロールバック手順)
7. [チェックリスト](#チェックリスト)

---

## 移行概要

### 移行戦略
- **段階的移行**: 3つのフェーズで安全に移行
- **ゼロダウンタイム**: サービス停止なしで移行
- **ロールバック可能**: 各段階でロールバック可能
- **データ整合性保証**: 継続的な同期と検証

### タイムライン
```
Phase 1 (2-3週間) → Phase 2 (3-6ヶ月) → Phase 3 (1-2ヶ月)
```

### 体制
- **移行責任者**: プロジェクトリード
- **技術担当**: バックエンドエンジニア 2名
- **QA担当**: テストエンジニア 1名
- **監視担当**: DevOpsエンジニア 1名

---

## 事前準備

### 1. 環境構築

#### 1.1 Supabaseプロジェクト作成
```bash
# Supabaseプロジェクトを作成
# https://app.supabase.com で新規プロジェクト作成

# プロジェクト情報を記録
SUPABASE_PROJECT_ID="your-project-id"
SUPABASE_PROJECT_NAME="seiji-watch-production"
SUPABASE_REGION="ap-northeast-1"  # 東京リージョン
```

#### 1.2 認証情報の設定
```bash
# .env.production を作成
cp .env.migration.example .env.production

# 以下の情報を設定:
# - AIRTABLE_PAT
# - AIRTABLE_BASE_ID
# - SUPABASE_URL
# - SUPABASE_ANON_KEY
# - SUPABASE_SERVICE_KEY
# - SUPABASE_DB_URL
# - REDIS_HOST/PORT/PASSWORD
# - MIGRATION_JWT_SECRET
# - MIGRATION_ADMIN_PASSWORD
```

#### 1.3 インフラ準備
```bash
# Redisインスタンス準備（GCP Memorystore推奨）
gcloud redis instances create migration-cache \
  --size=1 \
  --region=asia-northeast1 \
  --redis-version=redis_6_x

# モニタリング設定（Cloud Monitoring）
gcloud monitoring dashboards create \
  --config-from-file=monitoring/dashboard-config.json
```

### 2. データベーススキーマ設定

```bash
# Supabaseデータベースにスキーマを適用
cd infra/supabase

# 本番環境に接続
export DATABASE_URL=$SUPABASE_DB_URL

# マイグレーション実行
for migration in migrations/*.sql; do
  echo "Applying $(basename $migration)..."
  psql $DATABASE_URL < $migration
done

# スキーマ検証
psql $DATABASE_URL -c "\dt"
psql $DATABASE_URL -c "SELECT * FROM pg_indexes WHERE schemaname = 'public';"
```

### 3. 初期データ検証

```bash
# Airtableデータ量確認
python3 scripts/migration_cli.py validate --source airtable

# 期待される出力:
# Parties: 10-20 records
# Members: 700-800 records
# Bills: 1000+ records
# PolicyCategories: 100-200 records
# Meetings: 500+ records
# Speeches: 10000+ records
# Votes: 5000+ records
```

### 4. バックアップ作成

```bash
# Airtableバックアップ
python3 scripts/backup_airtable.py \
  --output backups/airtable_$(date +%Y%m%d).json

# 設定バックアップ
tar -czf backups/config_$(date +%Y%m%d).tar.gz \
  .env* \
  infra/ \
  docker-compose*.yml
```

---

## Phase 1: Read-Only移行

### 目標
- Supabaseからの読み取り: 100%
- Supabaseへの書き込み: 0%（Airtableのみ）
- パフォーマンス改善: 50-80%

### 1. 初期データ移行

```bash
# ロールバックポイント作成
python3 scripts/migration_cli.py rollback create \
  --phase 1 \
  --description "Before Phase 1 migration" \
  --type full

# ドライラン実行
python3 scripts/migration_cli.py migrate full --dry-run

# 本番移行実行
python3 scripts/migration_cli.py migrate full \
  --batch-size 100 \
  --tables "Parties,Members,PolicyCategories,Bills,Meetings,Speeches,Votes"

# 移行検証
python3 scripts/migration_cli.py migrate validate
```

### 2. 同期サービス起動

```bash
# Docker Composeで起動
docker-compose -f docker-compose.migration.yml up -d \
  redis \
  migration-worker \
  sync-worker \
  monitoring

# または個別起動
python3 scripts/sync_worker.py &
SYNC_PID=$!
echo $SYNC_PID > .sync.pid

# 同期状態確認
python3 scripts/migration_cli.py sync status
```

### 3. APIゲートウェイ切り替え

```python
# services/api-gateway/main.py を更新

# Before:
from routes import bills_router

# After:
from routes.hybrid_api import router as hybrid_router
app.include_router(hybrid_router)
```

```bash
# 環境変数設定
export FEATURE_SUPABASE_READ_ENABLED=true
export FEATURE_SUPABASE_WRITE_ENABLED=false
export FEATURE_AIRTABLE_FALLBACK_ENABLED=true
export FEATURE_CACHE_ENABLED=true

# APIサービス再起動
sudo systemctl restart api-gateway
```

### 4. モニタリング設定

```bash
# ダッシュボード起動
cd services/migration-dashboard
npm install
npm run build
npm run start

# アクセス: http://localhost:3001
```

### 5. パフォーマンステスト

```bash
# 負荷テスト実行
python3 tests/load_test.py \
  --endpoint http://localhost:8081/api/v2/bills \
  --concurrent 50 \
  --requests 1000

# 期待される結果:
# - レスポンス時間: < 200ms (p95)
# - エラー率: < 1%
# - キャッシュヒット率: > 80%
```

### 6. 監視項目

```yaml
監視項目:
  - データ整合性: > 95%
  - 同期遅延: < 5分
  - エラー率: < 1%
  - API応答時間: < 200ms
  - キャッシュヒット率: > 80%

アラート設定:
  - 整合性低下: < 90%
  - 同期遅延: > 30分
  - エラー率: > 5%
  - サービス停止
```

---

## Phase 2: Selective移行

### 目標
- 安定データの書き込みをSupabaseへ移行
- 重要データはAirtableに継続書き込み

### 1. 書き込み対象選定

```yaml
Supabase書き込み対象:
  - Parties（政党）: 変更頻度低
  - PolicyCategories（政策カテゴリ）: 変更頻度低
  - Members（議員）: 変更頻度中

Airtable継続:
  - Bills（法案）: 重要度高
  - Votes（投票）: 重要度高
  - Speeches（発言）: データ量大
```

### 2. 設定変更

```bash
# 選択的書き込み有効化
export FEATURE_SUPABASE_WRITE_ENABLED=true
export SUPABASE_WRITE_TABLES="parties,policy_categories,members"

# APIサービス更新
sudo systemctl restart api-gateway
```

### 3. 書き込みテスト

```python
# テストスクリプト実行
python3 tests/test_selective_writes.py

# 検証項目:
# - Parties: Supabase書き込み確認
# - Bills: Airtable書き込み確認
# - 双方向同期確認
```

### 4. 監視強化

```bash
# 書き込み監視追加
python3 scripts/monitor_writes.py \
  --tables parties,members,policy_categories \
  --interval 60
```

---

## Phase 3: 完全移行

### 目標
- すべての読み書きをSupabaseへ
- Airtableを読み取り専用バックアップに

### 1. 最終データ同期

```bash
# 完全同期実行
python3 scripts/migration_cli.py sync stop
python3 scripts/migration_cli.py migrate full --force

# 最終検証
python3 scripts/migration_cli.py migrate validate --strict
```

### 2. 完全切り替え

```bash
# すべての書き込みをSupabaseへ
export FEATURE_SUPABASE_WRITE_ENABLED=true
export FEATURE_AIRTABLE_FALLBACK_ENABLED=false
export SUPABASE_WRITE_TABLES="*"

# Airtableを読み取り専用に
export AIRTABLE_READ_ONLY=true
```

### 3. Airtable同期停止

```bash
# 同期サービス停止
kill $(cat .sync.pid)

# Dockerサービス停止
docker-compose -f docker-compose.migration.yml down sync-worker
```

### 4. 最終確認

```bash
# 全機能テスト
python3 tests/e2e_test.py --full

# パフォーマンス確認
python3 tests/performance_test.py
```

---

## ロールバック手順

### 緊急ロールバック（Phase 1）

```bash
# 1. APIを Airtableモードに切り替え
export FEATURE_SUPABASE_READ_ENABLED=false
sudo systemctl restart api-gateway

# 2. 同期停止
kill $(cat .sync.pid)

# 3. キャッシュクリア
redis-cli FLUSHALL

# 4. 健全性確認
curl http://localhost:8081/api/v2/monitoring/health
```

### データロールバック

```bash
# ロールバックポイント確認
python3 scripts/migration_cli.py rollback list

# ロールバック実行
python3 scripts/migration_cli.py rollback execute \
  --point-id rollback_1_xxxxx \
  --force

# データ再同期
python3 scripts/migration_cli.py migrate full
```

---

## チェックリスト

### Phase 1 開始前
- [ ] Supabaseプロジェクト作成完了
- [ ] 認証情報設定完了
- [ ] データベーススキーマ適用完了
- [ ] Redisインスタンス準備完了
- [ ] バックアップ作成完了
- [ ] ステークホルダーへの通知完了

### Phase 1 実施中
- [ ] 初期データ移行成功
- [ ] 同期サービス起動確認
- [ ] API切り替え完了
- [ ] モニタリング設定完了
- [ ] パフォーマンステスト合格
- [ ] 24時間安定稼働確認

### Phase 1 完了条件
- [ ] データ整合性 > 95%
- [ ] 同期遅延 < 5分
- [ ] エラー率 < 1%
- [ ] パフォーマンス改善確認
- [ ] ロールバック手順検証完了

### Phase 2 開始条件
- [ ] Phase 1が2週間以上安定稼働
- [ ] 書き込み対象テーブル選定完了
- [ ] 書き込みテスト成功
- [ ] バックアップ更新完了

### Phase 3 開始条件
- [ ] Phase 2が1ヶ月以上安定稼働
- [ ] 全テーブルの書き込みテスト完了
- [ ] パフォーマンス目標達成
- [ ] 最終バックアップ完了
- [ ] ステークホルダー承認取得

### 完了条件
- [ ] すべてのデータがSupabaseで稼働
- [ ] Airtable依存の完全除去
- [ ] ドキュメント更新完了
- [ ] 運用引き継ぎ完了

---

## トラブルシューティング

### よくある問題と対処法

#### 1. 同期遅延が増大
```bash
# 同期状態確認
python3 scripts/migration_cli.py sync status

# 同期リセット
python3 scripts/migration_cli.py sync reset --table <table_name>

# バッチサイズ調整
export SYNC_BATCH_SIZE=50
sudo systemctl restart sync-worker
```

#### 2. データ不整合
```bash
# 不整合テーブル特定
python3 scripts/migration_cli.py migrate validate --detailed

# 特定テーブル再同期
python3 scripts/migration_cli.py migrate table <table_name> --force
```

#### 3. パフォーマンス低下
```bash
# キャッシュ状態確認
python3 scripts/migration_cli.py cache stats

# キャッシュウォーミング
python3 scripts/migration_cli.py cache warm --priority high

# 接続プール調整
export SUPABASE_DB_POOL_MAX=20
```

#### 4. API エラー率上昇
```bash
# エラーログ確認
tail -f logs/api.log | grep ERROR

# ヘルスチェック
curl http://localhost:8081/api/v2/monitoring/health

# サーキットブレーカーリセット
curl -X POST http://localhost:8081/api/v2/circuit-breaker/reset
```

---

## 連絡先

### 緊急連絡先
- **移行責任者**: migration-lead@seiji-watch.jp
- **技術サポート**: tech-support@seiji-watch.jp
- **緊急ホットライン**: 03-xxxx-xxxx

### エスカレーション
1. Level 1: 担当エンジニア
2. Level 2: 技術リード
3. Level 3: CTO

### 定期報告
- **日次**: Slackチャンネル #migration-status
- **週次**: ステークホルダーミーティング（金曜15:00）
- **フェーズ完了時**: 経営会議報告

---

## 付録

### 参考資料
- [Supabase公式ドキュメント](https://supabase.com/docs)
- [Airtable API仕様](https://airtable.com/developers/web/api/introduction)
- [移行アーキテクチャ図](./architecture.md)
- [API仕様書](./api-specification.md)

### ツール・スクリプト
- `migration_cli.py`: 移行管理CLI
- `sync_worker.py`: 同期ワーカー
- `monitoring_server.py`: 監視サーバー
- `deploy_migration.sh`: デプロイメントスクリプト

### ログファイル
- 移行ログ: `logs/migration.log`
- 同期ログ: `logs/sync.log`
- APIログ: `logs/api.log`
- エラーログ: `logs/error.log`

---

最終更新: 2025-01-13
バージョン: 1.0.0