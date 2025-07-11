from src.models.user_profile import UserProfile
from src.scrapers.html_scraper import HTMLScraper
from src.processors.job_extractor import JobExtractor
from src.processors.job_matcher import JobMatcher
from src.utils.config import MATCHING_CONFIG
from src import logger

def main():
    try:
        logger.info("スクレイピングを開始します...")
        scraper = HTMLScraper()
        html_files = scraper.save_html_multiple()
        
        logger.info("案件情報を抽出します...")
        extractor = JobExtractor()
        jobs = []
        for html_file in html_files:
            jobs.extend(extractor.extract_jobs(html_file))
        
        # 抽出した案件情報を保存
        timestamp = html_files[0].stem.split('_')[-1]  # 最初のHTMLファイルのタイムスタンプを使用
        jobs_file = extractor.save_jobs_to_json(jobs, timestamp)
        logger.info(f"{len(jobs)}件の案件情報を抽出しました")
        
        # サンプルのユーザープロファイル
        user_profile = UserProfile(
            skills=["Python", "機械学習", "データ分析"],
            experience_years=2,
            preferred_categories=["AI・機械学習", "データサイエンス"],
            preferred_work_type=["リモート"],
            min_budget=3000,
            description="機械学習エンジニアとして2年の経験があり、特にPythonを使用したデータ分析や機械学習モデルの開発を得意としています。"
        )
        
        logger.info("案件のマッチング評価を開始します...")
        matcher = JobMatcher()
        matches = matcher.find_matching_jobs(
            user_profile,
            min_score=MATCHING_CONFIG["min_score"],
            max_jobs=MATCHING_CONFIG["max_jobs"]
        )
        
        # マッチング結果を保存
        matcher.save_matching_results(matches, user_profile)
        logger.info("処理が完了しました")
        
    except Exception as e:
        logger.error(f"エラーが発生しました: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    main() 