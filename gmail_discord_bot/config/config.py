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
EMAIL_ANALYZER_PROMPT_FILE = config_dir / "01_email_analyzer_prompt.txt"
EMAIL_RESPONDER_PROMPT_FILE = config_dir / "02_email_responder_prompt.txt"

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

# メールとユーザーのマッピング
EMAIL_USER_MAPPING_FILE = config_dir / os.getenv("EMAIL_USER_MAPPING_FILE", "email_user_mapping.json")

# メール設定ファイル
EMAIL_SETTINGS_FILE = config_dir / "email_settings.json"

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

def get_email_user_mapping():
    """メールアドレスとDiscordユーザーIDのマッピングを取得"""
    try:
        with open(EMAIL_USER_MAPPING_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # デフォルトの空のマッピングを返す
        return {}

def save_email_user_mapping(mapping):
    """メールアドレスとDiscordユーザーIDのマッピングを保存"""
    try:
        with open(EMAIL_USER_MAPPING_FILE, 'w', encoding='utf-8') as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"ユーザーマッピング保存エラー: {e}")
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

def get_email_settings():
    """メール設定を取得"""
    try:
        with open(EMAIL_SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # デフォルトの設定を返す
        return {
            "calendar": {
                "days": 30,
                "working_hours": {
                    "start": 18,
                    "end": 23
                },
                "duration_minutes": 60,
                "skip_weekends": True
            },
            "signature": {
                "company_name": "AiHUB株式会社",
                "name": "YUiCHI",
                "email": "yuichi@aihub.tokyo",
                "url": "https://aihub.co.jp/about"
            }
        }
    except Exception as e:
        print(f"メール設定読み込みエラー: {e}")
        # エラー時のフォールバック
        return {
            "calendar": {
                "days": 30,
                "working_hours": {
                    "start": 18,
                    "end": 23
                },
                "duration_minutes": 60,
                "skip_weekends": True
            },
            "signature": {
                "company_name": "AiHUB株式会社",
                "name": "YUiCHI",
                "email": "yuichi@aihub.tokyo",
                "url": "https://aihub.co.jp/about"
            }
        }

def save_email_settings(settings):
    """メール設定を保存"""
    try:
        with open(EMAIL_SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"メール設定保存エラー: {e}")
        return False

# 後方互換性のための関数は不要になりました