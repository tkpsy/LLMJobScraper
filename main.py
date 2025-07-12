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
    SCRAPING_CONFIG, MATCHING_CONFIG, 
    USER_PROFILE_CONFIG, EXECUTION_CONFIG, OUTPUT_CONFIG, LLM_CATEGORY_SELECTION_CONFIG
)
from api import generate_chat_completion

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
            preferred_categories=USER_PROFILE_CONFIG["preferred_categories"],
            preferred_work_type=USER_PROFILE_CONFIG["preferred_work_type"],
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
    
    def extract_jobs_only(self, html_files: List[Path]) -> List:
        """HTMLファイルから案件を抽出するのみ（ファイル保存なし）"""
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
        
        return unique_jobs
    
    def match_jobs_only(self, jobs: List) -> List:
        """案件のマッチング評価のみ（ファイル保存なし）"""
        if not jobs:
            if OUTPUT_CONFIG["console_output"]:
                print("案件が見つかりませんでした。")
            return []
        
        if OUTPUT_CONFIG["console_output"]:
            print("案件のマッチング評価を実行中...")
        
        # 一時的に案件を設定してマッチング実行
        self.job_matcher.jobs = jobs
        matches = self.job_matcher.find_matching_jobs(
            user_profile=self.user_profile,
            min_score=MATCHING_CONFIG["min_score"],
            max_jobs=MATCHING_CONFIG["max_jobs"]
        )
        
        return matches
    
    def save_all_jobs_and_matches(self, all_jobs: List, all_matches: List) -> None:
        """全カテゴリの案件とマッチング結果を統合して保存"""
        if OUTPUT_CONFIG["console_output"]:
            print(f"\n📊 全カテゴリの案件を統合保存中...")
            print(f"   総案件数: {len(all_jobs)}件")
            print(f"   マッチング結果: {len(all_matches)}件")
        
        # 全案件をJSONで保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        job_file = self.job_extractor.save_jobs_to_json(all_jobs, timestamp)
        self.saved_files['job_files'].append(job_file)
        
        # 全マッチング結果を保存
        if all_matches:
            try:
                matching_result_file = self.job_matcher.save_matching_results(all_matches, self.user_profile)
                self.saved_files['match_files'].append(matching_result_file)
                
                if OUTPUT_CONFIG["console_output"]:
                    print(f"✅ 全案件を {job_file} に保存しました。")
                    print(f"✅ 全マッチング結果を {matching_result_file} に保存しました。")
                    
            except Exception as e:
                if OUTPUT_CONFIG["console_output"]:
                    print(f"マッチング結果の保存中にエラーが発生しました: {e}")
        
        # マッチング結果のCSVファイルを記録
        match_files = list(Path("data/matches").glob("all_evaluations_*.csv"))
        if match_files:
            latest_match_file = max(match_files, key=lambda x: x.stat().st_mtime)
            if latest_match_file not in self.saved_files['match_files']:
                self.saved_files['match_files'].append(latest_match_file)
    
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
            # LLMによるカテゴリ選択
            selected_categories = self.select_categories_by_llm(categories, self.user_profile)
            
            if not selected_categories:
                if OUTPUT_CONFIG["console_output"]:
                    print("⚠️  適切なカテゴリが見つかりませんでした。")
                return
            
            # 全カテゴリの案件を収集
            all_jobs = []
            all_matches = []
            
            # 選択されたカテゴリでスクレイピング実行
            for i, selected_category in enumerate(selected_categories, 1):
                if OUTPUT_CONFIG["console_output"]:
                    print(f"\n🎯 実行 {i}/{len(selected_categories)}: {selected_category['name']}")
                
                # カテゴリページをスクレイピング
                html_files = self.scrape_category_jobs(selected_category['url'])
                if not html_files:
                    continue
                
                # 案件抽出（ファイル保存は行わない）
                category_jobs = self.extract_jobs_only(html_files)
                all_jobs.extend(category_jobs)
                
                # マッチング評価（ファイル保存は行わない）
                category_matches = self.match_jobs_only(category_jobs)
                all_matches.extend(category_matches)
                
                # 結果表示
                self.display_matches(category_matches)
                
                # 連続実行の場合は待機
                if i < len(selected_categories):
                    delay = EXECUTION_CONFIG.get("delay_between_categories", 5)
                    if OUTPUT_CONFIG["console_output"]:
                        print(f"\n⏳ 次のカテゴリまで {delay} 秒待機...")
                    time.sleep(delay)
            
            # 全カテゴリの案件を統合して保存
            if all_jobs:
                self.save_all_jobs_and_matches(all_jobs, all_matches)
        
        except KeyboardInterrupt:
            if OUTPUT_CONFIG["console_output"]:
                print("\n\n⚠️  プログラムが中断されました。")
        
        finally:
            # 保存されたファイルの情報を表示
            self.display_saved_files_summary()
            if OUTPUT_CONFIG["console_output"]:
                print("\nお疲れ様でした！")

    def select_categories_by_llm(self, categories: Dict, user_profile: UserProfile) -> List[Dict]:
        """LLMを使用してユーザープロファイルに基づいて最適なカテゴリを選択"""
        if not LLM_CATEGORY_SELECTION_CONFIG["enabled"]:
            if OUTPUT_CONFIG["console_output"]:
                print("⚠️  LLMカテゴリ選択が無効になっています。デフォルトカテゴリを使用します。")
            return self._get_default_categories(categories)
        
        if OUTPUT_CONFIG["console_output"]:
            print("🤖 LLMによるカテゴリ選択を実行中...")


        main_categories = categories['main_categories']
        categories_and_url = {}
        for main_category in main_categories:
            subcategories = main_category['subcategories']
            for subcategory in subcategories:
                categories_and_url[subcategory['name']] = subcategory['url']

        categories_name = categories_and_url.keys()
        
        # LLMプロンプトを作成
        prompt = self._create_category_selection_prompt(categories_name, user_profile)
        
        # LLMにカテゴリ選択を依頼
        response = generate_chat_completion(
            client=self.job_matcher.client,
            messages=[
                {"role": "system", "content": "あなたはCrowdWorksの案件カテゴリ選択の専門家です。ユーザーのスキル、経験、希望に基づいて最適なカテゴリを選択してください。"},
                {"role": "user", "content": prompt}
            ],
            temperature=LLM_CATEGORY_SELECTION_CONFIG["temperature"]
        )

        # LLMの応答を解析
        if hasattr(response, "choices"):
            # OpenAI/DeepSeek
            content = response.choices[0].message.content
        else:
            # Ollama
            content = response['choices'][0]['message']['content']

        selected_data = self._parse_llm_category_response(content, categories_and_url)
        

        if OUTPUT_CONFIG["console_output"]:
            print(f"✅ LLMが {len(selected_data)} 個のカテゴリを選択しました")
            for i, cat in enumerate(selected_data, 1):
                print(f"   {i}. {cat['name']} ")
        
        return selected_data
    
    
    def _create_category_selection_prompt(self, categories: Dict, user_profile: UserProfile) -> str:
        """カテゴリ選択用のLLMプロンプトを作成"""
        
        prompt = f"""
あなたはCrowdWorksの案件カテゴリ選択の専門家です。以下のユーザープロファイルを分析し、最も適したカテゴリを選択してください。

## ユーザープロファイル
- **スキル**: {', '.join(user_profile.skills)}
- **希望カテゴリ**: {', '.join(user_profile.preferred_categories)}
- **自己紹介**: {user_profile.description}

## 利用可能なカテゴリ
{categories}

## 選択条件
1. **ユーザーのスキルと経験に最も適したカテゴリを選択**
2. **最大{LLM_CATEGORY_SELECTION_CONFIG["max_categories"]}個のカテゴリまで選択可能**
3. **各カテゴリに0-10の関連度スコアを付与**
4. **関連度スコア{LLM_CATEGORY_SELECTION_CONFIG["min_relevance_score"]}以上のカテゴリのみ選択**

## 選択の優先順位
1. ユーザーのスキルと直接関連するカテゴリを優先
2. 希望カテゴリに含まれるカテゴリを優先

## 回答形式
以下のJSON形式で回答してください：
```json
[
  {{
    "main_category": "カテゴリ名（上記リストから正確に選択）",
    "relevance_score": 8.5,
  }}
]
```

**重要**: カテゴリ名は上記の「利用可能なカテゴリ」に記載されている正確な名前を使用してください。
"""
        return prompt
    

    def _parse_llm_category_response(self, response_text: str, categories_and_url: Dict) -> List[Dict]:
        """LLMの応答を解析してカテゴリ情報を抽出"""
        # JSON部分を抽出
        import re
        import json
        
        # JSON部分を検索
        json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
        if not json_match:
            # JSONブロックがない場合は全体をJSONとして解析
            json_text = response_text.strip()
        else:
            json_text = json_match.group(1).strip()

        # JSONテキストをクリーンアップ（trailing commaを除去）
        json_text = re.sub(r',\s*}', '}', json_text)
        json_text = re.sub(r',\s*]', ']', json_text)
        
        # JSONを解析
        selected_data = json.loads(json_text)
        
        # フラットなカテゴリリストを作成（検索用）
        flat_categories = []
        for category in selected_data:
            category_name = category['main_category']
            category_url = categories_and_url.get(category_name)
            # メインカテゴリを追加
            flat_categories.append({
                "name": category_name,
                "url": category_url,
            })

        return flat_categories
    


def main():
    """メイン関数"""
    explorer = CrowdWorksCategoryExplorer()
    explorer.run()

if __name__ == "__main__":
    main() 