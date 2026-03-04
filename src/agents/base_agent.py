"""
エージェント共通基底クラス
全エージェントで共有するAnthropic API呼び出しロジック
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from anthropic import Anthropic
from loguru import logger

from config import settings


class BaseAgent(ABC):
    """全エージェントの基底クラス"""

    def __init__(
        self,
        name: str,
        role: str,
        model: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ):
        self.name = name
        self.role = role
        self.model = model or settings.sonnet_model
        self.system_prompt = system_prompt or self._default_system_prompt()
        self._client: Optional[Anthropic] = None

    @property
    def client(self) -> Anthropic:
        """Anthropicクライアントの遅延初期化"""
        if self._client is None:
            self._client = Anthropic(api_key=settings.anthropic_api_key)
        return self._client

    def _default_system_prompt(self) -> str:
        """デフォルトのシステムプロンプト"""
        return f"""あなたは{self.name}です。役割: {self.role}

以下のガイドラインに従ってください:
- 日本語で応答してください
- 簡潔かつ正確に回答してください
- JSON形式での出力が求められた場合は、有効なJSONのみを返してください
"""

    def call_llm(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """LLMを呼び出してレスポンスを取得"""
        logger.info(f"[{self.name}] LLM呼び出し開始")
        logger.debug(f"[{self.name}] プロンプト: {prompt[:100]}...")

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=self.system_prompt,
                messages=[{"role": "user", "content": prompt}],
            )
            result = response.content[0].text
            logger.info(f"[{self.name}] LLM呼び出し完了")
            logger.debug(f"[{self.name}] レスポンス: {result[:100]}...")
            return result
        except Exception as e:
            logger.error(f"[{self.name}] LLM呼び出しエラー: {e}")
            raise

    def call_llm_json(
        self,
        prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> Dict[str, Any]:
        """LLMを呼び出してJSON形式のレスポンスを取得"""
        import json

        json_prompt = f"""{prompt}

重要: 必ず有効なJSON形式で応答してください。説明文は不要です。"""

        result = self.call_llm(json_prompt, max_tokens, temperature)

        # JSON部分を抽出（コードブロックで囲まれている場合に対応）
        if "```json" in result:
            result = result.split("```json")[1].split("```")[0]
        elif "```" in result:
            result = result.split("```")[1].split("```")[0]

        try:
            return json.loads(result.strip())
        except json.JSONDecodeError as e:
            logger.error(f"[{self.name}] JSON解析エラー: {e}")
            logger.error(f"[{self.name}] 生のレスポンス: {result}")
            raise

    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """エージェントのメインタスクを実行"""
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name}, model={self.model})"
