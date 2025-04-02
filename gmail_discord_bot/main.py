# Copyright 2025 YUiCHI
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
import time
import threading
from pathlib import Path
import logging

from gmail_discord_bot.gmail_module.gmail_client import GmailClient
from gmail_discord_bot.gmail_module.email_processor import EmailProcessor
from gmail_discord_bot.discord_module.discord_bot import DiscordBot
from gmail_discord_bot.discord_module.message_formatter import MessageFormatter
from gmail_discord_bot.name_module.name_manager import NameManager
from gmail_discord_bot.ai_module.ai_factory import AIFactory
from gmail_discord_bot.calendar_module.schedule_analyzer import ScheduleAnalyzer
from gmail_discord_bot.utils.logger import setup_logger
from gmail_discord_bot.config import config

logger = setup_logger(__name__)

class EmailBot:
    def __init__(self, ai_provider=None):
        # AIプロバイダーの設定
        self.ai_provider = ai_provider or config.DEFAULT_AI_PROVIDER
        logger.info(f"AIプロバイダー '{self.ai_provider}' を使用します")
        
        # 各モジュールの初期化
        self.gmail_client = GmailClient()
        self.email_processor = EmailProcessor(self.gmail_client)
        self.discord_bot = DiscordBot()
        self.message_formatter = MessageFormatter()
        self.name_manager = NameManager()
        self.prompt_generator = AIFactory.create_prompt_generator(self.ai_provider)
        self.response_processor = AIFactory.create_response_processor(self.ai_provider)
        self.schedule_analyzer = ScheduleAnalyzer()
        
        # 処理中のメールIDを追跡
        self.processing_emails = set()
        
        # 定期チェックの設定
        self.check_interval = 60  # 60秒ごとにメールをチェック
    
    async def process_email_for_discord(self, email_data):
        """メールを処理してDiscordに送信"""
        try:
            # 処理中のメールをトラッキング
            if email_data['id'] in self.processing_emails:
                logger.info(f"メール {email_data['id']} は既に処理中です")
                return
            
            self.processing_emails.add(email_data['id'])
            
            # 送信者情報を処理
            sender_info = self.name_manager.process_email(email_data)
            sender_email = sender_info['email']
            
            # 宛名を生成
            address = self.name_manager.format_address(sender_email)
            
            # Discordチャンネルにメール通知を送信
            channel_id = email_data['discord_channel_id']
            await self.discord_bot.send_email_notification(channel_id, email_data)
            
            # 日程調整関連のメールかどうかを判定
            is_schedule = self.prompt_generator.is_schedule_related(email_data)
            
            # プロンプトを生成
            if is_schedule:
                # 利用可能なスロットを取得
                available_slots = self.schedule_analyzer.get_available_slots()
                prompt = self.prompt_generator.generate_schedule_prompt(
                    email_data, sender_info, address, available_slots
                )
            else:
                prompt = self.prompt_generator.generate_normal_prompt(
                    email_data, sender_info, address
                )
            
            # 返信候補を生成
            responses = await self.response_processor.generate_responses(prompt)
            
            # 返信候補をDiscordに送信
            await self.discord_bot.send_response_options(channel_id, email_data, responses)
            
            # 処理完了したメールをトラッキングから削除
            self.processing_emails.remove(email_data['id'])
            
        except Exception as e:
            logger.error(f"メール処理エラー: {e}")
            if email_data['id'] in self.processing_emails:
                self.processing_emails.remove(email_data['id'])
    
    async def check_emails(self):
        """新しいメールをチェックして処理"""
        try:
            # 新しいメールを取得
            emails = self.email_processor.process_new_emails()
            
            if emails:
                logger.info(f"{len(emails)}件の新しいメールを処理します")
                
                # 各メールを処理
                for email_data in emails:
                    await self.process_email_for_discord(email_data)
            else:
                logger.info("新しいメールはありません")
        
        except Exception as e:
            logger.error(f"メールチェックエラー: {e}")
    
    async def periodic_check(self):
        """定期的にメールをチェック"""
        while True:
            await self.check_emails()
            await asyncio.sleep(self.check_interval)
    
    def start_periodic_check(self):
        """非同期の定期チェックを開始"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(self.periodic_check())
        except KeyboardInterrupt:
            logger.info("定期チェックを停止します")
        finally:
            loop.close()
    
    def run(self):
        """ボットを実行"""
        # 定期チェックを別スレッドで開始
        check_thread = threading.Thread(target=self.start_periodic_check)
        check_thread.daemon = True
        check_thread.start()
        
        # Discordボットを実行
        logger.info("Discordボットを起動します")
        self.discord_bot.run()

if __name__ == "__main__":
    bot = EmailBot()
    bot.run()