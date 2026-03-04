#!/usr/bin/env python3
"""
Adkit SNS - SNSマーケティング自動化ツール
エントリーポイント
"""
import argparse
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from loguru import logger

from config import settings
from src.orchestrator import Orchestrator


def setup_logging() -> None:
    """ロギングを設定"""
    settings.ensure_directories()

    # ログフォーマット
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    # コンソール出力
    logger.remove()
    logger.add(sys.stderr, format=log_format, level="INFO")

    # ファイル出力
    log_file = settings.logs_dir / "adkit_sns_{time:YYYY-MM-DD}.log"
    logger.add(
        log_file,
        format=log_format,
        level="DEBUG",
        rotation="1 day",
        retention="7 days",
        encoding="utf-8",
    )


def main() -> int:
    """メイン関数"""
    parser = argparse.ArgumentParser(
        description="Adkit SNS - SNSマーケティング自動化ツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
  python main.py
  python main.py --theme "AI活用マーケティング"
  python main.py --theme "SEO対策" --audience "Web担当者"
        """,
    )

    parser.add_argument(
        "--theme",
        type=str,
        default="デジタルマーケティング最新トレンド",
        help="リサーチテーマ（デフォルト: デジタルマーケティング最新トレンド）",
    )
    parser.add_argument(
        "--audience",
        type=str,
        default="マーケティング担当者",
        help="ターゲットオーディエンス（デフォルト: マーケティング担当者）",
    )
    parser.add_argument(
        "--urls",
        type=str,
        nargs="*",
        help="カスタム情報収集URL（スペース区切り）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="設定確認のみ実行（実際のAPI呼び出しなし）",
    )

    args = parser.parse_args()

    # ロギング設定
    setup_logging()

    logger.info("=" * 60)
    logger.info("Adkit SNS 開始")
    logger.info("=" * 60)

    # 設定確認
    if not settings.anthropic_api_key:
        logger.error("ANTHROPIC_API_KEY が設定されていません")
        logger.info("1. .env.example を .env にコピー")
        logger.info("2. .env に ANTHROPIC_API_KEY を設定")
        return 1

    if args.dry_run:
        logger.info("--- Dry Run モード ---")
        logger.info(f"テーマ: {args.theme}")
        logger.info(f"ターゲット: {args.audience}")
        logger.info(f"収集URL: {args.urls or settings.default_target_urls}")
        logger.info(f"Opusモデル: {settings.opus_model}")
        logger.info(f"Sonnetモデル: {settings.sonnet_model}")
        logger.info("設定OK。--dry-run を外して実行してください。")
        return 0

    # オーケストレーター実行
    orchestrator = Orchestrator()
    result = orchestrator.run(
        theme=args.theme,
        target_audience=args.audience,
        target_urls=args.urls,
    )

    # 結果表示
    if result["status"] == "success":
        logger.info("=" * 60)
        logger.info("実行完了")
        logger.info("=" * 60)

        summary = orchestrator.get_summary()
        logger.info(f"テーマ: {summary['theme']}")
        logger.info(f"収集記事数: {summary['total_researched']}")
        logger.info(f"選定記事数: {summary['selected_count']}")
        logger.info(f"生成画像数: {summary['images_count']}")
        logger.info(f"生成テキスト数: {summary['texts_count']}")
        logger.info(f"QA合格: {'Yes' if summary['qa_passed'] else 'No'}")
        logger.info(f"QAスコア: {summary['qa_score']}/10")

        if summary.get("excel_path"):
            logger.info(f"Excelレポート: {summary['excel_path']}")

        # デスクトップエクスポート情報
        export_info = orchestrator.results.get("export", {})
        if export_info.get("destination"):
            logger.info("=" * 60)
            logger.info(f"デスクトップに保存: {export_info['destination']}")
            logger.info(f"ファイル数: {export_info['files_count']}")

        logger.info(f"サマリー: {summary.get('executive_summary', '')[:100]}")

        return 0
    else:
        logger.error(f"実行失敗: {result.get('error', '不明なエラー')}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
