import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

from src.scrapers.html_scraper import HTMLScraper
from src.processors.job_extractor import JobExtractor
from src.processors.job_matcher import JobMatcher
from src.models.user_profile import UserProfile
from src.utils.config import (
    SCRAPING_CONFIG, MATCHING_CONFIG, AUTO_EXECUTION_CONFIG, 
    USER_PROFILE_CONFIG, EXECUTION_CONFIG, OUTPUT_CONFIG
)

class CrowdWorksCategoryExplorer:
    """カテゴリベースのCrowdWorks案件探索システム"""
    
    def __init__(self):
        self.html_scraper = HTMLScraper()
        self.job_extractor = JobExtractor()
        self.job_matcher = JobMatcher()
        self.categories_file = Path("categories.json")
        
        # セッション中に保存されたファイルを追跡
        self.saved_files = {
            'html_files': [],
            'job_files': [],
            'match_files': [],
            'screenshot_files': []
        }
        
        # 設定ファイルからユーザープロファイルを作成
        self.user_profile = UserProfile(
            skills=USER_PROFILE_CONFIG["skills"],
            experience_years=USER_PROFILE_CONFIG["experience_years"],
            preferred_categories=USER_PROFILE_CONFIG["preferred_categories"],
            preferred_work_type=USER_PROFILE_CONFIG["preferred_work_type"],
            min_budget=USER_PROFILE_CONFIG["min_budget"],
            description=USER_PROFILE_CONFIG["description"]
        )
    
    def load_categories(self) -> Dict:
        """カテゴリ情報を読み込む"""
        if not self.categories_file.exists():
            print("カテゴリファイルが見つかりません。まずカテゴリ情報を取得してください。")
            return {}
        
        with open(self.categories_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def find_category_by_name(self, categories: Dict, main_category_name: str, subcategory_name: Optional[str] = None) -> Optional[Dict]:
        """カテゴリ名から該当するカテゴリを検索"""
        for category in categories.get("main_categories", []):
            if category["name"] == main_category_name:
                if subcategory_name is None:
                    return category
                else:
                    # サブカテゴリを検索
                    for subcategory in category.get("subcategories", []):
                        if subcategory["name"] == subcategory_name:
                            return subcategory
        return None
    
    def scrape_category_jobs(self, category_url: str) -> List[Path]:
        """指定されたカテゴリの案件をスクレイピング"""
        # スクレイピング設定を更新
        original_url = SCRAPING_CONFIG["base_url"]
        SCRAPING_CONFIG["base_url"] = category_url
        
        try:
            if OUTPUT_CONFIG["console_output"]:
                print(f"カテゴリページをスクレイピング中: {category_url}")
            
            # 複数ページ対応のチェック
            max_pages = EXECUTION_CONFIG.get("max_pages_per_category", 1)
            if max_pages > 1:
                # 複数ページスクレイピング
                html_files = self.html_scraper.save_html_with_pagination(
                    category_url=category_url, 
                    max_pages=max_pages
                )
            else:
                # 従来の単一ページスクレイピング
                html_file = self.html_scraper.save_html_single()
                html_files = [html_file]
            
            # 保存されたファイルを記録
            self.saved_files['html_files'].extend(html_files)
            
            # スクリーンショットファイルも記録
            if EXECUTION_CONFIG["save_screenshots"]:
                for html_file in html_files:
                    timestamp = html_file.stem.replace('page_', '')
                    screenshot_file = html_file.parent / f'screenshot_{timestamp}.png'
                    if screenshot_file.exists():
                        self.saved_files['screenshot_files'].append(screenshot_file)
            
            return html_files
        
        except Exception as e:
            print(f"スクレイピング中にエラーが発生しました: {e}")
            return []
        
        finally:
            # 設定を元に戻す
            SCRAPING_CONFIG["base_url"] = original_url
    
    def extract_and_match_jobs(self, html_files: List[Path]) -> List:
        """複数のHTMLファイルから案件を抽出してマッチング評価を行う"""
        if OUTPUT_CONFIG["console_output"]:
            print("案件情報を抽出中...")
        
        all_jobs = []
        
        # 複数のHTMLファイルから案件を抽出
        for i, html_file in enumerate(html_files, 1):
            if OUTPUT_CONFIG["console_output"]:
                print(f"  ファイル {i}/{len(html_files)}: {html_file.name}")
            
            jobs = self.job_extractor.extract_jobs(html_file)
            all_jobs.extend(jobs)
            
            if OUTPUT_CONFIG["console_output"]:
                print(f"    抽出件数: {len(jobs)}件")
        
        # 重複案件の除去
        unique_jobs = self._remove_duplicate_jobs(all_jobs)
        
        if OUTPUT_CONFIG["console_output"]:
            print(f"合計抽出件数: {len(all_jobs)}件")
            print(f"重複除去後: {len(unique_jobs)}件")
        
        if not unique_jobs:
            if OUTPUT_CONFIG["console_output"]:
                print("案件が見つかりませんでした。")
            return []
        
        # 案件をJSONで保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        job_file = self.job_extractor.save_jobs_to_json(unique_jobs, timestamp)
        self.saved_files['job_files'].append(job_file)
        
        if OUTPUT_CONFIG["console_output"]:
            print(f"抽出された案件数: {len(unique_jobs)}件")
        
        # マッチング評価
        if OUTPUT_CONFIG["console_output"]:
            print("案件のマッチング評価を実行中...")
        matches = self.job_matcher.find_matching_jobs(
            user_profile=self.user_profile,
            min_score=MATCHING_CONFIG["min_score"],
            max_jobs=MATCHING_CONFIG["max_jobs"]
        )
        
        # 推薦案件をJSONで保存
        if matches:
            try:
                matching_result_file = self.job_matcher.save_matching_results(matches, self.user_profile)
                self.saved_files['match_files'].append(matching_result_file)
                
                if OUTPUT_CONFIG["console_output"]:
                    print(f"推薦案件を {matching_result_file} に保存しました。")
                    
            except Exception as e:
                if OUTPUT_CONFIG["console_output"]:
                    print(f"推薦案件の保存中にエラーが発生しました: {e}")
        
        # マッチング結果のCSVファイルを記録
        match_files = list(Path("data/matches").glob("all_evaluations_*.csv"))
        if match_files:
            latest_match_file = max(match_files, key=lambda x: x.stat().st_mtime)
            if latest_match_file not in self.saved_files['match_files']:
                self.saved_files['match_files'].append(latest_match_file)
        
        return matches
    
    def _remove_duplicate_jobs(self, jobs: List) -> List:
        """重複案件を除去する"""
        unique_jobs = []
        seen_titles = set()
        
        for job in jobs:
            # タイトルとクライアント名の組み合わせで重複チェック
            job_key = (job.title, job.client_name)
            if job_key not in seen_titles:
                seen_titles.add(job_key)
                unique_jobs.append(job)
        
        return unique_jobs
    
    def display_matches(self, matches: List) -> None:
        """マッチング結果を表示"""
        if not OUTPUT_CONFIG["console_output"]:
            return
            
        if not matches:
            print("\n条件に合う案件が見つかりませんでした。")
            return
        
        print(f"\n推薦案件 ({len(matches)}件):")
        print("=" * 60)
        
        for i, match in enumerate(matches, 1):
            job = match.job
            print(f"\n{i}. {job['title']}")
            print(f"   関連度スコア: {match.relevance_score:.1f}/100")
            print(f"   カテゴリ: {job.get('category', '未分類')}")
            print(f"   クライアント: {job.get('client_name', '不明')}")
            
            if job.get('budget'):
                budget = job['budget']
                if budget.get('min_amount') and budget.get('max_amount'):
                    print(f"   予算: {budget['min_amount']:,}円 ～ {budget['max_amount']:,}円 ({budget['type']})")
                elif budget.get('min_amount'):
                    print(f"   予算: {budget['min_amount']:,}円 ({budget['type']})")
                else:
                    print(f"   予算: 相談 ({budget['type']})")
            
            if job.get('deadline'):
                print(f"   期限: {job['deadline']}")
            
            if job.get('url'):
                print(f"   URL: {job['url']}")
            
            # 説明文の一部を表示
            description = job.get('description', '')
            if description:
                desc_preview = description[:100] + "..." if len(description) > 100 else description
                print(f"   説明: {desc_preview}")
            
            print("-" * 60)
    
    def display_saved_files_summary(self) -> None:
        """保存されたファイルの情報を表示"""
        if not OUTPUT_CONFIG["detailed_summary"]:
            return
            
        print("\n" + "=" * 60)
        print("🗂️  セッション中に保存されたファイル一覧")
        print("=" * 60)
        
        total_files = 0
        
        if self.saved_files['html_files']:
            print(f"\n📄 HTMLファイル ({len(self.saved_files['html_files'])}件):")
            for file_path in self.saved_files['html_files']:
                if OUTPUT_CONFIG["show_file_sizes"]:
                    file_size = file_path.stat().st_size / 1024  # KB
                    print(f"   - {file_path} ({file_size:.1f}KB)")
                else:
                    print(f"   - {file_path}")
                total_files += 1
        
        if self.saved_files['screenshot_files']:
            print(f"\n📸 スクリーンショット ({len(self.saved_files['screenshot_files'])}件):")
            for file_path in self.saved_files['screenshot_files']:
                if OUTPUT_CONFIG["show_file_sizes"]:
                    file_size = file_path.stat().st_size / 1024  # KB
                    print(f"   - {file_path} ({file_size:.1f}KB)")
                else:
                    print(f"   - {file_path}")
                total_files += 1
        
        if self.saved_files['job_files']:
            print(f"\n📋 案件データ (JSON) ({len(self.saved_files['job_files'])}件):")
            for file_path in self.saved_files['job_files']:
                if OUTPUT_CONFIG["show_file_sizes"]:
                    file_size = file_path.stat().st_size / 1024  # KB
                    print(f"   - {file_path} ({file_size:.1f}KB)")
                else:
                    print(f"   - {file_path}")
                total_files += 1
        
        if self.saved_files['match_files']:
            print(f"\n📊 マッチング結果 (CSV) ({len(self.saved_files['match_files'])}件):")
            for file_path in self.saved_files['match_files']:
                if OUTPUT_CONFIG["show_file_sizes"]:
                    file_size = file_path.stat().st_size / 1024  # KB
                    print(f"   - {file_path} ({file_size:.1f}KB)")
                else:
                    print(f"   - {file_path}")
                total_files += 1
        
        if total_files == 0:
            print("\n⚠️  このセッションで保存されたファイルはありません。")
        else:
            print(f"\n✅ 合計 {total_files} ファイルが保存されました。")
        
        print("\n💡 ヒント:")
        print("   - HTMLファイル: ブラウザで開いてページ内容を確認できます")
        print("   - JSONファイル: 案件の詳細データが構造化されて保存されています")  
        print("   - CSVファイル: Excelやスプレッドシートで開いて分析できます")
        print("=" * 60)
    
    def run(self):
        """自動実行モード"""
        if OUTPUT_CONFIG["console_output"]:
            print("CrowdWorks カテゴリベース案件探索システム")
            print("=" * 60)
        
        # カテゴリ情報を読み込み
        categories = self.load_categories()
        if not categories:
            return
        
        try:
            for i, target_config in enumerate(AUTO_EXECUTION_CONFIG["target_categories"]):
                if OUTPUT_CONFIG["console_output"]:
                    print(f"\n🎯 実行 {i+1}/{len(AUTO_EXECUTION_CONFIG['target_categories'])}: {target_config['description']}")
                
                # 設定からカテゴリを検索
                selected_category = self.find_category_by_name(
                    categories, 
                    target_config["main_category"], 
                    target_config.get("subcategory")
                )
                
                if selected_category is None:
                    print(f"⚠️  カテゴリが見つかりません: {target_config['main_category']}")
                    if target_config.get("subcategory"):
                        print(f"    サブカテゴリ: {target_config['subcategory']}")
                    continue
                
                if OUTPUT_CONFIG["console_output"]:
                    print(f"📂 対象カテゴリ: {selected_category['name']}")
                
                # カテゴリページをスクレイピング
                html_files = self.scrape_category_jobs(selected_category['url'])
                if not html_files:
                    continue
                
                # 案件抽出とマッチング
                matches = self.extract_and_match_jobs(html_files)
                
                # 結果表示
                self.display_matches(matches)
                
                # 連続実行の場合は待機
                if (AUTO_EXECUTION_CONFIG["continuous_execution"] and 
                    i < len(AUTO_EXECUTION_CONFIG["target_categories"]) - 1):
                    delay = AUTO_EXECUTION_CONFIG["delay_between_categories"]
                    if OUTPUT_CONFIG["console_output"]:
                        print(f"\n⏳ 次のカテゴリまで {delay} 秒待機...")
                    time.sleep(delay)
        
        except KeyboardInterrupt:
            if OUTPUT_CONFIG["console_output"]:
                print("\n\n⚠️  プログラムが中断されました。")
        
        finally:
            # 保存されたファイルの情報を表示
            self.display_saved_files_summary()
            if OUTPUT_CONFIG["console_output"]:
                print("\nお疲れ様でした！")

def main():
    """メイン関数"""
    explorer = CrowdWorksCategoryExplorer()
    explorer.run()

if __name__ == "__main__":
    main() 