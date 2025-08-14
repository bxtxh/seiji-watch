# Airtable to Supabase Migration Runbook

## 移行作業実行手順書

### 作業日時
```
開始予定: YYYY-MM-DD HH:MM JST
終了予定: YYYY-MM-DD HH:MM JST
作業時間: 約4時間
```

### 作業体制
| 役割 | 担当者 | 責任範囲 |
|------|--------|----------|
| 作業責任者 | [Name] | 全体統括、判断、承認 |
| 技術リード | [Name] | 技術作業実施、トラブル対応 |
| QAエンジニア | [Name] | テスト実施、検証 |
| 監視担当 | [Name] | モニタリング、アラート対応 |

---

## 事前準備チェックリスト（作業1週間前）

### インフラ準備
- [ ] Supabaseプロジェクト作成完了
- [ ] Redis (Memorystore) 準備完了
- [ ] Cloud Monitoring ダッシュボード設定完了
- [ ] Cloud Storage バケット準備完了

### 認証情報
- [ ] `.env.production` ファイル作成
- [ ] 全環境変数設定確認
- [ ] シークレット管理設定完了

### バックアップ
- [ ] Airtableデータ完全バックアップ取得
- [ ] 設定ファイルバックアップ取得
- [ ] ロールバックポイント作成

### 通知
- [ ] ステークホルダーへの作業通知送信
- [ ] メンテナンス告知（必要な場合）

---

## Phase 1: 初期移行作業手順

### Step 1: 作業環境確認（10分）

```bash
# 1.1 作業ディレクトリ移動
cd /home/migration/seiji-watch

# 1.2 最新コード取得
git pull origin main
git checkout feat/supabase-migration

# 1.3 環境変数確認
source .env.production
env | grep -E "AIRTABLE|SUPABASE|REDIS" | wc -l
# Expected: 10以上

# 1.4 接続テスト
python3 scripts/test_connections.py
# Expected: All connections OK
```

✅ **確認項目**: すべての接続がOKであること

### Step 2: データベーススキーマ設定（15分）

```bash
# 2.1 Supabaseスキーマ適用
cd infra/supabase
for migration in migrations/*.sql; do
  echo "[$(date +%H:%M:%S)] Applying $(basename $migration)..."
  psql $SUPABASE_DB_URL < $migration
  if [ $? -ne 0 ]; then
    echo "ERROR: Migration failed"
    exit 1
  fi
done

# 2.2 スキーマ検証
psql $SUPABASE_DB_URL -c "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';" | wc -l
# Expected: 11 tables

# 2.3 インデックス確認
psql $SUPABASE_DB_URL -c "SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'public';"
# Expected: 20+ indexes
```

✅ **確認項目**: 
- [ ] 全テーブル作成完了
- [ ] インデックス作成完了
- [ ] RLSポリシー適用完了

### Step 3: ロールバックポイント作成（5分）

```bash
# 3.1 タイムスタンプ記録
ROLLBACK_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
echo "Rollback point: $ROLLBACK_TIMESTAMP" | tee -a migration.log

# 3.2 ロールバックポイント作成
python3 scripts/migration_cli.py rollback create \
  --phase 1 \
  --description "Pre-migration backup $ROLLBACK_TIMESTAMP" \
  --type full

# 3.3 ポイントID記録
ROLLBACK_ID=$(python3 scripts/migration_cli.py rollback list --latest --json | jq -r '.id')
echo "Rollback ID: $ROLLBACK_ID" | tee -a migration.log
```

✅ **記録事項**: Rollback ID: ________________

### Step 4: 初期データ移行（60分）

