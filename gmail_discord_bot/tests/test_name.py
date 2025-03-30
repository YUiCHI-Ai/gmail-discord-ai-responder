import sys
import os
import unittest
import tempfile
import json
from pathlib import Path

from gmail_discord_bot.name_module.name_extractor import NameExtractor
from gmail_discord_bot.name_module.name_manager import NameManager

class TestNameModule(unittest.TestCase):
    
    def test_name_extractor(self):
        """NameExtractorのテスト"""
        extractor = NameExtractor()
        
        # テスト用のメールデータ
        email_data = {
            'sender': '山田太郎 <yamada@example.co.jp>',
            'body': '''
            お世話になっております。
            ミーティングの件、承知しました。
            
            よろしくお願いいたします。
            
            --
            山田 太郎
            株式会社サンプル
            営業部
            Tel: 03-1234-5678
            '''
        }
        
        # 抽出テスト
        result = extractor.extract_from_email(email_data)
        
        # 検証
        self.assertEqual(result['email'], 'yamada@example.co.jp')
        self.assertEqual(result['name'], '山田 太郎')
        self.assertEqual(result['company'], '株式会社サンプル')
        self.assertIn('営業部', result['department'])
        self.assertIn('03-1234-5678', result['phone'])
    
    def test_name_manager(self):
        """NameManagerのテスト"""
        # 一時ファイルを使用してテスト
        with tempfile.NamedTemporaryFile(delete=False) as temp:
            temp_path = temp.name
        
        try:
            # 空のJSONファイルを作成
            with open(temp_path, 'w') as f:
                json.dump({}, f)
            
            # NameManagerのインスタンス化
            manager = NameManager(db_file=temp_path)
            
            # テスト用のメールデータ
            email_data = {
                'sender': '山田太郎 <yamada@example.co.jp>',
                'body': '''
                お世話になっております。
                ミーティングの件、承知しました。
                
                よろしくお願いいたします。
                
                --
                山田 太郎
                株式会社サンプル
                営業部
                Tel: 03-1234-5678
                '''
            }
            
            # 処理テスト
            result = manager.process_email(email_data)
            
            # 検証
            self.assertEqual(result['email'], 'yamada@example.co.jp')
            self.assertEqual(result['name'], '山田 太郎')
            
            # 宛名フォーマットのテスト
            address = manager.format_address('yamada@example.co.jp')
            self.assertEqual(address, '株式会社サンプル 山田 太郎様')
            
            # 存在しないメールアドレスのテスト
            address = manager.format_address('unknown@example.com')
            self.assertEqual(address, 'お世話になっております')
            
            # データベースが保存されたか確認
            with open(temp_path, 'r') as f:
                saved_data = json.load(f)
            
            self.assertIn('yamada@example.co.jp', saved_data)
            
        finally:
            # テスト後に一時ファイルを削除
            if os.path.exists(temp_path):
                os.unlink(temp_path)

if __name__ == '__main__':
    unittest.main()