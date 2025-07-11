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
    "min_score": 70.0,
    "max_jobs": 5,
    "llm_model": "deepseek-chat",
    "temperature": 0.1
}

# ターゲットカテゴリ
TARGET_CATEGORIES = [
    'AI・機械学習',
    '機械学習・ディープラーニング',
    'AI・チャットボット開発',
    'ChatGPT開発',
    'AIアノテーション',
    'データサイエンス'
] 