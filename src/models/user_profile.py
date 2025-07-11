from dataclasses import dataclass
from typing import List, Optional

@dataclass
class UserProfile:
    """ユーザープロファイル"""
    skills: List[str]  # 持っているスキル
    experience_years: int  # 経験年数
    preferred_categories: List[str]  # 希望する案件カテゴリ
    preferred_work_type: List[str]  # 希望する働き方（リモート、オンサイトなど）
    min_budget: Optional[int]  # 希望する最低予算
    description: str  # 自己紹介や希望する案件の説明 