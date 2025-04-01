import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from pathlib import Path

# 設定ファイルのパス
config_dir = Path(__file__).parent / "config"
CREDENTIALS_FILE = config_dir / "credentials.json"
TOKEN_FILE = config_dir / "token.json"
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send"
]

def get_gmail_credentials():
    """Gmail APIの認証情報を取得"""
    creds = None
    
    # token.jsonが存在する場合は読み込む
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    
    # 認証情報がない、または期限切れの場合
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # トークンを保存
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    
    return creds

if __name__ == "__main__":
    print("Gmail APIの認証を開始します...")
    creds = get_gmail_credentials()
    print(f"認証が完了しました。トークンが {TOKEN_FILE} に保存されました。")