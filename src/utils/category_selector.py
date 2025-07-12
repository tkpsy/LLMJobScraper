"""
LLMベースカテゴリ選択エンジン
ユーザープロファイルを分析してcategories.jsonから最適なカテゴリを選択する
"""

import json
import os
from typing import List, Dict, Any
from dataclasses import dataclass
from src.models.user_profile import UserProfile
from api import get_client, generate_chat_completion
from src.utils.config import MATCHING_CONFIG


@dataclass
class SelectedCategory:
    """選択されたカテゴリ情報"""
    name: str
    url: str
    category_id: str
    category_type: str  # 'main' or 'sub'
    relevance_score: float
    reason: str


class CategorySelector:
    """LLMベースカテゴリ選択エンジン"""
    
    def __init__(self, categories_file: str = None):
        self.categories_file = categories_file or os.path.join(os.path.dirname(__file__), '../../categories.json')
        self.categories_data = self._load_categories()
        self.client = get_client("local")  # LocalLLMを使用
    
    def _load_categories(self) -> Dict[str, Any]:
        """categories.jsonを読み込む"""
        try:
            with open(self.categories_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"categories.json not found at {self.categories_file}")
    
    def _format_categories_for_llm(self) -> str:
        """LLMに提供するカテゴリ情報を整形"""
        formatted = "【利用可能なカテゴリ一覧】\n\n"
        
        for main_cat in self.categories_data['main_categories']:
            formatted += f"メインカテゴリ: {main_cat['name']} (ID: {main_cat['id']})\n"
            
            if main_cat.get('subcategories'):
                formatted += "  サブカテゴリ:\n"
                for sub_cat in main_cat['subcategories']:
                    formatted += f"    - {sub_cat['name']} (ID: {sub_cat['id']})\n"
            
            formatted += "\n"
        
        return formatted
    
    def select_categories(self, user_profile: UserProfile, max_categories: int = 5) -> List[SelectedCategory]:
        """
        ユーザープロファイルから最適なカテゴリを選択
        
        Args:
            user_profile: ユーザープロファイル
            max_categories: 選択する最大カテゴリ数
            
        Returns:
            選択されたカテゴリのリスト
        """
        categories_info = self._format_categories_for_llm()
        
        prompt = f"""
あなたは案件マッチングの専門家です。以下のユーザープロファイルを分析して、最も適切なカテゴリを選択してください。

【ユーザープロファイル】
- スキル: {', '.join(user_profile.skills)}
- 希望カテゴリ: {', '.join(user_profile.preferred_categories)}
- 希望勤務形態: {', '.join(user_profile.preferred_work_type)}
- 自己紹介: {user_profile.description}

{categories_info}

【選択基準】
1. ユーザーのスキルと最も関連性の高いカテゴリ
2. ユーザーの希望カテゴリとの親和性
3. 自己紹介文から読み取れる専門性・興味分野
4. 幅広い案件機会を提供できるカテゴリ

【出力形式】
必ず以下のJSON形式で回答してください：
{{
  "selected_categories": [
    {{
      "name": "カテゴリ名",
      "id": "カテゴリID",
      "type": "main" or "sub",
      "relevance_score": 0.0-100.0,
      "reason": "選択理由"
    }}
  ]
}}

最大{max_categories}個のカテゴリを、関連度の高い順に選択してください。
メインカテゴリとサブカテゴリの両方を適切に組み合わせて選択してください。
"""

        try:
            response = generate_chat_completion(
                client=self.client,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that selects appropriate categories based on user profile."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )
            
            # レスポンスから内容を取得
            if hasattr(response, 'choices'):
                content = response.choices[0].message.content
            else:
                content = response['choices'][0]['message']['content']
            
            result = self._parse_llm_response(content)
            return self._create_selected_categories(result)
        except Exception as e:
            print(f"カテゴリ選択中にエラーが発生しました: {e}")
            # フォールバック：デフォルトカテゴリを返す
            return self._get_default_categories()
    
    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """LLMの応答をパース"""
        try:
            # JSONブロックを抽出
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("JSON format not found in response")
            
            json_str = response[start_idx:end_idx]
            return json.loads(json_str)
        except (json.JSONDecodeError, ValueError) as e:
            print(f"LLM応答のパースに失敗しました: {e}")
            print(f"応答内容: {response}")
            raise
    
    def _create_selected_categories(self, parsed_result: Dict[str, Any]) -> List[SelectedCategory]:
        """パース結果からSelectedCategoryオブジェクトを作成"""
        selected_categories = []
        
        for cat_data in parsed_result.get('selected_categories', []):
            category_info = self._find_category_info(cat_data['id'])
            
            if category_info:
                selected_categories.append(SelectedCategory(
                    name=category_info['name'],
                    url=category_info['url'],
                    category_id=cat_data['id'],
                    category_type=cat_data['type'],
                    relevance_score=float(cat_data['relevance_score']),
                    reason=cat_data['reason']
                ))
        
        return selected_categories
    
    def _find_category_info(self, category_id: str) -> Dict[str, Any]:
        """カテゴリIDからカテゴリ情報を取得"""
        # メインカテゴリを検索
        for main_cat in self.categories_data['main_categories']:
            if main_cat['id'] == category_id:
                return {
                    'name': main_cat['name'],
                    'url': main_cat['url'],
                    'id': main_cat['id']
                }
            
            # サブカテゴリを検索
            for sub_cat in main_cat.get('subcategories', []):
                if sub_cat['id'] == category_id:
                    return {
                        'name': sub_cat['name'],
                        'url': sub_cat['url'],
                        'id': sub_cat['id']
                    }
        
        return None
    
    def _get_default_categories(self) -> List[SelectedCategory]:
        """デフォルトカテゴリを取得（エラー時のフォールバック）"""
        default_categories = []
        
        # AI・機械学習カテゴリをデフォルトとして使用
        ai_category = None
        for main_cat in self.categories_data['main_categories']:
            if main_cat['id'] == 'ai_machine_learning':
                ai_category = main_cat
                break
        
        if ai_category:
            default_categories.append(SelectedCategory(
                name=ai_category['name'],
                url=ai_category['url'],
                category_id=ai_category['id'],
                category_type='main',
                relevance_score=70.0,
                reason="デフォルト選択（AI・機械学習）"
            ))
        
        return default_categories
    
    def get_all_categories(self) -> Dict[str, Any]:
        """全カテゴリ情報を取得"""
        return self.categories_data
    
    def get_category_by_id(self, category_id: str) -> Dict[str, Any]:
        """IDによるカテゴリ情報取得"""
        return self._find_category_info(category_id) 