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
from ..filters.job_filters import apply_filters  # 新しいフィルターをインポート

logger = setup_logger(__name__)

@dataclass
class JobMatch:
    """案件とマッチング結果"""
    job: Dict  # 案件情報
    relevance_score: float  # 関連度スコア（0-100）
    match_reasons: List[str]  # マッチする理由
    concerns: List[str]  # 注意点や懸念事項
    quick_filtered: bool = False  # クイックフィルタリングで除外されたかどうか
    filter_reason: str = ""  # フィルタリングされた理由

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

    def evaluate_job_with_llm(self, job: Dict, user_profile: UserProfile) -> JobMatch:
        """LLMを使用して案件とユーザーの相性を評価"""
        # クイックフィルタリングを実施
        should_filter, filter_reason = self.quick_filter_job(job, user_profile)
        if should_filter:
            return JobMatch(
                job=job,
                relevance_score=0.0,
                match_reasons=[],
                concerns=[],
                quick_filtered=True,
                filter_reason=filter_reason
            )

        # 以下、既存のLLM評価コード
        prompt = f"""
あなたは、フリーランス案件とユーザーの相性を評価する専門家です。
以下の情報を基に、案件とユーザーの相性を分析し、JSONフォーマットで出力してください。

【ユーザープロファイル】
- スキル: {', '.join(user_profile.skills)}
- 経験年数: {user_profile.experience_years}年
- 希望カテゴリ: {', '.join(user_profile.preferred_categories)}
- 希望する働き方: {', '.join(user_profile.preferred_work_type)}
- 希望最低予算: {user_profile.min_budget}円
- 追加情報: {user_profile.description}

【案件情報】
- タイトル: {job['title']}
- カテゴリ: {job['category']}
- 予算: {job['budget']['type']} ({job['budget']['min_amount']}円 ～ {job['budget']['max_amount']}円)
- 説明: {job['description']}

以下の形式でJSONを出力してください:
{{
    "relevance_score": 0-100のスコア,
    "match_reasons": [マッチする理由のリスト（最大3つ）],
    "concerns": [注意点や懸念事項のリスト（最大3つ）]
}}
"""

        try:
            response = generate_chat_completion(
                client=self.client,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that evaluates job matches."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )

            if isinstance(self.client, OpenAI):
                result = json.loads(response.choices[0].message.content)
            else:
                result = json.loads(response['choices'][0]['message']['content'])
            
            return JobMatch(
                job=job,
                relevance_score=float(result['relevance_score']),
                match_reasons=result['match_reasons'],
                concerns=result['concerns'],
                quick_filtered=False
            )
        
        except Exception as e:
            logger.error(f"評価中にエラーが発生しました: {e}")
            return JobMatch(
                job=job,
                relevance_score=0.0,
                match_reasons=[],
                concerns=[f"評価エラー: {str(e)}"],
                quick_filtered=False
            )

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
        all_evaluations = []  # 全ての評価結果を保存
        
        for job in tqdm(jobs, desc="案件評価の進捗", unit="件"):
            match = self.evaluate_job_with_llm(job, user_profile)
            all_evaluations.append(match)  # 全ての評価結果を保存
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
                "経験年数": user_profile.experience_years,
                "希望カテゴリ": user_profile.preferred_categories,
                "希望する働き方": user_profile.preferred_work_type,
                "希望最低予算": user_profile.min_budget,
                "追加情報": user_profile.description
            },
            "マッチング結果": [
                {
                    "案件情報": match.job,
                    "マッチング詳細": {
                        "関連度スコア": match.relevance_score,
                        "マッチする理由": match.match_reasons,
                        "注意点": match.concerns
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
            logger.info("\nマッチする理由:")
            for reason in top_match.match_reasons:
                logger.info(f"- {reason}")
        
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
                'マッチング理由',
                '注意点',
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
                    ' | '.join(eval.match_reasons),
                    ' | '.join(eval.concerns),
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