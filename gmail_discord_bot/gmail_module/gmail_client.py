import os
import pickle
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from pathlib import Path
import base64
import email
from email.header import decode_header

from ..config import config
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

class GmailClient:
    def __init__(self):
        self.creds = None
        self.service = None
        self.initialize_service()
    
    def initialize_service(self):
        """Gmail APIサービスの初期化"""
        if os.path.exists(config.GMAIL_TOKEN_FILE):
            with open(config.GMAIL_TOKEN_FILE, 'rb') as token:
                self.creds = pickle.load(token)
        
        # 認証情報がない、または期限切れの場合
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    config.GMAIL_CREDENTIALS_FILE, config.GMAIL_SCOPES)
                self.creds = flow.run_local_server(port=0)
            
            # トークンを保存
            with open(config.GMAIL_TOKEN_FILE, 'wb') as token:
                pickle.dump(self.creds, token)
        
        self.service = build('gmail', 'v1', credentials=self.creds)
        logger.info("Gmail APIサービスが初期化されました")
    
    def get_unread_emails(self, max_results=10):
        """未読メールを取得"""
        try:
            results = self.service.users().messages().list(
                userId='me', labelIds=['INBOX', 'UNREAD'], maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            emails = []
            
            for message in messages:
                msg = self.service.users().messages().get(
                    userId='me', id=message['id'], format='full'
                ).execute()
                
                emails.append(self._parse_message(msg))
            
            return emails
        
        except Exception as e:
            logger.error(f"メール取得エラー: {e}")
            return []
    
    def _parse_message(self, message):
        """メッセージをパース"""
        msg_id = message['id']
        payload = message['payload']
        headers = payload.get('headers', [])
        
        # ヘッダー情報を取得
        subject = ""
        sender = ""
        date = ""
        
        for header in headers:
            name = header.get('name', '').lower()
            if name == 'subject':
                subject = header.get('value', '')
            elif name == 'from':
                sender = header.get('value', '')
            elif name == 'date':
                date = header.get('value', '')
        
        # 本文を取得
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    body = base64.urlsafe_b64decode(
                        part['body']['data']).decode('utf-8')
                    break
        elif 'body' in payload and 'data' in payload['body']:
            body = base64.urlsafe_b64decode(
                payload['body']['data']).decode('utf-8')
        
        return {
            'id': msg_id,
            'subject': subject,
            'sender': sender,
            'date': date,
            'body': body,
            'raw_message': message
        }
    
    def mark_as_read(self, msg_id):
        """メールを既読にする"""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=msg_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            logger.info(f"メール {msg_id} を既読にしました")
            return True
        except Exception as e:
            logger.error(f"既読マーク設定エラー: {e}")
            return False
    
    def send_email(self, to, subject, body, thread_id=None):
        """メールを送信する"""
        try:
            message = email.message.EmailMessage()
            message['To'] = to
            message['Subject'] = subject
            message.set_content(body)
            
            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            create_message = {
                'raw': encoded_message
            }
            
            if thread_id:
                create_message['threadId'] = thread_id
            
            send_message = self.service.users().messages().send(
                userId='me', body=create_message).execute()
            
            logger.info(f"メール送信成功: {send_message['id']}")
            return send_message
        
        except Exception as e:
            logger.error(f"メール送信エラー: {e}")
            return None