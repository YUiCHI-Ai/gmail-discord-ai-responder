import re
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

class MessageFormatter:
    def __init__(self):
        pass
    
    def format_email_for_discord(self, email_data):
        """メールをDiscord表示用にフォーマット"""
        # 基本情報
        formatted = f"**新しいメール**\n"
        formatted += f"**件名:** {email_data['subject']}\n"
        
        # 送信者情報を表示（会社名と名前を含む）
        sender_display = email_data['sender']
        if 'sender_name' in email_data and email_data['sender_name']:
            if 'sender_company' in email_data and email_data['sender_company']:
                sender_display = f"{email_data['sender']} ({email_data['sender_company']} {email_data['sender_name']})"
            else:
                sender_display = f"{email_data['sender']} ({email_data['sender_name']})"
        elif 'sender_company' in email_data and email_data['sender_company']:
            sender_display = f"{email_data['sender']} ({email_data['sender_company']})"
        
        formatted += f"**送信者:** {sender_display}\n"
        formatted += f"**日時:** {email_data['date']}\n\n"
        
        # 本文（長すぎる場合は分割）
        body = email_data['body']
        if len(body) > 1900:  # Discordのメッセージ制限に近い値
            # 本文を分割
            parts = []
            current_part = ""
            for line in body.split('\n'):
                if len(current_part) + len(line) + 1 > 1900:
                    parts.append(current_part)
                    current_part = line
                else:
                    if current_part:
                        current_part += '\n' + line
                    else:
                        current_part = line
            
            if current_part:
                parts.append(current_part)
            
            # 最初の部分を追加
            formatted += f"**本文 (1/{len(parts)}):**\n```\n{parts[0]}\n```"
            return formatted, parts[1:]
        else:
            formatted += f"**本文:**\n```\n{body}\n```"
            return formatted, []
    
    def format_response_options(self, options):
        """返信候補をフォーマット"""
        formatted_options = []
        
        for i, option in enumerate(options, 1):
            formatted = f"**候補 {i}**\n```\n{option}\n```"
            formatted_options.append(formatted)
        
        return formatted_options
    
    def extract_email_thread(self, discord_messages):
        """Discordメッセージからメールスレッドを抽出"""
        email_content = ""
        
        for message in discord_messages:
            if "新しいメール" in message.content:
                # メールの基本情報を抽出
                subject_match = re.search(r'\*\*件名:\*\* (.*?)\n', message.content)
                sender_match = re.search(r'\*\*送信者:\*\* (.*?)\n', message.content)
                
                if subject_match and sender_match:
                    email_content += f"件名: {subject_match.group(1)}\n"
                    email_content += f"送信者: {sender_match.group(1)}\n"
            
            # 本文部分を抽出
            body_match = re.search(r'\*\*本文.*?:\*\*\n```\n(.*?)\n```', message.content, re.DOTALL)
            if body_match:
                email_content += f"本文:\n{body_match.group(1)}\n\n"
        
        return email_content