import discord
from discord.ext import commands
import asyncio
from async_timeout import timeout as async_timeout
from ..config import config
from ..utils.logger import setup_logger
from discord import ui, ButtonStyle

logger = setup_logger(__name__)

class ApprovalView(ui.View):
    def __init__(self, email_id, bot, timeout=None):
        super().__init__(timeout=timeout)
        self.email_id = email_id
        self.bot = bot
        self.result = None
    
    @ui.button(label="承認する", style=ButtonStyle.success, custom_id="approve")
    async def approve_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message(f"メール {self.email_id} を承認しました。返信を生成します...")
        self.result = "approve"
        # 承認イベントを発火
        self.bot.dispatch('approval_decision', self.email_id, "approve")
        self.stop()
    
    @ui.button(label="拒否する", style=ButtonStyle.danger, custom_id="reject")
    async def reject_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message(f"メール {self.email_id} を拒否しました。")
        self.result = "reject"
        # 拒否イベントを発火
        self.bot.dispatch('approval_decision', self.email_id, "reject")
        self.stop()

class SendConfirmView(ui.View):
    def __init__(self, channel_id, option_number, response_text, bot, timeout=None):
        super().__init__(timeout=timeout)
        self.channel_id = channel_id
        self.option_number = option_number
        self.response_text = response_text
        self.bot = bot
    
    @ui.button(label="メールを送信する", style=ButtonStyle.primary, custom_id="confirm_send")
    async def confirm_send_button(self, interaction: discord.Interaction, button: ui.Button):
        # 最初の確認ボタンを押した後、最終確認ボタンを表示
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(view=self)
        
        # 最終確認ボタンを含む新しいビューを作成
        final_view = FinalSendConfirmView(self.channel_id, self.option_number, self.response_text, self.bot)
        await interaction.followup.send("**本当にこのメールを送信しますか？**", view=final_view)
        self.stop()
    
    @ui.button(label="キャンセル", style=ButtonStyle.secondary, custom_id="cancel_send")
    async def cancel_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("メール送信をキャンセルしました。")
        self.stop()

