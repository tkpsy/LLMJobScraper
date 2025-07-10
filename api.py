from openai import OpenAI
from dotenv import load_dotenv
import os
from pathlib import Path

env_path = Path('.env')
load_dotenv(dotenv_path=env_path)



def get_client(type: str):
    """
    DeepSeek APIのクライアントを取得する
    type: deepseek or openai
    """
    if type == "deepseek":
        client = OpenAI(
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com"
        )
    elif type == "openai":
        client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url="https://api.openai.com/v1"
        )
    else:
        raise ValueError("typeはdeepseekかopenaiのみ指定できます。")

    if not os.getenv("DEEPSEEK_API_KEY"):
        raise ValueError("DEEPSEEK_API_KEY環境変数が設定されていません。")
    
    return client

