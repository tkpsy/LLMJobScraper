from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import subprocess
import threading
import time
import json
from pathlib import Path

app = FastAPI(title="CrowdWorks Scraping API")

# 静的ファイル用のディレクトリを作成
static_dir = Path("static")
static_dir.mkdir(exist_ok=True)

# 静的ファイルをマウント
app.mount("/static", StaticFiles(directory="static"), name="static")

# 実行状態を管理
execution_status = {
    "is_running": False,
    "start_time": None,
    "end_time": None,
    "logs": [],
    "error": None
}

@app.get("/test")
async def test():
    """テスト用エンドポイント"""
    return {"message": "Server is running!", "status": "ok"}

@app.get("/", response_class=HTMLResponse)
async def home():
    """メインページ - 実行ボタンを表示"""
    html_content = """
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>CrowdWorks Scraping</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
                text-align: center;
                margin-bottom: 30px;
            }
            .execute-btn {
                display: block;
                width: 200px;
                height: 60px;
                margin: 20px auto;
                background-color: #007bff;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 18px;
                cursor: pointer;
                transition: background-color 0.3s;
            }
            .execute-btn:hover {
                background-color: #0056b3;
            }
            .execute-btn:disabled {
                background-color: #6c757d;
                cursor: not-allowed;
            }
            .status {
                margin-top: 20px;
                padding: 15px;
                border-radius: 5px;
                text-align: center;
            }
            .status.running {
                background-color: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }
            .status.completed {
                background-color: #d1ecf1;
                color: #0c5460;
                border: 1px solid #bee5eb;
            }
            .status.error {
                background-color: #f8d7da;
                color: #721c24;
                border: 1px solid #f5c6cb;
            }
            .logs {
                margin-top: 20px;
                padding: 15px;
                background-color: #f8f9fa;
                border-radius: 5px;
                max-height: 300px;
                overflow-y: auto;
                font-family: monospace;
                font-size: 14px;
                white-space: pre-wrap;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 CrowdWorks Scraping System</h1>
            
            <button id="executeBtn" class="execute-btn" onclick="executeScraping()">
                スクレイピング実行
            </button>
            
            <div id="status" class="status" style="display: none;"></div>
            
            <div id="logs" class="logs" style="display: none;"></div>
        </div>

        <script>
            let isRunning = false;
            
            async function executeScraping() {
                if (isRunning) return;
                
                const btn = document.getElementById('executeBtn');
                const status = document.getElementById('status');
                const logs = document.getElementById('logs');
                
                // ボタンを無効化
                btn.disabled = true;
                btn.textContent = '実行中...';
                isRunning = true;
                
                // ステータス表示
                status.style.display = 'block';
                status.className = 'status running';
                status.textContent = 'スクレイピングを開始しました...';
                
                // ログ表示エリアを表示
                logs.style.display = 'block';
                logs.textContent = '初期化中...\n';
                
                try {
                    // 実行開始
                    const response = await fetch('/api/execute', {
                        method: 'POST'
                    });
                    
                    if (!response.ok) {
                        throw new Error('実行に失敗しました');
                    }
                    
                    const result = await response.json();
                    
                    if (result.success) {
                        status.className = 'status completed';
                        status.textContent = 'スクレイピングが完了しました！';
                        logs.textContent += '✅ 完了\n';
                    } else {
                        throw new Error(result.error || '実行に失敗しました');
                    }
                    
                } catch (error) {
                    status.className = 'status error';
                    status.textContent = 'エラーが発生しました: ' + error.message;
                    logs.textContent += '❌ エラー: ' + error.message + '\n';
                } finally {
                    // ボタンを有効化
                    btn.disabled = false;
                    btn.textContent = 'スクレイピング実行';
                    isRunning = false;
                }
            }
            
            // ページ読み込み時にステータスをチェック
            window.onload = async function() {
                try {
                    const response = await fetch('/api/status');
                    const status = await response.json();
                    
                    if (status.is_running) {
                        document.getElementById('executeBtn').disabled = true;
                        document.getElementById('executeBtn').textContent = '実行中...';
                    }
                } catch (error) {
                    console.log('ステータスチェックエラー:', error);
                }
            };
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/api/execute")
async def execute_scraping():
    """main.pyを実行するAPIエンドポイント"""
    global execution_status
    
    if execution_status["is_running"]:
        return {"success": False, "error": "既に実行中です"}
    
    # 実行状態をリセット
    execution_status = {
        "is_running": True,
        "start_time": time.time(),
        "end_time": None,
        "logs": [],
        "error": None
    }
    
    def run_main_py():
        """main.pyを実行する関数"""
        global execution_status
        try:
            # main.pyを実行
            process = subprocess.Popen(
                ["python", "main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # 出力をリアルタイムで取得
            for line in process.stdout:
                execution_status["logs"].append(line.strip())
            
            # プロセス終了を待つ
            process.wait()
            
            if process.returncode == 0:
                execution_status["error"] = None
            else:
                execution_status["error"] = f"プロセスが終了コード {process.returncode} で終了しました"
                
        except Exception as e:
            execution_status["error"] = str(e)
        finally:
            execution_status["is_running"] = False
            execution_status["end_time"] = time.time()
    
    # 別スレッドで実行
    thread = threading.Thread(target=run_main_py)
    thread.daemon = True
    thread.start()
    
    return {"success": True, "message": "スクレイピングを開始しました"}

@app.get("/api/status")
async def get_status():
    """実行状態を取得するAPIエンドポイント"""
    return execution_status

@app.get("/api/logs")
async def get_logs():
    """ログを取得するAPIエンドポイント"""
    return {"logs": execution_status["logs"]}

if __name__ == "__main__":
    import uvicorn
    print("🚀 CrowdWorks Scraping Web Server を起動中...")
    print("📱 ブラウザで http://localhost:8000 にアクセスしてください")
    uvicorn.run("web_server:app", host="0.0.0.0", port=8000, reload=False) 