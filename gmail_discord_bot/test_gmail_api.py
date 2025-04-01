import os
import pickle
from googleapiclient.discovery import build
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

def get_gmail_service():
    """Gmail APIサービスを取得"""
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
    
    # Gmail APIサービスを構築
    service = build('gmail', 'v1', credentials=creds)
    return service

def list_labels():
    """Gmailのラベル一覧を取得"""
    service = get_gmail_service()
    results = service.users().labels().list(userId='me').execute()
    labels = results.get('labels', [])
    
    if not labels:
        print('ラベルが見つかりませんでした。')
    else:
        print('ラベル一覧:')
        for label in labels:
            print(f"- {label['name']} (ID: {label['id']})")

def list_recent_emails(max_results=5):
    """最近のメールを取得"""
    service = get_gmail_service()
    results = service.users().messages().list(
        userId='me', labelIds=['INBOX'], maxResults=max_results
    ).execute()
    
    messages = results.get('messages', [])
    
    if not messages:
        print('メールが見つかりませんでした。')
        return
    
    print(f'最近の{len(messages)}件のメール:')
    for message in messages:
        msg = service.users().messages().get(
            userId='me', id=message['id'], format='metadata'
        ).execute()
        
        headers = msg['payload']['headers']
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '(件名なし)')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), '(送信者不明)')
        
        print(f"- 件名: {subject}")
        print(f"  送信者: {sender}")
        print(f"  ID: {message['id']}")
        print()

if __name__ == "__main__":
    print("Gmail APIのテストを開始します...")
    
    print("\n=== ラベル一覧 ===")
    list_labels()
    
    print("\n=== 最近のメール ===")
    list_recent_emails()
    
    print("\nGmail APIのテストが完了しました。")