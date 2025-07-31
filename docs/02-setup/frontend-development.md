# Frontend Development Setup Guide

## 概要

このガイドでは、Diet Issue Trackerのフロントエンド開発環境のセットアップ手順を説明します。

## 前提条件

- Node.js 18.x以上
- npm 8.x以上
- Docker（PostgreSQLとRedis用）
- Python 3.11+（API Gateway用）

## セットアップ手順

### 1. リポジトリのクローン

```bash
git clone https://github.com/your-org/seiji-watch.git
cd seiji-watch
```

### 2. Dockerコンテナの起動

PostgreSQLとRedisを起動します：

```bash
docker-compose up -d
```

確認：
```bash
docker-compose ps
```

### 3. API Gatewayのセットアップ

別のターミナルで：

```bash
cd services/api-gateway

# 依存関係のインストール
poetry install

# 環境変数の設定
cp .env.example .env.development
# .env.developmentを編集してAirtableのAPIキーなどを設定

# API Gatewayの起動
python scripts/start_api.py
```

API Gatewayが起動していることを確認：
```bash
curl http://localhost:8080/health
```

### 4. フロントエンドのセットアップ

新しいターミナルで：

```bash
cd services/web-frontend

# 依存関係のインストール
npm install

# 環境変数の設定
cp .env.example .env.development

# 開発サーバーの起動
npm run dev
```

### 5. 接続テスト

プロジェクトルートから：

```bash
# API接続テスト
python scripts/test_api_connection.py

# フロントエンドが正しく起動しているか確認
open http://localhost:3000
```

## トラブルシューティング

### API接続エラー

1. **「Cannot connect to API Gateway」エラー**
   - API Gatewayが起動しているか確認
   - ポート8080が使用されていないか確認
   - `lsof -i :8080` でポートを確認

2. **CORS エラー**
   - ブラウザのコンソールでCORSエラーが表示される場合
   - API Gatewayのmain.pyでCORS設定を確認
   - localhost:3000が許可されているか確認

3. **環境変数が読み込まれない**
   - Next.jsを再起動（Ctrl+C後、npm run dev）
   - .env.developmentファイルが正しい場所にあるか確認
   - 環境変数名がNEXT_PUBLIC_で始まっているか確認

### データが表示されない

1. **法案一覧が空**
   - Airtableにデータが存在するか確認
   - API Gatewayのログでエラーを確認
   - ブラウザのネットワークタブでAPIレスポンスを確認

2. **カテゴリーが読み込まれない**
   - `/api/issues/categories`エンドポイントをテスト
   - Airtableの権限設定を確認

## デバッグモード

開発環境では、画面右下にデバッグ情報が表示されます：
- API Base URL
- 環境変数の状態
- その他の設定

この情報を使って、環境設定が正しく行われているか確認できます。

## 開発のベストプラクティス

1. **コミット前のチェック**
   ```bash
   npm run lint
   npm run type-check
   npm test
   ```

2. **APIモックの使用**
   - API Gatewayが利用できない場合は、MSWを使用してモックを作成

3. **ブランチ戦略**
   - feature/ブランチで開発
   - PRを作成してレビューを受ける

## よくある質問

**Q: ポート3000が既に使用されている**
A: 環境変数PORTを設定して別のポートを使用：
```bash
PORT=3001 npm run dev
```

**Q: TypeScriptエラーが大量に出る**
A: VSCodeの場合、TypeScriptのバージョンを確認：
- Cmd+Shift+P → "TypeScript: Select TypeScript Version"
- "Use Workspace Version"を選択

**Q: 本番環境の設定は？**
A: `.env.production`ファイルを作成し、本番用のAPI URLを設定してください。