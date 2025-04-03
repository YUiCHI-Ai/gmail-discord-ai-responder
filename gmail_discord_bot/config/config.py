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

# AI API設定
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")
DEFAULT_AI_PROVIDER = os.getenv("DEFAULT_AI_PROVIDER", "chatgpt")  # デフォルトはChatGPT
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4")  # デフォルトはGPT-4
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-3-sonnet-20240229")  # デフォルトはClaude 3 Sonnet

# システムプロンプト設定
EMAIL_ANALYZER_PROMPT_FILE = config_dir / "email_analyzer_prompt.txt"
EMAIL_RESPONDER_PROMPT_FILE = config_dir / "email_responder_prompt.txt"

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

def get_email_analyzer_prompt():
    """メール分析用のシステムプロンプトを取得"""
    try:
        with open(EMAIL_ANALYZER_PROMPT_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        # デフォルトのシステムプロンプトを返す
        return "あなたはメール分析アシスタント「メール分析くん」です。メールを分析し、必要な情報を特定してください。"
    except Exception as e:
        print(f"メール分析プロンプト読み込みエラー: {e}")
        # エラー時のフォールバック
        return "あなたはメール分析アシスタント「メール分析くん」です。メールを分析し、必要な情報を特定してください。"

def get_email_responder_prompt():
    """メール返信用のシステムプロンプトを取得"""
    try:
        with open(EMAIL_RESPONDER_PROMPT_FILE, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        # デフォルトのシステムプロンプトを返す
        return "あなたはメール返信アシスタント「メール返信くん」です。適切な返信を作成してください。"
    except Exception as e:
        print(f"メール返信プロンプト読み込みエラー: {e}")
        # エラー時のフォールバック
        return "あなたはメール返信アシスタント「メール返信くん」です。適切な返信を作成してください。"

# 後方互換性のための関数は不要になりました