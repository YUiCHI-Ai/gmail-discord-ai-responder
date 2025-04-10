#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Gmail-Discord自動転送・返信システム 設定ファイル自動生成スクリプト

このスクリプトは、Gmail-Discord自動転送・返信システムの初期設定を
対話形式で行い、必要な設定ファイルを自動的に生成します。
"""

import os
import json
import shutil
from pathlib import Path
import re

# 色付きテキスト出力用の定数
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    """ヘッダーテキストを表示"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(60)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'=' * 60}{Colors.ENDC}\n")

def print_step(text):
    """ステップテキストを表示"""
    print(f"\n{Colors.BLUE}{Colors.BOLD}>> {text}{Colors.ENDC}")

def print_success(text):
    """成功メッセージを表示"""
    print(f"{Colors.GREEN}{Colors.BOLD}✓ {text}{Colors.ENDC}")

def print_warning(text):
    """警告メッセージを表示"""
    print(f"{Colors.YELLOW}{Colors.BOLD}⚠ {text}{Colors.ENDC}")

def print_error(text):
    """エラーメッセージを表示"""
    print(f"{Colors.RED}{Colors.BOLD}✗ {text}{Colors.ENDC}")

def get_input(prompt, default=None, required=True, validator=None):
    """ユーザー入力を取得"""
    while True:
        if default:
            user_input = input(f"{prompt} [{default}]: ").strip()
            if not user_input:
                user_input = default
        else:
            user_input = input(f"{prompt}: ").strip()
        
        if not user_input and required:
            print_warning("この項目は必須です。値を入力してください。")
            continue
        
        if validator and user_input:
            valid, message = validator(user_input)
            if not valid:
                print_warning(message)
                continue
        
        return user_input

def validate_email(email):
    """メールアドレスの形式を検証"""
    if email == "*":
        return True, ""
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(pattern, email) or email.startswith("*@"):
        return True, ""
    return False, "有効なメールアドレスを入力してください（例: user@example.com）"

def validate_discord_id(discord_id):
    """DiscordのIDを検証"""
    if discord_id.isdigit() and len(discord_id) >= 17:
        return True, ""
    return False, "有効なDiscord IDを入力してください（17桁以上の数字）"

def validate_api_key(api_key):
    """APIキーの形式を検証（簡易的な検証）"""
    if len(api_key) >= 10:
        return True, ""
    return False, "APIキーは少なくとも10文字以上である必要があります"

def validate_hours(hours):
    """時間の形式を検証"""
    try:
        hour = int(hours)
        if 0 <= hour <= 23:
            return True, ""
        return False, "時間は0から23の間で入力してください"
    except ValueError:
        return False, "時間は数値で入力してください"

def validate_minutes(minutes):
    """分の形式を検証"""
    try:
        mins = int(minutes)
        if 0 <= mins <= 59:
            return True, ""
        return False, "分は0から59の間で入力してください"
    except ValueError:
        return False, "分は数値で入力してください"

def setup_env_file():
    """環境変数設定ファイル(.env)を作成"""
    print_step(".envファイルの設定")
    
    config_dir = Path("gmail_discord_bot/config")
    env_example = config_dir / ".env.example"
    env_file = config_dir / ".env"
    
    if not env_example.exists():
        print_error(f"{env_example} が見つかりません。リポジトリが正しくクローンされているか確認してください。")
        return False
    
    # .env.exampleをコピーして.envを作成
    shutil.copy(env_example, env_file)
    print_success(f"{env_file} を作成しました")
    
    # 各設定項目を対話形式で入力
    env_content = env_file.read_text(encoding='utf-8')
    
    # Discord設定
    print("\n--- Discord設定 ---")
    discord_token = get_input("Discord Bot Token", required=True, validator=validate_api_key)
    discord_guild_id = get_input("Discord Guild ID", required=True, validator=validate_discord_id)
    
    # AI API設定
    print("\n--- AI API設定 ---")
    openai_api_key = get_input("OpenAI API Key", required=False, validator=validate_api_key)
    claude_api_key = get_input("Claude API Key", required=False, validator=validate_api_key)
    
    if not openai_api_key and not claude_api_key:
        print_error("少なくともどちらかのAI APIキーを設定する必要があります")
        return False
    
    default_ai = "chatgpt" if openai_api_key else "claude"
    ai_provider = get_input(
        "デフォルトのAIプロバイダー (chatgpt または claude)",
        default=default_ai
    )
    
    # OpenAIモデル選択
    openai_model = "gpt-4o"
    if openai_api_key:
        print("\n利用可能なOpenAIモデル:")
        print("1. gpt-4o (GPT-4o)")
        print("2. gpt-4-turbo (GPT-4 Turbo)")
        print("3. gpt-3.5-turbo (GPT-3.5 Turbo)")
        model_choice = get_input("使用するモデル番号", default="1")
        
        if model_choice == "1":
            openai_model = "gpt-4o"
        elif model_choice == "2":
            openai_model = "gpt-4-turbo"
        elif model_choice == "3":
            openai_model = "gpt-3.5-turbo"
    
    # Claudeモデル選択
    claude_model = "claude-3-7-sonnet-20250219"
    if claude_api_key:
        print("\n利用可能なClaudeモデル:")
        print("1. claude-3-7-sonnet-20250219 (Claude 3.7 Sonnet)")
        print("2. claude-3-5-sonnet-20241022 (Claude 3.5 Sonnet)")
        print("3. claude-3-haiku-20240307 (Claude 3 Haiku)")
        model_choice = get_input("使用するモデル番号", default="1")
        
        if model_choice == "1":
            claude_model = "claude-3-7-sonnet-20250219"
        elif model_choice == "2":
            claude_model = "claude-3-5-sonnet-20241022"
        elif model_choice == "3":
            claude_model = "claude-3-haiku-20240307"
    
    # 環境変数ファイルを更新
    env_content = env_content.replace("your_discord_bot_token", discord_token)
    env_content = env_content.replace("your_discord_guild_id", discord_guild_id)
    env_content = env_content.replace("your_openai_api_key", openai_api_key or "")
    env_content = env_content.replace("your_claude_api_key", claude_api_key or "")
    env_content = env_content.replace("DEFAULT_AI_PROVIDER=chatgpt", f"DEFAULT_AI_PROVIDER={ai_provider}")
    env_content = env_content.replace("OPENAI_MODEL=gpt-4o", f"OPENAI_MODEL={openai_model}")
    env_content = env_content.replace("CLAUDE_MODEL=claude-3-7-sonnet-20250219", f"CLAUDE_MODEL={claude_model}")
    
    # 更新した内容を書き込み
    env_file.write_text(env_content, encoding='utf-8')
    print_success(".envファイルを更新しました")
    return True

