import re
from ..config import config
from ..utils.logger import setup_logger, flow_step, FlowStep
from .gmail_client import GmailClient

logger = setup_logger(__name__)

class EmailProcessor:
    def __init__(self, gmail_client=None):
        self.gmail_client = gmail_client or GmailClient()
        self.email_channel_mapping = config.get_email_channel_mapping()
    
    @flow_step(FlowStep.RECEIVE_EMAIL)
    def process_new_emails(self, max_emails=10):
        """新しいメールを処理"""
        emails = self.gmail_client.get_unread_emails(max_emails)
        logger.log_flow(FlowStep.RECEIVE_EMAIL, f"{len(emails)}件の未読メールを取得")
        
        processed_emails = []
        
        for email_data in emails:
            # 送信者のメールアドレスを抽出
            sender_email = self._extract_email_address(email_data['sender'])
            
            # 対応するDiscordチャンネルを検索
            logger.log_flow(FlowStep.CHECK_SENDER, f"メール {email_data['id']} の送信元アドレスを確認")
            channel_id = self._get_channel_for_email(sender_email)
            
            if channel_id:
                # 処理対象のメールとしてマーク
                email_data['discord_channel_id'] = channel_id
                processed_emails.append(email_data)
                
                # メールを既読にする
                self.gmail_client.mark_as_read(email_data['id'])
                logger.log_flow(FlowStep.CHECK_SENDER, f"メール {email_data['id']} を処理対象としてマーク")
            else:
                logger.log_flow(FlowStep.CHECK_SENDER, f"メール {email_data['id']} は処理対象外: マッピングなし")
        
        return processed_emails
    
    def _extract_email_address(self, sender_string):
        """送信者文字列からメールアドレスを抽出"""
        # 'Name <email@example.com>' または 'email@example.com' の形式に対応
        match = re.search(r'<([^>]+)>', sender_string)
        if match:
            return match.group(1).lower()
        else:
            # '<>'がない場合は文字列全体をメールアドレスとみなす
            return sender_string.lower()
    
    def _get_channel_for_email(self, email_address):
        """メールアドレスに対応するDiscordチャンネルIDを取得"""
        # 完全一致
        if email_address in self.email_channel_mapping:
            return self.email_channel_mapping[email_address]["discord_channel_id"]
        
        # ドメイン一致（example.com形式のマッピングがある場合）
        domain = email_address.split('@')[-1]
        if domain in self.email_channel_mapping:
            return self.email_channel_mapping[domain]["discord_channel_id"]
        
        # ワイルドカードマッピング（*@example.com形式）
        wildcard = f"*@{domain}"
        if wildcard in self.email_channel_mapping:
            return self.email_channel_mapping[wildcard]["discord_channel_id"]
        
        return None