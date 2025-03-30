import sys
import os
import unittest
from unittest.mock import MagicMock, patch

from gmail_discord_bot.gmail_module.gmail_client import GmailClient
from gmail_discord_bot.gmail_module.email_processor import EmailProcessor

class TestGmailModule(unittest.TestCase):
    
    @patch('gmail_discord_bot.gmail_module.gmail_client.build')
    @patch('gmail_discord_bot.gmail_module.gmail_client.InstalledAppFlow')
    @patch('gmail_discord_bot.gmail_module.gmail_client.Request')
    def test_gmail_client_initialization(self, mock_request, mock_flow, mock_build):
        """GmailClientの初期化テスト"""
        # モックの設定
        mock_build.return_value = MagicMock()
        
        # テスト実行
        client = GmailClient()
        
        # 検証
        self.assertIsNotNone(client.service)
        mock_build.assert_called_once()
    
    def test_email_processor(self):
        """EmailProcessorのテスト"""
        # モックのGmailClientを作成
        mock_client = MagicMock()
        mock_client.get_unread_emails.return_value = [
            {
                'id': '123',
                'subject': 'テストメール',
                'sender': 'Test User <test@example.com>',
                'date': '2023-01-01',
                'body': 'これはテストメールです。'
            }
        ]
        
        # EmailProcessorのインスタンス化
        processor = EmailProcessor(gmail_client=mock_client)
        
        # email_channel_mappingをモックで設定
        processor.email_channel_mapping = {
            'test@example.com': '123456789'
        }
        
        # テスト実行
        processed = processor.process_new_emails()
        
        # 検証
        self.assertEqual(len(processed), 1)
        self.assertEqual(processed[0]['discord_channel_id'], '123456789')
        mock_client.mark_as_read.assert_called_once_with('123')

if __name__ == '__main__':
    unittest.main()