from typing import Dict, List, Tuple
from ..models.user_profile import UserProfile
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

def filter_fixed_price(job: Dict) -> Tuple[bool, str]:
    """固定報酬制でない案件をフィルタリング
    
    Args:
        job (Dict): 案件情報
        
    Returns:
        Tuple[bool, str]: (除外すべきか, 除外理由)
    """
    budget_type = job['budget']['type']
    if budget_type != "固定報酬制":
        logger.debug(f"案件「{job['title']}」: 報酬形態「{budget_type}」は固定報酬制ではないため除外")
        return True, "固定報酬制でない案件です"
    return False, ""

def apply_filters(job: Dict, user_profile: UserProfile) -> Tuple[bool, str]:
    """全てのフィルターを適用
    
    Args:
        job (Dict): 案件情報
        user_profile (UserProfile): ユーザープロファイル（将来の拡張用）
        
    Returns:
        Tuple[bool, str]: (除外すべきか, 除外理由)
    """
    logger.info(f"\n=== 案件フィルタリング開始: {job['title']} ===")
    
    # フィルターのリスト
    filters = [
        filter_fixed_price,
    ]
    
    # 各フィルターを適用
    for filter_func in filters:
        should_filter, reason = filter_func(job)
        if should_filter:
            logger.info(f"フィルタリング結果: 除外 （理由: {reason}）")
            return True, reason
    
    logger.info("フィルタリング結果: 通過")
    return False, "" 