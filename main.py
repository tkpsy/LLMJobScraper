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
    
    def __init__(self, auto_mode: bool = False):
        self.html_scraper = HTMLScraper()
        self.job_extractor = JobExtractor()
        self.job_matcher = JobMatcher()
        self.categories_file = Path("categories.json")
        self.auto_mode = auto_mode
        
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
    
    def display_categories(self, categories: Dict) -> None:
        """カテゴリを表示"""
        print("\n利用可能なカテゴリ:")
        print("=" * 40)
        
        for i, category in enumerate(categories.get("main_categories", []), 1):
            print(f"{i}. {category['name']}")
            if category.get('subcategories'):
                for j, sub in enumerate(category['subcategories'][:3], 1):  # 最初の3つのサブカテゴリを表示
                    print(f"   {j}. {sub['name']}")
                if len(category['subcategories']) > 3:
                    print(f"   ... 他{len(category['subcategories']) - 3}件")
            print()
    
    def select_category(self, categories: Dict) -> Optional[Dict]:
        """ユーザーにカテゴリを選択させる（手動モード用）"""
        self.display_categories(categories)
        
        try:
            choice = int(input("探索したいカテゴリの番号を入力してください (0で終了): "))
            if choice == 0:
                return None
            
            main_categories = categories.get("main_categories", [])
            if 1 <= choice <= len(main_categories):
                selected = main_categories[choice - 1]
                
                # サブカテゴリがある場合は選択を促す
                if selected.get('subcategories'):
                    print(f"\n{selected['name']} のサブカテゴリ:")
                    print("0. メインカテゴリ全体")
                    for i, sub in enumerate(selected['subcategories'], 1):
                        print(f"{i}. {sub['name']}")
                    
                    sub_choice = int(input("サブカテゴリを選択してください: "))
                    if sub_choice == 0:
                        return selected
                    elif 1 <= sub_choice <= len(selected['subcategories']):
                        return selected['subcategories'][sub_choice - 1]
                
                return selected
            else:
                print("無効な選択です。")
                return None
        
        except (ValueError, IndexError):
            print("無効な入力です。")
            return None
    
    def scrape_category_jobs(self, category_url: str) -> Optional[Path]:
        """指定されたカテゴリの案件をスクレイピング"""
        # スクレイピング設定を更新
        original_url = SCRAPING_CONFIG["base_url"]
        SCRAPING_CONFIG["base_url"] = category_url
        
        try:
            if OUTPUT_CONFIG["console_output"]:
                print(f"カテゴリページをスクレイピング中: {category_url}")
            html_file = self.html_scraper.save_html_single()
            
            # 保存されたファイルを記録
            self.saved_files['html_files'].append(html_file)
            
            # スクリーンショットファイルも記録
            if EXECUTION_CONFIG["save_screenshots"]:
                timestamp = html_file.stem.replace('page_', '')
                screenshot_file = html_file.parent / f'screenshot_{timestamp}.png'
                if screenshot_file.exists():
                    self.saved_files['screenshot_files'].append(screenshot_file)
            
            return html_file
        
        except Exception as e:
            print(f"スクレイピング中にエラーが発生しました: {e}")
            return None
        
        finally:
            # 設定を元に戻す
            SCRAPING_CONFIG["base_url"] = original_url
    
    def extract_and_match_jobs(self, html_file: Path) -> List:
        """案件を抽出してマッチング評価を行う"""
        if OUTPUT_CONFIG["console_output"]:
            print("案件情報を抽出中...")
        jobs = self.job_extractor.extract_jobs(html_file)
        
        if not jobs:
            if OUTPUT_CONFIG["console_output"]:
                print("案件が見つかりませんでした。")
            return []
        
        # 案件をJSONで保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        job_file = self.job_extractor.save_jobs_to_json(jobs, timestamp)
        self.saved_files['job_files'].append(job_file)
        
        if OUTPUT_CONFIG["console_output"]:
            print(f"抽出された案件数: {len(jobs)}件")
        
        # マッチング評価
        if OUTPUT_CONFIG["console_output"]:
            print("案件のマッチング評価を実行中...")
        matches = self.job_matcher.find_matching_jobs(
            user_profile=self.user_profile,
            min_score=MATCHING_CONFIG["min_score"],
            max_jobs=MATCHING_CONFIG["max_jobs"]
        )
        
        # マッチング結果のCSVファイルを記録
        match_files = list(Path("data/matches").glob("all_evaluations_*.csv"))
        if match_files:
            latest_match_file = max(match_files, key=lambda x: x.stat().st_mtime)
            if latest_match_file not in self.saved_files['match_files']:
                self.saved_files['match_files'].append(latest_match_file)
        
        return matches
    
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
    
    def run_auto_mode(self):
        """自動実行モード"""
        if OUTPUT_CONFIG["console_output"]:
            print("CrowdWorks カテゴリベース案件探索システム（自動実行モード）")
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
                html_file = self.scrape_category_jobs(selected_category['url'])
                if html_file is None:
                    continue
                
                # 案件抽出とマッチング
                matches = self.extract_and_match_jobs(html_file)
                
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
    
    def run_manual_mode(self):
        """手動実行モード"""
        print("CrowdWorks カテゴリベース案件探索システム（手動モード）")
        print("=" * 50)
        
        # カテゴリ情報を読み込み
        categories = self.load_categories()
        if not categories:
            return
        
        try:
            while True:
                # カテゴリ選択
                selected_category = self.select_category(categories)
                if selected_category is None:
                    print("システムを終了します。")
                    break
                
                print(f"\n選択されたカテゴリ: {selected_category['name']}")
                
                # カテゴリページをスクレイピング
                html_file = self.scrape_category_jobs(selected_category['url'])
                if html_file is None:
                    continue
                
                # 案件抽出とマッチング
                matches = self.extract_and_match_jobs(html_file)
                
                # 結果表示
                self.display_matches(matches)
                
                # 継続確認
                continue_choice = input("\n別のカテゴリを探索しますか？ (y/n): ").lower()
                if continue_choice != 'y':
                    break
        
        except KeyboardInterrupt:
            print("\n\n⚠️  プログラムが中断されました。")
        
        finally:
            # 保存されたファイルの情報を表示
            self.display_saved_files_summary()
            print("\nお疲れ様でした！")
    
    def run(self):
        """メインの実行ループ"""
        if self.auto_mode or AUTO_EXECUTION_CONFIG["enabled"]:
            self.run_auto_mode()
        else:
            self.run_manual_mode()

def main():
    """メイン関数 - コマンドライン引数をサポート"""
    import argparse
    
    parser = argparse.ArgumentParser(description='CrowdWorks案件探索システム')
    parser.add_argument('--auto', action='store_true', help='自動実行モードで起動')
    parser.add_argument('--manual', action='store_true', help='手動実行モードで起動')
    
    args = parser.parse_args()
    
    # 自動実行モードの判定
    auto_mode = args.auto or (AUTO_EXECUTION_CONFIG["enabled"] and not args.manual)
    
    explorer = CrowdWorksCategoryExplorer(auto_mode=auto_mode)
    explorer.run()

if __name__ == "__main__":
    main() 