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
    
    def save_html_with_pagination(self, category_url: str, max_pages: int = 3) -> List[Path]:
        """複数ページに跨ったHTML保存を行う（シンプル版）"""
        print(f"📄 複数ページスクレイピング開始: 最大{max_pages}ページ")
        
        saved_files = []
        
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
                for page_num in range(1, max_pages + 1):
                    print(f"🔍 ページ {page_num}/{max_pages} を処理中...")
                    
                    # ページURLを構築
                    params = "&".join([f"{k}={v}" for k, v in SCRAPING_CONFIG["search_params"].items()])
                    if page_num == 1:
                        url = f"{category_url}?{params}"
                    else:
                        url = f"{category_url}?{params}&page={page_num}"
                    
                    print(f"  URL: {url}")
                    
                    # ページにアクセス
                    page.goto(url, wait_until='networkidle', timeout=30000)
                    page.wait_for_load_state('networkidle')
                    
                    # 既存と同じ待機処理
                    page.evaluate("""
                        window.scrollTo(0, document.body.scrollHeight);
                        new Promise((resolve) => setTimeout(resolve, 2000));
                    """)
                    time.sleep(3)
                    
                    # HTMLを取得して保存
                    html_content = page.content()
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    save_path = self.save_dir / f'page_{timestamp}_p{page_num}.html'
                    
                    save_path.write_text(html_content, encoding='utf-8')
                    saved_files.append(save_path)
                    
                    print(f"  ✅ 保存完了: {save_path}")
                    
                    # スクリーンショットも保存
                    screenshot_path = self.save_dir / f'screenshot_{timestamp}_p{page_num}.png'
                    page.screenshot(path=screenshot_path, full_page=True)
                    
                    # 次のページがあるかチェック（簡易版）
                    if page_num < max_pages:
                        # 次のページリンクがあるかチェック
                        next_page_exists = self._check_next_page_exists(page, page_num + 1)
                        if not next_page_exists:
                            print(f"  ⚠️  ページ {page_num + 1} は存在しません。{page_num}ページで終了します。")
                            break
                        
                        # ページ間の待機
                        time.sleep(2)
                
                print(f"🎉 複数ページスクレイピング完了: {len(saved_files)}ページ保存")
                return saved_files
                
            except Exception as e:
                print(f"❌ 複数ページスクレイピング中にエラー: {e}")
                return saved_files  # 途中まで保存されたファイルを返す
            
            finally:
                browser.close()
    
    def _check_next_page_exists(self, page, next_page_num: int) -> bool:
        """次のページが存在するかチェックする"""
        try:
            # 調査で見つかったセレクターを使用
            next_page_selectors = [
                'a:has-text("次のページ")',  # 調査で見つかった主要セレクター
                f'a:has-text("{next_page_num}")',  # ページ番号リンク
                'nav a'  # ナビゲーション内のリンク
            ]
            
            for selector in next_page_selectors:
                try:
                    elements = page.query_selector_all(selector)
                    for elem in elements:
                        text = elem.text_content().strip()
                        href = elem.get_attribute('href')
                        
                        # 次のページリンクまたはページ番号リンクを確認
                        if (('次のページ' in text) or 
                            (text == str(next_page_num)) or 
                            (href and f'page={next_page_num}' in href)):
                            return True
                except Exception:
                    continue
            
            return False
            
        except Exception:
            return False 