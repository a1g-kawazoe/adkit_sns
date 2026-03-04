"""
Orchestrator
6フェーズのワークフロー制御
"""
import json
import shutil
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from config import settings
from src.agents.lead_agent import LeadAgent
from src.agents.qa_agent import QAAgent
from src.agents.workers.excel_reporter import ExcelReporter
from src.agents.workers.image_creator import ImageCreator
from src.agents.workers.researcher import Researcher
from src.agents.workers.text_creator import TextCreator


class Orchestrator:
    """6フェーズのワークフローを制御"""

    def __init__(self):
        # エージェントを初期化
        self.lead = LeadAgent()
        self.qa = QAAgent()
        self.researcher = Researcher()
        self.excel_reporter = ExcelReporter()
        self.image_creator = ImageCreator()
        self.text_creator = TextCreator()

        # 実行結果を保存
        self.results: Dict[str, Any] = {}
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    def run(
        self,
        theme: str = "デジタルマーケティング最新トレンド",
        target_audience: str = "マーケティング担当者",
        target_urls: Optional[list] = None,
    ) -> Dict[str, Any]:
        """ワークフローを実行"""
        self.start_time = datetime.now()
        logger.info("=" * 60)
        logger.info("Orchestrator: ワークフロー開始")
        logger.info(f"テーマ: {theme}")
        logger.info(f"ターゲット: {target_audience}")
        logger.info("=" * 60)

        try:
            # Phase 1: Lead → 計画策定
            self._phase_1_planning(theme, target_audience)

            # Phase 2: Researcher → Web情報収集
            self._phase_2_research(target_urls)

            # Phase 3: Lead → リサーチレビュー & 選定
            self._phase_3_review()

            # Phase 4: Workers → 並列作業
            self._phase_4_parallel_work()

            # Phase 5: QA → 品質検証
            self._phase_5_qa()

            # Phase 6: Lead → 最終統合レポート
            self._phase_6_final_report()

            self.end_time = datetime.now()
            self._save_run_result()

            # 画像をデスクトップにエクスポート
            if settings.export_to_desktop:
                self._export_images_to_desktop()

            return {
                "status": "success",
                "results": self.results,
                "duration_seconds": (self.end_time - self.start_time).total_seconds(),
            }

        except Exception as e:
            logger.error(f"Orchestrator: エラー発生 - {e}")
            self.end_time = datetime.now()
            return {
                "status": "error",
                "error": str(e),
                "partial_results": self.results,
            }

    def _phase_1_planning(self, theme: str, target_audience: str) -> None:
        """Phase 1: 計画策定"""
        logger.info("-" * 40)
        logger.info("Phase 1: 計画策定")
        logger.info("-" * 40)

        context = {
            "phase": "planning",
            "user_input": {
                "theme": theme,
                "target_audience": target_audience,
            },
        }

        result = self.lead.execute(context)
        self.results["plan"] = result

        logger.info(f"Phase 1 完了: テーマ={result.get('theme')}")
        logger.info(f"  優先カテゴリ: {result.get('priority_categories')}")
        logger.info(f"  トーン: {result.get('tone')}")

    def _phase_2_research(self, target_urls: Optional[list] = None) -> None:
        """Phase 2: Web情報収集"""
        logger.info("-" * 40)
        logger.info("Phase 2: Web情報収集")
        logger.info("-" * 40)

        plan = self.results.get("plan", {})
        context = {
            "theme": plan.get("theme", "マーケティング"),
            "target_urls": target_urls or settings.default_target_urls,
            "max_articles": settings.max_articles_per_source,
        }

        result = self.researcher.execute(context)
        self.results["research"] = result

        logger.info(f"Phase 2 完了: {result.get('total_articles', 0)}件の記事を収集")

    def _phase_3_review(self) -> None:
        """Phase 3: リサーチレビュー & 選定"""
        logger.info("-" * 40)
        logger.info("Phase 3: リサーチレビュー")
        logger.info("-" * 40)

        research = self.results.get("research", {})
        plan = self.results.get("plan", {})

        context = {
            "phase": "review",
            "articles": research.get("articles", []),
            "plan": plan,
        }

        result = self.lead.execute(context)
        self.results["review"] = result

        logger.info(f"Phase 3 完了: {result.get('selected_count', 0)}件を選定")
        if result.get("rationale"):
            logger.info(f"  選定理由: {result['rationale'][:100]}...")

    def _phase_4_parallel_work(self) -> None:
        """Phase 4: Workers 並列作業"""
        logger.info("-" * 40)
        logger.info("Phase 4: 並列作業（Excel / 画像 / テキスト）")
        logger.info("-" * 40)

        review = self.results.get("review", {})
        plan = self.results.get("plan", {})
        selected_articles = review.get("selected_articles", [])

        if not selected_articles:
            logger.warning("選定された記事がありません。Phase 4 をスキップします。")
            self.results["excel"] = {"status": "skipped"}
            self.results["images"] = {"status": "skipped"}
            self.results["texts"] = {"status": "skipped"}
            return

        # 共通コンテキスト
        base_context = {
            "selected_articles": selected_articles,
            "articles": selected_articles,
            "theme": plan.get("theme", "マーケティング"),
            "tone": plan.get("tone", "professional"),
        }

        # 並列実行
        with ThreadPoolExecutor(max_workers=3) as executor:
            # Excel
            excel_future = executor.submit(
                self.excel_reporter.execute, base_context.copy()
            )
            # 画像
            image_context = base_context.copy()
            image_context["image_types"] = ["x_post", "instagram_square"]
            image_future = executor.submit(
                self.image_creator.execute, image_context
            )
            # テキスト
            text_context = base_context.copy()
            text_context["platforms"] = ["x_post", "instagram_caption"]
            text_future = executor.submit(
                self.text_creator.execute, text_context
            )

            # 結果を取得
            self.results["excel"] = excel_future.result()
            self.results["images"] = image_future.result()
            self.results["texts"] = text_future.result()

        logger.info(f"Phase 4 完了:")
        logger.info(f"  Excel: {self.results['excel'].get('output_path', 'N/A')}")
        logger.info(f"  画像: {self.results['images'].get('total_count', 0)}枚")
        logger.info(f"  テキスト: {self.results['texts'].get('total_articles', 0)}件")

    def _phase_5_qa(self) -> None:
        """Phase 5: 品質検証"""
        logger.info("-" * 40)
        logger.info("Phase 5: 品質検証")
        logger.info("-" * 40)

        context = {
            "text_result": self.results.get("texts", {}),
            "image_result": self.results.get("images", {}),
            "excel_result": self.results.get("excel", {}),
            "plan": self.results.get("plan", {}),
        }

        result = self.qa.execute(context)
        self.results["qa"] = result

        logger.info(f"Phase 5 完了:")
        logger.info(f"  総合評価: {'合格' if result.get('overall_passed') else '要改善'}")
        logger.info(f"  スコア: {result.get('overall_score', 0)}/10")
        if result.get("issues"):
            logger.warning(f"  問題点: {result['issues'][:3]}")

    def _phase_6_final_report(self) -> None:
        """Phase 6: 最終統合レポート"""
        logger.info("-" * 40)
        logger.info("Phase 6: 最終統合レポート")
        logger.info("-" * 40)

        context = {
            "phase": "final",
            "plan": self.results.get("plan", {}),
            "research_result": self.results.get("research", {}),
            "review_result": self.results.get("review", {}),
            "excel_result": self.results.get("excel", {}),
            "image_result": self.results.get("images", {}),
            "text_result": self.results.get("texts", {}),
            "qa_result": self.results.get("qa", {}),
        }

        result = self.lead.execute(context)
        self.results["final_report"] = result

        logger.info("Phase 6 完了:")
        logger.info(f"  サマリー: {result.get('executive_summary', '')[:100]}")

    def _save_run_result(self) -> None:
        """実行結果をJSONファイルに保存"""
        settings.ensure_directories()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = settings.output_dir / f"run_result_{timestamp}.json"

        # シリアライズ可能な形式に変換
        serializable_results = self._make_serializable(self.results)

        run_data = {
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": (
                (self.end_time - self.start_time).total_seconds()
                if self.start_time and self.end_time
                else None
            ),
            "results": serializable_results,
        }

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(run_data, f, ensure_ascii=False, indent=2)

        logger.info(f"実行結果を保存: {output_path}")

    def _export_images_to_desktop(self) -> List[Path]:
        """生成した画像をデスクトップにコピー"""
        logger.info("-" * 40)
        logger.info("画像をデスクトップにエクスポート")
        logger.info("-" * 40)

        images_result = self.results.get("images", {})
        images = images_result.get("images", [])

        if not images:
            logger.warning("エクスポートする画像がありません")
            return []

        # デスクトップの出力ディレクトリを作成
        desktop_dir = settings.desktop_output_dir
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_dir = desktop_dir / timestamp
        export_dir.mkdir(parents=True, exist_ok=True)

        exported_files = []
        for img_info in images:
            src_path = Path(img_info.get("path", ""))
            if src_path.exists():
                dst_path = export_dir / src_path.name
                shutil.copy2(src_path, dst_path)
                exported_files.append(dst_path)
                logger.debug(f"コピー: {src_path.name}")

        # Excelレポートもコピー
        excel_result = self.results.get("excel", {})
        excel_path = excel_result.get("output_path", "")
        if excel_path:
            src_excel = Path(excel_path)
            if src_excel.exists():
                dst_excel = export_dir / src_excel.name
                shutil.copy2(src_excel, dst_excel)
                exported_files.append(dst_excel)
                logger.debug(f"コピー: {src_excel.name}")

        logger.info(f"デスクトップにエクスポート完了: {export_dir}")
        logger.info(f"  ファイル数: {len(exported_files)}")

        # 結果に追記
        self.results["export"] = {
            "destination": str(export_dir),
            "files_count": len(exported_files),
        }

        return exported_files

    def _make_serializable(self, obj: Any) -> Any:
        """オブジェクトをJSON シリアライズ可能な形式に変換"""
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        elif isinstance(obj, Path):
            return str(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, "__dict__"):
            return str(obj)
        else:
            return obj

    def get_summary(self) -> Dict[str, Any]:
        """実行結果のサマリーを取得"""
        final = self.results.get("final_report", {})
        qa = self.results.get("qa", {})

        return {
            "theme": self.results.get("plan", {}).get("theme", ""),
            "total_researched": self.results.get("research", {}).get("total_articles", 0),
            "selected_count": self.results.get("review", {}).get("selected_count", 0),
            "excel_path": self.results.get("excel", {}).get("output_path", ""),
            "images_count": self.results.get("images", {}).get("total_count", 0),
            "texts_count": self.results.get("texts", {}).get("total_articles", 0),
            "qa_passed": qa.get("overall_passed", False),
            "qa_score": qa.get("overall_score", 0),
            "executive_summary": final.get("executive_summary", ""),
        }
