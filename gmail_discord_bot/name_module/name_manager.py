import json
import os
from pathlib import Path
from ..utils.logger import setup_logger
from .name_extractor import NameExtractor
from ..config import config

logger = setup_logger(__name__)

class NameManager:
    def __init__(self, db_file=None):
        self.db_file = db_file or config.NAME_DATABASE_FILE
        self.name_db = self._load_database()
        self.extractor = NameExtractor()
    
    def _load_database(self):
        """宛名データベースを読み込む"""
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"宛名データベース読み込みエラー: {e}")
                return {}
        else:
            logger.info(f"宛名データベースが存在しないため、新規作成します: {self.db_file}")
            return {}
    
    def _save_database(self):
        """宛名データベースを保存"""
        try:
            # ディレクトリが存在しない場合は作成
            os.makedirs(os.path.dirname(self.db_file), exist_ok=True)
            
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(self.name_db, f, ensure_ascii=False, indent=2)
            logger.info("宛名データベースを保存しました")
            return True
        except Exception as e:
            logger.error(f"宛名データベース保存エラー: {e}")
            return False
    
    def process_email(self, email_data):
        """メールから送信者情報を抽出し、データベースを更新"""
        # 送信者情報を抽出
        sender_info = self.extractor.extract_from_email(email_data)
        email = sender_info['email']
        
        if not email:
            logger.warning("メールアドレスが抽出できませんでした")
            return None
        
        # データベースを更新
        if email in self.name_db:
            # 既存の情報を更新（空でない値のみ）
            for key, value in sender_info.items():
                if value:
                    self.name_db[email][key] = value
        else:
            # 新規エントリ
            self.name_db[email] = sender_info
        
        # データベースを保存
        self._save_database()
        
        return self.name_db[email]
    
    def get_address_info(self, email):
        """メールアドレスに対応する宛名情報を取得"""
        return self.name_db.get(email, {})
    
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
    
    def update_address_info(self, email, info):
        """宛名情報を手動で更新"""
        if email in self.name_db:
            # 既存の情報を更新
            for key, value in info.items():
                if key in self.name_db[email]:
                    self.name_db[email][key] = value
        else:
            # 新規エントリ
            self.name_db[email] = info
        
        # データベースを保存
        return self._save_database()