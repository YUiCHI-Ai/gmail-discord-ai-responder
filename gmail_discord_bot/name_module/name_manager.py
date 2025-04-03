import json
import os
from pathlib import Path
from ..utils.logger import setup_logger
from ..config import config

logger = setup_logger(__name__)

class NameManager:
    def __init__(self):
        self.email_mapping = config.get_email_channel_mapping()
    
    def process_email(self, email_data):
        """メールから送信者情報を取得"""
        # 送信者のメールアドレスを抽出
        sender_email = self._extract_email_address(email_data['sender'])
        
        if not sender_email:
            logger.warning("メールアドレスが抽出できませんでした")
            return None
        
        # 送信者情報を取得
        sender_info = self.get_address_info(sender_email)
        
        return sender_info
    
    def _extract_email_address(self, sender_string):
        """送信者文字列からメールアドレスを抽出"""
        # 'Name <email@example.com>' または 'email@example.com' の形式に対応
        import re
        match = re.search(r'<([^>]+)>', sender_string)
        if match:
            return match.group(1).lower()
        else:
            # '<>'がない場合は文字列全体をメールアドレスとみなす
            return sender_string.lower()
    
    def get_address_info(self, email):
        """メールアドレスに対応する宛名情報を取得"""
        # 完全一致
        if email in self.email_mapping:
            return self.email_mapping[email]
        
        # ドメイン一致（example.com形式のマッピングがある場合）
        domain = email.split('@')[-1]
        if domain in self.email_mapping:
            return self.email_mapping[domain]
        
        # ワイルドカードマッピング（*@example.com形式）
        wildcard = f"*@{domain}"
        if wildcard in self.email_mapping:
            return self.email_mapping[wildcard]
        
        # マッピングがない場合は基本情報のみ返す
        return {
            "email": email,
            "name": "",
            "company": "",
            "discord_channel_id": ""
        }
    
    def format_address(self, email):
        """メールアドレスから適切な宛名形式を生成"""
        info = self.get_address_info(email)
        
        # 会社名と名前の両方がある場合
        if info.get('company') and info.get('name'):
            return f"{info['company']} {info['name']}様"
        
        # 会社名のみある場合
        elif info.get('company'):
            return f"{info['company']} ご担当者様"
        
        # 名前のみある場合
        elif info.get('name'):
            return f"{info['name']}様"
        
        # どちらもない場合
        else:
            return "お世話になっております"