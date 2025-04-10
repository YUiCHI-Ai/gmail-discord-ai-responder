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
        thread_id = message.get('threadId', '')
        payload = message['payload']
        headers = payload.get('headers', [])
        
        # ヘッダー情報を取得
        subject = ""
        sender = ""
        date = ""
        message_id = ""
        references = ""
        in_reply_to = ""
        
        for header in headers:
            name = header.get('name', '').lower()
            if name == 'subject':
                subject = header.get('value', '')
            elif name == 'from':
                sender = header.get('value', '')
            elif name == 'date':
                date = header.get('value', '')
            elif name == 'message-id':
                message_id = header.get('value', '')
                # <...@...> 形式から内部のIDだけを抽出
                if message_id.startswith('<') and '>' in message_id:
                    message_id = message_id.strip('<>').split('@')[0]
            elif name == 'references':
                references = header.get('value', '')
            elif name == 'in-reply-to':
                in_reply_to = header.get('value', '')
        
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
            'thread_id': thread_id,
            'subject': subject,
            'sender': sender,
            'date': date,
            'body': body,
            'message_id': message_id,
            'references': references,
            'in_reply_to': in_reply_to,
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
    
    def get_attachments(self, msg_id):
        """メールの添付ファイルを取得"""
        try:
            message = self.service.users().messages().get(
                userId='me', id=msg_id, format='full'
            ).execute()
            
            attachments = []
            
            # メッセージのパート（添付ファイルを含む）を処理
            if 'parts' in message['payload']:
                for part in message['payload']['parts']:
                    if 'filename' in part and part['filename']:
                        # 添付ファイル情報を取得
                        filename = part['filename']
                        attachment_id = part['body'].get('attachmentId')
                        
                        if attachment_id:
                            # 添付ファイルのデータを取得
                            attachment = self.service.users().messages().attachments().get(
                                userId='me', messageId=msg_id, id=attachment_id
                            ).execute()
                            
                            file_data = base64.urlsafe_b64decode(attachment['data'])
                            
                            # 添付ファイル情報を保存
                            attachments.append({
                                'filename': filename,
                                'data': file_data,
                                'size': len(file_data),
                                'mime_type': part.get('mimeType', 'application/octet-stream')
                            })
            
            logger.info(f"メール {msg_id} から {len(attachments)} 件の添付ファイルを取得しました")
            return attachments
            
        except Exception as e:
            logger.error(f"添付ファイル取得エラー: {e}")
            return []
    
    def get_thread_list(self, user_id='me', query='', max_results=10):
        """スレッドリストを取得する
        
        Args:
            user_id: ユーザーID（通常は'me'）
            query: 検索クエリ（例: 'in:sent'）
            max_results: 最大結果数
            
        Returns:
            スレッドリスト
        """
        try:
            thread_list = self.service.users().threads().list(
                userId=user_id, q=query, maxResults=max_results).execute().get('threads', [])
            logger.info(f"{len(thread_list)}件のスレッドを取得しました")
            return thread_list
        except Exception as e:
            logger.error(f"スレッド取得エラー: {e}")
            return []
    
    def get_thread(self, thread_id, user_id='me'):
        """スレッドの詳細を取得する
        
        Args:
            thread_id: スレッドID
            user_id: ユーザーID（通常は'me'）
            
        Returns:
            スレッド情報
        """
        try:
            thread = self.service.users().threads().get(
                userId=user_id, id=thread_id).execute()
            logger.info(f"スレッド {thread_id} の詳細を取得しました")
            return thread
        except Exception as e:
            logger.error(f"スレッド詳細取得エラー: {e}")
            return None
    
    def send_email(self, to, subject, body, thread_id=None, message_id=None, references=None, quote_original=False, reply_all=False, cc=None):
        """メールを送信する
        
        Args:
            to: 送信先メールアドレス
            subject: 件名
            body: 本文
            thread_id: スレッドID（返信の場合）
            message_id: 返信元メッセージID（返信の場合）
            references: 参照メッセージID（返信の場合）
            quote_original: 元のメッセージを引用するかどうか
            reply_all: 全員に返信するかどうか
            cc: CCに含めるメールアドレス（カンマ区切りの文字列またはリスト）
            
        Returns:
            送信成功時: 送信結果の辞書
            送信失敗時: None
        """
        try:
            # CCアドレスの初期化
            cc_addresses = []
            if cc:
                if isinstance(cc, list):
                    cc_addresses = cc
                else:
                    cc_addresses = [addr.strip() for addr in cc.split(',')]
            # 元のメッセージを引用する場合
            original_message_body = ""
            original_cc = []
            
            if (quote_original or reply_all) and thread_id and message_id:
                try:
                    # スレッドを取得して最新のメッセージを取得
                    thread = self.get_thread(thread_id)
                    if thread and 'messages' in thread:
                        # スレッド内の最新メッセージを探す
                        original_message = None
                        for msg in thread['messages']:
                            msg_headers = msg['payload']['headers']
                            for header in msg_headers:
                                if header['name'].lower() == 'message-id' and message_id in header['value']:
                                    original_message = msg
                                    break
                        
                        # 元のメッセージが見つかった場合
                        if original_message:
                            # メッセージの本文を取得
                            if 'parts' in original_message['payload']:
                                for part in original_message['payload']['parts']:
                                    if part['mimeType'] == 'text/plain':
                                        original_message_body = base64.urlsafe_b64decode(
                                            part['body']['data']).decode('utf-8')
                                        break
                            elif 'body' in original_message['payload'] and 'data' in original_message['payload']['body']:
                                original_message_body = base64.urlsafe_b64decode(
                                    original_message['payload']['body']['data']).decode('utf-8')
                            
                            # Reply Allの場合、元のメッセージからCCを取得
                            if reply_all:
                                for header in original_message['payload']['headers']:
                                    if header['name'].lower() == 'cc':
                                        # CCアドレスを取得してリストに追加
                                        cc_from_original = [addr.strip() for addr in header['value'].split(',')]
                                        original_cc = cc_from_original
                                        logger.info(f"元のメッセージからCCを取得: {original_cc}")
                                        break
                    
                    # 元のメッセージを引用形式に変換
                    if original_message_body:
                        quoted_body = ""
                        for line in original_message_body.splitlines():
                            quoted_body += f"> {line}\n"
                        
                        # 引用を本文に追加
                        body = f"{body}\n\n{quoted_body}"
                        logger.info("元のメッセージを引用形式で追加しました")
                except Exception as e:
                    logger.error(f"メッセージ引用処理エラー: {e}")
            
            # メッセージオブジェクトの作成
            message = email.message.EmailMessage()
            message['To'] = to
            message['Subject'] = subject
            message['From'] = self.get_user_email()  # 送信者のメールアドレスを設定
            
            # CCの設定
            if reply_all and original_cc:
                # 自分自身のアドレスをCCから除外
                my_email = self.get_user_email()
                filtered_cc = [cc_addr for cc_addr in original_cc if cc_addr != my_email and cc_addr != to]
                
                # ユーザー指定のCCと元のメールのCCをマージ
                all_cc = list(set(filtered_cc + cc_addresses))
                
                if all_cc:
                    message['Cc'] = ', '.join(all_cc)
                    logger.info(f"CCを設定: {message['Cc']}")
            elif cc_addresses:
                # 通常の返信でCCが指定されている場合
                message['Cc'] = ', '.join(cc_addresses)
                logger.info(f"CCを設定: {message['Cc']}")
            
            # 返信ヘッダーの設定（返信の場合）
            if message_id:
                # 完全なメッセージIDを作成（<>形式を保持）
                full_message_id = message_id
                if not (message_id.startswith('<') and message_id.endswith('>')):
                    full_message_id = f"<{message_id}@mail.gmail.com>"
                
                # In-Reply-To ヘッダーを設定
                message['In-Reply-To'] = full_message_id
                logger.info(f"In-Reply-To ヘッダーを設定: {full_message_id}")
                
                # References ヘッダーを設定
                if references:
                    message['References'] = f"{references} {full_message_id}"
                else:
                    message['References'] = full_message_id
                logger.info(f"References ヘッダーを設定: {message['References']}")
            
            # 本文を設定（文字コードを明示的に指定）
            message.set_content(body, subtype='plain', charset='UTF-8')
            
            # メッセージをエンコード
            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            # 送信用メッセージを作成
            create_message = {
                'raw': encoded_message
            }
            
            # スレッドIDがあれば指定
            if thread_id:
                create_message['threadId'] = thread_id
                logger.info(f"スレッドID {thread_id} を指定してメールを送信します")
            
            # メールを送信
            send_message = self.service.users().messages().send(
                userId='me', body=create_message).execute()
            
            logger.info(f"メール送信成功: {send_message['id']}")
            return send_message
        
        except Exception as e:
            logger.error(f"メール送信エラー: {e}")
            import traceback
            logger.error(f"詳細なエラー情報: {traceback.format_exc()}")
            return None
    
    def get_user_email(self):
        """現在認証されているユーザーのメールアドレスを取得"""
        try:
            profile = self.service.users().getProfile(userId='me').execute()
            return profile['emailAddress']
        except Exception as e:
            logger.error(f"ユーザープロファイル取得エラー: {e}")
            import traceback
            logger.error(f"詳細なエラー情報: {traceback.format_exc()}")
            return None
    
    # テスト用メソッドと不要な関数を削除しました