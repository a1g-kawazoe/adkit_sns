"""
Researcher Worker
Web情報リサーチ & カテゴライズを担当
"""
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from loguru import logger

from config import settings
from src.agents.base_agent import BaseAgent


class Researcher(BaseAgent):
    """Web情報リサーチ & カテゴライズ Worker"""

    def __init__(self):
        super().__init__(
            name="Researcher",
            role="Web情報リサーチ & カテゴライズ担当",
            model=settings.sonnet_model,
            system_prompt="""あなたはWebマーケティングリサーチの専門家です。

役割:
- 海外マーケティングサイトから最新情報を収集
- 記事をカテゴリ別に分類
- 日本市場向けの価値を評価

出力形式:
- 常にJSON形式で応答
- 日本語で要約を作成
"""
        )
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """リサーチタスクを実行"""
        logger.info(f"[{self.name}] リサーチ開始")

        theme = context.get("theme", "デジタルマーケティング")
        target_urls = context.get("target_urls", settings.default_target_urls)
        max_articles = context.get("max_articles", settings.max_articles_per_source)

        # Step 1: Web記事を収集
        raw_articles = self._scrape_articles(target_urls, max_articles)
        logger.info(f"[{self.name}] 収集記事数: {len(raw_articles)}")

        if not raw_articles:
            return {
                "status": "error",
                "message": "記事を収集できませんでした",
                "articles": [],
            }

        # Step 2: LLMでカテゴライズ & 評価
        categorized = self._categorize_articles(raw_articles, theme)

        return {
            "status": "success",
            "theme": theme,
            "total_articles": len(categorized),
            "articles": categorized,
            "collected_at": datetime.now().isoformat(),
        }

    def _scrape_articles(
        self, urls: List[str], max_per_source: int
    ) -> List[Dict[str, str]]:
        """URLリストから記事を収集"""
        articles = []

        for url in urls:
            try:
                logger.debug(f"[{self.name}] スクレイピング: {url}")
                response = requests.get(url, headers=self.headers, timeout=10)
                response.raise_for_status()

                soup = BeautifulSoup(response.text, "html.parser")
                page_articles = self._extract_articles(soup, url, max_per_source)
                articles.extend(page_articles)
                logger.info(f"[{self.name}] {url} から {len(page_articles)} 記事取得")

            except Exception as e:
                logger.warning(f"[{self.name}] {url} の取得失敗: {e}")
                continue

        return articles

    def _extract_articles(
        self, soup: BeautifulSoup, source_url: str, max_count: int
    ) -> List[Dict[str, str]]:
        """HTMLから記事情報を抽出"""
        articles = []

        # 一般的な記事セレクタを試行
        selectors = [
            "article",
            ".post",
            ".blog-post",
            ".entry",
            '[class*="article"]',
            '[class*="post"]',
        ]

        for selector in selectors:
            elements = soup.select(selector)
            if elements:
                break
        else:
            elements = []

        for element in elements[:max_count]:
            # タイトル抽出
            title_tag = element.find(["h1", "h2", "h3", "a"])
            title = title_tag.get_text(strip=True) if title_tag else ""

            # リンク抽出
            link_tag = element.find("a", href=True)
            link = link_tag["href"] if link_tag else ""
            if link and not link.startswith("http"):
                from urllib.parse import urljoin
                link = urljoin(source_url, link)

            # 概要抽出
            summary_tag = element.find(["p", ".excerpt", ".summary"])
            summary = summary_tag.get_text(strip=True)[:200] if summary_tag else ""

            if title:
                articles.append({
                    "title": title,
                    "url": link,
                    "summary": summary,
                    "source": source_url,
                })

        return articles

    def _categorize_articles(
        self, articles: List[Dict[str, str]], theme: str
    ) -> List[Dict[str, Any]]:
        """LLMで記事をカテゴライズ"""
        if not articles:
            return []

        articles_text = json.dumps(articles, ensure_ascii=False, indent=2)

        prompt = f"""以下の記事リストを分析し、カテゴライズしてください。

テーマ: {theme}

記事リスト:
{articles_text}

各記事に対して以下を判定してください:
1. category: カテゴリ（SEO, SNS, コンテンツマーケティング, 広告, その他）
2. relevance_score: テーマとの関連度（1-10）
3. japan_value: 日本市場での価値（高/中/低）
4. summary_ja: 日本語での要約（50文字以内）

JSON配列形式で出力してください。"""

        try:
            result = self.call_llm_json(prompt)
            if isinstance(result, list):
                # 元の記事情報とマージ
                for i, item in enumerate(result):
                    if i < len(articles):
                        item.update({
                            "original_title": articles[i].get("title", ""),
                            "url": articles[i].get("url", ""),
                            "source": articles[i].get("source", ""),
                        })
                return result
            return articles
        except Exception as e:
            logger.error(f"[{self.name}] カテゴライズエラー: {e}")
            # フォールバック: 元の記事にデフォルト値を追加
            for article in articles:
                article.update({
                    "category": "その他",
                    "relevance_score": 5,
                    "japan_value": "中",
                    "summary_ja": article.get("title", "")[:50],
                })
            return articles

    def _get_cache_path(self, url: str) -> Path:
        """キャッシュファイルパスを生成"""
        url_hash = hashlib.md5(url.encode()).hexdigest()[:10]
        return settings.cache_dir / f"research_{url_hash}.json"
