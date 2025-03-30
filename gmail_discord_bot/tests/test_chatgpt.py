import sys
import os
import unittest
from unittest.mock import MagicMock, patch
import asyncio

from gmail_discord_bot.chatgpt_module.prompt_generator import PromptGenerator
from gmail_discord_bot.chatgpt_module.response_processor import ResponseProcessor

class TestChatGPTModule(unittest.TestCase):
    
    def test_prompt_generator(self):
        """PromptGeneratorのテスト"""
        generator = PromptGenerator()
        
        # 通常のメール
        normal_email = {
            'subject': 'プロジェクト進捗について',
            'sender': 'test@example.com',
            'body': 'プロジェクトの進捗状況を教えてください。'
        }
        
        # 日程調整のメール
        schedule_email = {
            'subject': 'ミーティングの日程調整',
            'sender': 'test@example.com',
            'body': '来週のミーティングの日程を調整したいと思います。'
        }
        
        # 日程調整判定のテスト
        self.assertFalse(generator.is_schedule_related(normal_email))
        self.assertTrue(generator.is_schedule_related(schedule_email))
        
        # プロンプト生成のテスト
        sender_info = {'name': '山田太郎', 'company': '株式会社サンプル'}
        address = '株式会社サンプル 山田太郎様'
        
        normal_prompt = generator.generate_normal_prompt(normal_email, sender_info, address)
        self.assertIn('プロジェクト進捗について', normal_prompt)
        self.assertIn(address, normal_prompt)
        
        available_slots = ['2023-01-15 14:00-15:00', '2023-01-16 10:00-11:00']
        schedule_prompt = generator.generate_schedule_prompt(
            schedule_email, sender_info, address, available_slots
        )
        self.assertIn('ミーティングの日程調整', schedule_prompt)
        self.assertIn('2023-01-15', schedule_prompt)
        self.assertIn(address, schedule_prompt)
    
    @patch('gmail_discord_bot.chatgpt_module.response_processor.openai.ChatCompletion.create')
    def test_response_processor(self, mock_create):
        """ResponseProcessorのテスト"""
        # モックの設定
        mock_response = MagicMock()
        mock_response.choices[0].message.content = """
案1:
山田様

お世話になっております。株式会社サンプルの佐藤です。

ご連絡ありがとうございます。

よろしくお願いいたします。

株式会社〇〇
山田太郎

案2:
山田様

お問い合わせいただきありがとうございます。

ご確認よろしくお願いいたします。

株式会社〇〇
山田太郎

案3:
山田様

メールありがとうございます。

今後ともよろしくお願いいたします。

株式会社〇〇
山田太郎
"""
        mock_create.return_value = mock_response
        
        processor = ResponseProcessor()
        
        # 非同期関数をテストするためのヘルパー関数
        async def run_async_test():
            prompt = "テストプロンプト"
            responses = await processor.generate_responses(prompt)
            return responses
        
        # テスト実行
        loop = asyncio.get_event_loop()
        responses = loop.run_until_complete(run_async_test())
        
        # 検証
        self.assertEqual(len(responses), 3)
        self.assertIn('山田様', responses[0])
        self.assertIn('お問い合わせ', responses[1])
        self.assertIn('メールありがとう', responses[2])
        
        # クリーンアップのテスト
        cleaned = processor.clean_response("案1:\n山田様\n\nテスト\n\n\n\n署名")
        self.assertEqual(cleaned, "山田様\n\nテスト\n\n署名")

if __name__ == '__main__':
    unittest.main()