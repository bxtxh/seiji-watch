# 🔐 JWT認証設定ガイド

## 概要

このガイドでは、Seiji Watchプロジェクトの JWT 認証を正しく設定する方法を説明します。

## 🎯 重要な原則

**JWT_SECRET_KEYとトークン生成時のSECRET_KEYが完全一致していなければ認証は絶対に失敗します。**
1文字でも違うと認証できません。

## 📋 必要なGitHub Secrets

### 1. JWT_SECRET_KEY (必須)

**本番環境用の値:**
```
JuuqsKGh63LuvjXGoVgOgofPpn-mnDqPooTw8VT3zvmhBTrfWcpu815EDZDw9hBp2qMULqTJiu4o_-Gqu4Z73w
```

**設定手順:**
1. GitHub Repository → Settings → Secrets and variables → Actions
2. "New repository secret" をクリック
3. Name: `JWT_SECRET_KEY`
4. Value: 上記の本番環境用の値をコピーペースト
5. "Add secret" をクリック

### 2. API_BEARER_TOKEN (推奨)

**生成方法:**
```bash
# PyJWTをインストール
pip install PyJWT

# トークン生成スクリプトを実行
python3 scripts/generate_api_bearer_token.py
```

**設定手順:**
1. 上記スクリプトで生成された24時間有効なトークンをコピー
2. GitHub Repository → Settings → Secrets and variables → Actions
3. "New repository secret" をクリック
4. Name: `API_BEARER_TOKEN`
5. Value: 生成されたトークンをペースト
6. "Add secret" をクリック

## 🔍 設定の検証

### 1. JWT一貫性テスト

```bash
# 検証スクリプトを実行
python3 scripts/verify_jwt_consistency.py
```

**期待される出力:**
```
✅ All JWT configurations are working correctly
✅ Ready for production deployment
```

### 2. 手動でのトークン生成テスト

```python
import jwt
import datetime
import os

# GitHub Secretsと同じ値を使用
SECRET_KEY = "JuuqsKGh63LuvjXGoVgOgofPpn-mnDqPooTw8VT3zvmhBTrfWcpu815EDZDw9hBp2qMULqTJiu4o_-Gqu4Z73w"

payload = {
    "sub": "ci-bot",
    "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
    "role": "ci",
    "scopes": ["read", "write", "admin"],
    "type": "access_token"
}

token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
print(f"Generated Token: {token}")

# 検証
decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
print(f"Verification successful: {decoded['sub']}")
```

## 🌍 環境別設定

### 開発環境
```bash
export JWT_SECRET_KEY="test-jwt-secret-unified-for-ci-cd"
export ENVIRONMENT="development"
```

### テスト/CI-CD環境
- GitHub Secretsから自動取得
- フォールバック: `test-jwt-secret-unified-for-ci-cd`

### 本番環境
- **必須**: GitHub Secretsに正しい値を設定
- フォールバックは使用されない（セキュリティチェックでエラー）

## 🔧 ワークフロー設定

### 現在の設定（統一済み）

**ci-cd.yml:**
```yaml
env:
  JWT_SECRET_KEY: ${{ secrets.JWT_SECRET_KEY || 'test-jwt-secret-unified-for-ci-cd' }}
  ENVIRONMENT: testing
  API_BEARER_TOKEN: ${{ secrets.API_BEARER_TOKEN }}
```

**claude.yml:**
```yaml
claude_env: |
  JWT_SECRET_KEY: ${{ secrets.JWT_SECRET_KEY || 'test-jwt-secret-unified-for-ci-cd' }}
  ENVIRONMENT: testing
  API_BEARER_TOKEN: ${{ secrets.API_BEARER_TOKEN }}
```

## 🚨 トラブルシューティング

### よくあるエラー

1. **`API Error: 401 Invalid bearer token`**
   - JWT_SECRET_KEYの不一致
   - トークンの有効期限切れ
   - ワークフローでのトークン未設定

2. **`JWT_SECRET_KEY must be set in production`**
   - 本番環境でGitHub Secretsが未設定
   - 環境変数 `ENVIRONMENT=production` での設定不備

### 解決手順

1. **GitHub Secretsを確認:**
   ```bash
   # GitHub CLIで確認
   gh secret list
   ```

2. **ローカルでテスト:**
   ```bash
   export JWT_SECRET_KEY="JuuqsKGh63LuvjXGoVgOgofPpn-mnDqPooTw8VT3zvmhBTrfWcpu815EDZDw9hBp2qMULqTJiu4o_-Gqu4Z73w"
   python3 scripts/verify_jwt_consistency.py
   ```

3. **API呼び出しテスト:**
   ```bash
   # 生成されたトークンでAPIテスト
   curl -H "Authorization: Bearer YOUR_TOKEN" \
        http://localhost:8000/api/issues/
   ```

## 🔒 セキュリティ考慮事項

### 秘密鍵の管理
- ✅ GitHub Secretsに保存
- ❌ コードにハードコーディングしない
- ❌ ログに出力しない
- ✅ 定期的にローテーション（90日推奨）

### トークンの管理
- ✅ 適切な有効期限設定（1-24時間）
- ✅ 必要最小限のスコープ設定
- ❌ 長期間有効なトークンを避ける

### 環境分離
- ✅ 本番とテスト環境で異なる秘密鍵
- ✅ 環境変数による動的設定
- ✅ 本番環境での強制的な秘密鍵チェック

## ✅ チェックリスト

設定完了前に以下を確認してください：

- [ ] GitHub SecretsにJWT_SECRET_KEYが設定済み
- [ ] GitHub SecretsにAPI_BEARER_TOKENが設定済み
- [ ] `python3 scripts/verify_jwt_consistency.py`が成功
- [ ] CI/CDワークフローでの認証テストが成功
- [ ] 本番環境でのデプロイテストが成功

## 📞 サポート

問題が解決しない場合：

1. `scripts/verify_jwt_consistency.py`の出力を確認
2. GitHub Actionsのログを確認
3. Issue作成時に上記情報を添付

---

最終更新: 2025-01-20
バージョン: 1.0