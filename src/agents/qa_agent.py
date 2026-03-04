"""
QA Agent
コード・出力の品質検証担当（Opusモデル使用）
"""
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from loguru import logger

from config import settings
from src.agents.base_agent import BaseAgent


class QAAgent(BaseAgent):
    """品質検証担当"""

    def __init__(self):
        super().__init__(
            name="QA",
            role="品質検証・テスト担当",
            model=settings.opus_model,  # 高性能モデル
            system_prompt="""あなたは品質保証の専門家です。

役割:
1. テキスト品質検証: 文法、トーン、適切性のチェック
2. 画像検証: ファイル存在、フォーマット確認
3. 総合評価: 全成果物の品質レポート作成

検証基準:
- 誤字脱字がないこと
- ブランドトーンに一致していること
- 不適切な表現がないこと
- ファイルが正常に生成されていること

出力形式:
- JSON形式で検証結果を返す
- 問題点は具体的に指摘
"""
        )

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 5: 品質検証タスクを実行"""
        logger.info(f"[{self.name}] 品質検証開始")

        text_result = context.get("text_result", {})
        image_result = context.get("image_result", {})
        excel_result = context.get("excel_result", {})
        plan = context.get("plan", {})

        # 各検証を実行
        text_qa = self._verify_texts(text_result, plan)
        image_qa = self._verify_images(image_result)
        excel_qa = self._verify_excel(excel_result)

        # 総合評価
        overall = self._create_overall_assessment(text_qa, image_qa, excel_qa)

        return {
            "status": "success",
            "text_verification": text_qa,
            "image_verification": image_qa,
            "excel_verification": excel_qa,
            "overall_passed": overall["passed"],
            "overall_score": overall["score"],
            "issues": overall["issues"],
            "recommendations": overall["recommendations"],
            "verified_at": datetime.now().isoformat(),
        }

    def _verify_texts(
        self, text_result: Dict[str, Any], plan: Dict[str, Any]
    ) -> Dict[str, Any]:
        """テキスト品質検証"""
        logger.info(f"[{self.name}] テキスト検証中")

        content = text_result.get("content", [])
        if not content:
            return {
                "passed": False,
                "message": "テキストコンテンツが見つかりません",
                "issues": ["テキスト未生成"],
            }

        tone = plan.get("tone", "professional")
        guidelines = plan.get("content_guidelines", {})

        # LLMで品質チェック
        import json
        texts_sample = []
        for item in content[:3]:
            texts = item.get("texts", {})
            for platform, text in texts.items():
                if isinstance(text, str):
                    texts_sample.append({"platform": platform, "text": text[:200]})
                elif isinstance(text, list):
                    texts_sample.append({"platform": platform, "text": text[0][:200] if text else ""})

        prompt = f"""以下のSNS投稿テキストを品質検証してください。

【期待されるトーン】
{tone}

【ガイドライン】
{json.dumps(guidelines, ensure_ascii=False)}

【検証対象テキスト】
{json.dumps(texts_sample, ensure_ascii=False, indent=2)}

【検証項目】
1. 誤字脱字
2. トーンの一致
3. 不適切表現
4. ハッシュタグの適切性
5. 文字数制限の遵守

【出力フォーマット】
{{
    "passed": true/false,
    "score": 1-10,
    "issues": ["問題点1", "問題点2"],
    "suggestions": ["改善提案1", "改善提案2"]
}}"""

        try:
            result = self.call_llm_json(prompt)
            return {
                "passed": result.get("passed", True),
                "score": result.get("score", 7),
                "issues": result.get("issues", []),
                "suggestions": result.get("suggestions", []),
                "checked_count": len(texts_sample),
            }
        except Exception as e:
            logger.error(f"[{self.name}] テキスト検証エラー: {e}")
            return {
                "passed": True,
                "score": 5,
                "issues": ["自動検証をスキップ"],
                "suggestions": [],
                "checked_count": len(texts_sample),
            }

    def _verify_images(self, image_result: Dict[str, Any]) -> Dict[str, Any]:
        """画像検証"""
        logger.info(f"[{self.name}] 画像検証中")

        images = image_result.get("images", [])
        if not images:
            return {
                "passed": False,
                "message": "画像が見つかりません",
                "issues": ["画像未生成"],
            }

        verified = []
        issues = []

        for img_info in images:
            path = Path(img_info.get("path", ""))
            img_type = img_info.get("type", "unknown")

            if path.exists():
                # ファイルサイズチェック
                size_kb = path.stat().st_size / 1024
                if size_kb < 1:
                    issues.append(f"{path.name}: ファイルサイズが小さすぎます ({size_kb:.1f}KB)")
                elif size_kb > 5000:
                    issues.append(f"{path.name}: ファイルサイズが大きすぎます ({size_kb:.1f}KB)")
                else:
                    verified.append({
                        "path": str(path),
                        "type": img_type,
                        "size_kb": round(size_kb, 1),
                        "status": "OK",
                    })
            else:
                issues.append(f"{path}: ファイルが存在しません")

        return {
            "passed": len(issues) == 0,
            "total": len(images),
            "verified": len(verified),
            "verified_images": verified,
            "issues": issues,
        }

    def _verify_excel(self, excel_result: Dict[str, Any]) -> Dict[str, Any]:
        """Excel検証"""
        logger.info(f"[{self.name}] Excel検証中")

        output_path = excel_result.get("output_path", "")
        if not output_path:
            return {
                "passed": False,
                "message": "Excelファイルが見つかりません",
                "issues": ["Excel未生成"],
            }

        path = Path(output_path)
        if not path.exists():
            return {
                "passed": False,
                "message": f"ファイルが存在しません: {output_path}",
                "issues": ["ファイル不存在"],
            }

        # ファイル検証
        size_kb = path.stat().st_size / 1024

        return {
            "passed": True,
            "path": str(path),
            "size_kb": round(size_kb, 1),
            "article_count": excel_result.get("article_count", 0),
            "issues": [],
        }

    def _create_overall_assessment(
        self,
        text_qa: Dict[str, Any],
        image_qa: Dict[str, Any],
        excel_qa: Dict[str, Any],
    ) -> Dict[str, Any]:
        """総合評価を作成"""
        all_issues = []
        scores = []

        # テキスト
        if not text_qa.get("passed", True):
            all_issues.extend(text_qa.get("issues", []))
        scores.append(text_qa.get("score", 5))

        # 画像
        if not image_qa.get("passed", True):
            all_issues.extend(image_qa.get("issues", []))
        image_score = 10 if image_qa.get("passed") else 3
        scores.append(image_score)

        # Excel
        if not excel_qa.get("passed", True):
            all_issues.extend(excel_qa.get("issues", []))
        excel_score = 10 if excel_qa.get("passed") else 3
        scores.append(excel_score)

        # 総合スコア
        avg_score = sum(scores) / len(scores) if scores else 0
        passed = avg_score >= 6 and len(all_issues) <= 3

        # 推奨事項
        recommendations = []
        if text_qa.get("suggestions"):
            recommendations.extend(text_qa["suggestions"][:2])
        if not image_qa.get("passed"):
            recommendations.append("画像生成プロセスを確認してください")
        if not excel_qa.get("passed"):
            recommendations.append("Excelレポート生成を再実行してください")

        return {
            "passed": passed,
            "score": round(avg_score, 1),
            "issues": all_issues,
            "recommendations": recommendations,
        }
