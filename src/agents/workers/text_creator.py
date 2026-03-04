"""
TextCreator Worker
X/Instagram用テキストコンテンツを生成
"""
from datetime import datetime
from typing import Any, Dict, List

from loguru import logger

from config import settings
from src.agents.base_agent import BaseAgent


class TextCreator(BaseAgent):
    """SNS投稿テキスト生成 Worker"""

    # プラットフォーム別の文字数制限
    CHAR_LIMITS = {
        "x_post": 280,  # X (Twitter) 1ポスト
        "x_thread": 280,  # X スレッド各投稿
        "instagram_caption": 2200,  # Instagram キャプション
        "instagram_story": 100,  # ストーリー用短文
    }

    def __init__(self):
        super().__init__(
            name="TextCreator",
            role="SNS投稿テキスト生成担当",
            model=settings.sonnet_model,
            system_prompt="""あなたはSNSマーケティングの専門家です。

役割:
- 記事内容を元にSNS投稿テキストを作成
- プラットフォームに最適化した文章を生成
- エンゲージメントを高める表現を使用

スタイルガイド:
- 日本語で自然な文章
- 絵文字は適度に使用（1-3個）
- ハッシュタグは関連性の高いものを3-5個
- CTAを含める
"""
        )

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """テキスト生成タスクを実行"""
        logger.info(f"[{self.name}] テキスト生成開始")

        articles = context.get("selected_articles", context.get("articles", []))
        platforms = context.get("platforms", ["x_post", "instagram_caption"])
        tone = context.get("tone", "professional")

        if not articles:
            return {
                "status": "error",
                "message": "テキスト生成対象の記事がありません",
            }

        generated_texts = []

        for article in articles[:5]:  # 最大5記事分
            article_texts = self._generate_texts_for_article(article, platforms, tone)
            generated_texts.append({
                "article_title": article.get("original_title", article.get("title", "")),
                "texts": article_texts,
            })

        return {
            "status": "success",
            "content": generated_texts,
            "total_articles": len(generated_texts),
            "created_at": datetime.now().isoformat(),
        }

    def _generate_texts_for_article(
        self,
        article: Dict[str, Any],
        platforms: List[str],
        tone: str,
    ) -> Dict[str, Any]:
        """1記事に対して各プラットフォーム用テキストを生成"""
        title = article.get("original_title", article.get("title", ""))
        category = article.get("category", "マーケティング")
        summary = article.get("summary_ja", "")
        url = article.get("url", "")

        texts = {}

        for platform in platforms:
            char_limit = self.CHAR_LIMITS.get(platform, 280)
            text = self._generate_platform_text(
                title, category, summary, url, platform, tone, char_limit
            )
            texts[platform] = text

        # X用スレッドも生成（オプション）
        if "x_thread" in platforms or "x_post" in platforms:
            thread = self._generate_x_thread(title, category, summary, url, tone)
            texts["x_thread"] = thread

        return texts

    def _generate_platform_text(
        self,
        title: str,
        category: str,
        summary: str,
        url: str,
        platform: str,
        tone: str,
        char_limit: int,
    ) -> str:
        """プラットフォーム別テキストを生成"""
        platform_guides = {
            "x_post": "X（Twitter）用: 簡潔で目を引く内容。280文字以内。",
            "instagram_caption": "Instagram用: ストーリー性のある内容。ハッシュタグ多め。",
            "instagram_story": "ストーリー用: 超短文でインパクト重視。",
        }

        prompt = f"""以下の情報を元に、{platform}用の投稿テキストを作成してください。

【元記事情報】
タイトル: {title}
カテゴリ: {category}
要約: {summary}
URL: {url}

【プラットフォームガイド】
{platform_guides.get(platform, "SNS投稿用テキストを作成")}

【トーン】
{tone}（professional: ビジネス向け / casual: カジュアル / bold: 大胆）

【制限】
- 文字数: {char_limit}文字以内
- ハッシュタグ: 3-5個を末尾に
- 絵文字: 1-3個を適切に配置

投稿テキストのみを出力してください（説明不要）。"""

        try:
            text = self.call_llm(prompt, max_tokens=500, temperature=0.8)
            # 文字数チェック
            if len(text) > char_limit:
                text = text[:char_limit - 3] + "..."
            return text.strip()
        except Exception as e:
            logger.error(f"[{self.name}] テキスト生成エラー: {e}")
            return self._fallback_text(title, category, url, char_limit)

    def _generate_x_thread(
        self,
        title: str,
        category: str,
        summary: str,
        url: str,
        tone: str,
    ) -> List[str]:
        """X用スレッドを生成"""
        prompt = f"""以下の情報を元に、X（Twitter）用のスレッド投稿（3-5ツイート）を作成してください。

【元記事情報】
タイトル: {title}
カテゴリ: {category}
要約: {summary}
URL: {url}

【フォーマット】
- 1ツイート目: フック（興味を引く導入）
- 2-4ツイート目: 本文（ポイントを解説）
- 最終ツイート: CTA + URL + ハッシュタグ

【制限】
- 各ツイート280文字以内
- スレッド番号（1/5 など）を先頭に

JSON配列形式で出力してください:
["ツイート1", "ツイート2", ...]"""

        try:
            result = self.call_llm_json(prompt)
            if isinstance(result, list):
                return [str(t) for t in result[:5]]
            return [self._fallback_text(title, category, url, 280)]
        except Exception as e:
            logger.error(f"[{self.name}] スレッド生成エラー: {e}")
            return [self._fallback_text(title, category, url, 280)]

    def _fallback_text(
        self, title: str, category: str, url: str, char_limit: int
    ) -> str:
        """フォールバックテキスト"""
        hashtags = f"#{category} #マーケティング #ビジネス"
        base = f"【{category}】{title}\n\n詳細はこちら: {url}\n\n{hashtags}"
        if len(base) > char_limit:
            base = base[:char_limit - 3] + "..."
        return base
