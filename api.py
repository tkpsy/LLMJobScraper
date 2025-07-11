import os
from typing import Literal, Union, Dict, Any
from dotenv import load_dotenv
from openai import OpenAI
import ollama
import json

# .envファイルの読み込み
load_dotenv()

# LLMの種類を定義
LLMType = Literal["deepseek", "local"]

def get_client(llm_type: LLMType = "local") -> Union[OpenAI, ollama]:
    """LLMクライアントを取得
    
    Args:
        llm_type (LLMType): 使用するLLMの種類 ("deepseek" or "local")
        
    Returns:
        Union[OpenAI, ollama]: LLMクライアント
        
    Raises:
        ValueError: 不正なLLMタイプが指定された場合、またはDeepSeekのAPIキーが設定されていない場合
    """
    # 環境変数でLLMタイプを上書き可能
    llm_type = os.getenv("LLM_TYPE", llm_type)
    
    if llm_type == "deepseek":
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError(
                "DeepSeek APIを使用するには DEEPSEEK_API_KEY を環境変数に設定してください。"
                "\n.envファイルに DEEPSEEK_API_KEY=your_api_key_here を追加してください。"
            )
        print("DeepSeek APIモデル 'deepseek-chat' を使用します。")
        return OpenAI(api_key=api_key, base_url="https://api.deepseek.com/v1")
    
    elif llm_type == "local":
        # Ollamaが利用可能かチェック
        try:
            required_model = "elyza:jp8b"
            print(f"Local LLMモデル '{required_model}' を使用します。")
            return ollama
            
        except Exception as e:
            raise ValueError(
                "Ollamaサーバーに接続できません。以下を確認してください：\n"
                "1. Ollamaがインストールされているか\n"
                "2. Ollamaサーバーが起動しているか\n"
                f"エラー詳細: {str(e)}"
            )
    
    raise ValueError(f"未対応のLLMタイプです: {llm_type}")

# LLMの共通インターフェース
def generate_chat_completion(
    client: Union[OpenAI, ollama],
    messages: list,
    response_format: dict = None,
    temperature: float = 0.1
) -> Dict[str, Any]:
    """LLMを使用してチャット応答を生成
    
    Args:
        client: LLMクライアント（OpenAIまたはollama）
        messages: チャットメッセージのリスト
        response_format: 応答フォーマットの指定（DeepSeekのみ対応）
        temperature: 応答の多様性（0-1）
        
    Returns:
        Dict[str, Any]: 統一された形式の応答
        {
            'choices': [{
                'message': {
                    'content': str,
                    'role': str
                },
                'finish_reason': str
            }],
            'model': str
        }
    """
    try:
        if isinstance(client, OpenAI):
            # DeepSeek APIを使用
            response = client.chat.completions.create(
                model="deepseek-chat",
                messages=messages,
                response_format=response_format,
                temperature=temperature,
            )
            return response
            
        else:
            # Local LLM (Ollama) を使用
            response = client.chat(
                model='elyza:jp8b',
                messages=messages,
                stream=False,
                format="json" if response_format else None,
                options={"temperature": temperature}
            )
            
            # Ollamaの応答をDeepSeekと同じ形式に変換
            formatted_response = {
                'choices': [{
                    'message': {
                        'content': response['message']['content'],
                        'role': response['message']['role']
                    },
                    'finish_reason': 'stop'  # Ollamaは明示的なfinish_reasonを返さないため
                }],
                'model': response['model']
            }
            
            # response_formatが指定されている場合、JSONとしてパースを試みる
            if response_format and response_format.get('type') == 'json':
                try:
                    content = formatted_response['choices'][0]['message']['content']
                    # 文字列がJSONの場合はパースして再度文字列化
                    json_content = json.loads(content)
                    formatted_response['choices'][0]['message']['content'] = json.dumps(
                        json_content, ensure_ascii=False, indent=2
                    )
                except json.JSONDecodeError:
                    raise ValueError("Local LLMの応答をJSONとしてパースできませんでした。")
            
            return formatted_response
            
    except Exception as e:
        error_msg = f"LLMの実行中にエラーが発生しました: {str(e)}"
        raise Exception(error_msg)

