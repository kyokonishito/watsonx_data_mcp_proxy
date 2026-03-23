"""
watsonx.data MCP Proxy エントリーポイント
"""
import asyncio
from .server import main as server_main


def main():
    """メインエントリーポイント（pipx用）"""
    asyncio.run(server_main())


if __name__ == "__main__":
    main()

# Made with Bob
