# Docker環境での使用方法

このドキュメントでは、Dockerを使用してCrowdWorks AI案件マッチングシステムを実行する方法を説明します。

## 🐳 前提条件

- Docker
- Docker Compose
- 十分なディスク容量（Ollamaモデル用）

## 🚀 クイックスタート

### 1. リポジトリのクローン
```bash
git clone <repository-url>
cd scraping_base
```

### 2. 環境変数の設定（オプション）
DeepSeek APIを使用する場合のみ必要です：
```bash
# .envファイルを作成
echo "DEEPSEEK_API_KEY=your_api_key_here" > .env
```

### 3. Docker Composeで起動
```bash
# コンテナをビルドして起動
docker-compose up --build

# バックグラウンドで実行する場合
docker-compose up -d --build
```

### 4. ブラウザでアクセス
```
http://localhost:8000
```

## 📋 詳細手順

### 初回セットアップ

1. **Ollamaモデルのダウンロード**
   ```bash
   # コンテナが起動した後、Ollamaコンテナに接続
   docker exec -it ollama ollama pull elyza:jp8b
   
   # 他のモデルも必要に応じてダウンロード
   docker exec -it ollama ollama pull llama3.2:3b
   docker exec -it ollama ollama pull mistral:7b
   ```

2. **設定の確認**
   - Web UIの設定タブでデフォルト設定を確認
   - 必要に応じてユーザープロファイルを設定

### 通常の使用方法

1. **システムの起動**
   ```bash
   docker-compose up -d
   ```

2. **Web UIでの操作**
   - ブラウザで http://localhost:8000 にアクセス
   - 設定タブでユーザープロファイルとLLM設定を調整
   - スクレイピング実行タブで案件収集を開始

3. **システムの停止**
   ```bash
   docker-compose down
   ```

## 🔧 設定とカスタマイズ

### 環境変数

`.env`ファイルで以下の環境変数を設定できます：

```bash
# DeepSeek API使用時のみ
DEEPSEEK_API_KEY=your_api_key_here

# Ollamaホストのカスタマイズ（通常は変更不要）
OLLAMA_HOST=http://ollama:11434
```

### データの永続化

以下のディレクトリがホストマシンにマウントされます：

- `./data/` - スクレイピングデータとマッチング結果
- `./logs/` - ログファイル
- `./web_config.json` - Web設定ファイル

### ボリューム

- `ollama_data` - Ollamaモデルデータ（永続化）

## 🐛 トラブルシューティング

### よくある問題

1. **ポート8000が使用中**
   ```bash
   # 別のポートを使用
   docker-compose up -p 8001:8000
   ```

2. **Ollamaモデルが見つからない**
   ```bash
   # モデルを再ダウンロード
   docker exec -it ollama ollama pull elyza:jp8b
   ```

3. **メモリ不足**
   ```bash
   # Dockerのメモリ制限を増やす
   # Docker Desktop設定で確認・変更
   ```

4. **設定ファイルの権限問題**
   ```bash
   # ホスト側でファイルを作成
   touch web_config.json
   chmod 666 web_config.json
   ```

### ログの確認

```bash
# アプリケーションログ
docker-compose logs llm-job-scraper

# Ollamaログ
docker-compose logs ollama

# リアルタイムログ
docker-compose logs -f
```

## 🔄 更新とメンテナンス

### システムの更新

```bash
# 最新のコードを取得
git pull

# コンテナを再ビルド
docker-compose down
docker-compose up --build -d
```

### データのバックアップ

```bash
# データディレクトリのバックアップ
tar -czf backup_$(date +%Y%m%d).tar.gz data/ logs/ web_config.json
```

### 完全リセット

```bash
# すべてのコンテナとボリュームを削除
docker-compose down -v
docker system prune -a

# データディレクトリも削除（注意！）
rm -rf data/ logs/ web_config.json
```

## 📊 パフォーマンス

### 推奨システム要件

- **CPU**: 4コア以上
- **メモリ**: 8GB以上（Ollama使用時は16GB推奨）
- **ストレージ**: 20GB以上の空き容量
- **ネットワーク**: 安定したインターネット接続

### 最適化のヒント

1. **Ollamaモデルの選択**
   - 軽量モデル（3B）: 高速、低メモリ使用量
   - 高精度モデル（7B+）: 高精度、高メモリ使用量

2. **バッチサイズの調整**
   - Web UIの設定でバッチ処理サイズを調整
   - メモリ使用量と処理速度のバランス

3. **並行処理の制限**
   - 大量の案件を処理する場合は段階的に実行

## 🔒 セキュリティ

### 注意事項

- `.env`ファイルにAPIキーを保存する場合は適切に保護
- 本番環境ではHTTPSの使用を推奨
- ファイアウォールで不要なポートを閉じる

### 本番環境での設定

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  llm-job-scraper:
    # 本番用の設定
    environment:
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
    ports:
      - "127.0.0.1:8000:8000"  # localhostのみにバインド
```

## 📞 サポート

問題が発生した場合は、以下を確認してください：

1. DockerとDocker Composeのバージョン
2. システムリソース（メモリ、ディスク容量）
3. ネットワーク接続
4. ログファイルの内容

詳細なログとエラーメッセージを添えて、GitHubのIssuesで報告してください。 