#!/bin/bash

# ポート8000を使用しているプロセスをチェック
echo "Checking if port 8000 is in use..."

# ポート8000を使用しているプロセスのPIDを取得
PID=$(lsof -ti:8000 2>/dev/null)

if [ ! -z "$PID" ]; then
    echo "Port 8000 is in use by process $PID. Killing the process..."
    kill -9 $PID
    sleep 2
    echo "Process killed."
else
    echo "Port 8000 is available."
fi

# Ollamaサーバーをバックグラウンドで起動
echo "Starting Ollama server..."
ollama serve &
OLLAMA_PID=$!

# Ollamaサーバーが起動するまで待機
sleep 5

# Webサーバーを起動
echo "Starting Web server on 0.0.0.0:8000..."
python simple_server.py 