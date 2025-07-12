from typing import Dict, List, Tuple
from datetime import datetime
import json
import csv
import re
from pathlib import Path
from dataclasses import dataclass
from tqdm import tqdm
from ..models.user_profile import UserProfile
from api import get_client, generate_chat_completion
from openai import OpenAI
from ..utils.logger import setup_logger
from ..filters.job_filters import apply_filters

logger = setup_logger(__name__)

@dataclass
class JobMatch:
    """案件とマッチング結果"""
    job: Dict  # 案件情報
    relevance_score: float  # 関連度スコア（0-100）
    quick_filtered: bool = False  # クイックフィルタリングで除外されたかどうか
    filter_reason: str = ""  # フィルタリングされた理由

BATCH_SIZE = 3  # 一度に評価する案件数

class JobMatcher:
    """案件とユーザーのマッチングを行うクラス"""
    
    def __init__(self, save_dir: str = "data/matches"):
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.client = get_client("local")  # LocalLLMを使用するように変更

    def quick_filter_job(self, job: Dict, user_profile: UserProfile) -> Tuple[bool, str]:
        """基本的な条件でジョブをフィルタリング
        
        Returns:
            Tuple[bool, str]: (除外すべきか, 除外理由)
        """
        return apply_filters(job, user_profile)

    def evaluate_jobs_batch(self, jobs: List[Dict], user_profile: UserProfile) -> List[JobMatch]:
        """複数の案件を一括で評価"""
        prompt = f"""
以下のユーザープロファイルと案件情報を基に、各案件の関連度スコアを評価してください。

【評価基準】
スコアの基準:
- 0-20点: ユーザープロファイルと全く合致しない
- 21-40点: ユーザープロファイルとの合致が低い
- 41-60点: ユーザープロファイルと部分的に合致
- 61-80点: ユーザープロファイルと良く合致
- 81-100点: ユーザープロファイルと非常に良く合致

以下の要素を総合的に評価してください：
1. スキルの合致度
2. 希望カテゴリとの合致度
3. 希望する働き方との合致度
4. 案件内容とユーザー詳細情報の親和性

【ユーザープロファイル】
- スキル: {', '.join(user_profile.skills)}
- 希望カテゴリ: {', '.join(user_profile.preferred_categories)}
- 希望する働き方: {', '.join(user_profile.preferred_work_type)}
- 追加情報: {user_profile.description}

【評価対象案件】
{json.dumps([{
    'id': i,
    'title': job['title'],
    'category': job['category'],
    'budget': job['budget'],
    'description': job['description']
} for i, job in enumerate(jobs)], ensure_ascii=False, indent=2)}

以下の形式でJSONを出力してください:
{{
    "scores": [
        {{ 
            "id": 案件ID,
            "score": 0-100のスコア
        }},
        ...
    ]
}}
"""

        try:
            response = generate_chat_completion(
                client=self.client,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that evaluates job matches based on user profile requirements."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )

            if isinstance(self.client, OpenAI):
                result = json.loads(response.choices[0].message.content)
            else:
                result = json.loads(response['choices'][0]['message']['content'])

            # スコアを各案件に割り当て
            job_matches = []
            for job in jobs:
                score_info = next((s for s in result['scores'] if s['id'] == len(job_matches)), None)
                score = float(score_info['score']) if score_info else 0.0
                # スコアの範囲を確認
                score = max(0.0, min(100.0, score))
                
                job_matches.append(JobMatch(
                    job=job,
                    relevance_score=score,
                    quick_filtered=False
                ))
            
            return job_matches

        except Exception as e:
            logger.error(f"評価中にエラーが発生しました: {e}")
            return [JobMatch(
                job=job,
                relevance_score=0.0,
                quick_filtered=False
            ) for job in jobs]

    def find_matching_jobs(
        self,
        user_profile: UserProfile,
        min_score: float = 70.0,
        max_jobs: int = 5
    ) -> List[JobMatch]:
        """ユーザープロファイルに合致する案件を探す"""
        # 最新の分析済み案件を読み込む
        analyzed_files = sorted(
            Path("data/jobs").glob("extracted_jobs_*.json"),
            key=lambda x: x.stat().st_mtime,
            reverse=True
        )
        
        if not analyzed_files:
            raise FileNotFoundError("分析済みの案件ファイルが見つかりません")
        
        with open(analyzed_files[0], 'r', encoding='utf-8') as f:
            jobs = json.load(f)
        
        logger.info(f"合計{len(jobs)}件の案件を評価します...")
        
        # 各案件を評価
        matches = []
        all_evaluations = []
        
        # バッチ処理用の一時リスト
        batch_jobs = []
        
        for job in tqdm(jobs, desc="案件評価の進捗", unit="件"):
            # クイックフィルタを適用
            should_filter, reason = self.quick_filter_job(job, user_profile)
            if should_filter:
                match = JobMatch(
                    job=job,
                    relevance_score=0.0,
                    quick_filtered=True,
                    filter_reason=reason
                )
                all_evaluations.append(match)
                continue
            
            # フィルタを通過した案件をバッチに追加
            batch_jobs.append(job)
            
            # バッチサイズに達したら評価実行
            if len(batch_jobs) >= BATCH_SIZE:
                batch_matches = self.evaluate_jobs_batch(batch_jobs, user_profile)
                for match in batch_matches:
                    all_evaluations.append(match)
                    if match.relevance_score >= min_score:
                        matches.append(match)
                batch_jobs = []  # バッチをクリア
        
        # 残りの案件を評価
        if batch_jobs:
            batch_matches = self.evaluate_jobs_batch(batch_jobs, user_profile)
            for match in batch_matches:
                all_evaluations.append(match)
                if match.relevance_score >= min_score:
                    matches.append(match)
        
        # 全案件の評価結果をCSVに保存
        self.save_all_evaluations_to_csv(all_evaluations)
        
        # スコアで降順ソート
        matches.sort(key=lambda x: x.relevance_score, reverse=True)
        return matches[:max_jobs]

    def save_matching_results(self, matches: List[JobMatch], user_profile: UserProfile):
        """マッチング結果をJSONファイルとして保存"""
        results = {
            "実行日時": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "ユーザープロファイル": {
                "スキル": user_profile.skills,
                "希望カテゴリ": user_profile.preferred_categories,
                "希望する働き方": user_profile.preferred_work_type,
                "追加情報": user_profile.description
            },
            "マッチング結果": [
                {
                    "案件情報": match.job,
                    "マッチング詳細": {
                        "関連度スコア": match.relevance_score,
                    }
                }
                for match in matches
            ]
        }
        
        # 結果を保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = self.save_dir / f"matching_results_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        logger.info(f"\nマッチング結果を {output_file} に保存しました。")
        
        # 結果の要約を表示
        logger.info("\n=== マッチング結果の要約 ===")
        logger.info(f"評価した案件数: {len(matches)}件")
        
        if matches:
            logger.info("\n最も相性の良い案件:")
            top_match = matches[0]
            logger.info(f"タイトル: {top_match.job['title']}")
            logger.info(f"関連度スコア: {top_match.relevance_score:.1f}")
        
        return output_file

    def save_all_evaluations_to_csv(self, evaluations: List[JobMatch]):
        """全案件の評価結果をCSVファイルとして保存"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = self.save_dir / f"all_evaluations_{timestamp}.csv"
        
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'タイトル',
                'カテゴリ',
                '予算形態',
                '最小予算',
                '最大予算',
                '関連度スコア',
                'クイックフィルタ',
                'フィルタ理由',
                'URL'
            ])
            
            for eval in evaluations:
                writer.writerow([
                    eval.job['title'],
                    eval.job['category'],
                    eval.job['budget']['type'],
                    eval.job['budget']['min_amount'],
                    eval.job['budget']['max_amount'],
                    f"{eval.relevance_score:.1f}",
                    "除外" if eval.quick_filtered else "詳細評価",
                    eval.filter_reason,
                    eval.job['url']
                ])
        
        # フィルタリング統計の出力
        filtered_count = sum(1 for e in evaluations if e.quick_filtered)
        detailed_count = len(evaluations) - filtered_count
        
        # 予算形態ごとの集計
        budget_types = {}
        filtered_budget_types = {}
        for eval in evaluations:
            budget_type = eval.job['budget']['type']
            budget_types[budget_type] = budget_types.get(budget_type, 0) + 1
            if eval.quick_filtered:
                filtered_budget_types[budget_type] = filtered_budget_types.get(budget_type, 0) + 1
        
        logger.info(f"\n=== フィルタリング統計 ===")
        logger.info(f"全案件数: {len(evaluations)}件")
        logger.info(f"クイックフィルタで除外: {filtered_count}件")
        logger.info(f"詳細評価実施: {detailed_count}件")
        
        logger.info(f"\n予算形態別集計:")
        for budget_type, count in budget_types.items():
            filtered = filtered_budget_types.get(budget_type, 0)
            passed = count - filtered
            logger.info(f"- {budget_type}: 全{count}件（除外: {filtered}件, 通過: {passed}件）")
        
        logger.info(f"\n全案件の評価結果を {output_file} に保存しました。") 