def setup_email_mapping():
    """メールとチャンネルのマッピングファイルを作成"""
    print_step("email_channel_mapping.jsonファイルの設定")
    
    config_dir = Path("gmail_discord_bot/config")
    mapping_example = config_dir / "email_channel_mapping.json.example"
    mapping_file = config_dir / "email_channel_mapping.json"
    
    if not mapping_example.exists():
        print_error(f"{mapping_example} が見つかりません。リポジトリが正しくクローンされているか確認してください。")
        return False
    
    # 既存のマッピングファイルがあるか確認
    if mapping_file.exists():
        overwrite = get_input("既存のマッピングファイルが見つかりました。上書きしますか？ (yes/no)", default="no")
        if overwrite.lower() != "yes":
            print_warning("マッピングファイルの設定をスキップします")
            return True
    
    # マッピング情報を入力
    mappings = {}
    
    print("\nメールアドレスとDiscordチャンネルのマッピングを設定します")
    print("完了したら、メールアドレスの入力時に何も入力せずにEnterを押してください")
    
    while True:
        email = get_input("メールアドレス（例: user@example.com または *@example.com）", required=False, validator=validate_email)
        if not email:
            break
        
        name = get_input("送信者の名前（空でも可）", required=False)
        company = get_input("会社名（空でも可）", required=False)
        channel_id = get_input("Discord チャンネルID", required=True, validator=validate_discord_id)
        
        mappings[email] = {
            "email": email,
            "name": name,
            "company": company,
            "discord_channel_id": channel_id
        }
        
        print_success(f"マッピングを追加しました: {email} -> チャンネルID: {channel_id}")
    
    # マッピング情報をJSONファイルに保存
    with open(mapping_file, 'w', encoding='utf-8') as f:
        json.dump(mappings, f, ensure_ascii=False, indent=2)
    
    print_success(f"{mapping_file} を作成しました")
    return True

