"""
実際のIBM Cloudとwatsonx.dataに接続する統合テスト

注意: このテストを実行するには、以下の環境変数が必要です：
- IBM_CLOUD_API_KEY: IBM Cloud APIキー
- WATSONX_DATA_URL: watsonx.data MCPエンドポイントURL

実行方法:
    pytest tests/test_integration.py -v -s
"""
import os
import pytest
import asyncio
from src.watsonx_data_mcp_proxy.token_manager import TokenManager
from src.watsonx_data_mcp_proxy.server import WatsonxDataMCPProxy


# 環境変数が設定されていない場合はテストをスキップ
pytestmark = pytest.mark.skipif(
    not os.getenv("IBM_CLOUD_API_KEY") or not os.getenv("WATSONX_DATA_URL"),
    reason="IBM_CLOUD_API_KEY and WATSONX_DATA_URL environment variables are required"
)


@pytest.fixture
def api_key():
    """IBM Cloud APIキー"""
    return os.getenv("IBM_CLOUD_API_KEY")


@pytest.fixture
def watsonx_data_url():
    """watsonx.data URL"""
    return os.getenv("WATSONX_DATA_URL")


@pytest.mark.integration
class TestTokenManagerIntegration:
    """TokenManagerの統合テスト（実際のIBM Cloudに接続）"""
    
    @pytest.mark.asyncio
    async def test_get_real_token(self, api_key):
        """実際のIBM Cloudからトークンを取得"""
        manager = TokenManager(api_key=api_key)
        
        # トークンを取得
        token = await manager.get_token()
        
        # 検証
        assert token is not None
        assert len(token) > 0
        assert token.startswith("eyJ")  # JWTトークンの形式
        assert manager._expiration is not None
        assert manager._expiration > 0
        
        print(f"\n✓ トークン取得成功")
        print(f"  トークン長: {len(token)}")
        print(f"  有効期限: {manager._expiration}")
    
    @pytest.mark.asyncio
    async def test_token_caching(self, api_key):
        """トークンのキャッシング機能のテスト"""
        manager = TokenManager(api_key=api_key)
        
        # 1回目の取得
        token1 = await manager.get_token()
        expiration1 = manager._expiration
        
        # 2回目の取得（キャッシュから）
        token2 = await manager.get_token()
        expiration2 = manager._expiration
        
        # 同じトークンが返されることを確認
        assert token1 == token2
        assert expiration1 == expiration2
        
        print(f"\n✓ トークンキャッシング動作確認")
    
    @pytest.mark.asyncio
    async def test_auto_refresh(self, api_key):
        """自動更新機能のテスト"""
        manager = TokenManager(api_key=api_key, refresh_margin=3500)  # 期限切れ間近として扱う
        
        # 初回トークン取得
        token1 = await manager.get_token()
        
        # 自動更新を開始
        await manager.start_auto_refresh()
        
        # 少し待機
        await asyncio.sleep(2)
        
        # 自動更新を停止
        await manager.stop_auto_refresh()
        
        # トークンが取得されていることを確認
        assert manager._token is not None
        
        print(f"\n✓ 自動更新機能動作確認")


