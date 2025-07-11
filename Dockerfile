# Python 3.12 slim image
FROM python:3.12-slim

# システムパッケージのインストール
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 作業ディレクトリの設定
WORKDIR /app

# requirements.txtをコピーして依存関係をインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Playwrightのブラウザをインストール
RUN playwright install chromium
RUN playwright install-deps

# アプリケーションコードをコピー
COPY . .

# データディレクトリを作成
RUN mkdir -p data/html data/jobs data/matches logs

# デフォルトコマンド
CMD ["python", "main.py"] 