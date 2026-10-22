<p align="center">
  <img src="https://raw.githubusercontent.com/madebyman/gentleman/main/.github/assets/gentleman-logo.svg" alt="Gentleman" width="520">
</p>

<p align="center">
  <a href="https://pypi.org/project/gentleman-agents/"><img src="https://img.shields.io/pypi/v/gentleman-agents?labelColor=222&color=fff" alt="PyPI"></a>
  <a href="https://github.com/madebyman/gentleman/pkgs/container/gentleman"><img src="https://img.shields.io/badge/ghcr.io-gentleman-fff?labelColor=222&logo=docker&logoColor=fff" alt="Docker"></a>
  <a href="https://artifacthub.io/packages/helm/gentleman/gentleman"><img src="https://img.shields.io/badge/Artifact_Hub-gentleman-fff?labelColor=222&logo=artifacthub&logoColor=fff" alt="Artifact Hub"></a>
  <a href="https://pypi.org/project/gentleman-agents/"><img src="https://img.shields.io/pypi/pyversions/gentleman-agents?labelColor=222&color=fff" alt="Python"></a>
  <a href="https://github.com/madebyman/gentleman/blob/main/LICENSE"><img src="https://img.shields.io/pypi/l/gentleman-agents?labelColor=222&color=fff" alt="License"></a>
</p>

<p align="center">
  <a href="https://github.com/madebyman/gentleman/blob/main/README.md">EN</a> | JA
</p>

<hr>

<p align="center">
  <b>Gentleman</b> <i>Declarative AI agent framework</i> — MCP for tools, A2A for agents, AG-UI for humans.
</p>

Gentleman は、宣言的なマルチAIエージェントフレームワークです。
エージェントはコードではなく、設定ファイルで宣言します。`agents/` の下にエージェントごとの
ディレクトリを置くだけで、1 つのプロセスが 3 つのプロトコルですべてのエージェントを公開します。

- **AG-UI** — チャット UI から人が利用
- **A2A** — ローカルやリモートの他のエージェントから呼び出し
- **MCP** — MCP クライアントからツールとして利用

MCP サーバーのツールを使うのも、他のエージェントに処理を委譲するのも、設定ファイルに
書くだけです。グルーコードは不要です。

```
agents/
  concierge/
    agent.yaml
    mcp_config.json
  writer/
    agent.yaml
```

## 動作環境

- Python 3.14 以上

## クイックスタート

[uv](https://docs.astral.sh/uv/) でプロジェクトを作成し、起動します。

```sh
uvx --from gentleman-agents gentleman init my-gentleman
cd my-gentleman
uv sync
# agents/example/agent.yaml を編集
uv run gentleman dev
```

`gentleman dev` は `http://127.0.0.1:8000` でエージェントを公開します。
各インターフェースには次の URL でアクセスできます。

```
AG-UI : http://localhost:8000/agui
A2A   : http://localhost:8000/a2a
MCP   : http://localhost:8000/mcp
```

サンプルのエージェントは組み込みの `gentleman:echo` モデルを使うため、認証情報なしで
動作します。モデルプロバイダーを使う場合は、`.env.sample` を `.env` にコピーして
API キーを設定し、`uv run --env-file .env gentleman dev` で起動してください。

`gentleman init` は、指定したディレクトリにプロジェクトのひな形を作成します。
ディレクトリが存在しない場合は作成し、引数を省略するとカレントディレクトリに作成します。

パッケージ名は `gentleman-agents`、コマンド名は `gentleman` のため、`uvx` では
`--from` の指定が必要です。

## インストール

コマンドラインツールとして:

```sh
uv tool install gentleman-agents
gentleman --help
```

プロジェクトの依存関係として:

```sh
uv add gentleman-agents
```

pip の場合:

```sh
pip install gentleman-agents
```

## モデルプロバイダー

モデルプロバイダーは extras として提供しています。使用するものをインストールしてください。

```sh
uv add "gentleman-agents[openai]"
```

| Extra | モデルのプレフィックス | 認証情報 |
|---|---|---|
| `openai` | `openai:`、`ollama:` など OpenAI 互換の API | `OPENAI_API_KEY` |
| `anthropic` | `anthropic:` | `ANTHROPIC_API_KEY` |
| `google` | `google:`、`google-cloud:` | `GOOGLE_API_KEY` |
| `bedrock` | `bedrock:` | AWS の認証情報 |
| `xai` | `xai:` | `XAI_API_KEY` |

`providers` を指定すると、5 つすべてをインストールします。組み込みの `gentleman:echo`
モデルは、プロバイダーなしで動作します。`gentleman init` で作成したプロジェクトには
`openai` が含まれます。

Pydantic AI が対応しているその他のプロバイダーは、直接追加できます。

```sh
uv add "pydantic-ai-slim[groq]"
```

## チャット

`gentleman chat` は、ターミナルからエージェントの動作を確認するための簡易クライアントです。
開発やテストでの利用を想定しており、利用者向けのチャット画面ではありません。

`gentleman chat` サブコマンドを使うには、`chat` extra が必要です。

```sh
uv tool install "gentleman-agents[chat]"
gentleman chat
```

直接実行する場合:

```sh
uvx --from "gentleman-agents[chat]" gentleman chat
```

プロジェクトに追加する場合:

```sh
uv add "gentleman-agents[chat]"
```

extras は `gentleman-agents[chat,openai]` のように組み合わせられます。

## Docker

コンテナイメージは、GitHub Container Registry で `linux/amd64` と `linux/arm64` 向けに
公開しています。5 つのモデルプロバイダーをすべて含みます。

```sh
docker pull ghcr.io/madebyman/gentleman:edge
```

`edge` は `main` ブランチの最新ビルドです。利用できるタグは
[パッケージページ](https://github.com/madebyman/gentleman/pkgs/container/gentleman)
を参照してください。

## Helm

Helm チャートで Kubernetes にデプロイできます。エージェントはチャートの values に YAML で
定義し、エージェントごとのディレクトリとして Pod にマウントされます。

```sh
helm install gentleman oci://ghcr.io/madebyman/charts/gentleman
kubectl port-forward svc/gentleman 8000:80
```

各インターフェースには、[クイックスタート](#クイックスタート)と同じ URL でアクセスできます。

values を指定しない場合、チャートには `gentleman:echo` を使うサンプルエージェントが
含まれるため、認証情報なしで起動します。エージェント・Secret・Ingress の設定は、
[Artifact Hub](https://artifacthub.io/packages/helm/gentleman/gentleman) のチャートページを
参照してください。

## ステータス

アルファ版です。API や設定ファイルの形式は、予告なく変更される場合があります。

## ライセンス

MIT
