from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import subprocess
import threading
import time
import json
import glob
from pathlib import Path
from datetime import datetime

app = FastAPI()

# 実行状態を管理
execution_status = {
    "is_running": False,
    "logs": [],
    "error": None,
    "progress": 0
}

# 設定ファイルのパス
CONFIG_FILE = Path("web_config.json")

def load_web_config():
    """Web設定を読み込み"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return get_default_config()

def save_web_config(config):
    """Web設定を保存"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def get_default_config():
    """デフォルト設定を取得"""
    return {
        "user_profile": {
            "skills": ["Python", "機械学習", "AI", "データサイエンス", "ChatGPT", "深層学習", "自然言語処理", "Web制作", "デザイン"],
            "preferred_categories": ["AI・機械学習", "機械学習・ディープラーニング", "ChatGPT開発", "AI・チャットボット開発"],
            "preferred_work_type": ["リモート", "フルリモート", "在宅"],
            "description": "AI・機械学習分野でのフリーランス案件を探しています。特にChatGPT、LLM、深層学習関連の案件に興味があります。Python、TensorFlow、PyTorchを使った開発経験があります。また，Next.jsなどを利用したフロントエンドやバックエンドの開発経験があります。"
        },
        "llm_settings": {
            "type": "local",
            "model": "qwen2.5:latest",
            "temperature": 0.2,
            "max_categories": 3,
            "min_relevance_score": 7.0
        },
        "matching_settings": {
            "min_score": 80.0,
            "max_jobs": 20,
            "batch_size": 10
        }
    }

def get_latest_matching_results():
    """最新のマッチング結果ファイルを取得"""
    matches_dir = Path("data/matches")
    if not matches_dir.exists():
        return None
    
    # matching_results_*.jsonファイルを検索
    json_files = list(matches_dir.glob("matching_results_*.json"))
    if not json_files:
        return None
    
    # 最新のファイルを取得
    latest_file = max(json_files, key=lambda x: x.stat().st_mtime)
    
    try:
        with open(latest_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"マッチング結果ファイル読み込みエラー: {e}")
        return None

