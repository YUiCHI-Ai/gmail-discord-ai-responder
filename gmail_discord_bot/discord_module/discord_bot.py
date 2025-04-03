import discord
from discord.ext import commands
import asyncio
from async_timeout import timeout as async_timeout
from ..config import config
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

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
    
    def setup_events(self):
        """イベントハンドラの設定"""
        @self.bot.event
        async def on_ready():
            logger.info(f'{self.bot.user.name} としてログインしました')
            logger.info(f'Bot ID: {self.bot.user.id}')
            logger.info('------')
    
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
            """
            await ctx.send(help_text)
        
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
            
            await ctx.send(f"返信 {option_number} を選択しました：\n```\n{selected_text}\n```\n`!send {option_number}` で送信できます。")
    
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
            embed.add_field(name="送信者", value=email_data['sender'], inline=False)
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
                logger.info("返信候補生成完了メッセージを送信中...")
                await channel.send("**返信候補が生成されました**\n以下から選択するか、編集してください：")
                
                # 返信候補を保存
                self.response_options[str(channel_id)] = {
                    'email': email_data,
                    'options': response_options,
                    'selected': None
                }
                
                # 各候補を表示
                logger.info(f"{len(response_options)}個の返信候補を送信中...")
                for i, option in enumerate(response_options, 1):
                    await channel.send(f"**候補 {i}**\n```\n{option}\n```")
                
                await channel.send("選択するには `!select [番号]` を使用してください。")
            
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
    
    def run_async(self):
        """非同期でボットを実行（テスト用）"""
        loop = asyncio.get_event_loop()
        try:
            loop.create_task(self.bot.start(self.token))
        except KeyboardInterrupt:
            loop.run_until_complete(self.bot.close())
        finally:
            loop.close()