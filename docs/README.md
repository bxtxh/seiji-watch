# Diet Issue Tracker - Documentation Index

**政治ウォッチ！ドキュメント索引**

_Version: 1.0 | Date: 2025-07-12 | Status: Reorganized Structure_

---

## 📁 ドキュメント構成

### 🎯 [00-overview/](./00-overview/) - プロダクト概要・戦略

- **[roadmap.md](./00-overview/roadmap.md)** - 製品ロードマップ・開発計画

### 📋 [01-specs/](./01-specs/) - 製品・技術仕様

#### 🏢 [product/](./01-specs/product/) - プロダクト仕様

- **[requirements.md](./01-specs/product/requirements.md)** - 機能・非機能要件定義

#### 🔧 [technical/](./01-specs/technical/) - 技術仕様

- **[infrastructure-specification.md](./01-specs/technical/infrastructure-specification.md)** - インフラ構成仕様（GCP・Terraform）
- **[issue-feature-specification.md](./01-specs/technical/issue-feature-specification.md)** - イシュー機能・3層分類システム
- **[ingestion-pipeline-hybrid.md](./01-specs/technical/ingestion-pipeline-hybrid.md)** - ハイブリッドインジェスションパイプライン（NDL API × Whisper）
- **[development-implementation-mapping.md](./01-specs/technical/development-implementation-mapping.md)** - 開発チケット⇔実装ファイル対応
- **[development-tickets-final.md](./01-specs/technical/development-tickets-final.md)** - EPIC・チケット進捗管理

#### 🎨 [ux-ui/](./01-specs/ux-ui/) - UX・UI設計

- **[user-experience-specification.md](./01-specs/ux-ui/user-experience-specification.md)** - ユーザー体験・UI設計仕様（TOPページ詳細含む）

### ⚖️ [02-legal/](./02-legal/) - 法的コンプライアンス

- **[legal-compliance-requirements.md](./02-legal/legal-compliance-requirements.md)** - 法的コンプライアンス要件定義
- **[terms-of-service.md](./02-legal/terms-of-service.md)** - 利用規約
- **[privacy-policy.md](./02-legal/privacy-policy.md)** - プライバシーポリシー

### 📝 [03-project-mgmt/](./03-project-mgmt/) - プロジェクト管理

- **[additional-development-requests.md](./03-project-mgmt/additional-development-requests.md)** - 追加開発要求管理
- **[minutes/](./03-project-mgmt/minutes/)** - 会議議事録
  - **[product-development-minutes.md](./03-project-mgmt/minutes/product-development-minutes.md)** - プロダクト開発議事録

### 🔬 [90-specialized/](./90-specialized/) - 専門機能仕様

- **[issue-tagging/](./90-specialized/issue-tagging/)** - イシュータグシステム
  - **[phase0_seed.md](./90-specialized/issue-tagging/phase0_seed.md)** - フェーズ0シードデータ定義

### 🗄️ [archive/](./archive/) - アーカイブ文書

- **[ProductGrowth-archived-2025-07-12.md](./archive/ProductGrowth-archived-2025-07-12.md)** - プロダクト成長戦略（アーカイブ）

---

## 📖 主要ドキュメント読書ガイド

### 🚀 **新規メンバー向け**

1. [roadmap.md](./00-overview/roadmap.md) - プロダクト全体像
2. [requirements.md](./01-specs/product/requirements.md) - 機能要件
3. [user-experience-specification.md](./01-specs/ux-ui/user-experience-specification.md) - UI/UX設計

### 🛠️ **エンジニア向け**

1. [infrastructure-specification.md](./01-specs/technical/infrastructure-specification.md) - インフラ構成
2. [development-implementation-mapping.md](./01-specs/technical/development-implementation-mapping.md) - 実装構造
3. [issue-feature-specification.md](./01-specs/technical/issue-feature-specification.md) - イシュー機能詳細

### 📊 **プロジェクト管理者向け**

1. [development-tickets-final.md](./01-specs/technical/development-tickets-final.md) - 開発進捗
2. [additional-development-requests.md](./03-project-mgmt/additional-development-requests.md) - 要求管理
3. [product-development-minutes.md](./03-project-mgmt/minutes/product-development-minutes.md) - 意思決定履歴

### ⚖️ **法務・コンプライアンス担当者向け**

1. [legal-compliance-requirements.md](./02-legal/legal-compliance-requirements.md) - 法的要件
2. [terms-of-service.md](./02-legal/terms-of-service.md) - 利用規約
3. [privacy-policy.md](./02-legal/privacy-policy.md) - プライバシーポリシー

---

## 🔄 文書管理ルール

### バージョン管理

- **アクティブ文書**: 各ディレクトリ内で継続的更新
- **アーカイブ**: `archive/` に日付付きで保存
- **命名規則**: `filename-archived-YYYY-MM-DD.md`

### 更新プロセス

1. **機能追加・変更時**: 関連仕様書の同期更新
2. **重要変更**: 古い版をアーカイブに移動
3. **定期見直し**: 四半期ごとの内容確認

### 文書階層ポリシー

- **最大階層**: 3レベル（`docs/01-specs/technical/`）
- **命名**: kebab-case、数字プレフィックスでソート順制御
- **README**: 各ディレクトリに役割説明を配置

---

## 📈 実装ステータス

### 🎯 **MVP Complete (2025-07-12)**

- ✅ 全主要機能実装完了
- ✅ 品質指標達成（Lighthouse 90+）
- ✅ セキュリティ・法的コンプライアンス対応
- ✅ E2Eテスト・監視体制完備

### 📊 **実装統計**

- **総EPIC数**: 9個（7個完了）
- **総チケット数**: 62個（58個完了）
- **実装ファイル数**: 200+ファイル
- **コスト削減**: 75%（$628→$155/月）

---

**文書構造設計**

- 設計指針: o3 AI recommendations + 実運用考慮
- 再編成日: 2025-07-12
- 次回見直し: 2025-10-12
- 管理者: 開発チーム