def setup_email_settings():
    """メール設定ファイルを作成"""
    print_step("email_settings.jsonファイルの設定")
    
    config_dir = Path("gmail_discord_bot/config")
    settings_file = config_dir / "email_settings.json"
    
    # 既存の設定ファイルがあるか確認
    if settings_file.exists():
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                settings = json.load(f)
        except json.JSONDecodeError:
            settings = {
                "calendar": {
                    "days": 30,
                    "working_hours": {
                        "start": 9,
                        "end": 18
                    },
                    "duration_minutes": 60,
                    "skip_weekends": True
                },
                "signature": {
                    "company_name": "",
                    "name": "",
                    "email": "",
                    "url": ""
                }
            }
    else:
        settings = {
            "calendar": {
                "days": 30,
                "working_hours": {
                    "start": 9,
                    "end": 18
                },
                "duration_minutes": 60,
                "skip_weekends": True
            },
            "signature": {
                "company_name": "",
                "name": "",
                "email": "",
                "url": ""
            },
            "discord": {
                "mention_user_id": ""
            }
        }
    
    # カレンダー設定
    print("\n--- カレンダー設定 ---")
    days = get_input("何日先までの予定を確認するか", default=str(settings["calendar"]["days"]))
    start_hour = get_input("勤務開始時間（0-23）", default=str(settings["calendar"]["working_hours"]["start"]), validator=validate_hours)
    end_hour = get_input("勤務終了時間（0-23）", default=str(settings["calendar"]["working_hours"]["end"]), validator=validate_hours)
    duration = get_input("会議の標準時間（分）", default=str(settings["calendar"]["duration_minutes"]))
    skip_weekends = get_input("週末をスキップするか（true/false）", default="true" if settings["calendar"]["skip_weekends"] else "false")
    
    # 署名設定
    print("\n--- 署名設定 ---")
    company_name = get_input("会社名", default=settings["signature"]["company_name"])
    name = get_input("名前", default=settings["signature"]["name"])
    email = get_input("メールアドレス", default=settings["signature"]["email"], validator=validate_email)
    url = get_input("ウェブサイトURL", default=settings["signature"]["url"])
    
    # Discord設定
    print("\n--- Discord設定 ---")
    mention_user_id = get_input("メール確認時にメンションするユーザーID", default="432550702032617473", validator=validate_discord_id)
    
    # 設定を更新
    settings["calendar"]["days"] = int(days)
    settings["calendar"]["working_hours"]["start"] = int(start_hour)
    settings["calendar"]["working_hours"]["end"] = int(end_hour)
    settings["calendar"]["duration_minutes"] = int(duration)
    settings["calendar"]["skip_weekends"] = skip_weekends.lower() == "true"
    
    settings["signature"]["company_name"] = company_name
    settings["signature"]["name"] = name
    settings["signature"]["email"] = email
    settings["signature"]["url"] = url
    
    settings["discord"]["mention_user_id"] = mention_user_id
    
    # 設定をJSONファイルに保存
    with open(settings_file, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)
    
    print_success(f"{settings_file} を作成しました")
    return True

def check_credentials():
    """認証情報ファイルの存在を確認"""
    print_step("認証情報ファイルの確認")
    
    config_dir = Path("gmail_discord_bot/config")
    gmail_creds = config_dir / "credentials.json"
    calendar_creds = config_dir / "calendar_credentials.json"
    
    if not gmail_creds.exists():
        print_error("Gmail API認証情報ファイル (credentials.json) が見つかりません")
        print("Google Cloud Consoleから認証情報をダウンロードし、gmail_discord_bot/config/ディレクトリに配置してください")
        return False
    
    if not calendar_creds.exists():
        print_warning("Googleカレンダー API認証情報ファイル (calendar_credentials.json) が見つかりません")
        print("credentials.jsonをcalendar_credentials.jsonとしてコピーしますか？ (yes/no)")
        copy_creds = get_input("", default="yes")
        
        if copy_creds.lower() == "yes":
            shutil.copy(gmail_creds, calendar_creds)
            print_success("credentials.jsonをcalendar_credentials.jsonとしてコピーしました")
        else:
            print_warning("Googleカレンダー API認証情報ファイルを手動で配置してください")
            return False
    
    print_success("認証情報ファイルの確認が完了しました")
    return True

def main():
    """メイン関数"""
    print_header("Gmail-Discord自動転送・返信システム 設定ファイル自動生成ツール")
    
    print("このツールは、Gmail-Discord自動転送・返信システムの初期設定を対話形式で行います。")
    print("必要な情報を入力すると、設定ファイルが自動的に生成されます。")
    print("\n開始する前に、以下の情報を準備してください：")
    print("1. Discord Bot Token")
    print("2. Discord Guild ID（サーバーID）")
    print("3. OpenAI APIキーまたはClaude APIキー")
    print("4. Google Cloud Platformからダウンロードした認証情報ファイル（credentials.json）")
    
    proceed = get_input("\n準備ができたら「yes」と入力して続行してください", default="yes")
    if proceed.lower() != "yes":
        print("セットアップを中止します。準備ができたら再度実行してください。")
        return
    
    # 各設定ファイルのセットアップ
    if not check_credentials():
        print_error("認証情報ファイルの確認に失敗しました。セットアップを中止します。")
        return
    
    if not setup_env_file():
        print_error(".envファイルの設定に失敗しました。セットアップを中止します。")
        return
    
    if not setup_email_mapping():
        print_error("email_channel_mapping.jsonファイルの設定に失敗しました。セットアップを中止します。")
        return
    
    if not setup_email_settings():
        print_error("email_settings.jsonファイルの設定に失敗しました。セットアップを中止します。")
        return
    
    print_header("セットアップ完了")
    print("Gmail-Discord自動転送・返信システムの設定ファイルが正常に生成されました。")
    print("\n次のコマンドでシステムを起動できます：")
    print(f"{Colors.BOLD}python -m gmail_discord_bot.main{Colors.ENDC}")
    print("\n初回起動時は、ブラウザが開いてGoogleアカウントの認証が求められます。")
    print("認証が完了すると、システムが自動的に起動します。")

if __name__ == "__main__":
    main()