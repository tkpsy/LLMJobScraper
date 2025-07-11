# 🐳 Docker環境での実行ガイド

このプロジェクトはDocker環境で簡単に実行できるようになっています。

## 📋 必要な準備

### 1. 環境変数の設定
```bash
# .env.exampleをコピーして.envファイルを作成
cp .env.example .env

# .envファイルを編集してAPIキーを設定
# DEEPSEEK_API_KEY=your-actual-api-key
```

### 2. Docker環境の確認
- Docker Desktop または Docker Engine がインストールされていることを確認
- docker-compose が利用可能であることを確認

## 🚀 使用方法

### 初回セットアップ
```bash
# 初回セットアップ（イメージビルド + コンテナ起動）
./docker-run.sh setup
```

### コンテナに入ってコマンドを実行
```bash
# コンテナに入る
./docker-run.sh shell

# コンテナ内で以下のコマンドを実行
python main.py              # 手動モード
python main.py --auto       # 自動モード
```

### 直接アプリケーションを実行
```bash
# 手動モード
./docker-run.sh run

# 自動モード
./docker-run.sh run --auto
```

## 🛠️ 便利なコマンド

```bash
# Dockerイメージを再ビルド
./docker-run.sh build

# コンテナを起動
./docker-run.sh up

# コンテナに入る
./docker-run.sh shell

# アプリケーションを直接実行
./docker-run.sh run [オプション]

# コンテナを停止
./docker-run.sh down

# 使い方を表示
./docker-run.sh
```

## 📂 データの永続化

以下のディレクトリは自動的にホストマシンと同期されます：
- `./data/` - スクレイピングしたデータ
- `./logs/` - ログファイル
- `./categories.json` - カテゴリ設定ファイル

## 🔧 手動でDocker Composeを使用

```bash
# コンテナをビルドして起動
docker-compose up -d

# コンテナに入る
docker-compose exec llm-job-scraper bash

# アプリケーションを実行
docker-compose exec llm-job-scraper python main.py

# コンテナを停止
docker-compose down
```

## 🐛 トラブルシューティング

### 権限エラーが発生する場合
```bash
# スクリプトに実行権限を付与
chmod +x docker-run.sh
```

### コンテナが起動しない場合
```bash
# コンテナを完全に削除して再作成
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

### 環境変数が読み込まれない場合
```bash
# .envファイルが存在し、正しく設定されているか確認
cat .env
```

## 📝 注意事項

- 初回起動時はPlaywrightのブラウザダウンロードのため、時間がかかる場合があります
- 環境変数（DEEPSEEK_API_KEY）が正しく設定されていることを確認してください
- データファイルはホストマシンと同期されるため、コンテナを削除してもデータは保持されます 