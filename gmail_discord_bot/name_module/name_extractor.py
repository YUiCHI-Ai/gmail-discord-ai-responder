import re
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

class NameExtractor:
    def __init__(self):
        # 署名を検出するための正規表現パターン
        self.signature_patterns = [
            r'--+\s*\n([\s\S]+)',  # "---" で始まる署名
            r'^\s*(?:敬具|よろしくお願いします|よろしくお願い致します).*?\n([\s\S]+)',  # 日本語の締めの後の署名
            r'(?:Regards|Sincerely|Best regards|Thanks|Thank you).*?\n([\s\S]+)',  # 英語の締めの後の署名
        ]
    
    def extract_from_email(self, email_data):
        """メールから送信者情報を抽出"""
        sender = email_data['sender']
        body = email_data['body']
        
        # 送信者文字列から情報を抽出
        sender_info = self._parse_sender_string(sender)
        
        # 署名から情報を抽出
        signature_info = self._extract_from_signature(body)
        
        # 情報を統合（署名の情報を優先）
        result = {
            'email': sender_info.get('email', ''),
            'name': signature_info.get('name', sender_info.get('name', '')),
            'company': signature_info.get('company', ''),
            'department': signature_info.get('department', ''),
            'title': signature_info.get('title', ''),
            'phone': signature_info.get('phone', ''),
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
        
        return result
    
    def _extract_from_signature(self, body):
        """メール本文から署名情報を抽出"""
        result = {}
        
        # 署名部分を抽出
        signature = None
        for pattern in self.signature_patterns:
            match = re.search(pattern, body, re.MULTILINE)
            if match:
                signature = match.group(1)
                break
        
        if not signature:
            return result
        
        # 署名から情報を抽出
        # 名前を抽出（通常は署名の最初の行）
        lines = signature.strip().split('\n')
        if lines:
            result['name'] = lines[0].strip()
        
        # 会社名を抽出（よくある形式: 株式会社XXX、XXX株式会社、XXX Co., Ltd.など）
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
                    result['company'] = match.group(1)
                    break
            
            # 部署名・役職を抽出
            dept_patterns = [
                r'(部長|課長|マネージャー|リーダー|ディレクター|エンジニア)',
                r'(Department|Division|Team)',
            ]
            
            for pattern in dept_patterns:
                match = re.search(pattern, line)
                if match:
                    if '部' in line or 'Department' in line or 'Division' in line:
                        result['department'] = line.strip()
                    else:
                        result['title'] = line.strip()
            
            # 電話番号を抽出
            phone_match = re.search(r'(?:Tel|TEL|電話)[:：]?\s*(\+?[\d\-\(\)\s]+)', line)
            if phone_match:
                result['phone'] = phone_match.group(1).strip()
        
        return result