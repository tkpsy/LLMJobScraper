from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import List, Optional, Dict
from datetime import datetime
import re
import json
from pathlib import Path

@dataclass
class Budget:
    """予算情報を格納するデータクラス"""
    type: str  # 固定報酬制、時間単価制など
    min_amount: Optional[int]  # 最小金額（円）
    max_amount: Optional[int]  # 最大金額（円）
    is_negotiable: bool  # 相談可能かどうか

@dataclass
class JobItem:
    """案件情報を格納するデータクラス"""
    title: str
    category: str
    description: str
    budget: Budget
    deadline: Optional[str]
    posted_date: datetime
    client_name: str
    url: Optional[str]
    is_pr: bool

class JobExtractor:
    """HTMLから案件情報を抽出するクラス"""
    
    def __init__(self, save_dir: str = "data/jobs"):
        self.save_dir = Path(save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
    
    def parse_budget_text(self, budget_text: str) -> Budget:
        """予算テキストをパースしてBudgetオブジェクトを返す"""
        budget_text = budget_text.strip()
        
        # 相談可能かどうかを判定
        is_negotiable = "相談" in budget_text or "応相談" in budget_text
        
        # 報酬形態を判定
        if "固定報酬制" in budget_text:
            type_ = "固定報酬制"
        elif "時間単価制" in budget_text:
            type_ = "時間単価制"
        else:
            type_ = "その他"
        
        # 金額を抽出
        amount_pattern = r'(\d{1,3}(?:,\d{3})*)'
        amounts = re.findall(amount_pattern, budget_text)
        
        # 金額をint型に変換（カンマを除去）
        amounts = [int(amount.replace(',', '')) for amount in amounts]
        
        if not amounts:
            return Budget(type=type_, min_amount=None, max_amount=None, is_negotiable=is_negotiable)
        elif len(amounts) == 1:
            return Budget(type=type_, min_amount=amounts[0], max_amount=amounts[0], is_negotiable=is_negotiable)
        else:
            return Budget(type=type_, min_amount=min(amounts), max_amount=max(amounts), is_negotiable=is_negotiable)
    
    def parse_date_text(self, date_text: str) -> datetime:
        """日付テキストをパースしてdatetimeオブジェクトを返す"""
        pattern = r'(\d{4})年(\d{2})月(\d{2})日'
        match = re.search(pattern, date_text)
        if match:
            year, month, day = map(int, match.groups())
            return datetime(year, month, day)
        raise ValueError(f"Invalid date format: {date_text}")
    
    def extract_jobs(self, html_file: Path) -> List[JobItem]:
        """HTMLファイルから案件情報を抽出する"""
        with open(html_file, 'r', encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')
        
        jobs = []
        # 案件カードのコンテナを取得
        job_containers = soup.find_all('div', class_='UNzN7')
        
        for container in job_containers:
            try:
                # タイトル情報を含むdivを取得
                title_div = container.find('div', class_='rGkuO')
                if not title_div:
                    continue
                
                # クライアント名と掲載日を分離
                title_text = title_div.get_text().strip()
                client_match = re.match(r'^(.+?)掲載日：', title_text)
                client_name = client_match.group(1) if client_match else "不明"
                
                # 案件本文を取得
                job_text = container.get_text().strip()
                
                # PRかどうかを判定
                is_pr = job_text.startswith('PR')
                
                # タイトルを抽出（PRプレフィックスを除去）
                title = job_text.split('\n')[0]
                if is_pr:
                    title = title[2:].strip()
                
                # カテゴリを判定
                categories = [
                    'AI・機械学習', '機械学習・ディープラーニング', 'AI・チャットボット開発',
                    'ChatGPT開発', 'AIアノテーション', 'データサイエンス'
                ]
                category = next((cat for cat in categories if cat in title), '')
                
                # 予算と期限を取得
                budget_elements = container.find_all('div', class_='mLant')
                budget = None
                deadline = None
                
                for element in budget_elements:
                    text = element.get_text().strip()
                    if any(keyword in text for keyword in ['円', '報酬']):
                        budget = self.parse_budget_text(text)
                    elif 'まで' in text:
                        deadline = text
                
                # 掲載日を取得
                date_div = container.find('div', class_='cAtkF')
                posted_date = self.parse_date_text(date_div.get_text()) if date_div else None
                
                # 説明文を取得
                description_lines = [line.strip() for line in job_text.split('\n')[1:] 
                                   if line.strip() and not any(keyword in line for keyword in ['円', 'まで', '掲載日：'])]
                description = '\n'.join(description_lines)
                
                # URLを取得
                url_element = container.find('a', href=True)
                url = url_element['href'] if url_element else None
                
                job = JobItem(
                    title=title,
                    category=category,
                    description=description,
                    budget=budget or Budget(type="不明", min_amount=None, max_amount=None, is_negotiable=True),
                    deadline=deadline,
                    posted_date=posted_date,
                    client_name=client_name,
                    url=url,
                    is_pr=is_pr
                )
                jobs.append(job)
                
            except Exception as e:
                print(f"案件の解析中にエラーが発生しました: {e}")
                continue
        
        return jobs
    
    def save_jobs_to_json(self, jobs: List[JobItem], timestamp: str = None):
        """案件情報をJSONファイルとして保存"""
        if timestamp is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        jobs_data = [
            {
                'title': job.title,
                'category': job.category,
                'description': job.description,
                'budget': {
                    'type': job.budget.type,
                    'min_amount': job.budget.min_amount,
                    'max_amount': job.budget.max_amount,
                    'is_negotiable': job.budget.is_negotiable
                },
                'deadline': job.deadline,
                'posted_date': job.posted_date.isoformat() if job.posted_date else None,
                'client_name': job.client_name,
                'url': job.url,
                'is_pr': job.is_pr
            }
            for job in jobs
        ]
        
        output_file = self.save_dir / f'extracted_jobs_{timestamp}.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(jobs_data, f, ensure_ascii=False, indent=2)
        
        print(f"\n案件情報を {output_file} に保存しました。")
        return output_file 