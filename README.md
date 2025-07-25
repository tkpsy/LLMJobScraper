# CrowdWorks AI案件マッチングシステム

CrowdWorksのAI・機械学習関連案件を自動収集し、ユーザープロファイルとのマッチング評価を行うWebベースのシステムです。

## 🚀 主要機能

### 🤖 自動案件収集・マッチング
- CrowdWorksからのAI関連案件の自動収集
- LLMを使用したユーザープロファイルとのマッチング評価
- 案件情報の構造化抽出と保存

### 🌐 Web UI
- **スクレイピング実行**: ワンクリックでスクレイピング開始
- **設定管理**: ユーザープロファイル、LLM設定、フィルタリング設定
- **結果表示**: マッチング結果の詳細表示と履歴管理
- **リアルタイム進捗**: 実行状況とログのリアルタイム表示

### ⚙️ 高度な設定機能
- **LLM選択**: Ollama（ローカル）またはDeepSeek API
- **モデル選択**: 複数のLLMモデルから選択
- **パラメータ調整**: 創造性レベル、バッチサイズ、閾値など
- **カテゴリ自動選択**: ユーザースキルに基づくLLMによる最適カテゴリ選択

## 🛠️ セットアップ

### 方法1: ローカル環境でのセットアップ

### 1. 必要なパッケージのインストール
```bash
pip install -r requirements.txt
```

### 2. Playwrightのセットアップ
```bash
playwright install
```

### 3. 環境変数の設定（DeepSeek API使用時のみ）
`.env`ファイルを作成し、以下の内容を設定してください：
```
DEEPSEEK_API_KEY=your_api_key_here
```

### 4. Ollamaのセットアップ（ローカルLLM使用時）
```bash
# Ollamaのインストール（macOS）
curl -fsSL https://ollama.ai/install.sh | sh

# モデルのダウンロード
ollama pull qwen2.5:latest
```

### 方法2: Docker環境でのセットアップ

Dockerを使用すると、環境構築なしで簡単にシステムを起動できます。

#### 前提条件
- Docker Desktop または Docker Engine

#### 手順

1. **リポジトリのクローン**
   ```bash
   git clone <repository-url>
   cd scraping_base
   ```

2. **Dockerイメージのビルド**
   ```bash
   docker-compose build
   ```

3. **Dockerでコンテナを起動**
   ```bash
   docker-compose up -d
   ```

4. **コンテナに入る**
   ```bash
   docker exec -it llm-job-scraper bash
   ```

5. **Ollama serverを起動**
   ```bash
   ollama serve &
   ```
6. **Webサーバーを起動**
   ```bash
   python simple_server.py
   ```

7. **ブラウザでアクセス**
   ```
   http://localhost:8000
   ```

8. **Dockerコンテナを停止**
    ```bash
    docker-compose down
    ```

#### 使用方法

1. **Web UIでの設定**
   - 設定タブでユーザープロファイルを入力
   - LLM設定で「Local (Ollama)」を選択
   - 必要に応じてフィルタリング設定を調整

2. **スクレイピング実行**
   - スクレイピング実行タブで「スクレイピング実行」ボタンをクリック
   - 進捗バーで実行状況を確認

3. **結果の確認**
   - マッチング結果タブで結果を確認
   - 過去の実行履歴も表示可能

#### システムの停止
```bash
# コンテナ内でCtrl+CでWebサーバーを停止
# コンテナを停止
docker-compose down
```

#### トラブルシューティング

- **ポート8000が使用中**: 別のポートで起動するか、既存のプロセスを停止
- **Ollamaモデルエラー**: コンテナ内で`ollama pull qwen2.5:latest`を実行
- **詳細なログ**: コンテナ内でログを確認

詳細な設定やトラブルシューティングは [DOCKER.md](DOCKER.md) を参照してください。

## 🎯 使用方法

### Web UIでの実行
1. Webサーバーの起動:
```bash
python simple_server.py
```

2. ブラウザでアクセス:
```
http://localhost:8000
```

3. 設定タブで以下を設定:
   - **ユーザープロファイル**: スキル、好みのカテゴリ、勤務地、自己紹介
   - **LLM設定**: LLMタイプ、モデル、創造性レベル、検索対象カテゴリ数
   - **フィルタリング設定**: 閾値、最大案件数、バッチ処理サイズ

4. スクレイピング実行タブで「スクレイピング実行」ボタンをクリック

### コマンドラインでの実行
```bash
python main.py
```

## 📁 プロジェクト構造

```
.
├── data/
│   ├── html/          # スクレイピングしたHTMLファイル
│   ├── jobs/          # 抽出された案件情報
│   └── matches/       # マッチング結果（履歴含む）
├── logs/              # ログファイル
├── src/
│   ├── models/        # データモデル
│   ├── scrapers/      # スクレイピング機能
│   ├── processors/    # データ処理機能
│   └── utils/         # ユーティリティ（設定ファイル含む）
├── main.py            # メインスクリプト
├── simple_server.py   # Webサーバー
├── web_config.json    # Web設定ファイル
├── requirements.txt
└── README.md
```

## ⚙️ 設定項目

### ユーザープロファイル設定
- **スキル**: 技術スキル（Python、機械学習など）
- **好みのカテゴリ**: 希望する案件カテゴリ
- **好みの勤務地**: リモート、在宅など
- **自己紹介**: 経験や希望の詳細

### LLM設定
- **LLMタイプ**: `local`（Ollama）または `deepseek`（API）
- **LLMモデル**: 選択したタイプに応じたモデル
- **LLM創造性レベル**: 0.0（一貫性重視）〜2.0（創造性重視）
- **検索対象カテゴリ数**: 検索するカテゴリの最大数
- **カテゴリ選択の閾値**: カテゴリ選択時の関連度スコア（0-10点）

### フィルタリング設定
- **案件推薦の閾値**: マッチングスコアの最小値（0-100点）
- **最大案件数**: 推薦する案件の最大数
- **バッチ処理サイズ**: 一度にLLMに渡す案件数

## 📊 出力ファイル

- **HTMLファイル**: `data/html/`
- **抽出された案件情報**: `data/jobs/`
- **マッチング結果**: `data/matches/matching_results_YYYYMMDD_HHMMSS.json`
- **ログファイル**: `logs/`

## 🔧 技術仕様

### 対応LLM
- **ローカル**: Ollama（Qwen2.5など）
- **API**: DeepSeek Chat、DeepSeek Coder

### スクレイピング機能
- ページネーション対応
- 複数カテゴリ対応
- 自動カテゴリ選択（LLM使用）

### マッチング機能
- ユーザープロファイルベースの評価
- 関連度スコア計算
- バッチ処理による効率化

## ⚠️ 注意事項

- スクレイピングの際は、対象サイトの利用規約を確認してください
- APIキーは適切に管理してください
- 大量のリクエストは避けてください
- ローカルLLM使用時は十分なメモリとストレージを確保してください

## 🆕 更新履歴

- **Web UI追加**: FastAPIベースのWebインターフェース
- **設定機能強化**: リアルタイム設定変更と保存
- **履歴管理**: 過去のマッチング結果の保存と表示
- **LLM選択機能**: ローカルとAPIの選択可能
- **バッチ処理**: 効率的な案件評価処理 