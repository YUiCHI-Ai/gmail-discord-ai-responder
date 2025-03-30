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

# JSONファイル設定
DATA_DIR = config_dir / "data"
os.makedirs(DATA_DIR, exist_ok=True)

# 名前データベースファイル
NAME_DATABASE_FILE = DATA_DIR / "name_database.json"

# メールとチャンネルのマッピング
EMAIL_CHANNEL_MAPPING_FILE = config_dir / os.getenv("EMAIL_CHANNEL_MAPPING_FILE", "email_channel_mapping.json")

def get_email_channel_mapping():
    """メールアドレスとDiscordチャンネルのマッピングを取得"""
    try:
        with open(EMAIL_CHANNEL_MAPPING_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # デフォルトの空のマッピングを返す
        return {}

def save_email_channel_mapping(mapping):
    """メールアドレスとDiscordチャンネルのマッピングを保存"""
    try:
        with open(EMAIL_CHANNEL_MAPPING_FILE, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"マッピング保存エラー: {e}")
        return False