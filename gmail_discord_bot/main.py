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
from async_timeout import timeout as async_timeout

from gmail_discord_bot.gmail_module.gmail_client import GmailClient
from gmail_discord_bot.gmail_module.email_processor import EmailProcessor
from gmail_discord_bot.discord_module.discord_bot import DiscordBot
from gmail_discord_bot.discord_module.message_formatter import MessageFormatter
from gmail_discord_bot.name_module.name_manager import NameManager
from gmail_discord_bot.ai_module.ai_factory import AIFactory
from gmail_discord_bot.calendar_module.schedule_analyzer import ScheduleAnalyzer
from gmail_discord_bot.utils.logger import setup_logger, flow_step, FlowStep
from gmail_discord_bot.config import config

logger = setup_logger(__name__)

class EmailBot:
    def __init__(self, ai_provider=None):
        # AIプロバイダーの設定
        self.ai_provider = ai_provider or config.DEFAULT_AI_PROVIDER
        logger.log_flow(FlowStep.RECEIVE_EMAIL, f"AIプロバイダー '{self.ai_provider}' を使用します")
        
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
    
    @flow_step(FlowStep.RECEIVE_EMAIL)
    async def process_email_for_discord(self, email_data):
        """メールを処理してDiscordに送信"""
        try:
            # 処理中のメールをトラッキング
            if email_data['id'] in self.processing_emails:
                logger.info(f"メール {email_data['id']} は既に処理中です")
                return
            
            logger.info(f"メール {email_data['id']} の処理を開始します")
            self.processing_emails.add(email_data['id'])
            
            try:
                # 送信元アドレスの確認
                logger.log_flow(FlowStep.CHECK_SENDER, f"メール {email_data['id']} の送信元を確認")
                
                # 送信者情報を処理
                logger.log_flow(FlowStep.EXTRACT_ADDRESS, "送信者情報から宛名を抽出")
                sender_info = self.name_manager.process_email(email_data)
                sender_email = sender_info['email']
                logger.info(f"送信者メールアドレス: {sender_email}")
                
                # 宛名を生成
                address = self.name_manager.format_address(sender_email)
                logger.info(f"生成された宛名: {address}")
                
                # Discordチャンネルにメール通知を送信
                logger.log_flow(FlowStep.TRANSFER_TO_DISCORD, "Discordチャンネルへメールを転送")
                channel_id = email_data['discord_channel_id']
                logger.info(f"送信先チャンネルID: {channel_id}")
                
                # タイムアウト処理を追加
                try:
                    async with async_timeout(15):  # 15秒のタイムアウト
                        success = await self.discord_bot.send_email_notification(channel_id, email_data)
                        if not success:
                            logger.error(f"メール通知の送信に失敗しました: チャンネルID {channel_id}")
                            return
                except asyncio.TimeoutError:
                    logger.error(f"メール通知の送信がタイムアウトしました: チャンネルID {channel_id}")
                    return
                
                # 基本プロンプトを生成
                logger.log_flow(FlowStep.GENERATE_PROMPT, "メール分析用プロンプトを生成")
                
                # メール情報を含むプロンプトを生成
                prompt = f"""
# 元のメール情報
件名: {email_data['subject']}
送信者: {email_data['sender']}
本文:
{email_data['body']}

# 宛名情報
宛名: {address}
"""
                
                # ステップ1: メール分析
                logger.log_flow(FlowStep.ANALYZE_EMAIL, "AIでメールを分析")
                try:
                    async with async_timeout(30):  # 30秒のタイムアウト
                        analysis_result = await self.response_processor.analyze_email(prompt)
                except asyncio.TimeoutError:
                    logger.error("メール分析がタイムアウトしました")
                    return
                
                # 必要情報の確認
                required_info_type = analysis_result.get("required_info", {}).get("type")
                logger.info(f"必要情報タイプ: {required_info_type}")
                
                # カレンダー情報が必要な場合、スケジュールを取得
                if required_info_type == "カレンダー":
                    logger.log_flow(FlowStep.GET_CALENDAR, "Googleカレンダーからスケジュールを取得")
                    # カレンダー情報は response_processor.generate_responses 内で取得される
                
                # ステップ2: 返信生成
                logger.log_flow(FlowStep.GENERATE_RESPONSE, "AIで返信を生成")
                try:
                    async with async_timeout(60):  # 60秒のタイムアウト（AI生成は時間がかかる可能性がある）
                        responses = await self.response_processor.generate_responses(prompt, analysis_result)
                except asyncio.TimeoutError:
                    logger.error("AI応答生成がタイムアウトしました")
                    return
                
                # 返信候補をDiscordに送信
                logger.log_flow(FlowStep.DISPLAY_RESPONSE, "Discordに返信を表示")
                try:
                    async with async_timeout(30):  # 30秒のタイムアウト
                        success = await self.discord_bot.send_response_options(channel_id, email_data, responses)
                        if not success:
                            logger.error(f"返信候補の送信に失敗しました: チャンネルID {channel_id}")
                            return
                except asyncio.TimeoutError:
                    logger.error(f"返信候補の送信がタイムアウトしました: チャンネルID {channel_id}")
                    return
                
                logger.log_flow(FlowStep.COMPLETE, f"メール {email_data['id']} の処理を完了")
            finally:
                # 処理完了したメールをトラッキングから削除
                if email_data['id'] in self.processing_emails:
                    self.processing_emails.remove(email_data['id'])
                    logger.info(f"メール {email_data['id']} の処理を完了し、トラッキングから削除しました")
            
        except Exception as e:
            logger.error(f"メール処理エラー: {e}")
            import traceback
            logger.error(f"詳細なエラー情報: {traceback.format_exc()}")
            if email_data['id'] in self.processing_emails:
                self.processing_emails.remove(email_data['id'])
    
    @flow_step(FlowStep.RECEIVE_EMAIL)
    async def check_emails(self):
        """新しいメールをチェックして処理"""
        try:
            # 新しいメールを取得
            emails = self.email_processor.process_new_emails()
            
            if emails:
                logger.log_flow(FlowStep.RECEIVE_EMAIL, f"{len(emails)}件の新しいメールを処理します")
                
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
    
    async def start_bot_and_check(self):
        """DiscordボットとメールチェックをまとめてAsync実行"""
        logger.info("Discordボットを非同期モードで起動します")
        
        # Discordボットを非同期で起動
        bot_task = asyncio.create_task(self.discord_bot.bot.start(self.discord_bot.token))
        
        # 少し待ってからメールチェックを開始（ボットの起動を待つ）
        await asyncio.sleep(5)
        
        # 定期チェックを開始
        logger.info("メールの定期チェックを開始します")
        check_task = asyncio.create_task(self.periodic_check())
        
        # 両方のタスクが完了するまで待機
        try:
            await asyncio.gather(bot_task, check_task)
        except asyncio.CancelledError:
            logger.info("タスクがキャンセルされました")
        except Exception as e:
            logger.error(f"タスク実行中にエラーが発生しました: {e}")
            import traceback
            logger.error(f"詳細なエラー情報: {traceback.format_exc()}")
    
    def run(self):
        """ボットを実行"""
        logger.info("アプリケーションを起動します")
        
        # 単一のイベントループでDiscordボットとメールチェックを実行
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            loop.run_until_complete(self.start_bot_and_check())
        except KeyboardInterrupt:
            logger.info("アプリケーションを停止します")
            # Discordボットを停止
            if hasattr(loop, 'is_running') and loop.is_running():
                asyncio.create_task(self.discord_bot.bot.close())
        finally:
            loop.close()
            logger.info("イベントループを閉じました")

if __name__ == "__main__":
    logger.log_flow(FlowStep.RECEIVE_EMAIL, "アプリケーションを起動")
    bot = EmailBot()
    bot.run()