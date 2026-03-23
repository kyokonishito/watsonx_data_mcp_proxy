"""
TokenManagerのユニットテスト
"""
import pytest
import time
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from src.watsonx_data_mcp_proxy.token_manager import TokenManager


@pytest.fixture
def token_manager():
    """TokenManagerのフィクスチャ"""
    return TokenManager(api_key="test-api-key", refresh_margin=300)


@pytest.fixture
def mock_token_response():
    """モックトークンレスポンス"""
    return {
        "access_token": "test-access-token-12345",
        "refresh_token": "not_supported",
        "token_type": "Bearer",
        "expires_in": 3600,
        "expiration": int(time.time()) + 3600,
        "scope": "ibm openid"
    }


class TestTokenManager:
    """TokenManagerのテストクラス"""
    
    @pytest.mark.asyncio
    async def test_init(self, token_manager):
        """初期化のテスト"""
        assert token_manager.api_key == "test-api-key"
        assert token_manager.refresh_margin == 300
        assert token_manager._token is None
        assert token_manager._expiration is None
    
    @pytest.mark.asyncio
    async def test_get_token_first_time(self, token_manager, mock_token_response):
        """初回トークン取得のテスト"""
        with patch('httpx.AsyncClient') as mock_client:
            # モックレスポンスを設定
            mock_response = MagicMock()
            mock_response.json = MagicMock(return_value=mock_token_response)
            mock_response.raise_for_status = MagicMock()
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            # トークンを取得
            token = await token_manager.get_token()
            
            # 検証
            assert token == "test-access-token-12345"
            assert token_manager._token == "test-access-token-12345"
            assert token_manager._expiration == mock_token_response["expiration"]
    
    @pytest.mark.asyncio
    async def test_get_token_cached(self, token_manager):
        """キャッシュされたトークンの取得テスト"""
        # トークンを事前に設定
        token_manager._token = "cached-token"
        token_manager._expiration = int(time.time()) + 3600
        
        # トークンを取得（HTTPリクエストは発生しないはず）
        token = await token_manager.get_token()
        
        # 検証
        assert token == "cached-token"
    
    @pytest.mark.asyncio
    async def test_needs_refresh_no_token(self, token_manager):
        """トークンがない場合の更新判定テスト"""
        assert token_manager._needs_refresh() is True
    
    @pytest.mark.asyncio
    async def test_needs_refresh_expired(self, token_manager):
        """期限切れトークンの更新判定テスト"""
        token_manager._token = "expired-token"
        token_manager._expiration = int(time.time()) - 100  # 過去の時刻
        
        assert token_manager._needs_refresh() is True
    
    @pytest.mark.asyncio
    async def test_needs_refresh_valid(self, token_manager):
        """有効なトークンの更新判定テスト"""
        token_manager._token = "valid-token"
        token_manager._expiration = int(time.time()) + 3600  # 1時間後
        
        assert token_manager._needs_refresh() is False
    
    @pytest.mark.asyncio
    async def test_needs_refresh_near_expiration(self, token_manager):
        """期限切れ間近のトークンの更新判定テスト"""
        token_manager._token = "near-expiration-token"
        # refresh_margin(300秒)以内
        token_manager._expiration = int(time.time()) + 200
        
        assert token_manager._needs_refresh() is True
    
    @pytest.mark.asyncio
    async def test_refresh_token_success(self, token_manager, mock_token_response):
        """トークン更新成功のテスト"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json = MagicMock(return_value=mock_token_response)
            mock_response.raise_for_status = MagicMock()
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            await token_manager._refresh_token()
            
            assert token_manager._token == "test-access-token-12345"
            assert token_manager._expiration == mock_token_response["expiration"]
    
    @pytest.mark.asyncio
    async def test_refresh_token_http_error(self, token_manager):
        """トークン更新HTTPエラーのテスト"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock(
                side_effect=httpx.HTTPStatusError("HTTP Error", request=MagicMock(), response=MagicMock())
            )
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            with pytest.raises(RuntimeError, match="IBM Cloudトークンの取得に失敗しました"):
                await token_manager._refresh_token()
    
    @pytest.mark.asyncio
    async def test_start_auto_refresh(self, token_manager):
        """自動更新開始のテスト"""
        await token_manager.start_auto_refresh()
        
        assert token_manager._refresh_task is not None
        assert not token_manager._refresh_task.done()
        
        # クリーンアップ
        await token_manager.stop_auto_refresh()
    
    @pytest.mark.asyncio
    async def test_stop_auto_refresh(self, token_manager):
        """自動更新停止のテスト"""
        await token_manager.start_auto_refresh()
        assert token_manager._refresh_task is not None
        
        await token_manager.stop_auto_refresh()
        assert token_manager._refresh_task is None
    
    @pytest.mark.asyncio
    async def test_auto_refresh_already_running(self, token_manager):
        """既に実行中の自動更新の再開始テスト"""
        await token_manager.start_auto_refresh()
        first_task = token_manager._refresh_task
        
        # 再度開始を試みる
        await token_manager.start_auto_refresh()
        
        # タスクは変わらないはず
        assert token_manager._refresh_task is first_task
        
        # クリーンアップ
        await token_manager.stop_auto_refresh()


@pytest.mark.asyncio
async def test_token_manager_integration():
    """TokenManagerの統合テスト（モック使用）"""
    manager = TokenManager(api_key="integration-test-key")
    
    mock_response_data = {
        "access_token": "integration-token",
        "expiration": int(time.time()) + 3600
    }
    
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value=mock_response_data)
        mock_response.raise_for_status = MagicMock()
        
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(
            return_value=mock_response
        )
        
        # トークンを取得
        token1 = await manager.get_token()
        assert token1 == "integration-token"
        
        # キャッシュから取得（HTTPリクエストなし）
        token2 = await manager.get_token()
        assert token2 == token1
        
        # 期限切れにする
        manager._expiration = int(time.time()) - 100
        
        # 新しいトークンを取得
        token3 = await manager.get_token()
        assert token3 == "integration-token"

# Made with Bob