class FinalSendConfirmView(ui.View):
    def __init__(self, channel_id, option_number, response_text, bot, timeout=None):
        super().__init__(timeout=timeout)
        self.channel_id = channel_id
        self.option_number = option_number
        self.response_text = response_text
        self.bot = bot
    
    @ui.button(label="はい、送信します", style=ButtonStyle.success, custom_id="final_confirm")
    async def final_confirm_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("メールを送信しています...")
        # 送信イベントを発火
        self.bot.dispatch('send_email', self.channel_id, self.option_number)
        self.stop()
    
    @ui.button(label="いいえ、キャンセルします", style=ButtonStyle.danger, custom_id="final_cancel")
    async def final_cancel_button(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("メール送信をキャンセルしました。")
        self.stop()

class ResponseSelectView(ui.View):
    def __init__(self, discord_bot, channel_id, option_number, response_text, timeout=None):
        super().__init__(timeout=timeout)
        self.discord_bot = discord_bot
        self.channel_id = channel_id
        self.option_number = option_number
        self.response_text = response_text
    
    @ui.button(label="この返信を選択", style=ButtonStyle.primary, custom_id="select_response")
    async def select_button(self, interaction: discord.Interaction, button: ui.Button):
        # 選択した返信を保存
        thread_id = str(self.channel_id)
        if thread_id in self.discord_bot.response_options:
            self.discord_bot.response_options[thread_id]['selected'] = self.option_number - 1
            
            # 送信確認ボタンを表示
            view = SendConfirmView(thread_id, self.option_number, self.response_text, self.discord_bot.bot, timeout=3600)
            await interaction.response.send_message(f"返信 {self.option_number} を選択しました。送信しますか？", view=view)
        else:
            await interaction.response.send_message("返信候補の情報が見つかりません。")
        self.stop()

class DiscordBot:
    def __init__(self):
        self.token = config.DISCORD_BOT_TOKEN
        self.guild_id = config.DISCORD_GUILD_ID
        
        intents = discord.Intents.default()
        intents.message_content = True
        
        self.bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)
        self.setup_events()
        self.setup_commands()
        
        # 応答選択のためのデータ保存
        self.response_options = {}
        # 承認リクエストのためのデータ保存
        self.approval_requests = {}
    
    def setup_events(self):
        """イベントハンドラの設定"""
        @self.bot.event
        async def on_ready():
            logger.info(f'{self.bot.user.name} としてログインしました')
            logger.info(f'Bot ID: {self.bot.user.id}')
            logger.info('------')
            
        @self.bot.event
        async def on_send_email(channel_id, option_number):
            """メール送信イベントを処理"""
            logger.info(f"メール送信イベント: チャンネルID {channel_id}, オプション {option_number}")
            
            # 返信候補情報を取得
            thread_id = str(channel_id)
            if thread_id not in self.response_options:
                logger.error(f"チャンネル {channel_id} の返信候補情報が見つかりません")
                await self.send_message(channel_id, "エラー: 返信候補情報が見つかりません。")
                return
            
            # 選択された返信と元のメール情報を取得
            response_data = self.response_options[thread_id]
            email_data = response_data['email']
            selected_text = response_data['options'][option_number - 1]
            
            try:
                # Gmail APIクライアントを取得（クラス外でインポート）
                from gmail_discord_bot.gmail_module.gmail_client import GmailClient
                gmail_client = GmailClient()
                
                # 送信先メールアドレスを取得
                to_email = email_data['sender']
                
                # 件名を作成（Re: を付ける）
                subject = email_data['subject']
                if not subject.lower().startswith('re:'):
                    subject = f"Re: {subject}"
                
                # メールを送信するために必要な情報を取得
                thread_id = email_data.get('thread_id')
                message_id = email_data.get('message_id')
                references = email_data.get('references')
                
                # 情報をログに出力
                if thread_id:
                    logger.info(f"スレッドID {thread_id} を使用してメールを送信します")
                if message_id:
                    logger.info(f"メッセージID {message_id} を使用してメールを送信します")
                if references:
                    logger.info(f"参照情報 {references} を使用してメールを送信します")
                
                # バックアップ: raw_messageから情報を取得（古いメールデータ形式との互換性のため）
                if (not thread_id or not message_id) and 'raw_message' in email_data:
                    raw_message = email_data['raw_message']
                    
                    # スレッドIDを取得
                    if not thread_id and 'threadId' in raw_message:
                        thread_id = raw_message['threadId']
                        logger.info(f"raw_messageからスレッドID {thread_id} を取得しました")
                    
                    # メッセージIDを取得
                    if not message_id and 'id' in raw_message:
                        message_id = raw_message['id']
                        logger.info(f"raw_messageからメッセージID {message_id} を取得しました")
                
                # メールを送信（元のメッセージを引用する）
                result = gmail_client.send_email(
                    to=to_email,
                    subject=subject,
                    body=selected_text,
                    thread_id=thread_id,
                    message_id=message_id,
                    references=references,
                    quote_original=True  # 元のメッセージを引用する
                )
                
                if result:
                    # 送信成功
                    logger.info(f"メール送信成功: {result['id']}")
                    # 送信成功メッセージを詳細化
                    success_message = (
                        f"✅ メールを送信しました！\n"
                        f"送信先: {to_email}\n"
                        f"件名: {subject}\n"
                        f"メールID: {result['id']}\n"
                        f"引用モード: 有効"  # 引用モードが有効であることを表示
                    )
                    if thread_id:
                        success_message += f"\nスレッドID: {thread_id}"
                    
                    await self.send_message(channel_id, success_message)
                else:
                    # 送信失敗
                    logger.error("メール送信に失敗しました")
                    # エラーメッセージを詳細化
                    error_message = (
                        "❌ メール送信に失敗しました。以下を確認してください：\n"
                        "1. Gmail APIの認証情報が有効か\n"
                        "2. メール送信権限（スコープ）が正しく設定されているか\n"
                        "3. 送信先メールアドレスが正しいか\n"
                        "4. ネットワーク接続に問題がないか\n\n"
                        "詳細はログを確認してください。"
                    )
                    await self.send_message(channel_id, error_message)
            
            except Exception as e:
                logger.error(f"メール送信処理中にエラーが発生しました: {e}")
                import traceback
                logger.error(f"詳細なエラー情報: {traceback.format_exc()}")
                await self.send_message(channel_id, f"❌ エラーが発生しました: {str(e)}")
    
    def setup_commands(self):
        """コマンドの設定"""
        @self.bot.command(name='help')
        async def help_command(ctx):
            """ヘルプコマンド"""
            help_text = """
            **メール自動返信ボットのコマンド**
            
            `!help` - このヘルプメッセージを表示
            `!status` - ボットのステータスを表示
            `!select [番号]` - 提案された返信から選択（番号は1から始まる）
            `!edit [番号] [新しい内容]` - 提案された返信を編集
            `!send [番号]` - 選択した返信を実際にメールとして送信
            `!approve [メールID]` - 承認リクエストを承認
            `!reject [メールID]` - 承認リクエストを拒否
            `!handle [メールID] [番号または対処法]` - その他情報リクエストに対処
            """
            await ctx.send(help_text)
            
        @self.bot.command(name='send')
        async def send_email(ctx, option_number: int):
            """選択した返信をメールとして送信"""
            thread_id = str(ctx.channel.id)
            
            if thread_id not in self.response_options:
                await ctx.send("このチャンネルでは返信候補が生成されていません。")
                return
            
            if self.response_options[thread_id]['selected'] is None:
                await ctx.send("まず `!select [番号]` で返信を選択してください。")
                return
            
            if option_number < 1 or option_number > len(self.response_options[thread_id]['options']):
                await ctx.send(f"1から{len(self.response_options[thread_id]['options'])}の間の番号を選択してください。")
                return
            
            # 選択した返信を取得
            selected_text = self.response_options[thread_id]['options'][option_number - 1]
            
            # 送信確認ボタンを表示
            view = SendConfirmView(thread_id, option_number, selected_text, self.bot, timeout=3600)  # 1時間のタイムアウト
            await ctx.send("メール送信の確認:", view=view)
            
        @self.bot.command(name='approve')
        async def approve_request(ctx, email_id: str):
            """承認リクエストを承認"""
            if email_id not in self.approval_requests:
                await ctx.send(f"メール {email_id} の承認リクエストが見つかりません。")
                return
                
            # 承認情報を保存
            self.approval_requests[email_id]['result'] = "approve"
            await ctx.send(f"メール {email_id} を承認しました。返信を生成します...")
            
            # 承認イベントを発火（メインプログラムで処理）
            self.bot.dispatch('approval_decision', email_id, "approve")
            
        @self.bot.command(name='reject')
        async def reject_request(ctx, email_id: str):
            """承認リクエストを拒否"""
            if email_id not in self.approval_requests:
                await ctx.send(f"メール {email_id} の承認リクエストが見つかりません。")
                return
                
            # 拒否情報を保存
            self.approval_requests[email_id]['result'] = "reject"
            await ctx.send(f"メール {email_id} を拒否しました。")
            
            # 拒否イベントを発火（メインプログラムで処理）
            self.bot.dispatch('approval_decision', email_id, "reject")
            
        @self.bot.command(name='handle')
        async def handle_other_info(ctx, email_id: str, *, action: str):
            """その他情報リクエストに対処"""
            await ctx.send(f"メール {email_id} に対して「{action}」の対処を行います。")
            # ここで対処後の処理を実装
        
        @self.bot.command(name='select')
        async def select_response(ctx, option_number: int):
            """提案された返信から選択"""
            thread_id = str(ctx.channel.id)
            
            if thread_id not in self.response_options:
                await ctx.send("このチャンネルでは返信候補が生成されていません。")
                return
            
            if option_number < 1 or option_number > len(self.response_options[thread_id]['options']):
                await ctx.send(f"1から{len(self.response_options[thread_id]['options'])}の間の番号を選択してください。")
                return
            
            # 選択した返信を保存
            self.response_options[thread_id]['selected'] = option_number - 1
            selected_text = self.response_options[thread_id]['options'][option_number - 1]
            
            # 送信確認ボタンを表示
            view = SendConfirmView(thread_id, option_number, selected_text, self.bot, timeout=3600)  # 1時間のタイムアウト
            await ctx.send(f"```\n{selected_text}\n```", view=view)
    
    async def send_email_notification(self, channel_id, email_data):
        """メール通知をDiscordチャンネルに送信"""
        logger.info(f"send_email_notification: チャンネルID {channel_id} へメール通知を送信開始")
        try:
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                logger.error(f"チャンネルが見つかりません: {channel_id}")
                return False
            
            logger.info(f"チャンネル {channel.name} が見つかりました")
            
            # メール情報を整形
            embed = discord.Embed(
                title=f"新しいメール: {email_data['subject']}",
                color=discord.Color.blue()
            )
            
            # 送信者情報を表示（会社名と名前を含む）
            sender_display = email_data['sender']
            if 'sender_name' in email_data and email_data['sender_name']:
                if 'sender_company' in email_data and email_data['sender_company']:
                    sender_display = f"{email_data['sender']} ({email_data['sender_company']} {email_data['sender_name']})"
                else:
                    sender_display = f"{email_data['sender']} ({email_data['sender_name']})"
            elif 'sender_company' in email_data and email_data['sender_company']:
                sender_display = f"{email_data['sender']} ({email_data['sender_company']})"
            
            embed.add_field(name="送信者", value=sender_display, inline=False)
            embed.add_field(name="日時", value=email_data['date'], inline=False)
            
            # 本文が長い場合は省略
            body = email_data['body']
            if len(body) > 1000:
                body = body[:997] + "..."
            
            embed.add_field(name="本文", value=body, inline=False)
            
            # タイムアウト処理を追加
            async with async_timeout(10):  # 10秒のタイムアウト
                logger.info("embedメッセージを送信中...")
                await channel.send(embed=embed)
                logger.info("返信候補生成メッセージを送信中...")
                await channel.send("返信候補を生成中...")
            
            logger.info(f"チャンネル {channel_id} へのメール通知送信完了")
            return True
        except asyncio.TimeoutError:
            logger.error(f"チャンネル {channel_id} へのメッセージ送信がタイムアウトしました")
            return False
        except Exception as e:
            logger.error(f"メール通知送信エラー: {e}")
            return False
    
    async def send_response_options(self, channel_id, email_data, response_options):
        """返信候補をDiscordチャンネルに送信"""
        logger.info(f"send_response_options: チャンネルID {channel_id} へ返信候補を送信開始")
        try:
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                logger.error(f"チャンネルが見つかりません: {channel_id}")
                return False
            
            logger.info(f"チャンネル {channel.name} が見つかりました")
            
            # タイムアウト処理を追加
            async with async_timeout(30):  # 30秒のタイムアウト（複数のメッセージを送信するため長めに設定）
                # 返信候補を保存
                self.response_options[str(channel_id)] = {
                    'email': email_data,
                    'options': response_options,
                    'selected': None
                }
                
                # 各候補を表示（選択ボタン付き）
                logger.info(f"{len(response_options)}個の返信候補を送信中...")
                for i, option in enumerate(response_options, 1):
                    # 選択ボタンを含むビューを作成
                    select_view = ResponseSelectView(self, channel_id, i, option, timeout=86400)  # 24時間のタイムアウト
                    
                    # Embedを作成して返信候補を表示
                    embed = discord.Embed(
                        title=f"返信候補 {i}",
                        description=f"```\n{option}\n```",
                        color=discord.Color.blue()
                    )
                    
                    await channel.send(embed=embed, view=select_view)
            
            logger.info(f"チャンネル {channel_id} への返信候補送信完了")
            return True
        except asyncio.TimeoutError:
            logger.error(f"チャンネル {channel_id} への返信候補送信がタイムアウトしました")
            return False
        except Exception as e:
            logger.error(f"返信候補送信エラー: {e}")
            return False
    
    def run(self):
        """ボットを実行"""
        self.bot.run(self.token)
    
    async def send_message(self, channel_id, message):
        """一般的なメッセージをDiscordチャンネルに送信"""
        try:
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                logger.error(f"チャンネルが見つかりません: {channel_id}")
                return False
            
            await channel.send(message)
            return True
        except Exception as e:
            logger.error(f"メッセージ送信エラー: {e}")
            return False
    
    async def send_approval_request(self, channel_id, email_data, message):
        """承認リクエストをDiscordチャンネルに送信"""
        logger.info(f"send_approval_request: チャンネルID {channel_id} へ承認リクエストを送信開始")
        try:
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                logger.error(f"チャンネルが見つかりません: {channel_id}")
                return False
            
            # 承認リクエスト用のEmbed作成
            embed = discord.Embed(
                title=f"承認リクエスト: {email_data['subject']}",
                description=message,
                color=discord.Color.orange()
            )
            
            # ボタン付きのビューを作成
            view = ApprovalView(email_data['id'], self.bot, timeout=86400)  # 24時間のタイムアウト
            
            # 承認リクエストを保存
            self.approval_requests[email_data['id']] = {
                'email_data': email_data,
                'channel_id': channel_id,
                'view': view,
                'result': None
            }
            
            # メッセージを送信
            await channel.send(embed=embed, view=view)
            logger.info(f"チャンネル {channel_id} への承認リクエスト送信完了")
            return True
        except Exception as e:
            logger.error(f"承認リクエスト送信エラー: {e}")
            return False
    
    async def send_attachments_and_urls(self, channel_id, email_data, attachments, urls):
        """添付ファイルとURLをDiscordチャンネルに送信"""
        logger.info(f"send_attachments_and_urls: チャンネルID {channel_id} へ添付ファイルとURLを送信開始")
        try:
            import io
            
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                logger.error(f"チャンネルが見つかりません: {channel_id}")
                return False
            
            # 確認メッセージ
            embed = discord.Embed(
                title=f"確認リクエスト: {email_data['subject']}",
                description="以下の添付ファイルとURLを確認してください。",
                color=discord.Color.green()
            )
            
            await channel.send(embed=embed)
            
            # 添付ファイルを送信
            for attachment in attachments:
                try:
                    # バイナリデータをBytesIOオブジェクトに変換
                    file_data = io.BytesIO(attachment['data'])
                    file_data.seek(0)  # ファイルポインタを先頭に戻す
                    
                    # ファイル名とMIMEタイプをログに出力
                    logger.info(f"添付ファイル送信: {attachment['filename']} ({attachment['mime_type']}) サイズ: {attachment['size']} バイト")
                    
                    # Discord.Fileオブジェクトを作成
                    file = discord.File(
                        fp=file_data,
                        filename=attachment['filename']
                    )
                    
                    # ファイルを送信
                    await channel.send(f"添付ファイル: {attachment['filename']} ({attachment['mime_type']})", file=file)
                    logger.info(f"添付ファイル {attachment['filename']} の送信に成功しました")
                except Exception as file_error:
                    logger.error(f"添付ファイル {attachment['filename']} の送信に失敗しました: {file_error}")
            
            # URLを送信
            if urls:
                url_message = "**メール内のURL:**\n" + "\n".join(urls)
                await channel.send(url_message)
                logger.info(f"{len(urls)}件のURLを送信しました")
            
            logger.info(f"チャンネル {channel_id} への添付ファイルとURL送信完了")
            return True
        except Exception as e:
            logger.error(f"添付ファイルとURL送信エラー: {e}")
            import traceback
            logger.error(f"詳細なエラー情報: {traceback.format_exc()}")
            return False
    
    async def send_other_info_request(self, channel_id, email_data, message):
        """その他情報リクエストをDiscordチャンネルに送信"""
        logger.info(f"send_other_info_request: チャンネルID {channel_id} へその他情報リクエストを送信開始")
        try:
            channel = self.bot.get_channel(int(channel_id))
            if not channel:
                logger.error(f"チャンネルが見つかりません: {channel_id}")
                return False
            
            # その他情報リクエスト用のEmbed作成
            embed = discord.Embed(
                title=f"追加情報リクエスト: {email_data['subject']}",
                description=message,
                color=discord.Color.purple()
            )
            
            await channel.send(embed=embed)
            logger.info(f"チャンネル {channel_id} へのその他情報リクエスト送信完了")
            return True
        except Exception as e:
            logger.error(f"その他情報リクエスト送信エラー: {e}")
            return False
    
    def run_async(self):
        """非同期でボットを実行（テスト用）"""
        loop = asyncio.get_event_loop()
        try:
            loop.create_task(self.bot.start(self.token))
        except KeyboardInterrupt:
            loop.run_until_complete(self.bot.close())
        finally:
            loop.close()