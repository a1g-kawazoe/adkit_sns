# 開発進捗ログ

## セッション 1: プロジェクト初期セットアップ（2026-02-24）

### やったこと

1. **CLAUDE.md 作成** — 開発ガイドライン（日本語応対・初心者教育・サブエージェント活用など）を策定
2. **Git リポジトリ初期化** — `git init` で版管理を開始
3. **`.gitignore` 作成** — Python / 機密情報 / IDE / OS ファイルを除外設定
4. **`.env.example` 作成** — X API / Instagram / Anthropic API のキーテンプレート
5. **ディレクトリ構成を設計・作成**
   ```
   Adkit_SNS/
   ├── config/          # 設定管理
   ├── src/
   │   ├── collectors/  # Web情報収集
   │   ├── processors/  # AIコンテンツ生成
   │   ├── publishers/  # SNS投稿
   │   └── utils/       # ロガーなど共通処理
   ├── docs/            # ドキュメント
   ├── data/cache/      # スクレイピングキャッシュ
   └── logs/            # 実行ログ
   ```
6. **`requirements.txt` 作成** — tweepy, instagrapi, beautifulsoup4, anthropic 等を定義
7. **各モジュールのスケルトンコードを作成**
   - `web_scraper.py` — 海外マーケティングサイトから記事を収集
   - `content_generator.py` — Anthropic APIで日本語SNSコンテンツを生成
   - `x_publisher.py` — X (Twitter) への投稿（通常投稿 + スレッド対応）
   - `instagram_publisher.py` — Instagramへの画像/カルーセル投稿
   - `logger.py` — loguru ベースのロギング設定
   - `settings.py` — pydantic で環境変数を型安全に管理
8. **`main.py` 作成** — 収集 → 生成 → 投稿の3ステップパイプライン
9. **`README.md` 作成** — プロジェクト概要・セットアップ手順・API情報

---

## セッション 2: Agent Team アーキテクチャへのリファクタリング（2026-02-24）

### やったこと

単一パイプライン構造から **Lead + Workers + QA の Agent Team** 構成に全面リファクタリング。

#### モデル配置

| エージェント | 役割 | モデル |
|---|---|---|
| **Lead** | 全体進行管理・ディレクション | Opus（高性能） |
| **QA** | コード・出力の品質検証 | Opus（高性能） |
| Worker 1: Researcher | Web情報リサーチ & カテゴライズ | Sonnet（標準） |
| Worker 2: ExcelReporter | リサーチ結果をExcelにまとめる | Sonnet（標準） |
| Worker 3: ImageCreator | SNS投稿画像クリエイティブ生成 | Sonnet（標準） |
| Worker 4: TextCreator | SNS投稿テキスト生成 | Sonnet（標準） |

#### ワークフロー（Orchestrator が制御）

```
Phase 1: Lead → 計画策定（テーマ・優先カテゴリ・トーン決定）
Phase 2: Researcher → Web情報収集 & カテゴライズ
Phase 3: Lead → リサーチ結果レビュー & 投稿対象選定
Phase 4: ExcelReporter / ImageCreator / TextCreator → 並列作業
Phase 5: QA → テキスト品質検証 & 画像存在確認
Phase 6: Lead → 最終統合レポート
```

#### 新規作成ファイル

| ファイル | 内容 |
|---|---|
| `src/agents/base_agent.py` | 全エージェント共通基底クラス（モデル自動割当） |
| `src/agents/lead_agent.py` | Lead: 計画策定・レビュー・最終統合 |
| `src/agents/qa_agent.py` | QA: テキスト検証・画像検証 |
| `src/agents/workers/researcher.py` | Worker1: スクレイピング & LLMカテゴライズ |
| `src/agents/workers/excel_reporter.py` | Worker2: openpyxl でExcelレポート生成 |
| `src/agents/workers/image_creator.py` | Worker3: Pillow でX/IG用画像生成 |
| `src/agents/workers/text_creator.py` | Worker4: X/IG用テキスト生成 |
| `src/orchestrator.py` | 6フェーズのワークフロー制御 |

#### 更新したファイル

- `config/settings.py` — opus_model / sonnet_model の2モデル設定を追加
- `main.py` — Orchestrator 経由の実行に書き換え
- `requirements.txt` — openpyxl を追加

### 次回やること

- `.env` にAPIキーを設定して接続テスト
- 各エージェントの単体テスト
- SNS投稿（publishers）との連携
- スケジューラーによる定期自動実行
- エラーハンドリングの強化
