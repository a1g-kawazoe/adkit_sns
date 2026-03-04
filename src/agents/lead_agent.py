"""
Lead Agent
全体進行管理・ディレクション担当（Opusモデル使用）
"""
from datetime import datetime
from typing import Any, Dict, List

from loguru import logger

from config import settings
from src.agents.base_agent import BaseAgent


class LeadAgent(BaseAgent):
    """全体進行管理・ディレクション担当"""

    def __init__(self):
        super().__init__(
            name="Lead",
            role="全体進行管理・ディレクション",
            model=settings.opus_model,  # 高性能モデル
            system_prompt="""あなたはSNSマーケティングチームのリードです。

役割:
1. 計画策定: テーマ・優先カテゴリ・トーンの決定
2. リサーチレビュー: 収集された情報の評価と選定
3. 最終統合: 全成果物の統合レポート作成

責任:
- チーム全体の方向性を決定
- 品質基準を設定
- 最終成果物の承認

出力形式:
- JSON形式で指示・評価を返す
- 明確で実行可能な指示を出す
"""
        )

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """メインタスク実行（フェーズに応じて分岐）"""
        phase = context.get("phase", "planning")

        if phase == "planning":
            return self.create_plan(context)
        elif phase == "review":
            return self.review_research(context)
        elif phase == "final":
            return self.create_final_report(context)
        else:
            logger.warning(f"[{self.name}] 不明なフェーズ: {phase}")
            return {"status": "error", "message": f"Unknown phase: {phase}"}

    def create_plan(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 1: 計画策定"""
        logger.info(f"[{self.name}] 計画策定開始")

        user_input = context.get("user_input", {})
        theme = user_input.get("theme", "デジタルマーケティング最新トレンド")
        target_audience = user_input.get("target_audience", "マーケティング担当者")

        prompt = f"""以下の情報に基づいて、SNSコンテンツ制作の計画を策定してください。

【入力情報】
テーマ: {theme}
ターゲット: {target_audience}

【出力フォーマット】
{{
    "theme": "決定したテーマ",
    "priority_categories": ["優先カテゴリ1", "優先カテゴリ2", "優先カテゴリ3"],
    "tone": "professional" | "casual" | "bold",
    "content_guidelines": {{
        "key_messages": ["メッセージ1", "メッセージ2"],
        "avoid_topics": ["避けるトピック"],
        "hashtag_strategy": "ハッシュタグ戦略"
    }},
    "target_platforms": ["x", "instagram"],
    "quality_criteria": {{
        "min_relevance_score": 7,
        "required_japan_value": "中以上"
    }}
}}"""

        try:
            plan = self.call_llm_json(prompt)
            plan["status"] = "success"
            plan["created_at"] = datetime.now().isoformat()
            logger.info(f"[{self.name}] 計画策定完了")
            return plan
        except Exception as e:
            logger.error(f"[{self.name}] 計画策定エラー: {e}")
            return self._default_plan(theme)

    def review_research(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 3: リサーチ結果レビュー & 投稿対象選定"""
        logger.info(f"[{self.name}] リサーチレビュー開始")

        articles = context.get("articles", [])
        plan = context.get("plan", {})
        quality_criteria = plan.get("quality_criteria", {})

        if not articles:
            return {
                "status": "error",
                "message": "レビュー対象の記事がありません",
            }

        # 品質基準に基づいてフィルタリング
        min_score = quality_criteria.get("min_relevance_score", 6)
        required_value = quality_criteria.get("required_japan_value", "中")

        import json
        articles_json = json.dumps(articles[:20], ensure_ascii=False, indent=2)

        prompt = f"""以下のリサーチ結果をレビューし、投稿対象を選定してください。

【品質基準】
- 最低関連度スコア: {min_score}
- 必要な日本市場価値: {required_value}以上

【リサーチ結果】
{articles_json}

【出力フォーマット】
{{
    "selected_count": 選定数,
    "selected_indices": [選定した記事のインデックス],
    "selection_rationale": "選定理由",
    "improvement_suggestions": ["改善提案1", "改善提案2"]
}}"""

        try:
            review = self.call_llm_json(prompt)

            # 選定された記事を抽出
            selected_indices = review.get("selected_indices", [])
            selected_articles = [
                articles[i] for i in selected_indices if i < len(articles)
            ]

            return {
                "status": "success",
                "selected_articles": selected_articles,
                "selected_count": len(selected_articles),
                "rationale": review.get("selection_rationale", ""),
                "suggestions": review.get("improvement_suggestions", []),
                "reviewed_at": datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"[{self.name}] レビューエラー: {e}")
            # フォールバック: 上位記事を選定
            sorted_articles = sorted(
                articles,
                key=lambda x: x.get("relevance_score", 0),
                reverse=True,
            )
            return {
                "status": "success",
                "selected_articles": sorted_articles[:5],
                "selected_count": min(5, len(sorted_articles)),
                "rationale": "関連度スコア上位を自動選定",
                "suggestions": [],
            }

    def create_final_report(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Phase 6: 最終統合レポート作成"""
        logger.info(f"[{self.name}] 最終レポート作成開始")

        # 全フェーズの結果を収集
        plan = context.get("plan", {})
        research = context.get("research_result", {})
        review = context.get("review_result", {})
        excel_result = context.get("excel_result", {})
        image_result = context.get("image_result", {})
        text_result = context.get("text_result", {})
        qa_result = context.get("qa_result", {})

        import json

        summary_data = {
            "theme": plan.get("theme", ""),
            "total_researched": research.get("total_articles", 0),
            "selected_count": review.get("selected_count", 0),
            "excel_path": excel_result.get("output_path", ""),
            "images_count": image_result.get("total_count", 0),
            "texts_count": text_result.get("total_articles", 0),
            "qa_passed": qa_result.get("overall_passed", False),
        }

        prompt = f"""以下の成果を統合し、最終レポートサマリーを作成してください。

【成果サマリー】
{json.dumps(summary_data, ensure_ascii=False, indent=2)}

【出力フォーマット】
{{
    "executive_summary": "エグゼクティブサマリー（100文字）",
    "achievements": ["達成事項1", "達成事項2", "達成事項3"],
    "deliverables": {{
        "excel_report": "パス",
        "images": 枚数,
        "texts": 件数
    }},
    "next_steps": ["次のステップ1", "次のステップ2"],
    "overall_quality": "high" | "medium" | "low"
}}"""

        try:
            report = self.call_llm_json(prompt)
            report["status"] = "success"
            report["completed_at"] = datetime.now().isoformat()
            report["raw_results"] = {
                "plan": plan,
                "research": {"total": research.get("total_articles", 0)},
                "review": {"selected": review.get("selected_count", 0)},
                "excel": excel_result,
                "images": image_result,
                "texts": text_result,
                "qa": qa_result,
            }
            logger.info(f"[{self.name}] 最終レポート作成完了")
            return report
        except Exception as e:
            logger.error(f"[{self.name}] 最終レポートエラー: {e}")
            return {
                "status": "success",
                "executive_summary": "レポート生成完了",
                "raw_results": summary_data,
                "completed_at": datetime.now().isoformat(),
            }

    def _default_plan(self, theme: str) -> Dict[str, Any]:
        """デフォルトの計画"""
        return {
            "status": "success",
            "theme": theme,
            "priority_categories": ["SEO", "SNS", "コンテンツマーケティング"],
            "tone": "professional",
            "content_guidelines": {
                "key_messages": ["最新トレンドを日本市場向けに解説"],
                "avoid_topics": [],
                "hashtag_strategy": "カテゴリ名 + マーケティング関連タグ",
            },
            "target_platforms": ["x", "instagram"],
            "quality_criteria": {
                "min_relevance_score": 6,
                "required_japan_value": "中",
            },
            "created_at": datetime.now().isoformat(),
        }
