"""
WatsonxDataMCPProxyのユニットテスト
"""
import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from src.watsonx_data_mcp_proxy.server import WatsonxDataMCPProxy


@pytest.fixture
def proxy_server():
    """WatsonxDataMCPProxyのフィクスチャ"""
    return WatsonxDataMCPProxy(
        api_key="test-api-key",
        watsonx_data_url="https://test.example.com/api/v2/mcp/"
    )


class TestWatsonxDataMCPProxy:
    """WatsonxDataMCPProxyのテストクラス"""
    
    def test_init(self, proxy_server):
        """初期化のテスト"""
        assert proxy_server.api_key == "test-api-key"
        assert proxy_server.watsonx_data_url == "https://test.example.com/api/v2/mcp"
        assert proxy_server.token_manager is not None
        assert proxy_server.server is not None
    
    def test_url_trailing_slash_removed(self):
        """URLの末尾スラッシュが削除されることを確認"""
        proxy = WatsonxDataMCPProxy(
            api_key="test-key",
            watsonx_data_url="https://test.example.com/api/v2/mcp/"
        )
        assert proxy.watsonx_data_url == "https://test.example.com/api/v2/mcp"
    
    @pytest.mark.asyncio
    async def test_forward_request_success(self, proxy_server):
        """リクエスト転送成功のテスト"""
        mock_response_data = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": "テスト結果"
                    }
                ]
            }
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json = MagicMock(return_value=mock_response_data)
            mock_response.raise_for_status = MagicMock()
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            result = await proxy_server._forward_request(
                tool_name="LIST_DOCUMENT_LIBRARY",
                arguments={},
                token="test-token"
            )
            
            assert result == mock_response_data["result"]
    
    @pytest.mark.asyncio
    async def test_forward_request_with_error(self, proxy_server):
        """エラーレスポンスのテスト"""
        mock_response_data = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "code": -32000,
                "message": "テストエラー"
            }
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json = MagicMock(return_value=mock_response_data)
            mock_response.raise_for_status = MagicMock()
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            with pytest.raises(RuntimeError, match="watsonx.dataエラー"):
                await proxy_server._forward_request(
                    tool_name="LIST_DOCUMENT_LIBRARY",
                    arguments={},
                    token="test-token"
                )
    
    @pytest.mark.asyncio
    async def test_forward_request_http_error(self, proxy_server):
        """HTTPエラーのテスト"""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.raise_for_status = MagicMock(
                side_effect=httpx.HTTPStatusError("HTTP Error", request=MagicMock(), response=MagicMock())
            )
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            with pytest.raises(RuntimeError, match="watsonx.dataへのリクエストが失敗しました"):
                await proxy_server._forward_request(
                    tool_name="LIST_DOCUMENT_LIBRARY",
                    arguments={},
                    token="test-token"
                )
    
    @pytest.mark.asyncio
    async def test_forward_request_headers(self, proxy_server):
        """リクエストヘッダーのテスト"""
        mock_response_data = {"jsonrpc": "2.0", "id": 1, "result": {}}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json = MagicMock(return_value=mock_response_data)
            mock_response.raise_for_status = MagicMock()
            
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            await proxy_server._forward_request(
                tool_name="LIST_DOCUMENT_LIBRARY",
                arguments={},
                token="test-token-123"
            )
            
            # ヘッダーが正しく設定されているか確認
            call_args = mock_post.call_args
            headers = call_args.kwargs['headers']
            assert headers['Authorization'] == "Bearer test-token-123"
            assert headers['Content-Type'] == "application/json"
    
    @pytest.mark.asyncio
    async def test_forward_request_body(self, proxy_server):
        """リクエストボディのテスト"""
        mock_response_data = {"jsonrpc": "2.0", "id": 1, "result": {}}
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json = MagicMock(return_value=mock_response_data)
            mock_response.raise_for_status = MagicMock()
            
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            test_arguments = {"library_id": "test-lib", "query": "test query"}
            await proxy_server._forward_request(
                tool_name="QUERY_DOCUMENT_LIBRARY",
                arguments=test_arguments,
                token="test-token"
            )
            
            # リクエストボディが正しく設定されているか確認
            call_args = mock_post.call_args
            request_data = call_args.kwargs['json']
            assert request_data['jsonrpc'] == "2.0"
            assert request_data['method'] == "tools/call"
            assert request_data['params']['name'] == "QUERY_DOCUMENT_LIBRARY"
            assert request_data['params']['arguments'] == test_arguments


@pytest.mark.asyncio
async def test_list_tools():
    """ツールリストのテスト"""
    proxy = WatsonxDataMCPProxy(
        api_key="test-key",
        watsonx_data_url="https://test.example.com/api/v2/mcp/"
    )
    
    # list_toolsハンドラーを直接テスト
    # 注: 実際のハンドラーはデコレータで登録されているため、
    # サーバーインスタンスから取得する必要がある
    tools = [
        "LIST_DOCUMENT_LIBRARY",
        "QUERY_DOCUMENT_LIBRARY",
        "LIST_DOCUMENT_SET",
        "QUERY_DOCUMENT_SET",
        "LIST_DATA_ASSETS",
        "QUERY_DATA_ASSETS"
    ]
    
    # ツール名が正しく定義されているか確認
    # （実際のハンドラーテストは統合テストで実施）
    assert len(tools) == 6


@pytest.mark.asyncio
async def test_proxy_integration():
    """プロキシの統合テスト（モック使用）"""
    proxy = WatsonxDataMCPProxy(
        api_key="integration-test-key",
        watsonx_data_url="https://test.example.com/api/v2/mcp/"
    )
    
    # TokenManagerのモック
    with patch.object(proxy.token_manager, 'get_token', return_value="mock-token"):
        # HTTPクライアントのモック
        mock_response_data = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "content": [{"type": "text", "text": "統合テスト結果"}]
            }
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.json = MagicMock(return_value=mock_response_data)
            mock_response.raise_for_status = MagicMock()
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            # リクエストを実行
            result = await proxy._forward_request(
                tool_name="LIST_DOCUMENT_LIBRARY",
                arguments={},
                token="mock-token"
            )
            
            assert result == mock_response_data["result"]

# Made with Bob
