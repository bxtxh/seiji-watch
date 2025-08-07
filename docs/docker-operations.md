# Docker Operations Guide
## Diet Issue Tracker - 運用ガイド

### 目次
1. [開発環境セットアップ](#開発環境セットアップ)
2. [本番環境デプロイ](#本番環境デプロイ)
3. [運用コマンド](#運用コマンド)
4. [トラブルシューティング](#トラブルシューティング)
5. [セキュリティ](#セキュリティ)
6. [モニタリング](#モニタリング)

---

## 開発環境セットアップ

### 必要条件
- Docker Desktop 4.0+
- Docker Compose v2.0+
- Make (GNU Make 3.81+)
- Git

### 初期セットアップ

```bash
# リポジトリのクローン
git clone https://github.com/your-org/seiji-watch.git
cd seiji-watch

# 環境変数の設定
cp .env.example .env
# .envファイルを編集して必要な値を設定

# 開発環境の構築
make dev-setup

# サービスの起動
make up
```

### 開発ワークフロー

#### 1. 全サービス起動
```bash
make up-all  # 全サービス起動
make up      # コアサービスのみ起動
make up-workers  # ワーカーサービス起動
```

#### 2. ログ確認
```bash
make logs SERVICE=api-gateway  # 特定サービスのログ
make logs  # 全サービスのログ
```

#### 3. サービスへのアクセス
```bash
make shell SERVICE=api-gateway  # コンテナ内シェル
```

#### 4. テスト実行
```bash
make test  # 全テスト実行
make test-service SERVICE=api-gateway  # 特定サービスのテスト
```

---

## 本番環境デプロイ

### 前提条件
- GCP プロジェクトのセットアップ
- Cloud SQL インスタンスの作成
- Cloud Memorystore (Redis) の設定
- Secret Manager での秘密情報管理

### デプロイ手順

#### 1. 環境変数の設定
```bash
# 本番環境用の環境変数を設定
cp .env.production .env.prod
# Secret Managerから値を取得して設定
```

#### 2. イメージのビルド
```bash
# 本番用イメージのビルド
make build-prod

# セキュリティスキャン
make security-scan
```

#### 3. デプロイ
```bash
# Docker Swarm モードでのデプロイ
docker stack deploy -c docker-compose.yml -c docker-compose.prod.yml seiji-watch

# または Kubernetes へのデプロイ
kubectl apply -f k8s/
```

#### 4. ヘルスチェック
```bash
# サービスの状態確認
make health

# エンドポイントテスト
curl https://api.seiji-watch.jp/health
```

---

## 運用コマンド

### サービス管理

| コマンド | 説明 |
|---------|------|
| `make up` | コアサービス起動 |
| `make down` | 全サービス停止 |
| `make restart` | サービス再起動 |
| `make ps` | サービス状態確認 |
| `make health` | ヘルスチェック |

### ビルド・デプロイ

| コマンド | 説明 |
|---------|------|
| `make build` | 開発用イメージビルド |
| `make build-prod` | 本番用イメージビルド |
| `make rebuild` | キャッシュなしビルド |
| `make push` | イメージをレジストリにプッシュ |

### データベース管理

| コマンド | 説明 |
|---------|------|
| `make db-migrate` | マイグレーション実行 |
| `make db-backup` | データベースバックアップ |
| `make db-restore` | データベースリストア |
| `make db-reset` | データベースリセット（注意！） |

### テスト・品質

| コマンド | 説明 |
|---------|------|
| `make test` | 全テスト実行 |
| `make lint` | リントチェック |
| `make format` | コードフォーマット |
| `make security-scan` | セキュリティスキャン |

### モニタリング

| コマンド | 説明 |
|---------|------|
| `make logs` | ログ表示 |
| `make stats` | リソース使用状況 |
| `make monitor` | リアルタイム監視 |

---

## トラブルシューティング

### よくある問題と解決方法

#### 1. ポート競合
```bash
# エラー: bind: address already in use
# 解決方法:
lsof -i :3000  # ポート使用確認
kill -9 <PID>  # プロセス終了
# または docker-compose.yml でポート変更
```

#### 2. メモリ不足
```bash
# エラー: Cannot allocate memory
# 解決方法:
# Docker Desktop設定でメモリ増加
# Resources > Advanced > Memory: 8GB以上推奨
```

#### 3. ビルドエラー
```bash
# package-lock.json エラー
# 解決方法:
rm -rf node_modules package-lock.json
npm install
docker compose build --no-cache
```

#### 4. データベース接続エラー
```bash
# 接続確認
docker exec seiji-watch-postgres pg_isready
docker compose logs postgres

# 再起動
docker compose restart postgres
```

#### 5. 環境変数の問題
```bash
# 環境変数確認
docker compose config
docker exec <container> env

# 再読み込み
docker compose up -d --force-recreate
```

### ログ調査

```bash
# エラーログの検索
docker compose logs | grep ERROR

# 特定時間のログ
docker compose logs --since 30m

# ログのフォロー
docker compose logs -f api-gateway
```

---

## セキュリティ

### セキュリティチェックリスト

- [ ] 環境変数の秘密情報管理
- [ ] HTTPSの有効化
- [ ] ファイアウォール設定
- [ ] セキュリティヘッダーの設定
- [ ] 定期的な脆弱性スキャン
- [ ] アクセスログの監査

### セキュリティスキャン実行

```bash
# ローカルでのセキュリティチェック
./scripts/security-check.sh

# Trivyによるコンテナスキャン
trivy image seiji-watch-api-gateway:latest

# 依存関係の脆弱性チェック
make security-scan
```

### シークレット管理

```bash
# Google Secret Managerの使用
gcloud secrets create jwt-secret-key --data-file=secret.txt

# Dockerでのシークレット
docker secret create jwt_key jwt_key.txt
```

---

## モニタリング

### Prometheus + Grafana

#### アクセス方法
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3003
  - Default user: admin
  - Default password: (環境変数で設定)

#### メトリクス確認

```bash
# サービスメトリクス
curl http://localhost:8000/metrics

# Nginxステータス
curl http://localhost/metrics
```

### アラート設定

```yaml
# monitoring/alerts.yml
groups:
  - name: service_alerts
    rules:
      - alert: ServiceDown
        expr: up == 0
        for: 5m
        annotations:
          summary: "Service {{ $labels.job }} is down"
```

### ログ集約

```bash
# Fluentdの設定（オプション）
docker run -d \
  -v /var/log:/var/log \
  -v ./fluent.conf:/fluentd/etc/fluent.conf \
  fluent/fluentd
```

---

## バックアップとリストア

### 自動バックアップ

```bash
# Cronジョブの設定
0 2 * * * /usr/local/bin/backup-seiji-watch.sh
```

### 手動バックアップ

```bash
# データベースバックアップ
make db-backup

# ボリュームバックアップ
docker run --rm \
  -v seiji-watch_postgres_data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/postgres-backup-$(date +%Y%m%d).tar.gz /data
```

### リストア手順

```bash
# データベースリストア
gunzip < backups/db-backup-20250801.sql.gz | \
  docker exec -i seiji-watch-postgres psql -U seiji_watch_user

# ボリュームリストア
docker run --rm \
  -v seiji-watch_postgres_data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar xzf /backup/postgres-backup-20250801.tar.gz
```

---

## CI/CD パイプライン

### GitHub Actions ワークフロー

```yaml
# 自動デプロイ設定
on:
  push:
    branches: [main]
    
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build and push
        run: |
          make build-prod
          make push
      - name: Deploy to production
        run: |
          gcloud run deploy
```

---

## 緊急時対応

### サービス障害時

1. **即座の対応**
   ```bash
   # サービス状態確認
   make health
   
   # 問題のあるサービスを再起動
   docker compose restart <service>
   ```

2. **ロールバック**
   ```bash
   # 前のバージョンに戻す
   docker service rollback seiji-watch_api-gateway
   ```

3. **スケールアウト**
   ```bash
   # レプリカ数増加
   docker service scale seiji-watch_api-gateway=3
   ```

### 連絡先

- 開発チーム: dev-team@seiji-watch.jp
- インフラチーム: infra@seiji-watch.jp
- 緊急連絡: emergency@seiji-watch.jp

---

## 付録

### 推奨される開発ツール

- **Docker Desktop**: コンテナ管理
- **Lens**: Kubernetes GUI
- **Portainer**: Docker Web UI
- **ctop**: コンテナモニタリング
- **dive**: イメージ分析

### 参考リンク

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Project Wiki](https://github.com/your-org/seiji-watch/wiki)

---

最終更新: 2025-08-01
バージョン: 1.0.0