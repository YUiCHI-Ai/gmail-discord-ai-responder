import os
import json
from dotenv import load_dotenv
from pathlib import Path

# .envファイルを読み込む
config_dir = Path(__file__).parent
load_dotenv(config_dir / ".env")

# Gmail API設定
GMAIL_CREDENTIALS_FILE = config_dir / os.getenv("GMAIL_CREDENTIALS_FILE")
GMAIL_TOKEN_FILE = config_dir / os.getenv("GMAIL_TOKEN_FILE")
GMAIL_SCOPES = os.getenv("GMAIL_SCOPES").split(",")

# Discord API設定
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID")

# OpenAI API設定
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Google Calendar API設定
CALENDAR_CREDENTIALS_FILE = config_dir / os.getenv("CALENDAR_CREDENTIALS_FILE")
CALENDAR_TOKEN_FILE = config_dir / os.getenv("CALENDAR_TOKEN_FILE")
CALENDAR_SCOPES = os.getenv("CALENDAR_SCOPES").split(",")

# データベース設定
DATABASE_URL = os.getenv("DATABASE_URL")

# メールとチャンネルのマッピング
EMAIL_CHANNEL_MAPPING_FILE = config_dir / os.getenv("EMAIL_CHANNEL_MAPPING_FILE")

def get_email_channel_mapping():
    """メールアドレスとDiscordチャンネルのマッピングを取得"""
    try:
        with open(EMAIL_CHANNEL_MAPPING_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        # デフォルトの空のマッピングを返す
        return {}