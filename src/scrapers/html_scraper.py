from playwright.sync_api import sync_playwright
import time
from pathlib import Path
from datetime import datetime
from typing import List
from ..utils.config import SCRAPING_CONFIG

class HTMLScraper:
    """CrowdWorksのHTMLをスクレイピングするクラス"""
    
    def __init__(self, save_dir: str = "data/html"):
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
    
    def save_html_single(self) -> Path:
        """1回分のHTML保存を行う"""
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=['--disable-blink-features=AutomationControlled']
            )
            context = browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
                viewport={'width': 1280, 'height': 800},
                accept_downloads=True,
                java_script_enabled=True,
                bypass_csp=True,
            )
            page = context.new_page()
            
            try:
                # 設定から検索URLを構築
                params = "&".join([f"{k}={v}" for k, v in SCRAPING_CONFIG["search_params"].items()])
                url = f"{SCRAPING_CONFIG['base_url']}?{params}"
                page.goto(url, wait_until='networkidle', timeout=30000)
                
                # 動的コンテンツの完全な読み込みを待機
                page.wait_for_load_state('networkidle')
                
                # スクロールして遅延読み込みコンテンツを表示
                page.evaluate("""
                    window.scrollTo(0, document.body.scrollHeight);
                    new Promise((resolve) => setTimeout(resolve, 2000));
                """)
                
                # さらに待機
                time.sleep(3)
                
                # HTMLを取得
                html_content = page.content()
                
                # ファイル名に現在時刻を含める
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                save_path = self.save_dir / f'page_{timestamp}.html'
                
                # HTMLを保存
                save_path.write_text(html_content, encoding='utf-8')
                print(f"Saved HTML to: {save_path}")
                
                # スクリーンショットも保存
                screenshot_path = self.save_dir / f'screenshot_{timestamp}.png'
                page.screenshot(path=screenshot_path, full_page=True)
                print(f"Saved screenshot to: {screenshot_path}")
                
                return save_path
                
            except Exception as e:
                print(f"Error occurred: {str(e)}")
                raise
            
            finally:
                browser.close()
    
    def save_html_multiple(self, times: int = 1, delay_seconds: int = 5) -> List[Path]:
        """指定回数分のHTML保存を実行（デフォルトは1回）"""
        saved_files = []
        for i in range(times):
            print(f"\n=== 実行 {i+1}/{times} ===")
            saved_path = self.save_html_single()
            saved_files.append(saved_path)
            if i < times - 1:  # 最後の実行以外は待機
                print(f"次の実行まで{delay_seconds}秒待機...")
                time.sleep(delay_seconds)
        return saved_files 