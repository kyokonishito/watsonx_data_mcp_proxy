> [!NOTE]
> まだテスト中です！


# watsonx.data MCP Proxy

IBM watsonx.data Premium用のMCPプロキシサーバー。[IBM watsonx.data remote Model Context Protocol (MCP) server](https://www.ibm.com/docs/en/watsonxdata/premium/2.3.x?topic=agents-watsonxdata-remote-model-context-protocol-mcp-server)に接続し、IBM Cloud APIキーからアクセストークンを自動的に取得・更新してリクエストを中継します。

## 概要

このプロキシサーバーは、IBM watsonx.data Premiumの[remote MCP server](https://www.ibm.com/docs/en/watsonxdata/premium/2.3.x?topic=agents-watsonxdata-remote-model-context-protocol-mcp-server)機能を利用するためのツールです。IBM Cloud IAMトークンの自動管理により、MCPクライアント（IBM BobやClaude Desktopなど）から簡単にwatsonx.dataのデータにアクセスできます。

## 特徴

- **自動トークン更新**: IBM Cloud APIキーから自動的にトークンを取得し、期限切れ前に更新
- **MCPプロトコル対応**: Model Context Protocol (MCP)に完全対応
- **6つのツールをサポート**: watsonx.dataのすべてのMCPツールに対応
- **エラーハンドリング**: 堅牢なエラー処理とリトライロジック
- **ログ機能**: 詳細なログでデバッグが容易

## サポートされるツール

1. **LIST_DOCUMENT_LIBRARY** - ドキュメントライブラリの一覧取得
2. **QUERY_DOCUMENT_LIBRARY** - ドキュメントライブラリへのクエリ実行
3. **LIST_DOCUMENT_SET** - ドキュメントセットの一覧取得
4. **QUERY_DOCUMENT_SET** - ドキュメントセットへのクエリ実行
5. **LIST_DATA_ASSETS** - データアセット（テーブル）の一覧取得
6. **QUERY_DATA_ASSETS** - データアセットへのクエリ実行

## インストール

### 前提条件

- Python 3.10以上
- pipx（推奨）またはpip
- IBM Cloud APIキー
- watsonx.data Premiumインスタンス

### インストール方法

#### 方法1: pipxでGitHubから直接インストール（推奨）

pipxを使用すると、独立した環境にインストールされ、システムのPython環境を汚染しません。

```bash
# pipxがインストールされていない場合
python -m pip install --user pipx
python -m pipx ensurepath

# GitHubから直接インストール
pipx install git+https://github.com/kyokonishito/watsonx_data_mcp_proxy.git

# 特定のブランチやタグからインストール
pipx install git+https://github.com/kyokonishito/watsonx_data_mcp_proxy.git@main
pipx install git+https://github.com/kyokonishito/watsonx_data_mcp_proxy.git@v0.1.0
```

#### 方法2: pipでGitHubから直接インストール

```bash
# GitHubから直接インストール
pip install git+https://github.com/kyokonishito/watsonx_data_mcp_proxy.git

# または、ユーザーディレクトリにインストール
pip install --user git+https://github.com/kyokonishito/watsonx_data_mcp_proxy.git
```

#### 方法3: ローカル開発用（開発者向け）

```bash
# リポジトリをクローン
git clone https://github.com/kyokonishito/watsonx_data_mcp_proxy.git
cd watsonx_data_mcp_proxy

# uvで仮想環境を作成（推奨）
uv venv
source .venv/bin/activate  # Linux/macOS
# または .venv\Scripts\activate  # Windows

# 開発モードでインストール
uv pip install -e ".[dev]"

# または、pipを使用
pip install -e ".[dev]"
```

### インストールの確認

```bash
# コマンドが利用可能か確認
watsonx-data-mcp-proxy --help

# または、Pythonモジュールとして実行
python -m watsonx_data_mcp_proxy --help
```

### アンインストール

#### pipxでインストールした場合

```bash
pipx uninstall watsonx-data-mcp-proxy
```

#### pipでインストールした場合

```bash
pip uninstall watsonx-data-mcp-proxy
```

#### ローカル開発環境の場合

```bash
# 開発モードでインストールした場合
pip uninstall watsonx-data-mcp-proxy

# または、仮想環境ごと削除
rm -rf .venv
```

## 使用方法

### IBM Bob (MCP Client)での設定

IBM Bobで使用する場合、`.bob/mcp.json`に設定を追加します。インストール方法に応じて設定が異なります。

#### 方法1: pipxでインストールした場合（推奨）

```json
{
  "mcpServers": {
    "watsonx-data-premium": {
      "command": "watsonx-data-mcp-proxy",
      "env": {
        "IBM_CLOUD_API_KEY": "your-ibm-cloud-api-key",
        "WATSONX_DATA_URL": "https://your-instance.lakehouse.saas.ibm.com/api/v2/mcp/"
      }
    }
  }
}
```

#### 方法2: ローカル開発環境の場合

仮想環境のPythonの絶対パスを指定します：

```json
{
  "mcpServers": {
    "watsonx-data-premium": {
      "command": "/path/to/your/project/.venv/bin/python",
      "args": ["-m", "watsonx_data_mcp_proxy"],
      "env": {
        "IBM_CLOUD_API_KEY": "your-ibm-cloud-api-key",
        "WATSONX_DATA_URL": "https://your-instance.lakehouse.saas.ibm.com/api/v2/mcp/"
      }
    }
  }
}
```

**例**: プロジェクトが`/Users/username/watsonx-data-mcp-proxy`にある場合：
```json
{
  "mcpServers": {
    "watsonx-data-premium": {
      "command": "/Users/username/watsonx-data-mcp-proxy/.venv/bin/python",
      "args": ["-m", "watsonx_data_mcp_proxy"],
      "env": {
        "IBM_CLOUD_API_KEY": "your-ibm-cloud-api-key",
        "WATSONX_DATA_URL": "https://your-instance.lakehouse.saas.ibm.com/api/v2/mcp/"
      }
    }
  }
}
```

**重要**:
- 環境変数は`.bob/mcp.json`の`env`セクションで設定するため、シェルで別途`export`する必要はありません
- ローカル開発環境では、必ず仮想環境のPythonの**絶対パス**を指定してください
- `python`や`python3`などの相対コマンドは使用しないでください（モジュールが見つからないエラーが発生します）

### Claude Desktop (MCP Client)での設定

Claude Desktopで使用する場合、設定ファイルの場所が異なります。

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

#### 方法1: pipxでインストールした場合（推奨）

```json
{
  "mcpServers": {
    "watsonx-data-premium": {
      "command": "watsonx-data-mcp-proxy",
      "env": {
        "IBM_CLOUD_API_KEY": "your-ibm-cloud-api-key",
        "WATSONX_DATA_URL": "https://your-instance.lakehouse.saas.ibm.com/api/v2/mcp/"
      }
    }
  }
}
```

#### 方法2: ローカル開発環境の場合

```json
{
  "mcpServers": {
    "watsonx-data-premium": {
      "command": "/path/to/your/project/.venv/bin/python",
      "args": ["-m", "watsonx_data_mcp_proxy"],
      "env": {
        "IBM_CLOUD_API_KEY": "your-ibm-cloud-api-key",
        "WATSONX_DATA_URL": "https://your-instance.lakehouse.saas.ibm.com/api/v2/mcp/"
      }
    }
  }
}
```

### サーバーの起動

IBM BobまたはClaude Desktopを起動すると、自動的にプロキシサーバーが起動します。トークンは自動的に取得・更新されます。

手動でテストする場合（開発時のみ）：

```bash
export IBM_CLOUD_API_KEY="your-ibm-cloud-api-key"
export WATSONX_DATA_URL="https://your-instance.lakehouse.saas.ibm.com/api/v2/mcp/"
python -m watsonx_data_mcp_proxy
```

## 設定オプション

### トークン更新マージン

デフォルトでは、トークンの有効期限の5分前に自動更新されます。この値は`TokenManager`クラスの`refresh_margin`パラメータで変更できます。

### ログレベル

環境変数`LOG_LEVEL`でログレベルを設定できます：

```bash
export LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

## 開発

### テストの実行

```bash
# すべてのテストを実行
pytest

# カバレッジレポート付きで実行
pytest --cov=src/watsonx_data_mcp_proxy --cov-report=html

# 特定のテストファイルのみ実行
pytest tests/test_token_manager.py

# 統合テストを実行（実際のwatsonx.dataに接続）
# 環境変数を設定して実行
export IBM_CLOUD_API_KEY="your-ibm-cloud-api-key"
export WATSONX_DATA_URL="https://your-instance.lakehouse.saas.ibm.com/api/v2/mcp/"
pytest tests/test_integration.py -v -m integration

# または、uv仮想環境を使用する場合
IBM_CLOUD_API_KEY="your-api-key" WATSONX_DATA_URL="https://your-instance.lakehouse.saas.ibm.com/api/v2/mcp/" uv run pytest tests/test_integration.py -v -m integration
```

### テストの種類

1. **ユニットテスト** (`test_token_manager.py`, `test_server.py`)
   - モックを使用した単体テスト
   - 高速で依存関係なし

2. **統合テスト** (`test_integration.py`)
   - 実際のIBM Cloudとwatsonx.dataに接続
   - 環境変数の設定が必要

### プロジェクト構造

```
mcp_wxd_premium/
├── src/
│   └── watsonx_data_mcp_proxy/
│       ├── __init__.py
│       ├── __main__.py
│       ├── server.py          # MCPサーバー実装
│       └── token_manager.py   # トークン管理
├── tests/
│   ├── test_token_manager.py  # トークン管理のテスト
│   ├── test_server.py         # サーバーのテスト
│   └── test_integration.py    # 統合テスト
├── .bob/
│   └── mcp.json              # IBM Bob設定ファイル
├── pyproject.toml            # プロジェクト設定
└── README.md                 # このファイル
```

## トラブルシューティング

### トークン取得エラー

```
RuntimeError: IBM Cloudトークンの取得に失敗しました
```

**解決方法**:
- IBM Cloud APIキーが正しいか確認
- APIキーに適切な権限があるか確認
- ネットワーク接続を確認

### watsonx.data接続エラー

```
RuntimeError: watsonx.dataへのリクエストが失敗しました
```

**解決方法**:
- watsonx.data URLが正しいか確認
- watsonx.dataインスタンスでMCPサーバー機能が有効化されているか確認
- トークンに適切な権限があるか確認

### レスポンス形式エラー

```
Invalid response format: 'rows' is not a string []
```

**解決方法**:
- watsonx.dataのMCPサーバーバージョンを確認
- プロキシサーバーのログを確認してレスポンス内容を調査

## ライセンス

このプロジェクトはApache License 2.0の下でライセンスされています。詳細は[LICENSE](LICENSE)ファイルを参照してください。


## 参考資料

- [IBM watsonx.data Documentation](https://www.ibm.com/docs/en/watsonxdata)
- [IBM watsonx.data remote Model Context Protocol (MCP) server](https://www.ibm.com/docs/en/watsonxdata/premium/2.3.x?topic=agents-watsonxdata-remote-model-context-protocol-mcp-server)
- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- [IBM Cloud API Keys](https://cloud.ibm.com/iam/apikeys)