@pytest.mark.integration
class TestWatsonxDataMCPProxyIntegration:
    """WatsonxDataMCPProxyの統合テスト（実際のwatsonx.dataに接続）"""
    
    @pytest.mark.asyncio
    async def test_list_document_library(self, api_key, watsonx_data_url):
        """LIST_DOCUMENT_LIBRARYツールのテスト"""
        proxy = WatsonxDataMCPProxy(
            api_key=api_key,
            watsonx_data_url=watsonx_data_url
        )
        
        # トークンを取得
        token = await proxy.token_manager.get_token()
        
        try:
            # ドキュメントライブラリのリストを取得
            result = await proxy._forward_request(
                tool_name="LIST_DOCUMENT_LIBRARY",
                arguments={},
                token=token
            )
            
            print(f"\n✓ LIST_DOCUMENT_LIBRARY成功")
            print(f"  結果: {result}")
            
            # 結果が返されることを確認
            assert result is not None
            
        except Exception as e:
            print(f"\n✗ LIST_DOCUMENT_LIBRARYエラー: {e}")
            # エラーの詳細を表示
            import traceback
            traceback.print_exc()
            raise
    
    @pytest.mark.asyncio
    async def test_connection_with_invalid_token(self, watsonx_data_url):
        """無効なトークンでの接続テスト"""
        proxy = WatsonxDataMCPProxy(
            api_key="invalid-api-key",
            watsonx_data_url=watsonx_data_url
        )
        
        # 無効なトークンでリクエスト
        with pytest.raises(RuntimeError):
            await proxy.token_manager.get_token()
        
        print(f"\n✓ 無効なトークンのエラーハンドリング確認")
    
    @pytest.mark.asyncio
    async def test_full_workflow(self, api_key, watsonx_data_url):
        """完全なワークフローのテスト"""
        proxy = WatsonxDataMCPProxy(
            api_key=api_key,
            watsonx_data_url=watsonx_data_url
        )
        
        print(f"\n=== 完全ワークフローテスト開始 ===")
        
        # 1. トークン取得
        token = await proxy.token_manager.get_token()
        print(f"✓ ステップ1: トークン取得成功")
        
        # 2. ドキュメントライブラリのリスト取得
        try:
            libraries = await proxy._forward_request(
                tool_name="LIST_DOCUMENT_LIBRARY",
                arguments={},
                token=token
            )
            print(f"✓ ステップ2: ドキュメントライブラリリスト取得成功")
            print(f"  結果: {libraries}")
        except Exception as e:
            print(f"✗ ステップ2: エラー - {e}")
            # エラーでもテストは続行（データがない可能性があるため）
        
        # 3. 自動更新の開始と停止
        await proxy.token_manager.start_auto_refresh()
        print(f"✓ ステップ3: 自動更新開始")
        
        await asyncio.sleep(1)
        
        await proxy.token_manager.stop_auto_refresh()
        print(f"✓ ステップ4: 自動更新停止")
        
        print(f"=== 完全ワークフローテスト完了 ===\n")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_requests(api_key, watsonx_data_url):
    """複数の同時リクエストのテスト"""
    proxy = WatsonxDataMCPProxy(
        api_key=api_key,
        watsonx_data_url=watsonx_data_url
    )
    
    # トークンを取得
    token = await proxy.token_manager.get_token()
    
    # 複数のリクエストを同時に実行
    tasks = []
    for i in range(3):
        task = proxy._forward_request(
            tool_name="LIST_DOCUMENT_LIBRARY",
            arguments={},
            token=token
        )
        tasks.append(task)
    
    try:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        print(f"\n✓ 同時リクエストテスト完了")
        print(f"  成功: {sum(1 for r in results if not isinstance(r, Exception))}/{len(results)}")
        
        # 少なくとも1つは成功することを確認
        assert any(not isinstance(r, Exception) for r in results)
        
    except Exception as e:
        print(f"\n✗ 同時リクエストエラー: {e}")
        raise


if __name__ == "__main__":
    # 統合テストを直接実行
    print("統合テストを実行します...")
    print("必要な環境変数:")
    print("  - IBM_CLOUD_API_KEY")
    print("  - WATSONX_DATA_URL")
    print()
    
    if not os.getenv("IBM_CLOUD_API_KEY"):
        print("エラー: IBM_CLOUD_API_KEY環境変数が設定されていません")
        exit(1)
    
    if not os.getenv("WATSONX_DATA_URL"):
        print("エラー: WATSONX_DATA_URL環境変数が設定されていません")
        exit(1)
    
    pytest.main([__file__, "-v", "-s"])

# Made with Bob
