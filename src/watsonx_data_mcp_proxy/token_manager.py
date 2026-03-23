"""
IBM Cloud トークン管理モジュール
トークンの自動取得と更新を管理します。
"""
import asyncio
import time
from typing import Optional
import httpx
import logging

logger = logging.getLogger(__name__)


class TokenManager:
    """IBM Cloud APIキーからアクセストークンを管理するクラス"""
    
    def __init__(self, api_key: str, refresh_margin: int = 300):
        """
        Args:
            api_key: IBM Cloud APIキー
            refresh_margin: トークン期限切れ前の更新マージン（秒）デフォルト5分
        """
        self.api_key = api_key
        self.refresh_margin = refresh_margin
        self._token: Optional[str] = None
        self._expiration: Optional[int] = None
        self._refresh_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        
    async def get_token(self) -> str:
        """
        有効なアクセストークンを取得します。
        期限切れの場合は自動的に更新します。
        
        Returns:
            有効なアクセストークン
        """
        async with self._lock:
            if self._needs_refresh():
                await self._refresh_token()
            return self._token
    
    def _needs_refresh(self) -> bool:
        """トークンの更新が必要かチェック"""
        if self._token is None or self._expiration is None:
            return True
        
        current_time = int(time.time())
        return current_time >= (self._expiration - self.refresh_margin)
    
    async def _refresh_token(self) -> None:
        """IBM Cloud IAMからトークンを取得"""
        logger.info("トークンを更新中...")
        
        url = "https://iam.cloud.ibm.com/identity/token"
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }
        data = {
            "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
            "apikey": self.api_key
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, data=data, timeout=30.0)
                response.raise_for_status()
                
                token_data = response.json()
                self._token = token_data["access_token"]
                self._expiration = token_data["expiration"]
                
                logger.info(f"トークン更新成功。有効期限: {self._expiration}")
                
        except httpx.HTTPError as e:
            logger.error(f"トークン取得エラー: {e}")
            raise RuntimeError(f"IBM Cloudトークンの取得に失敗しました: {e}")
    
    async def start_auto_refresh(self) -> None:
        """バックグラウンドでトークンの自動更新を開始"""
        if self._refresh_task is not None:
            logger.warning("自動更新タスクは既に実行中です")
            return
        
        self._refresh_task = asyncio.create_task(self._auto_refresh_loop())
        logger.info("トークン自動更新を開始しました")
    
    async def stop_auto_refresh(self) -> None:
        """トークンの自動更新を停止"""
        if self._refresh_task is not None:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass
            self._refresh_task = None
            logger.info("トークン自動更新を停止しました")
    
    async def _auto_refresh_loop(self) -> None:
        """トークンを定期的に更新するループ"""
        while True:
            try:
                # 次の更新までの待機時間を計算
                if self._expiration is not None:
                    current_time = int(time.time())
                    wait_time = max(
                        60,  # 最低1分
                        (self._expiration - current_time - self.refresh_margin)
                    )
                else:
                    wait_time = 60
                
                logger.debug(f"次のトークン更新まで {wait_time} 秒待機")
                await asyncio.sleep(wait_time)
                
                # トークンを更新
                await self.get_token()
                
            except asyncio.CancelledError:
                logger.info("自動更新ループがキャンセルされました")
                raise
            except Exception as e:
                logger.error(f"自動更新中にエラーが発生: {e}")
                # エラー時は1分後にリトライ
                await asyncio.sleep(60)

# Made with Bob
