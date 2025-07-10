from scraping import get_html_content, extract_main_text, extract_keywords_with_llm

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

if __name__ == "__main__":
    main() 