def get_all_matching_results():
    """全てのマッチング結果ファイル一覧を取得"""
    matches_dir = Path("data/matches")
    if not matches_dir.exists():
        return []
    
    # matching_results_*.jsonファイルを検索
    json_files = list(matches_dir.glob("matching_results_*.json"))
    
    results = []
    for file_path in sorted(json_files, key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                results.append({
                    "filename": file_path.name,
                    "filepath": str(file_path),
                    "timestamp": file_path.stat().st_mtime,
                    "date": datetime.fromtimestamp(file_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                    "match_count": len(data.get('マッチング結果', [])),
                    "data": data
                })
        except Exception as e:
            print(f"ファイル読み込みエラー {file_path}: {e}")
    
    return results

def get_matching_result_by_filename(filename):
    """指定されたファイル名のマッチング結果を取得"""
    matches_dir = Path("data/matches")
    file_path = matches_dir / filename
    
    if not file_path.exists():
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"マッチング結果ファイル読み込みエラー: {e}")
        return None

@app.get("/")
async def home():
    """メインページ"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>CrowdWorks Scraping</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            .btn { 
                background: #007bff; 
                color: white; 
                padding: 15px 30px; 
                border: none; 
                border-radius: 5px; 
                font-size: 16px; 
                cursor: pointer; 
                margin: 5px;
            }
            .btn:disabled { background: #6c757d; cursor: not-allowed; }
            .btn-secondary {
                background: #6c757d;
            }
            .btn-secondary:hover {
                background: #545b62;
            }
            .status { margin: 20px 0; padding: 10px; border-radius: 5px; }
            .running { background: #d4edda; color: #155724; }
            .completed { background: #d1ecf1; color: #0c5460; }
            .error { background: #f8d7da; color: #721c24; }
            .progress-bar {
                width: 100%;
                height: 20px;
                background-color: #f0f0f0;
                border-radius: 10px;
                overflow: hidden;
                margin: 10px 0;
            }
            .progress-fill {
                height: 100%;
                background-color: #007bff;
                width: 0%;
                transition: width 0.3s ease;
            }
            .logs {
                margin-top: 20px;
                padding: 10px;
                background: #f8f9fa;
                border-radius: 5px;
                font-family: monospace;
                white-space: pre-wrap;
                max-height: 400px;
                overflow-y: auto;
                display: none;
            }
            .results-container {
                margin-top: 30px;
                display: none;
            }
            .job-card {
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 15px;
                margin: 10px 0;
                background: white;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            .job-title {
                font-size: 18px;
                font-weight: bold;
                color: #333;
                margin-bottom: 10px;
            }
            .job-meta {
                display: flex;
                flex-wrap: wrap;
                gap: 15px;
                margin-bottom: 10px;
                font-size: 14px;
            }
            .job-meta span {
                background: #f8f9fa;
                padding: 4px 8px;
                border-radius: 4px;
            }
            .job-description {
                color: #666;
                line-height: 1.5;
                margin-bottom: 10px;
            }
            .job-budget {
                font-weight: bold;
                color: #28a745;
            }
            .score-badge {
                background: #007bff;
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            .tabs {
                display: flex;
                margin-bottom: 20px;
                border-bottom: 1px solid #ddd;
            }
            .tab {
                padding: 10px 20px;
                cursor: pointer;
                border: none;
                background: none;
                border-bottom: 2px solid transparent;
            }
            .tab.active {
                border-bottom-color: #007bff;
                color: #007bff;
                font-weight: bold;
            }
            .tab-content {
                display: none;
            }
            .tab-content.active {
                display: block;
            }
            .form-group {
                margin-bottom: 15px;
            }
            .form-group label {
                display: block;
                margin-bottom: 5px;
                font-weight: bold;
            }
            .form-control {
                width: 100%;
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
            }
            .form-control:focus {
                outline: none;
                border-color: #007bff;
                box-shadow: 0 0 0 2px rgba(0,123,255,0.25);
            }
            textarea.form-control {
                resize: vertical;
                min-height: 100px;
            }
            .btn-primary {
                background: #007bff;
            }
            .btn-primary:hover {
                background: #0056b3;
            }
            .results-header {
                display: flex;
                align-items: center;
                gap: 15px;
                margin-bottom: 20px;
                flex-wrap: wrap;
            }
            .results-header h2 {
                margin: 0;
                flex: 1;
            }
            .file-selector {
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .file-selector label {
                margin: 0;
                white-space: nowrap;
            }
            .file-selector .form-control {
                width: 300px;
            }
            .no-results {
                text-align: center;
                padding: 40px;
                color: #666;
                font-style: italic;
            }
        </style>
    </head>
    <body>
        <h1>🤖 CrowdWorks Scraping System</h1>
        
        <div class="tabs">
            <button class="tab active" onclick="showTab('scraping')">スクレイピング実行</button>
            <button class="tab" onclick="showTab('results')">マッチング結果</button>
            <button class="tab" onclick="showTab('settings')">設定</button>
        </div>
        
        <div id="scraping-tab" class="tab-content active">
            <button id="executeBtn" class="btn" onclick="executeScraping()">
                スクレイピング実行
            </button>
            <div id="status" class="status" style="display: none;"></div>
            <div id="progressContainer" style="display: none;">
                <div class="progress-bar">
                    <div id="progressFill" class="progress-fill"></div>
                </div>
                <div id="progressText">0%</div>
            </div>
            <div id="logs" class="logs"></div>
        </div>
        
        <div id="results-tab" class="tab-content">
            <div class="results-header">
                <h2>マッチング結果</h2>
                <div class="file-selector">
                    <label for="resultFileSelect">実行履歴から選択:</label>
                    <select id="resultFileSelect" class="form-control" onchange="loadSelectedResult()">
                        <option value="">最新の結果を表示</option>
                    </select>
                </div>
                <button class="btn btn-secondary" onclick="loadAllResults()">履歴を更新</button>
            </div>
            <div id="resultsContainer" class="results-container">
                <div id="resultsInfo"></div>
                <div id="jobsList"></div>
            </div>
        </div>

        <div id="settings-tab" class="tab-content">
            <h2>設定</h2>
            
            <div style="background: #f8f9fa; border-left: 4px solid #007bff; padding: 15px; margin-bottom: 20px; border-radius: 4px;">
                <h4 style="margin-top: 0; color: #007bff;">💡 設定の説明</h4>
                <p style="margin-bottom: 10px;"><strong>カテゴリ選択の閾値:</strong> LLMがあなたのスキルに基づいてカテゴリを選択する際の厳選度（0-10点）</p>
                <p style="margin-bottom: 10px;"><strong>案件推薦の閾値:</strong> 個別の案件があなたに合致するかの判定基準（0-100点）</p>
                <p style="margin-bottom: 10px;"><strong>LLM創造性レベル:</strong> AIの応答の創造性を制御（0.0=一貫性重視、2.0=創造性重視）</p>
                <p style="margin-bottom: 10px;"><strong>検索対象カテゴリ数:</strong> あなたのスキルに基づいて検索するカテゴリの最大数</p>
                <p style="margin-bottom: 10px;"><strong>最大案件数:</strong> 推薦する案件の最大数。多いほど多くの案件が表示されます</p>
                <p style="margin-bottom: 0;"><strong>バッチ処理サイズ:</strong> 一度にLLMに渡す案件数。大きくしすぎると精度が落ちる可能性があります。</p>
            </div>
            
            <div id="settingsContent">
                <form id="settingsForm">
                    <div class="form-group">
                        <label for="userSkills">スキル:</label>
                        <input type="text" id="userSkills" class="form-control" placeholder="Python, 機械学習, AI, データサイエンス...">
                    </div>
                    <div class="form-group">
                        <label for="preferredCategories">好みのカテゴリ:</label>
                        <input type="text" id="preferredCategories" class="form-control" placeholder="AI・機械学習, 機械学習・ディープラーニング...">
                    </div>
                    <div class="form-group">
                        <label for="preferredWorkType">好みの勤務地:</label>
                        <input type="text" id="preferredWorkType" class="form-control" placeholder="リモート, フルリモート, 在宅">
                    </div>
                    <div class="form-group">
                        <label for="userDescription">自己紹介:</label>
                        <textarea id="userDescription" class="form-control" rows="5" placeholder="あなたのスキルや経験について説明してください..."></textarea>
                    </div>
                    
                    <h3 style="margin-top: 30px; margin-bottom: 15px; color: #007bff; border-bottom: 2px solid #007bff; padding-bottom: 5px;">🤖 LLM設定</h3>
                    
                    <div class="form-group">
                        <label for="llmType">LLMタイプ:</label>
                        <select id="llmType" class="form-control" onchange="updateModelOptions()">
                            <option value="local">Local (Ollama)</option>
                            <option value="deepseek">DeepSeek API</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="llmModel">LLMモデル:</label>
                        <select id="llmModel" class="form-control">
                            <option value="qwen2.5:latest">Qwen2.5 (Local)</option>
                            <option value="deepseek-chat">DeepSeek Chat</option>
                            <option value="gpt-4">GPT-4</option>
                            <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label for="llmTemperature">LLM創造性レベル:</label>
                        <input type="number" id="llmTemperature" class="form-control" value="0.1" step="0.1" min="0" max="2">
                        <small class="form-text text-muted">AIの応答の創造性を制御（0.0=一貫性重視、2.0=創造性重視）。低い値ほど安定した結果が得られます。</small>
                    </div>
                    <div class="form-group">
                        <label for="maxCategories">検索対象カテゴリ数:</label>
                        <input type="number" id="maxCategories" class="form-control" value="3" min="1" max="10">
                        <small class="form-text text-muted">あなたのスキルに基づいて検索するカテゴリの最大数。多いほど幅広い案件が見つかりますが、処理時間が長くなります。</small>
                    </div>
                    
                    <h3 style="margin-top: 30px; margin-bottom: 15px; color: #28a745; border-bottom: 2px solid #28a745; padding-bottom: 5px;">🎯 フィルタリング設定</h3>
                    
                    <div class="form-group">
                        <label for="minRelevanceScore">カテゴリ選択の閾値 (0-10点):</label>
                        <input type="number" id="minRelevanceScore" class="form-control" value="7.0" step="0.5" min="0" max="10">
                        <small class="form-text text-muted">LLMがカテゴリを選択する際の関連度スコアの最小値。高いほど厳選されたカテゴリのみが選択されます。</small>
                    </div>
                    <div class="form-group">
                        <label for="minScore">案件推薦の閾値 (0-100点):</label>
                        <input type="number" id="minScore" class="form-control" value="70.0" step="5" min="0" max="100">
                        <small class="form-text text-muted">個別案件のマッチングスコアの最小値。高いほど厳選された案件のみが推薦されます。</small>
                    </div>
                    <div class="form-group">
                        <label for="maxJobs">最大案件数:</label>
                        <input type="number" id="maxJobs" class="form-control" value="5" min="1" max="20">
                        <small class="form-text text-muted">推薦する案件の最大数。多いほど多くの案件が表示されますが、関連性の低い案件も含まれる可能性があります。</small>
                    </div>
                    <div class="form-group">
                        <label for="batchSize">バッチ処理サイズ:</label>
                        <input type="number" id="batchSize" class="form-control" value="3" min="1" max="10">
                        <small class="form-text text-muted">一度にLLMに渡す案件数。大きくしすぎると精度が落ちる可能性があります。</small>
                    </div>
                    <button type="submit" class="btn btn-primary">設定を保存</button>
                </form>
            </div>
        </div>

        <script>
            let isRunning = false;
            let progressInterval = null;
            
            // ページ読み込み時に設定を読み込む
            document.addEventListener('DOMContentLoaded', function() {
                loadSettings();
                loadAllResults(); // 結果履歴も読み込む
                updateModelOptions(); // LLMタイプに応じてモデルオプションを初期化
            });
            
            function showTab(tabName) {
                // タブを非アクティブにする
                document.querySelectorAll('.tab').forEach(tab => {
                    tab.classList.remove('active');
                });
                document.querySelectorAll('.tab-content').forEach(content => {
                    content.classList.remove('active');
                });
                
                // 選択されたタブをアクティブにする
                event.target.classList.add('active');
                document.getElementById(tabName + '-tab').classList.add('active');
                
                // 結果タブが選択された場合、自動的に結果を読み込む
                if (tabName === 'results') {
                    loadAllResults();
                }
            }
            
            async function loadSettings() {
                try {
                    const response = await fetch('/api/settings');
                    const data = await response.json();
                    
                    if (data.success) {
                        const config = data.config;
                        
                        // フォームに値を設定
                        document.getElementById('userSkills').value = config.user_profile.skills.join(', ');
                        document.getElementById('preferredCategories').value = config.user_profile.preferred_categories.join(', ');
                        document.getElementById('preferredWorkType').value = config.user_profile.preferred_work_type.join(', ');
                        document.getElementById('userDescription').value = config.user_profile.description;
                        document.getElementById('llmType').value = config.llm_settings.type;
                        document.getElementById('llmModel').value = config.llm_settings.model;
                        document.getElementById('llmTemperature').value = config.llm_settings.temperature;
                        document.getElementById('maxCategories').value = config.llm_settings.max_categories;
                        document.getElementById('minRelevanceScore').value = config.llm_settings.min_relevance_score;
                        document.getElementById('minScore').value = config.matching_settings.min_score;
                        document.getElementById('maxJobs').value = config.matching_settings.max_jobs;
                        document.getElementById('batchSize').value = config.matching_settings.batch_size;
                    }
                } catch (error) {
                    console.error('設定読み込みエラー:', error);
                }
            }
            
            // 設定フォームの送信処理
            document.getElementById('settingsForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const config = {
                    user_profile: {
                        skills: document.getElementById('userSkills').value.split(',').map(s => s.trim()).filter(s => s),
                        preferred_categories: document.getElementById('preferredCategories').value.split(',').map(s => s.trim()).filter(s => s),
                        preferred_work_type: document.getElementById('preferredWorkType').value.split(',').map(s => s.trim()).filter(s => s),
                        description: document.getElementById('userDescription').value
                    },
                    llm_settings: {
                        type: document.getElementById('llmType').value,
                        model: document.getElementById('llmModel').value,
                        temperature: parseFloat(document.getElementById('llmTemperature').value),
                        max_categories: parseInt(document.getElementById('maxCategories').value),
                        min_relevance_score: parseFloat(document.getElementById('minRelevanceScore').value)
                    },
                    matching_settings: {
                        min_score: parseFloat(document.getElementById('minScore').value),
                        max_jobs: parseInt(document.getElementById('maxJobs').value),
                        batch_size: parseInt(document.getElementById('batchSize').value)
                    }
                };
                
                try {
                    const response = await fetch('/api/settings', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(config)
                    });
                    
                    const result = await response.json();
                    if (result.success) {
                        alert('設定を保存しました！');
                    } else {
                        alert('設定の保存に失敗しました: ' + result.error);
                    }
                } catch (error) {
                    console.error('設定保存エラー:', error);
                    alert('設定の保存に失敗しました');
                }
            });
            
            // LLMタイプに応じてモデルオプションを更新
            function updateModelOptions() {
                const llmType = document.getElementById('llmType').value;
                const modelSelect = document.getElementById('llmModel');
                
                // 既存のオプションをクリア
                modelSelect.innerHTML = '';
                
                if (llmType === 'local') {
                    // Ollamaモデル
                    const localModels = [
                        { value: 'qwen2.5:latest', text: 'Qwen2.5 (Local)' },
                        { value: 'llama3.2:3b', text: 'Llama 3.2 3B (Local)' },
                        { value: 'llama3.2:7b', text: 'Llama 3.2 7B (Local)' },
                        { value: 'mistral:7b', text: 'Mistral 7B (Local)' }
                    ];
                    localModels.forEach(model => {
                        const option = document.createElement('option');
                        option.value = model.value;
                        option.textContent = model.text;
                        modelSelect.appendChild(option);
                    });
                } else if (llmType === 'deepseek') {
                    // DeepSeekモデル
                    const deepseekModels = [
                        { value: 'deepseek-chat', text: 'DeepSeek Chat' },
                        { value: 'deepseek-coder', text: 'DeepSeek Coder' }
                    ];
                    deepseekModels.forEach(model => {
                        const option = document.createElement('option');
                        option.value = model.value;
                        option.textContent = model.text;
                        modelSelect.appendChild(option);
                    });
                }
                
                // デフォルト値を設定
                if (llmType === 'local') {
                    modelSelect.value = 'qwen2.5:latest';
                } else if (llmType === 'deepseek') {
                    modelSelect.value = 'deepseek-chat';
                }
            }
            
            async function loadAllResults() {
                try {
                    const response = await fetch('/api/all_results');
                    const data = await response.json();
                    
                    if (data.success) {
                        const select = document.getElementById('resultFileSelect');
                        select.innerHTML = '<option value="">最新の結果を表示</option>';
                        
                        data.results.forEach(result => {
                            const option = document.createElement('option');
                            option.value = result.filename;
                            option.textContent = `${result.date} (${result.match_count}件)`;
                            select.appendChild(option);
                        });
                        
                        // 最新の結果を表示
                        if (data.results.length > 0) {
                            displayResults(data.results[0].data);
                        } else {
                            displayNoResults();
                        }
                    } else {
                        displayNoResults();
                    }
                } catch (error) {
                    console.error('結果履歴読み込みエラー:', error);
                    displayNoResults();
                }
            }
            
            async function loadSelectedResult() {
                const select = document.getElementById('resultFileSelect');
                const selectedFile = select.value;
                
                if (!selectedFile) {
                    // 最新の結果を表示
                    await loadAllResults();
                    return;
                }
                
                try {
                    const response = await fetch(`/api/results/${selectedFile}`);
                    const data = await response.json();
                    
                    if (data.success) {
                        displayResults(data.results);
                    } else {
                        displayNoResults();
                    }
                } catch (error) {
                    console.error('結果読み込みエラー:', error);
                    displayNoResults();
                }
            }
            
            function displayResults(results) {
                const container = document.getElementById('resultsContainer');
                const info = document.getElementById('resultsInfo');
                const jobsList = document.getElementById('jobsList');
                
                container.style.display = 'block';
                
                // 実行情報を表示
                info.innerHTML = `
                    <p><strong>実行日時:</strong> ${results['実行日時']}</p>
                    <p><strong>マッチング件数:</strong> ${results['マッチング結果'].length}件</p>
                `;
                
                // 案件一覧を表示
                jobsList.innerHTML = '';
                results['マッチング結果'].forEach((match, index) => {
                    const job = match['案件情報'];
                    const score = match['マッチング詳細']['関連度スコア'];
                    
                    const budgetText = job.budget.min_amount && job.budget.max_amount 
                        ? `${job.budget.min_amount.toLocaleString()}円 ～ ${job.budget.max_amount.toLocaleString()}円`
                        : job.budget.is_negotiable ? '相談' : '未定';
                    
                    const jobCard = document.createElement('div');
                    jobCard.className = 'job-card';
                    jobCard.innerHTML = `
                        <div style="display: flex; justify-content: space-between; align-items: start;">
                            <div class="job-title">${job.title}</div>
                            <span class="score-badge">${score}点</span>
                        </div>
                        <div class="job-meta">
                            <span>カテゴリ: ${job.category}</span>
                            <span>クライアント: ${job.client_name}</span>
                            <span>期限: ${job.deadline}</span>
                            <span class="job-budget">予算: ${budgetText}</span>
                        </div>
                        <div class="job-description">${job.description.substring(0, 200)}...</div>
                        <a href="https://crowdworks.jp${job.url}" target="_blank" class="btn btn-secondary">詳細を見る</a>
                    `;
                    jobsList.appendChild(jobCard);
                });
            }
            
            function displayNoResults() {
                const container = document.getElementById('resultsContainer');
                const info = document.getElementById('resultsInfo');
                const jobsList = document.getElementById('jobsList');
                
                container.style.display = 'block';
                info.innerHTML = '';
                jobsList.innerHTML = '<div class="no-results">マッチング結果が見つかりませんでした。</div>';
            }
            
            // 後方互換性のため、古い関数名も残す
            async function loadResults() {
                await loadAllResults();
            }
            
            async function executeScraping() {
                if (isRunning) return;
                
                const btn = document.getElementById('executeBtn');
                const status = document.getElementById('status');
                const logs = document.getElementById('logs');
                const progressContainer = document.getElementById('progressContainer');
                const progressFill = document.getElementById('progressFill');
                const progressText = document.getElementById('progressText');
                
                btn.disabled = true;
                btn.textContent = '実行中...';
                isRunning = true;
                
                status.style.display = 'block';
                status.className = 'status running';
                status.textContent = 'スクレイピングを開始しました...';
                
                progressContainer.style.display = 'block';
                progressFill.style.width = '0%';
                progressText.textContent = '0%';
                
                logs.style.display = 'block';
                logs.textContent = '初期化中...\\n';
                
                try {
                    const response = await fetch('/api/execute', { method: 'POST' });
                    const result = await response.json();
                    
                    if (result.success) {
                        startProgressMonitoring();
                    } else {
                        throw new Error(result.error || '実行に失敗しました');
                    }
                } catch (error) {
                    status.className = 'status error';
                    status.textContent = 'エラー: ' + error.message;
                    logs.textContent += '❌ エラー: ' + error.message + '\\n';
                    stopProgressMonitoring();
                    resetUI();
                }
            }
            
            function startProgressMonitoring() {
                progressInterval = setInterval(async () => {
                    try {
                        const response = await fetch('/api/status');
                        const status = await response.json();
                        
                        if (status.logs && status.logs.length > 0) {
                            const logs = document.getElementById('logs');
                            logs.textContent = status.logs.join('\\n');
                            logs.scrollTop = logs.scrollHeight;
                        }
                        
                        if (status.progress !== undefined) {
                            const progressFill = document.getElementById('progressFill');
                            const progressText = document.getElementById('progressText');
                            progressFill.style.width = status.progress + '%';
                            progressText.textContent = status.progress + '%';
                        }
                        
                        if (!status.is_running) {
                            stopProgressMonitoring();
                            
                            const statusDiv = document.getElementById('status');
                            if (status.error) {
                                statusDiv.className = 'status error';
                                statusDiv.textContent = 'エラー: ' + status.error;
                            } else {
                                statusDiv.className = 'status completed';
                                statusDiv.textContent = 'スクレイピングが完了しました！';
                            }
                            
                            resetUI();
                        }
                    } catch (error) {
                        console.error('進捗監視エラー:', error);
                    }
                }, 1000);
            }
            
            function stopProgressMonitoring() {
                if (progressInterval) {
                    clearInterval(progressInterval);
                    progressInterval = null;
                }
            }
            
            function resetUI() {
                const btn = document.getElementById('executeBtn');
                btn.disabled = false;
                btn.textContent = 'スクレイピング実行';
                isRunning = false;
            }
            
            window.onload = async function() {
                try {
                    const response = await fetch('/api/status');
                    const status = await response.json();
                    
                    if (status.is_running) {
                        document.getElementById('executeBtn').disabled = true;
                        document.getElementById('executeBtn').textContent = '実行中...';
                        startProgressMonitoring();
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

@app.get("/test")
async def test():
    """テスト用エンドポイント"""
    return {"message": "Server is running!", "status": "ok"}

@app.get("/api/results")
async def get_results():
    """最新のマッチング結果を取得"""
    results = get_latest_matching_results()
    if results:
        return {"success": True, "results": results}
    else:
        return {"success": False, "error": "マッチング結果が見つかりません"}

@app.get("/api/all_results")
async def get_all_results():
    """全てのマッチング結果ファイル一覧を取得"""
    results = get_all_matching_results()
    return {"success": True, "results": results}

@app.get("/api/results/{filename}")
async def get_result_by_filename(filename: str):
    """指定されたファイル名のマッチング結果を取得"""
    result = get_matching_result_by_filename(filename)
    if result:
        return {"success": True, "results": result}
    else:
        return {"success": False, "error": "マッチング結果が見つかりません"}

@app.get("/api/settings")
async def get_settings():
    """設定を取得"""
    try:
        config = load_web_config()
        return {"success": True, "config": config}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/settings")
async def save_settings(request: dict):
    """設定を保存"""
    try:
        save_web_config(request)
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.post("/api/execute")
async def execute_scraping():
    """スクレイピングを実行"""
    if execution_status["is_running"]:
        return {"success": False, "error": "既に実行中です"}
    
    execution_status["is_running"] = True
    execution_status["logs"] = []
    execution_status["error"] = None
    execution_status["progress"] = 0
    
    def run_main_py():
        try:
            # 設定ファイルを一時的に更新
            web_config = load_web_config()
            update_config_with_web_settings(web_config)
            
            # main.pyを実行
            process = subprocess.Popen(
                ["python", "main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # ログをリアルタイムで取得
            for line in process.stdout:
                execution_status["logs"].append(line.strip())
                if "進捗:" in line:
                    try:
                        progress_match = line.split("進捗:")[1].strip()
                        if "%" in progress_match:
                            progress = int(progress_match.split("%")[0])
                            execution_status["progress"] = progress
                    except:
                        pass
            
            process.wait()
            
            if process.returncode == 0:
                execution_status["progress"] = 100
            else:
                execution_status["error"] = "実行中にエラーが発生しました"
                
        except Exception as e:
            execution_status["error"] = str(e)
        finally:
            execution_status["is_running"] = False
    
    thread = threading.Thread(target=run_main_py)
    thread.start()
    
    return {"success": True, "message": "スクレイピングを開始しました"}

def update_config_with_web_settings(web_config):
    """Web設定をconfig.pyに反映"""
    try:
        # config.pyを読み込み
        config_content = Path("src/utils/config.py").read_text(encoding='utf-8')
        
        # ユーザープロファイル設定を更新
        user_profile_config = {
            "skills": web_config["user_profile"]["skills"],
            "preferred_categories": web_config["user_profile"]["preferred_categories"],
            "preferred_work_type": web_config["user_profile"]["preferred_work_type"],
            "description": web_config["user_profile"]["description"]
        }
        config_content = update_config_section(
            config_content, 
            "USER_PROFILE_CONFIG", 
            user_profile_config
        )
        
        # LLM設定を更新
        llm_config = {
            "max_categories": web_config["llm_settings"]["max_categories"],
            "min_relevance_score": web_config["llm_settings"]["min_relevance_score"],
            "llm_type": web_config["llm_settings"]["type"],
            "llm_model": web_config["llm_settings"]["model"],
            "temperature": web_config["llm_settings"]["temperature"],
            "max_tokens": 1000
        }
        config_content = update_config_section(
            config_content, 
            "LLM_CATEGORY_SELECTION_CONFIG", 
            llm_config
        )
        
        # マッチング設定を更新
        matching_config = {
            "min_score": web_config["matching_settings"]["min_score"],
            "max_jobs": web_config["matching_settings"]["max_jobs"],
            "batch_size": web_config["matching_settings"]["batch_size"],
            "llm_type": web_config["llm_settings"]["type"],
            "llm_model": web_config["llm_settings"]["model"],
            "temperature": web_config["llm_settings"]["temperature"]
        }
        config_content = update_config_section(
            config_content, 
            "MATCHING_CONFIG", 
            matching_config
        )
        
        # 設定ファイルを保存
        Path("src/utils/config.py").write_text(config_content, encoding='utf-8')
        
    except Exception as e:
        print(f"設定更新エラー: {e}")

def update_config_section(config_content, section_name, new_values):
    """設定セクションを更新"""
    import re
    
    # セクションの開始と終了を検索
    start_pattern = rf"^{section_name}\s*=\s*\{{"
    end_pattern = r"^\}"
    
    lines = config_content.split('\n')
    start_line = None
    end_line = None
    
    for i, line in enumerate(lines):
        if re.match(start_pattern, line.strip()):
            start_line = i
        elif start_line is not None and re.match(end_pattern, line.strip()):
            end_line = i
            break
    
    if start_line is not None and end_line is not None:
        # 新しい設定値を生成
        new_section = f"{section_name} = {{\n"
        for key, value in new_values.items():
            if isinstance(value, str):
                new_section += f'    "{key}": "{value}",\n'
            elif isinstance(value, list):
                new_section += f'    "{key}": {repr(value)},\n'
            else:
                new_section += f'    "{key}": {value},\n'
        new_section += "}\n"
        
        # セクションを置換
        lines[start_line:end_line+1] = new_section.split('\n')
        return '\n'.join(lines)
    
    return config_content

@app.get("/api/status")
async def get_status():
    """実行状態を取得"""
    return execution_status

if __name__ == "__main__":
    import uvicorn
    import socket
    import subprocess
    import sys
    
    def check_port_in_use(port):
        """ポートが使用中かチェック"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(('localhost', port)) == 0
    
    def kill_process_on_port(port):
        """指定ポートを使用しているプロセスを終了"""
        try:
            # 方法1: lsofでポートを使用しているプロセスのPIDを取得
            try:
                result = subprocess.run(['lsof', '-ti', f':{port}'], 
                                      capture_output=True, text=True)
                if result.stdout.strip():
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        if pid:
                            print(f"ポート{port}を使用しているプロセス {pid} を終了します...")
                            subprocess.run(['kill', '-9', pid])
                            print(f"プロセス {pid} を終了しました")
                    return True
            except FileNotFoundError:
                print("lsofコマンドが見つかりません。別の方法でプロセスを終了します...")
            
            # 方法2: netstatでポートを使用しているプロセスのPIDを取得
            try:
                result = subprocess.run(['netstat', '-tlnp'], 
                                      capture_output=True, text=True)
                for line in result.stdout.split('\n'):
                    if f':{port}' in line and 'LISTEN' in line:
                        parts = line.split()
                        if len(parts) >= 7:
                            pid_part = parts[6]
                            if '/' in pid_part:
                                pid = pid_part.split('/')[0]
                                print(f"ポート{port}を使用しているプロセス {pid} を終了します...")
                                subprocess.run(['kill', '-9', pid])
                                print(f"プロセス {pid} を終了しました")
                                return True
            except Exception as e:
                print(f"netstatエラー: {e}")
                
        except Exception as e:
            print(f"プロセス終了エラー: {e}")
        return False
    
    # ポート8000が使用中かチェック
    if check_port_in_use(8000):
        print("⚠️  ポート8000が使用中です。既存のプロセスを終了します...")
        if kill_process_on_port(8000):
            print("✅ 既存のプロセスを終了しました")
        else:
            print("❌ プロセスの終了に失敗しました")
            sys.exit(1)
    
    print("🚀 シンプルWebサーバーを起動中...")
    print("📱 http://localhost:8000 にアクセスしてください")
    print("🌐 Docker環境では http://0.0.0.0:8000 でリッスンしています")
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_level="info"
    ) 