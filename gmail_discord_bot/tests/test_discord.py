import sys
import os
import unittest
from unittest.mock import MagicMock, patch

from gmail_discord_bot.discord_module.message_formatter import MessageFormatter

class TestDiscordModule(unittest.TestCase):
    
    def test_message_formatter(self):
        """MessageFormatterのテスト"""
        formatter = MessageFormatter()
        
        # テスト用のメールデータ
        email_data = {
            'subject': 'テスト件名',
            'sender': 'test@example.com',
            'date': '2023-01-01',
            'body': 'これはテスト本文です。\n改行も含まれています。'
        }
        
        # フォーマットテスト
        formatted, remaining = formatter.format_email_for_discord(email_data)
        
        # 検証
        self.assertIn('テスト件名', formatted)
        self.assertIn('test@example.com', formatted)
        self.assertIn('これはテスト本文です。', formatted)
        self.assertEqual(len(remaining), 0)  # 本文が短いので分割なし
        
        # 長い本文のテスト
        long_body = 'a' * 2000
        email_data['body'] = long_body
        
        formatted, remaining = formatter.format_email_for_discord(email_data)
        
        # 検証
        self.assertGreater(len(remaining), 0)  # 本文が分割されている
    
    def test_response_options_formatting(self):
        """返信候補フォーマットのテスト"""
        formatter = MessageFormatter()
        
        options = [
            "返信候補1です。",
            "返信候補2です。"
        ]
        
        formatted = formatter.format_response_options(options)
        
        # 検証
        self.assertEqual(len(formatted), 2)
        self.assertIn("候補 1", formatted[0])
        self.assertIn("返信候補1です。", formatted[0])
        self.assertIn("候補 2", formatted[1])

if __name__ == '__main__':
    unittest.main()