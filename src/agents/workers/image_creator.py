"""
ImageCreator Worker
SNS投稿用画像を生成
"""
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger
from PIL import Image, ImageDraw, ImageFont

from config import settings
from src.agents.base_agent import BaseAgent


class ImageCreator(BaseAgent):
    """SNS投稿用画像生成 Worker"""

    # 画像サイズ定義
    IMAGE_SIZES = {
        "x_post": (1200, 675),  # X (Twitter) 投稿画像
        "x_header": (1500, 500),  # X ヘッダー
        "instagram_square": (1080, 1080),  # Instagram スクエア
        "instagram_portrait": (1080, 1350),  # Instagram ポートレート
        "instagram_story": (1080, 1920),  # Instagram ストーリー
    }

    # カラーパレット
    COLORS = {
        "primary": "#1DA1F2",  # Twitter Blue
        "secondary": "#14171A",
        "accent": "#FF6B6B",
        "background": "#FFFFFF",
        "text": "#14171A",
        "text_light": "#657786",
    }

    def __init__(self):
        super().__init__(
            name="ImageCreator",
            role="SNS投稿用画像クリエイティブ生成担当",
            model=settings.sonnet_model,
            system_prompt="""あなたは画像デザインの専門家です。

役割:
- SNS投稿に最適な画像デザインを提案
- テキスト配置とカラースキームを決定

出力形式:
- JSON形式でデザイン指示を返す
"""
        )

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """画像生成タスクを実行"""
        logger.info(f"[{self.name}] 画像生成開始")

        articles = context.get("selected_articles", context.get("articles", []))
        theme = context.get("theme", "マーケティング")
        image_types = context.get("image_types", ["x_post", "instagram_square"])

        if not articles:
            return {
                "status": "error",
                "message": "画像生成対象の記事がありません",
            }

        settings.ensure_directories()
        generated_images = []

        for article in articles[:5]:  # 最大5記事分
            for img_type in image_types:
                try:
                    image_path = self._create_image(article, img_type, theme)
                    generated_images.append({
                        "path": str(image_path),
                        "type": img_type,
                        "article_title": article.get("original_title", article.get("title", "")),
                    })
                except Exception as e:
                    logger.error(f"[{self.name}] 画像生成エラー: {e}")

        return {
            "status": "success",
            "images": generated_images,
            "total_count": len(generated_images),
            "created_at": datetime.now().isoformat(),
        }

    def _create_image(
        self,
        article: Dict[str, Any],
        image_type: str,
        theme: str,
    ) -> Path:
        """1枚の画像を生成"""
        size = self.IMAGE_SIZES.get(image_type, (1200, 675))
        title = article.get("original_title", article.get("title", ""))[:60]
        category = article.get("category", theme)
        summary = article.get("summary_ja", "")[:80]

        # デザイン指示をLLMで生成
        design = self._get_design_suggestion(title, category, image_type)

        # 画像生成
        img = self._render_image(size, title, category, summary, design)

        # 保存
        filename = self._generate_filename(title, image_type)
        output_path = settings.images_dir / filename
        img.save(output_path, "PNG", quality=95)

        logger.info(f"[{self.name}] 画像保存: {output_path}")
        return output_path

    def _get_design_suggestion(
        self, title: str, category: str, image_type: str
    ) -> Dict[str, Any]:
        """LLMでデザイン提案を取得"""
        prompt = f"""以下の情報に基づいて、SNS画像のデザイン指示を作成してください。

タイトル: {title}
カテゴリ: {category}
画像タイプ: {image_type}

以下の形式で出力してください:
{{
    "background_color": "#HEXCODE",
    "accent_color": "#HEXCODE",
    "text_color": "#HEXCODE",
    "layout": "centered" | "left_aligned" | "overlay",
    "mood": "professional" | "casual" | "bold"
}}"""

        try:
            return self.call_llm_json(prompt)
        except Exception:
            # デフォルトデザイン
            return {
                "background_color": "#1A1A2E",
                "accent_color": "#E94560",
                "text_color": "#FFFFFF",
                "layout": "centered",
                "mood": "professional",
            }

    def _render_image(
        self,
        size: Tuple[int, int],
        title: str,
        category: str,
        summary: str,
        design: Dict[str, Any],
    ) -> Image.Image:
        """画像をレンダリング"""
        width, height = size

        # 背景色
        bg_color = design.get("background_color", "#1A1A2E")
        img = Image.new("RGB", size, bg_color)
        draw = ImageDraw.Draw(img)

        # アクセントバー
        accent_color = design.get("accent_color", "#E94560")
        bar_height = height // 15
        draw.rectangle([(0, 0), (width, bar_height)], fill=accent_color)

        # カテゴリラベル
        text_color = design.get("text_color", "#FFFFFF")
        try:
            # システムフォントを試行
            font_small = ImageFont.truetype("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc", 24)
            font_large = ImageFont.truetype("/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc", 48)
            font_medium = ImageFont.truetype("/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc", 28)
        except OSError:
            # フォールバック
            font_small = ImageFont.load_default()
            font_large = ImageFont.load_default()
            font_medium = ImageFont.load_default()

        # カテゴリ
        category_y = bar_height + 40
        draw.text((60, category_y), f"#{category}", fill=accent_color, font=font_small)

        # タイトル（折り返し処理）
        title_y = category_y + 60
        title_lines = self._wrap_text(title, font_large, width - 120)
        for i, line in enumerate(title_lines[:3]):
            draw.text((60, title_y + i * 60), line, fill=text_color, font=font_large)

        # サマリー
        summary_y = title_y + len(title_lines[:3]) * 60 + 40
        if summary:
            summary_lines = self._wrap_text(summary, font_medium, width - 120)
            for i, line in enumerate(summary_lines[:2]):
                draw.text(
                    (60, summary_y + i * 40),
                    line,
                    fill=self._adjust_color(text_color, -40),
                    font=font_medium,
                )

        # フッター
        footer_y = height - 60
        draw.text(
            (60, footer_y),
            "Generated by Adkit SNS",
            fill=self._adjust_color(text_color, -80),
            font=font_small,
        )

        return img

    def _wrap_text(
        self, text: str, font: ImageFont.FreeTypeFont, max_width: int
    ) -> List[str]:
        """テキストを指定幅で折り返し"""
        lines = []
        current_line = ""

        for char in text:
            test_line = current_line + char
            try:
                bbox = font.getbbox(test_line)
                line_width = bbox[2] - bbox[0]
            except AttributeError:
                line_width = len(test_line) * 20

            if line_width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = char

        if current_line:
            lines.append(current_line)

        return lines

    def _adjust_color(self, hex_color: str, amount: int) -> str:
        """色の明度を調整"""
        hex_color = hex_color.lstrip("#")
        r = max(0, min(255, int(hex_color[0:2], 16) + amount))
        g = max(0, min(255, int(hex_color[2:4], 16) + amount))
        b = max(0, min(255, int(hex_color[4:6], 16) + amount))
        return f"#{r:02x}{g:02x}{b:02x}"

    def _generate_filename(self, title: str, image_type: str) -> str:
        """ファイル名を生成"""
        title_hash = hashlib.md5(title.encode()).hexdigest()[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{image_type}_{title_hash}_{timestamp}.png"
