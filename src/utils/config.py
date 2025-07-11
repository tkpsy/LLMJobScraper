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

# 自動実行設定
AUTO_EXECUTION_CONFIG = {
    "enabled": True,  # 自動実行を有効にするかどうか
    "target_categories": [
        {
            "main_category": "AI（人工知能）・機械学習",
            "subcategory": None,  # Noneの場合はメインカテゴリ全体を対象
            "description": "AI・機械学習分野全般の案件を取得"
        }
        # 複数カテゴリを設定したい場合は以下のように追加
        # {
        #     "main_category": "システム開発",
        #     "subcategory": "Web開発・システム設計",
        #     "description": "Web開発案件を取得"
        # },
        # {
        #     "main_category": "ホームページ制作・Webデザイン",
        #     "subcategory": None,
        #     "description": "Webデザイン全般の案件を取得"
        # }
    ],
    "continuous_execution": False,  # 全カテゴリを連続実行するかどうか
    "delay_between_categories": 10,  # カテゴリ間の待機時間（秒）
}

# ユーザープロファイル設定
USER_PROFILE_CONFIG = {
    "skills": ["Python", "機械学習", "AI", "データサイエンス", "ChatGPT", "深層学習", "自然言語処理"],
    "experience_years": 3,
    "preferred_categories": ["AI・機械学習", "機械学習・ディープラーニング", "ChatGPT開発", "AI・チャットボット開発"],
    "preferred_work_type": ["リモート", "フルリモート", "在宅"],
    "min_budget": 50000,
    "description": "AI・機械学習分野でのフリーランス案件を探しています。特にChatGPT、LLM、深層学習関連の案件に興味があります。Python、TensorFlow、PyTorchを使った開発経験があります。"
}

# 実行オプション設定
EXECUTION_CONFIG = {
    "save_detailed_logs": True,  # 詳細なログを保存するかどうか
    "save_screenshots": True,    # スクリーンショットを保存するかどうか
    "max_pages_per_category": 5, # カテゴリごとの最大取得ページ数（1=単一ページ, 2以上=複数ページ）
    "show_progress": True,       # 進捗表示を行うかどうか
    "auto_open_results": False,  # 結果ファイルを自動で開くかどうか
}

# 出力設定
OUTPUT_CONFIG = {
    "console_output": True,      # コンソール出力を行うかどうか
    "file_output": True,         # ファイル出力を行うかどうか
    "detailed_summary": True,    # 詳細なサマリーを表示するかどうか
    "show_file_sizes": True,     # ファイルサイズを表示するかどうか
    "export_formats": ["json", "csv"],  # 出力形式
} 