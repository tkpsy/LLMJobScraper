from dataclasses import dataclass
from typing import List

@dataclass
class UserProfile:
    """ユーザープロファイル"""
    skills: List[str]  # 持っているスキル
    preferred_categories: List[str]  # 希望する案件カテゴリ
    preferred_work_type: List[str]  # 希望する働き方（リモート、オンサイトなど）
    description: str  # 自己紹介や希望する案件の説明 