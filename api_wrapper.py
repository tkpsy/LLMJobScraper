#!/usr/bin/env python3
"""
既存のスクレイピングシステムをAPI化するためのラッパー
既存コードは一切変更せず、新しいAPI層を追加
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import os
import asyncio
import uuid
from datetime import datetime
import glob
import csv

# 追加インポート
from src.utils.category_selector import CategorySelector, SelectedCategory
from src.models.user_profile import UserProfile
from src.utils.config import USER_PROFILE_CONFIG, MATCHING_CONFIG
from main import CrowdWorksCategoryExplorer

app = FastAPI()

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静的ファイル配信
app.mount("/static", StaticFiles(directory="static"), name="static")

# グローバル変数
execution_status = {}
execution_results = {}
category_selector = CategorySelector()

class UserProfile(BaseModel):
    skills: List[str]
    preferred_categories: List[str]
    preferred_work_type: List[str]
    description: str

class LLMSettings(BaseModel):
    min_score: float
    max_jobs: int
    llm_model: str
    temperature: float

class ExecutionRequest(BaseModel):
    user_profile: UserProfile
    llm_settings: LLMSettings
    selected_categories: Optional[List[str]] = None  # 選択されたカテゴリID

class CategorySelectionRequest(BaseModel):
    user_profile: UserProfile
    max_categories: int = 5

class SelectedCategoryResponse(BaseModel):
    name: str
    url: str
    category_id: str
    category_type: str
    relevance_score: float
    reason: str

@app.get("/")
async def root():
    return {"message": "CrowdWorks Job Matching API"}

@app.get("/api/config")
async def get_config():
    """設定情報を取得"""
    return {
        "user_profile": USER_PROFILE_CONFIG,
        "llm_settings": MATCHING_CONFIG
    }

@app.post("/api/categories/select")
async def select_categories(request: CategorySelectionRequest):
    """
    ユーザープロファイルから最適なカテゴリを選択
    """
    try:
        # UserProfileオブジェクトを作成
        user_profile = UserProfile(
            skills=request.user_profile.skills,
            preferred_categories=request.user_profile.preferred_categories,
            preferred_work_type=request.user_profile.preferred_work_type,
            description=request.user_profile.description
        )
        
        # カテゴリ選択
        selected_categories = category_selector.select_categories(
            user_profile=user_profile,
            max_categories=request.max_categories
        )
        
        # レスポンス形式に変換
        response_categories = []
        for cat in selected_categories:
            response_categories.append(SelectedCategoryResponse(
                name=cat.name,
                url=cat.url,
                category_id=cat.category_id,
                category_type=cat.category_type,
                relevance_score=cat.relevance_score,
                reason=cat.reason
            ))
        
        return {
            "status": "success",
            "selected_categories": response_categories,
            "total_available_categories": len(category_selector.get_all_categories()['main_categories'])
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"カテゴリ選択中にエラーが発生しました: {str(e)}")

@app.get("/api/categories/all")
async def get_all_categories():
    """
    全カテゴリ情報を取得
    """
    try:
        categories = category_selector.get_all_categories()
        return {
            "status": "success",
            "categories": categories
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"カテゴリ情報取得中にエラーが発生しました: {str(e)}")

@app.post("/api/execute")
async def execute_job_matching(request: ExecutionRequest, background_tasks: BackgroundTasks):
    """
    案件マッチング実行（カテゴリ選択機能付き）
    """
    execution_id = str(uuid.uuid4())
    execution_status[execution_id] = "running"
    
    try:
        # 選択されたカテゴリから実行対象を決定
        target_categories = []
        
        if request.selected_categories:
            # 指定されたカテゴリを使用
            for cat_id in request.selected_categories:
                cat_info = category_selector.get_category_by_id(cat_id)
                if cat_info:
                    target_categories.append({
                        "name": cat_info['name'],
                        "url": cat_info['url'],
                        "id": cat_info['id']
                    })
        
        if not target_categories:
            # カテゴリが指定されていない場合、自動選択
            user_profile = UserProfile(
                skills=request.user_profile.skills,
                preferred_categories=request.user_profile.preferred_categories,
                preferred_work_type=request.user_profile.preferred_work_type,
                description=request.user_profile.description
            )
            
            selected_categories = category_selector.select_categories(user_profile, max_categories=3)
            
            for cat in selected_categories:
                target_categories.append({
                    "name": cat.name,
                    "url": cat.url,
                    "id": cat.category_id
                })
        
        # バックグラウンドタスクで実行
        background_tasks.add_task(
            run_job_matching,
            execution_id,
            request.user_profile,
            request.llm_settings,
            target_categories
        )
        
        return {
            "execution_id": execution_id,
            "status": "started",
            "target_categories": target_categories,
            "message": "案件マッチングを開始しました"
        }
    
    except Exception as e:
        execution_status[execution_id] = "failed"
        raise HTTPException(status_code=500, detail=f"実行開始中にエラーが発生しました: {str(e)}")

async def run_job_matching(
    execution_id: str,
    user_profile: UserProfile,
    llm_settings: LLMSettings,
    target_categories: List[Dict[str, str]]
):
    """
    案件マッチング実行（バックグラウンドタスク）
    """
    try:
        # CrowdWorksCategoryExplorerを初期化
        explorer = CrowdWorksCategoryExplorer()
        
        # ユーザープロファイルを設定
        explorer.user_profile = UserProfile(
            skills=user_profile.skills,
            preferred_categories=user_profile.preferred_categories,
            preferred_work_type=user_profile.preferred_work_type,
            description=user_profile.description
        )
        
        # LLM設定を更新
        if hasattr(explorer, 'job_matcher') and hasattr(explorer.job_matcher, 'llm_client'):
            explorer.job_matcher.llm_client.model = llm_settings.llm_model
            explorer.job_matcher.llm_client.temperature = llm_settings.temperature
        
        # 各カテゴリに対して実行
        all_results = []
        for category in target_categories:
            try:
                # カテゴリURLでスクレイピング実行
                html_files = explorer.scrape_category_jobs(category['url'])
                
                if html_files:
                    # 案件の抽出とマッチング
                    results = explorer.extract_and_match_jobs(html_files)
                    
                    if results:
                        all_results.extend(results)
                    
            except Exception as e:
                print(f"カテゴリ {category['name']} の処理中にエラーが発生しました: {e}")
                continue
        
        # 結果を統合・フィルタリング
        if all_results:
            # スコアによるフィルタリング
            filtered_results = [
                result for result in all_results
                if hasattr(result, 'relevance_score') and result.relevance_score >= llm_settings.min_score
            ]
            
            # 最大件数制限
            filtered_results = sorted(
                filtered_results,
                key=lambda x: getattr(x, 'relevance_score', 0),
                reverse=True
            )[:llm_settings.max_jobs]
            
            # 結果を保存
            if hasattr(explorer, 'job_matcher') and hasattr(explorer.job_matcher, 'save_matching_results'):
                explorer.job_matcher.save_matching_results(filtered_results, explorer.user_profile)
            
            # 実行結果を保存
            execution_results[execution_id] = {
                "results": [
                    {
                        "案件情報": getattr(result, 'job', result),
                        "マッチング詳細": {
                            "関連度スコア": getattr(result, 'relevance_score', 0),
                        }
                    }
                    for result in filtered_results
                ],
                "statistics": {
                    "total_jobs": len(all_results),
                    "recommended_jobs": len(filtered_results)
                },
                "target_categories": target_categories,
                "execution_time": datetime.now().isoformat()
            }
            
            execution_status[execution_id] = "completed"
        else:
            execution_status[execution_id] = "completed_no_results"
            execution_results[execution_id] = {
                "results": [],
                "statistics": {"total_jobs": 0, "recommended_jobs": 0},
                "target_categories": target_categories,
                "execution_time": datetime.now().isoformat()
            }
    
    except Exception as e:
        execution_status[execution_id] = "failed"
        execution_results[execution_id] = {
            "error": str(e),
            "execution_time": datetime.now().isoformat()
        }
        print(f"実行中にエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

@app.get("/api/status/{execution_id}")
async def get_execution_status(execution_id: str):
    """実行状況を取得"""
    if execution_id not in execution_status:
        raise HTTPException(status_code=404, detail="実行IDが見つかりません")
    
    return {
        "execution_id": execution_id,
        "status": execution_status[execution_id]
    }

@app.get("/api/results/{execution_id}")
async def get_execution_results(execution_id: str):
    """実行結果を取得"""
    if execution_id not in execution_results:
        # ファイルから結果を読み込み
        result_files = glob.glob(f"results/*{execution_id}*.json")
        if not result_files:
            # 古い形式のファイルも確認
            result_files = glob.glob(f"results/*.json")
            
        if result_files:
            try:
                with open(result_files[0], 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # 統計情報を計算
                stats = calculate_statistics()
                
                return {
                    "execution_id": execution_id,
                    "results": data.get("マッチング結果", []),
                    "statistics": stats,
                    "user_profile": data.get("ユーザープロファイル", {}),
                    "execution_time": data.get("実行日時", "")
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"結果読み込み中にエラーが発生しました: {str(e)}")
        else:
            raise HTTPException(status_code=404, detail="実行結果が見つかりません")
    
    return {
        "execution_id": execution_id,
        **execution_results[execution_id]
    }

@app.get("/api/history")
async def get_execution_history():
    """実行履歴を取得"""
    history = []
    
    # JSONファイルから履歴を取得
    result_files = glob.glob("results/*.json")
    result_files.sort(key=os.path.getmtime, reverse=True)
    
    for file_path in result_files[:10]:  # 最新10件
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            filename = os.path.basename(file_path)
            execution_id = filename.replace('.json', '')
            
            # 統計情報を計算
            stats = calculate_statistics()
            
            history.append({
                "execution_id": execution_id,
                "execution_time": data.get("実行日時", ""),
                "total_jobs": stats.get("total_jobs", 0),
                "recommended_jobs": len(data.get("マッチング結果", [])),
                "filename": filename
            })
        except Exception as e:
            print(f"履歴ファイル読み込みエラー: {e}")
            continue
    
    return {"history": history}

def calculate_statistics():
    """統計情報を計算"""
    try:
        # CSVファイルから総件数を取得
        csv_files = glob.glob("results/*.csv")
        total_jobs = 0
        
        if csv_files:
            latest_csv = max(csv_files, key=os.path.getmtime)
            with open(latest_csv, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                next(reader)  # ヘッダーをスキップ
                total_jobs = sum(1 for row in reader)
        
        # JSONファイルから推薦件数を取得
        json_files = glob.glob("results/*.json")
        recommended_jobs = 0
        
        if json_files:
            latest_json = max(json_files, key=os.path.getmtime)
            with open(latest_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
                recommended_jobs = len(data.get("マッチング結果", []))
        
        return {
            "total_jobs": total_jobs,
            "recommended_jobs": recommended_jobs
        }
    except Exception as e:
        print(f"統計情報計算エラー: {e}")
        return {"total_jobs": 0, "recommended_jobs": 0}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 