```bash
# 4.1 移行前データ量確認
echo "[$(date +%H:%M:%S)] Checking source data counts..."
python3 scripts/migration_cli.py validate --source airtable | tee pre_migration_counts.txt

# 4.2 ドライラン実行
echo "[$(date +%H:%M:%S)] Starting dry run..."
python3 scripts/migration_cli.py migrate full --dry-run
if [ $? -ne 0 ]; then
  echo "ERROR: Dry run failed"
  exit 1
fi

# 4.3 本番移行実行
echo "[$(date +%H:%M:%S)] Starting actual migration..."
time python3 scripts/migration_cli.py migrate full \
  --batch-size 100 \
  --tables "Parties,Members,PolicyCategories,Bills,Meetings,Speeches,Votes" \
  --verbose | tee migration_output.log

# 4.4 移行結果確認
echo "[$(date +%H:%M:%S)] Validating migration..."
python3 scripts/migration_cli.py migrate validate | tee validation_result.txt
```

✅ **確認項目**:
- [ ] 全テーブル移行成功
- [ ] データ整合性 > 95%
- [ ] エラー率 < 1%

### Step 5: 同期サービス起動（20分）

```bash
# 5.1 Docker サービス起動
echo "[$(date +%H:%M:%S)] Starting sync services..."
docker-compose -f docker-compose.migration.yml up -d redis migration-worker sync-worker monitoring

# 5.2 サービス状態確認
sleep 10
docker-compose -f docker-compose.migration.yml ps

# 5.3 同期開始
python3 scripts/migration_cli.py sync start \
  --mode incremental \
  --interval 5

# 5.4 同期状態確認
sleep 30
python3 scripts/migration_cli.py sync status
```

✅ **確認項目**:
- [ ] 全サービス起動確認
- [ ] 同期ステータス: Running
- [ ] キューサイズ < 100

### Step 6: API切り替え（30分）

```bash
# 6.1 現在のAPI設定バックアップ
cp /etc/api-gateway/config.yaml /etc/api-gateway/config.yaml.backup

# 6.2 環境変数設定
cat >> /etc/api-gateway/env.conf << EOF
FEATURE_SUPABASE_READ_ENABLED=true
FEATURE_SUPABASE_WRITE_ENABLED=false
FEATURE_AIRTABLE_FALLBACK_ENABLED=true
FEATURE_CACHE_ENABLED=true
EOF

# 6.3 API再起動
sudo systemctl restart api-gateway

# 6.4 ヘルスチェック
sleep 10
for i in {1..5}; do
  echo "[$(date +%H:%M:%S)] Health check attempt $i..."
  curl -s http://localhost:8081/api/v2/monitoring/health | jq '.status'
  sleep 5
done
```

✅ **確認項目**:
- [ ] API起動確認
- [ ] ヘルスチェック: healthy
- [ ] エラーログなし

### Step 7: パフォーマンステスト（30分）

```bash
# 7.1 基本動作確認
echo "[$(date +%H:%M:%S)] Testing basic endpoints..."
for endpoint in bills members parties policy-categories; do
  echo "Testing /api/v2/$endpoint"
  time curl -s "http://localhost:8081/api/v2/$endpoint?limit=10" | jq '.data | length'
done

# 7.2 負荷テスト
echo "[$(date +%H:%M:%S)] Running load test..."
python3 tests/load_test.py \
  --endpoint http://localhost:8081/api/v2/bills \
  --concurrent 50 \
  --requests 1000 \
  --output load_test_result.json

# 7.3 結果確認
python3 scripts/analyze_load_test.py load_test_result.json
```

✅ **パフォーマンス基準**:
- [ ] 応答時間 p95 < 200ms
- [ ] エラー率 < 1%
- [ ] キャッシュヒット率 > 80%

### Step 8: モニタリング設定（15分）

```bash
# 8.1 ダッシュボード起動
cd services/migration-dashboard
npm run build
npm run start &
DASHBOARD_PID=$!
echo $DASHBOARD_PID > /tmp/dashboard.pid

# 8.2 アクセス確認
sleep 10
curl -I http://localhost:3001

# 8.3 メトリクス確認
curl http://localhost:8081/api/v2/monitoring/metrics | jq '.'
```

✅ **確認項目**:
- [ ] ダッシュボードアクセス可能
- [ ] メトリクス取得正常
- [ ] アラート設定完了

---

## 検証チェックリスト

