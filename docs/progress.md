# 開発進捗ログ

## このエージェント、もう使えますか？

**結論: コードが揃っていれば「ほぼ使える」状態です。ただし次が必要です。**

| 項目 | 状態 | 備考 |
|------|------|------|
| 設計・アーキテクチャ | ✅ 完了 | Lead + Workers + QA、モデル割当済み |
| 実行に必要なコード | ⚠️ 要確認 | main / config / agents / orchestrator が存在するか確認 |
| 環境構築 | ❌ 未実施 | 仮想環境・pip install・.env の設定 |
| APIキー | ❌ 未設定 | Anthropic 必須。X/Instagram は投稿する場合のみ |
| 動作確認 | ❌ 未実施 | `python main.py` でエラーなく動くか |
| SNS投稿連携 | ❌ 未実装 | 現状は「成果物生成」まで。投稿は publishers と未接続 |

- **「リサーチ → Excel・画像・テキスト生成」まで試すだけ**なら、**Anthropic API キー + 環境構築**ができれば可能です。
- **X / Instagram への自動投稿**まで使うには、**各APIキー設定**と **Orchestrator と publishers の接続**が追加で必要です。

---

## あと何が必要か（チェックリスト）

### 1. コードが揃っているか確認

- [ ] `main.py` にエントリーポイントがある
- [ ] `config/settings.py` で `opus_model` / `sonnet_model` と環境変数を読んでいる
- [ ] `src/orchestrator.py` が存在し、6フェーズを実行する
- [ ] `src/agents/` 配下に `base_agent.py`, `lead_agent.py`, `qa_agent.py`, `workers/` がある
- [ ] `requirements.txt` に anthropic, openpyxl, Pillow, requests, beautifulsoup4 等がある

足りないファイルがあれば、`docs/explanation.md` の設計に沿って再実装する必要があります。

### 2. 環境構築（必須）

- [ ] Python 3.10+ を用意
- [ ] プロジェクト直下で `python -m venv .venv` して仮想環境作成
- [ ] `.venv` を有効化して `pip install -r requirements.txt`
- [ ] `.env.example` をコピーして `.env` を作成

### 3. APIキー（必須: Anthropic / 投稿時: X・Instagram）

- [ ] **ANTHROPIC_API_KEY** を取得して `.env` に記載（必須。Lead/QA/Workers が Claude を呼ぶため）
- [ ] X に投稿する場合: X Developer でアプリ作成し、`.env` に API Key / Secret / Access Token 等を設定
- [ ] Instagram に投稿する場合: `.env` に INSTAGRAM_USERNAME / INSTAGRAM_PASSWORD を設定（instagrapi 利用）

### 4. 動作確認

- [ ] `python main.py` を実行してエラーが出ないか確認
- [ ] `data/output/` に Excel や `run_result_*.json` が出力されるか確認
- [ ] `data/images/` に画像が生成されるか確認
- [ ] ログで Lead → Researcher → … → QA の順に処理されているか確認

### 5. 投稿まで使う場合（オプション）

- [ ] `src/publishers/`（x_publisher, instagram_publisher）が Orchestrator または main から呼ばれるように接続
- [ ] 投稿はレート制限に注意し、テスト用アカウントで先に試す

### 6. 運用・改善（任意）

- [ ] スケジューラー（例: schedule / cron）で定期実行
- [ ] エラーハンドリング・リトライの強化
- [ ] 各エージェントの単体テスト追加

---

## 進捗サマリー（日付別）

### 2026-02-24

- プロジェクト初期セットアップ（Git, .gitignore, ディレクトリ, スケルトン）
- CLAUDE.md にワークフロー・タスク管理・コア原則を追加
- Agent Team アーキテクチャ設計・実装（Lead / QA: Opus、Workers: Sonnet）
- progress.md 作成・「使えるか / あと何が必要か」を整理
