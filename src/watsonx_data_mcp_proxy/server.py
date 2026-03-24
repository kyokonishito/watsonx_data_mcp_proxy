"""
watsonx.data Premium MCP プロキシサーバー
IBM watsonx.dataへのリクエストを中継し、トークンを自動管理します。
"""
import asyncio
import os
import json
import logging
from typing import Any, Optional
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource

from .token_manager import TokenManager

logger = logging.getLogger(__name__)


class WatsonxDataMCPProxy:
    """watsonx.data Premium MCPプロキシサーバー"""
    
    def __init__(self, api_key: str, watsonx_data_url: str):
        """
        Args:
            api_key: IBM Cloud APIキー
            watsonx_data_url: watsonx.data MCPエンドポイントURL
        """
        self.api_key = api_key
        self.watsonx_data_url = watsonx_data_url.rstrip('/')
        self.token_manager = TokenManager(api_key)
        self.server = Server("watsonx-data-mcp-proxy")
        self.session_id: Optional[str] = None  # MCPセッションID
        self._setup_handlers()
        
    def _setup_handlers(self):
        """MCPハンドラーをセットアップ"""
        
        @self.server.list_tools()
        async def list_tools() -> list[Tool]:
            """利用可能なツールのリストを返す"""
            return [
                Tool(
                    name="LIST_DOCUMENT_LIBRARY",
                    description="すべての利用可能なドキュメントライブラリとそのメタデータをリストします",
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                ),
                Tool(
                    name="QUERY_DOCUMENT_LIBRARY",
                    description="指定されたドキュメントライブラリに対して自然言語クエリを実行します",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "library_id": {
                                "type": "string",
                                "description": "ドキュメントライブラリID"
                            },
                            "query": {
                                "type": "string",
                                "description": "自然言語クエリ"
                            }
                        },
                        "required": ["library_id", "query"]
                    }
                ),
                Tool(
                    name="LIST_DOCUMENT_SET",
                    description="指定されたドキュメントライブラリ内のすべてのドキュメントセットとそのメタデータをリストします",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "library_id": {
                                "type": "string",
                                "description": "ドキュメントライブラリID"
                            }
                        },
                        "required": ["library_id"]
                    }
                ),
                Tool(
                    name="QUERY_DOCUMENT_SET",
                    description="指定されたドキュメントセットに対して自然言語クエリを実行します",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "library_id": {
                                "type": "string",
                                "description": "ドキュメントライブラリID"
                            },
                            "set_id": {
                                "type": "string",
                                "description": "ドキュメントセットID"
                            },
                            "query": {
                                "type": "string",
                                "description": "自然言語クエリ"
                            }
                        },
                        "required": ["library_id", "set_id", "query"]
                    }
                ),
                Tool(
                    name="LIST_DATA_ASSETS",
                    description="提供された接続パラメータに基づいてフィルタリングされたPrestoテーブルを返します",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "container_type": {
                                "type": "string",
                                "description": "コンテナタイプ"
                            },
                            "container_id": {
                                "type": "string",
                                "description": "コンテナID"
                            },
                            "presto_instance_crn": {
                                "type": "string",
                                "description": "PrestoインスタンスCRN"
                            },
                            "presto_engine_id": {
                                "type": "string",
                                "description": "PrestoエンジンID"
                            }
                        },
                        "required": ["container_type", "container_id", "presto_instance_crn", "presto_engine_id"]
                    }
                ),
                Tool(
                    name="QUERY_DATA_ASSETS",
                    description="選択されたPrestoテーブルに対して自然言語クエリを実行します",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "container_type": {
                                "type": "string",
                                "description": "コンテナタイプ"
                            },
                            "container_id": {
                                "type": "string",
                                "description": "コンテナID"
                            },
                            "presto_instance_crn": {
                                "type": "string",
                                "description": "PrestoインスタンスCRN"
                            },
                            "presto_engine_id": {
                                "type": "string",
                                "description": "PrestoエンジンID"
                            },
                            "tables": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "クエリ対象のテーブルリスト"
                            },
                            "query": {
                                "type": "string",
                                "description": "自然言語クエリ"
                            }
                        },
                        "required": ["container_type", "container_id", "presto_instance_crn", "presto_engine_id", "tables", "query"]
                    }
                )
            ]
        
        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent | ImageContent | EmbeddedResource]:
            """ツールを呼び出す"""
            logger.info(f"ツール呼び出し: {name}, 引数: {arguments}")
            
            try:
                # トークンを取得
                token = await self.token_manager.get_token()
                
                # watsonx.dataにリクエストを転送
                result = await self._forward_request(name, arguments, token)
                
                return [TextContent(
                    type="text",
                    text=str(result)
                )]
                
            except Exception as e:
                logger.error(f"ツール呼び出しエラー: {e}")
                return [TextContent(
                    type="text",
                    text=f"エラー: {str(e)}"
                )]
    
    async def _initialize_session(self, token: str) -> None:
        """MCPセッションを初期化"""
        if self.session_id:
            return  # すでに初期化済み
            
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        
        # 初期化リクエスト（initialize メソッド）
        request_data = {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "watsonx-data-mcp-proxy",
                    "version": "0.1.0"
                }
            }
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    self.watsonx_data_url,
                    headers=headers,
                    json=request_data
                )
                
                # レスポンスヘッダーからセッションIDを取得
                if "mcp-session-id" in response.headers:
                    self.session_id = response.headers["mcp-session-id"]
                    logger.info(f"MCPセッション初期化完了: {self.session_id}")
                
            except Exception as e:
                logger.warning(f"セッション初期化エラー（続行します）: {e}")
    
    async def _forward_request(self, tool_name: str, arguments: dict[str, Any], token: str) -> Any:
        """watsonx.dataにリクエストを転送"""
        # セッションを初期化
        await self._initialize_session(token)
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        
        # セッションIDがある場合は追加
        if self.session_id:
            headers["mcp-session-id"] = self.session_id
        
        # MCPプロトコルに従ってリクエストを構築
        request_data = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    self.watsonx_data_url,
                    headers=headers,
                    json=request_data
                )
                
                response.raise_for_status()
                
                # レスポンスがSSE形式の場合はパース
                content_type = response.headers.get("content-type", "")
                if "text/event-stream" in content_type:
                    # SSE形式をパース
                    lines = response.text.strip().split('\n')
                    for line in lines:
                        if line.startswith('data: '):
                            json_str = line[6:]  # "data: " を除去
                            result = json.loads(json_str)
                            
                            # MCPレスポンスから結果を抽出
                            if "result" in result:
                                return result["result"]
                            elif "error" in result:
                                raise RuntimeError(f"watsonx.dataエラー: {result['error']}")
                    
                    raise RuntimeError("SSEレスポンスにdataが含まれていません")
                else:
                    # 通常のJSON形式
                    result = response.json()
                    
                    # MCPレスポンスから結果を抽出
                    if "result" in result:
                        return result["result"]
                    elif "error" in result:
                        raise RuntimeError(f"watsonx.dataエラー: {result['error']}")
                    else:
                        return result
                    
            except httpx.HTTPError as e:
                logger.error(f"HTTPエラー: {e}")
                raise RuntimeError(f"watsonx.dataへのリクエストが失敗しました: {e}")
    
    async def run(self):
        """サーバーを起動"""
        logger.info("watsonx.data MCPプロキシサーバーを起動中...")
        
        # トークンの自動更新を開始
        await self.token_manager.start_auto_refresh()
        
        try:
            async with stdio_server() as (read_stream, write_stream):
                await self.server.run(
                    read_stream,
                    write_stream,
                    self.server.create_initialization_options()
                )
        finally:
            # クリーンアップ
            await self.token_manager.stop_auto_refresh()
            logger.info("サーバーを停止しました")


async def main():
    """メインエントリーポイント"""
    # ログ設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 環境変数から設定を取得
    api_key = os.getenv("IBM_CLOUD_API_KEY")
    watsonx_data_url = os.getenv("WATSONX_DATA_URL")
    
    if not api_key:
        raise ValueError("IBM_CLOUD_API_KEY環境変数が設定されていません")
    if not watsonx_data_url:
        raise ValueError("WATSONX_DATA_URL環境変数が設定されていません")
    
    # プロキシサーバーを起動
    proxy = WatsonxDataMCPProxy(api_key, watsonx_data_url)
    await proxy.run()


if __name__ == "__main__":
    asyncio.run(main())

# Made with Bob