### 機能検証
- [ ] Bills API: リスト取得、個別取得、フィルタリング
- [ ] Members API: リスト取得、個別取得
- [ ] PolicyCategories API: 階層取得
- [ ] 検索機能: キーワード検索動作
- [ ] ページネーション動作

### データ検証
```bash
# データ整合性チェック
python3 scripts/migration_cli.py migrate validate --detailed
```
- [ ] Bills: 整合性 > 95%
- [ ] Members: 整合性 > 95%
- [ ] PolicyCategories: 整合性 > 95%
- [ ] その他テーブル: 整合性 > 95%

### パフォーマンス検証
- [ ] API応答時間: < 200ms (p95)
- [ ] 同期遅延: < 5分
- [ ] キャッシュヒット率: > 80%
- [ ] CPU使用率: < 70%
- [ ] メモリ使用率: < 80%

---

## トラブルシューティング

### 問題: データ移行失敗
```bash
# 対処法
# 1. エラーログ確認
tail -100 migration_output.log | grep ERROR

# 2. 特定テーブルのみ再移行
python3 scripts/migration_cli.py migrate table <table_name> --force

# 3. それでも失敗する場合はロールバック
python3 scripts/migration_cli.py rollback execute --point-id $ROLLBACK_ID
```

### 問題: API応答遅延
```bash
# 対処法
# 1. キャッシュ状態確認
redis-cli INFO stats

# 2. キャッシュウォーミング
python3 scripts/migration_cli.py cache warm --priority high

# 3. 接続プール調整
export SUPABASE_DB_POOL_MAX=30
sudo systemctl restart api-gateway
```

### 問題: 同期遅延増大
```bash
# 対処法
# 1. 同期キュー確認
python3 scripts/migration_cli.py sync status

# 2. バッチサイズ調整
export SYNC_BATCH_SIZE=50
docker-compose restart sync-worker

# 3. 手動同期実行
python3 scripts/migration_cli.py sync table <table_name> --mode full
```

---

## ロールバック手順

### 即時ロールバック（5分以内）

```bash
# 1. API切り戻し
export FEATURE_SUPABASE_READ_ENABLED=false
sudo systemctl restart api-gateway

# 2. 同期停止
python3 scripts/migration_cli.py sync stop
docker-compose -f docker-compose.migration.yml down

# 3. キャッシュクリア
redis-cli FLUSHALL

# 4. 状態確認
curl http://localhost:8081/api/v2/monitoring/health
```

### データロールバック（30分）

```bash
# 1. ロールバックポイント確認
python3 scripts/migration_cli.py rollback list

# 2. ロールバック実行
python3 scripts/migration_cli.py rollback execute \
  --point-id $ROLLBACK_ID \
  --force

# 3. データ再検証
python3 scripts/migration_cli.py migrate validate

# 4. サービス再起動
sudo systemctl restart api-gateway
```

---

## 作業完了確認

### 最終チェックリスト
- [ ] 全API正常動作確認
- [ ] データ整合性95%以上
- [ ] パフォーマンス基準達成
- [ ] モニタリング正常
- [ ] ドキュメント更新

### 作業記録
```bash
# 作業ログ集約
tar -czf migration_logs_$(date +%Y%m%d_%H%M%S).tar.gz \
  migration.log \
  migration_output.log \
  validation_result.txt \
  load_test_result.json \
  logs/

# S3アップロード
gsutil cp migration_logs_*.tar.gz gs://seiji-watch-backups/migrations/
```

### 報告事項
- 作業開始時刻: _______________
- 作業終了時刻: _______________
- 移行レコード数: _____________
- データ整合性: _______________%
- 問題発生: Yes / No
- 問題内容: ___________________

---

## 連絡先

### エスカレーション
1. 技術リード: [Name] - [Phone]
2. プロジェクトマネージャー: [Name] - [Phone]
3. CTO: [Name] - [Phone]

### サポート
- Supabaseサポート: support@supabase.io
- GCPサポート: [Support Case URL]
- 内部Slackチャンネル: #migration-support

---

最終更新: 2025-01-13
Version: 1.0.0