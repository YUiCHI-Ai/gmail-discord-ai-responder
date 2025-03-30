import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import asyncio

from gmail_discord_bot.main import EmailBot

class TestIntegration(unittest.TestCase):
    
    @patch('gmail_discord_bot.main.GmailClient')
    @patch('gmail_discord_bot.main.DiscordBot')
    @patch('gmail_discord_bot.main.NameManager')
    @patch('gmail_discord_bot.main.ResponseProcessor')
    @patch('gmail_discord_bot.main.ScheduleAnalyzer')
    async def test_email_processing_flow(self, mock_scheduler, mock_response, mock_name, mock_discord, mock_gmail):
        """メール処理フローの統合テスト"""
        # モックの設定
        mock_email_processor = MagicMock()
        mock_gmail.return_value.get_unread_emails.return_value = []
        
        # テスト用のメールデータ
        test_email = {
            'id': 'test123',
            'subject': 'テストメール',
            'sender': 'Test User <test@example.com>',
            'date': '2023-01-01',
            'body': 'これはテストメールです。',
            'discord_channel_id': '123456789'
        }
        
        mock_email_processor.process_new_emails.return_value = [test_email]
        
        # 名前管理のモック
        mock_name.return_value.process_email.return_value = {
            'email': 'test@example.com',
            'name': 'Test User',
            'company': 'Test Company'
        }
        mock_name.return_value.format_address.return_value = 'Test Company Test User様'
        
        # 返信生成のモック
        mock_response.return_value.generate_responses.return_value = [
            "返信候補1",
            "返信候補2"
        ]
        
        # スケジュール分析のモック
        mock_scheduler.return_value.get_available_slots.return_value = [
            "2023年1月15日(月) 14:00-15:00",
            "2023年1月16日(火) 10:00-11:00"
        ]
        
        # EmailBotのインスタンス化
        bot = EmailBot()
        bot.email_processor = mock_email_processor
        
        # テスト実行
        await bot.check_emails()
        
        # 検証
        mock_email_processor.process_new_emails.assert_called_once()
        mock_name.return_value.process_email.assert_called_once()
        mock_discord.return_value.send_email_notification.assert_called_once()
        mock_discord.return_value.send_response_options.assert_called_once()

def run_async_test(test_func):
    """非同期テスト関数を実行するヘルパー"""
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_func())

if __name__ == '__main__':
    # 非同期テストを実行
    run_async_test(TestIntegration().test_email_processing_flow)
    print("統合テスト成功")