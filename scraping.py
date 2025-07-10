import os
import requests
from openai import OpenAI  # OpenAIクライアントを使用
from bs4 import BeautifulSoup
import json
from dotenv import load_dotenv
from pathlib import Path
from playwright.sync_api import sync_playwright
import time

# --- 1. 定数と初期設定 ---
# .envファイルの読み込み
env_path = Path('.env')
load_dotenv(dotenv_path=env_path)

# DeepSeek APIの設定
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"  # DeepSeekのエンドポイント
)

if not os.getenv("DEEPSEEK_API_KEY"):
    raise ValueError("DEEPSEEK_API_KEY環境変数が設定されていません。")

# --- 2. WebページのHTMLコンテンツを取得する関数 ---
def get_html_content(url: str) -> str | None:
    """
    指定されたURLからWebページのHTMLコンテンツを取得します。
    Playwrightを使用して動的なコンテンツを取得します。

    Args:
        url (str): 取得したいWebページのURL。

    Returns:
        str | None: HTMLコンテンツ。取得に失敗した場合はNone。
    """
    try:
        with sync_playwright() as p:
            # ブラウザの起動
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            try:
                # ページの取得
                page.goto(url)
                # JavaScriptの実行を待機
                page.wait_for_load_state('networkidle')
                time.sleep(2)  # 追加の待機時間
                
                # ページのHTMLを取得
                html_content = page.content()
                
                return html_content
                
            finally:
                # ブラウザを終了
                browser.close()
                
    except Exception as e:
        print(f"エラー: URL '{url}' からコンテンツを取得できませんでした。詳細: {e}")
        return None

# --- 3. HTMLから主要なテキストコンテンツを抽出する関数 ---
# LLMに渡す前に、余分なHTMLタグやスクリプトを除去し、テキストとして扱いやすくします。
def extract_main_text(html_content: str) -> str:
    """
    HTMLコンテンツから主要なテキストコンテンツを抽出します。
    <script>, <style>タグを除去し、タグ内のテキストを結合します。

    Args:
        html_content (str): WebページのHTMLコンテンツ。

    Returns:
        str: 抽出された主要なテキストコンテンツ。
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # スクリプトとスタイルタグを削除
    for script_or_style in soup(["script", "style"]):
        script_or_style.extract() # これによりタグとその内容がHTMLから削除される

    # テキストのみを抽出
    # .get_text(separator=' ') で、各要素の間にスペースを挿入して結合
    text = soup.get_text(separator=' ')

    # 連続する改行やスペースを一つにまとめる
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for phrase in ' '.join(lines).split("  ")) # 連続するスペースを一つに
    text = '\n'.join(chunk for chunk in chunks if chunk) # 空のチャンクは除去

    # デバッグ用に抽出されたテキストの一部を表示
    print("\n--- 抽出されたテキストの冒頭 ---")
    print(text[:500])
    print("----------------------------\n")

    return text

# --- 4. LLMにキーワード抽出を依頼する関数 ---
def extract_keywords_with_llm(text_content: str, user_query: str) -> dict | None:
    """
    LLM (Deepseek) を使用して、テキストコンテンツから関連キーワードや案件情報を抽出します。

    Args:
        text_content (str): Webページから抽出された主要なテキストコンテンツ。
        user_query (str): ユーザーが求めている案件のタイプやスキル（例: "Python開発の案件"）。

    Returns:
        dict | None: 抽出されたキーワードや案件情報を含む辞書。LLMがJSONを生成しなかった場合はNone。
    """
    prompt = f"""
    あなたは、与えられたWebページのテキストコンテンツから、ユーザーの要望に合致するフリーランス案件の情報を抽出する専門家です。
    以下の情報を使って、案件のキーワードと合致度を判断し、JSON形式で出力してください。

    ユーザーの要望: "{user_query}"

    テキストコンテンツ:
    ---
    {text_content[:2000]}
    ---

    抽出する情報とフォーマット:
    - `relevant_keywords`: テキストコンテンツ内でユーザーの要望に関連する主要なキーワードのリスト (例: ["Python", "Django", "Web開発", "リモート"])
    - `relevance_score`: ユーザーの要望に対するこのテキストコンテンツの関連度を1から100の数値で評価してください (100が最も関連度が高い)。
    - `summary`: 案件の簡単な要約 (50文字以内)
    - `is_relevant`: この案件がユーザーの要望と**非常に強く関連するか**どうかをTrue/Falseで判断してください。

    JSON形式で出力してください。JSON以外の余計な説明は含めないでください。
    """

    try:
        # DeepSeek Chat API を呼び出す
        response = client.chat.completions.create(
            model="deepseek-chat",  # DeepSeekのモデル名
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts structured information from text."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )

        # レスポンスからメッセージの内容を取得
        llm_output_content = response.choices[0].message.content
        print(f"\n--- LLMからの生出力 ---\n{llm_output_content}\n--------------------")

        # LLMからの出力がJSON形式であることを期待してパース
        parsed_json = json.loads(llm_output_content)
        return parsed_json

    except Exception as e:
        print(f"DeepSeek APIエラーが発生しました: {e}")
        return None

# --- 5. メイン処理 ---
def main():
    """
    プログラムのメイン処理。
    ユーザーからURLとクエリを受け取り、WebスクレイピングとLLMによるキーワード抽出を実行します。
    """
    print("--- Web案件キーワード抽出サービス (MVP) ---")

    # ユーザーからの入力
    # target_url = input("分析したいWebページのURLを入力してください (例: https://www.lancers.jp/work/search/system/freelance?work_kind%5B%5D=1&amp;amp;work_kind%5B%5D=2&work_kind%5B%5D=3 ): ")
    # user_skill_query = input("あなたのスキルや探している案件のタイプを自然言語で入力してください (例: Python開発、Webデザイン): ")

    target_url = "https://crowdworks.jp/public/jobs/group/ai_machine_learning"
    user_skill_query = "LLMエンジニア"

    if not target_url:
        print("URLが入力されていません。終了します。")
        return
    if not user_skill_query:
        print("スキルクエリが入力されていません。終了します。")
        return

    print(f"\nURL: {target_url} からコンテンツを取得中...")
    html_content = get_html_content(target_url)

    if html_content:
        print("HTMLコンテンツの取得に成功しました。主要テキストを抽出中...")
        main_text = extract_main_text(html_content)

        print(f"\nLLM(deepseek-chat)でキーワードを抽出中...")
        llm_result = extract_keywords_with_llm(main_text, user_skill_query)

        if llm_result:
            print("\n--- 抽出結果 ---")
            print(f"関連キーワード: {llm_result.get('relevant_keywords', 'N/A')}")
            print(f"関連度スコア: {llm_result.get('relevance_score', 'N/A')}")
            print(f"要約: {llm_result.get('summary', 'N/A')}")
            print(f"ユーザー関連度が高い: {llm_result.get('is_relevant', 'N/A')}")
            print("-----------------")
        else:
            print("LLMからのキーワード抽出に失敗しました。")
    else:
        print("Webページのコンテンツを取得できませんでした。")

# --- プログラム実行のエントリーポイント ---
if __name__ == "__main__":
    main()