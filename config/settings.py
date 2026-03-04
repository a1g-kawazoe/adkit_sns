"""
設定管理モジュール
環境変数とモデル設定をpydanticで型安全に管理
"""
from pathlib import Path
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """アプリケーション設定"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # === Anthropic API ===
    anthropic_api_key: str = Field(default="", description="Anthropic API Key")
    opus_model: str = Field(
        default="claude-sonnet-4-20250514",
        description="Lead/QA用モデル（高性能）"
    )
    sonnet_model: str = Field(
        default="claude-sonnet-4-20250514",
        description="Worker用モデル（標準）"
    )

    # === X (Twitter) API ===
    x_api_key: str = Field(default="", description="X API Key")
    x_api_secret: str = Field(default="", description="X API Secret")
    x_access_token: str = Field(default="", description="X Access Token")
    x_access_token_secret: str = Field(default="", description="X Access Token Secret")
    x_bearer_token: str = Field(default="", description="X Bearer Token")

    # === Instagram API ===
    instagram_username: str = Field(default="", description="Instagram Username")
    instagram_password: str = Field(default="", description="Instagram Password")

    # === Directories ===
    base_dir: Path = Field(default=Path(__file__).parent.parent, description="プロジェクトルート")

    @property
    def data_dir(self) -> Path:
        return self.base_dir / "data"

    @property
    def output_dir(self) -> Path:
        return self.data_dir / "output"

    @property
    def images_dir(self) -> Path:
        return self.data_dir / "images"

    @property
    def cache_dir(self) -> Path:
        return self.data_dir / "cache"

    @property
    def logs_dir(self) -> Path:
        return self.base_dir / "logs"

    @property
    def desktop_output_dir(self) -> Path:
        """デスクトップの出力ディレクトリ"""
        return Path.home() / "Desktop" / "adkit_images"

    # === Output Settings ===
    export_to_desktop: bool = Field(
        default=True,
        description="生成画像をデスクトップにコピーするか"
    )

    # === Web Scraping Targets ===
    default_target_urls: List[str] = Field(
        default=[
            "https://blog.hubspot.com/marketing",
            "https://neilpatel.com/blog/",
            "https://contentmarketinginstitute.com/articles/",
            "https://www.socialmediaexaminer.com/",
        ],
        description="デフォルトの情報収集先URL"
    )

    # === Content Settings ===
    max_articles_per_source: int = Field(default=5, description="ソースあたりの最大記事数")
    content_language: str = Field(default="ja", description="生成コンテンツの言語")

    def ensure_directories(self) -> None:
        """必要なディレクトリを作成"""
        for dir_path in [self.output_dir, self.images_dir, self.cache_dir, self.logs_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)


# シングルトンインスタンス
settings = Settings()
