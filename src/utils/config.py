from pathlib import Path

# プロジェクトのルートディレクトリ
ROOT_DIR = Path(__file__).parent.parent.parent

# データ保存用のディレクトリ
DATA_DIR = ROOT_DIR / "data"
HTML_DIR = DATA_DIR / "html"
JOBS_DIR = DATA_DIR / "jobs"
MATCHES_DIR = DATA_DIR / "matches"

# 各ディレクトリを作成
for dir_path in [DATA_DIR, HTML_DIR, JOBS_DIR, MATCHES_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# スクレイピング設定
SCRAPING_CONFIG = {
    "base_url": "https://crowdworks.jp/public/jobs/search",
    "search_params": {
        "category": "jobs",
        "order": "new",
        "hide_expired": "true"
    },
    "retry_count": 3,
    "retry_delay": 5  # seconds
}

# マッチング設定
MATCHING_CONFIG = {
    "min_score": 80,
    "max_jobs": 20,
    "batch_size": 10,
    "llm_type": "local",
    "llm_model": "qwen2.5:latest",
    "temperature": 0.2,
}




# LLMカテゴリ選択設定
LLM_CATEGORY_SELECTION_CONFIG = {
    "max_categories": 2,
    "min_relevance_score": 8,
    "llm_type": "local",
    "llm_model": "qwen2.5:latest",
    "temperature": 0.2,
    "max_tokens": 1000,
}









# ユーザープロファイル設定
USER_PROFILE_CONFIG = {
    "skills": ['Figma'],
    "preferred_categories": ['webデザイン'],
    "preferred_work_type": ['リモート'],
    "description": "FigmaやAdobeを使ってwebなどのデザインができます",
}









# 実行オプション設定
EXECUTION_CONFIG = {
    "save_detailed_logs": True,  # 詳細なログを保存するかどうか
    "save_screenshots": True,    # スクリーンショットを保存するかどうか
    "max_pages_per_category": 5, # カテゴリごとの最大取得ページ数（1=単一ページ, 2以上=複数ページ）
    "show_progress": True,       # 進捗表示を行うかどうか
    "auto_open_results": False,  # 結果ファイルを自動で開くかどうか
    "delay_between_categories": 5,  # カテゴリ間の待機時間（秒）
}

# 出力設定
OUTPUT_CONFIG = {
    "console_output": True,      # コンソール出力を行うかどうか
    "file_output": True,         # ファイル出力を行うかどうか
    "detailed_summary": True,    # 詳細なサマリーを表示するかどうか
    "show_file_sizes": True,     # ファイルサイズを表示するかどうか
    "export_formats": ["json", "csv"],  # 出力形式
} 