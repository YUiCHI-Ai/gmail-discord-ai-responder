import re
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

class NameExtractor:
    def __init__(self):
        # 簡素化：基本的な署名検出のみ
        self.signature_pattern = r'--+\s*\n([\s\S]+)'  # "---" で始まる署名
    
    def extract_from_email(self, email_data):
        """メールから送信者情報を抽出（簡素化版）"""
        sender = email_data['sender']
        body = email_data['body']
        
        # 送信者文字列から基本情報を抽出
        sender_info = self._parse_sender_string(sender)
        
        # 署名から会社名を抽出（簡素化）
        company_name = self._extract_company_from_signature(body)
        if company_name:
            sender_info['company'] = company_name
        
        # 基本情報のみを返す
        result = {
            'email': sender_info.get('email', ''),
            'name': sender_info.get('name', ''),
            'company': sender_info.get('company', '')
        }
        
        logger.info(f"送信者情報を抽出: {result}")
        return result
    
    def _parse_sender_string(self, sender):
        """送信者文字列をパース（'Name <email@example.com>' 形式）"""
        result = {'email': '', 'name': ''}
        
        # メールアドレスを抽出
        email_match = re.search(r'<([^>]+)>', sender)
        if email_match:
            result['email'] = email_match.group(1)
            # 名前部分を抽出（<>の前の部分）
            name_part = sender.split('<')[0].strip()
            if name_part:
                result['name'] = name_part
        else:
            # '<>'がない場合
            if '@' in sender:
                result['email'] = sender.strip()
                # メールアドレスからユーザー名を抽出
                username = sender.split('@')[0].strip()
                if username:
                    result['name'] = username
        
        # ドメインから会社名を推測
        if result['email'] and '@' in result['email']:
            domain = result['email'].split('@')[1]
            company_part = domain.split('.')[0]
            if company_part and company_part not in ['gmail', 'yahoo', 'hotmail', 'outlook', 'icloud']:
                result['company'] = company_part.capitalize()
        
        return result
    
    def _extract_company_from_signature(self, body):
        """メール本文から会社名のみを抽出（簡素化）"""
        # 署名部分を抽出
        signature_match = re.search(self.signature_pattern, body, re.MULTILINE)
        if not signature_match:
            return None
        
        signature = signature_match.group(1)
        lines = signature.strip().split('\n')
        
        # 会社名を抽出（よくある形式のみ）
        company_patterns = [
            r'(株式会社\S+)',
            r'(\S+株式会社)',
            r'(\S+\s*Co[\.,]\s*Ltd\.)',
            r'(\S+\s*Corporation)',
            r'(\S+\s*Inc\.)',
        ]
        
        for line in lines:
            for pattern in company_patterns:
                match = re.search(pattern, line)
                if match:
                    return match.group(1)
        
        return None