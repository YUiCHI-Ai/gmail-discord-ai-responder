import re
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

class PromptGenerator:
    def __init__(self):
        # 日程調整関連のキーワード
        self.schedule_keywords = [
            '日程', 'スケジュール', '予定', '空き時間', '都合', '面談', '面接',
            '打ち合わせ', 'ミーティング', '会議', '訪問', '来社',
            'schedule', 'meeting', 'appointment', 'interview', 'visit'
        ]
    
    def is_schedule_related(self, email_data):
        """メールが日程調整に関連するかを判定"""
        subject = email_data['subject'].lower()
        body = email_data['body'].lower()
        
        # 件名または本文に日程調整関連のキーワードが含まれるか確認
        for keyword in self.schedule_keywords:
            if keyword in subject or keyword in body:
                logger.info(f"日程調整関連のメールと判定: キーワード '{keyword}' を検出")
                return True
        
        return False
    
    def generate_normal_prompt(self, email_data, sender_info, address):
        """通常の返信用プロンプトを生成"""
        prompt = f"""
あなたは、プロフェッショナルなビジネスメールの返信を作成するアシスタントです。
以下のメールに対して、丁寧かつ適切なビジネスメール形式の返信を3つの異なるバリエーションで作成してください。

# 元のメール情報
件名: {email_data['subject']}
送信者: {email_data['sender']}
本文:
{email_data['body']}

# 返信の要件
1. 宛名は「{address}」を使用してください。
2. 日本語のビジネスメールとして適切な敬語と構成を使用してください。
3. 元のメールの内容に対して具体的に応答してください。
4. 簡潔かつ明確な文章を心がけてください。
5. 署名は「株式会社〇〇 山田太郎」としてください。
6. 各バリエーションは異なる表現や構成を持つようにしてください。
7. 返信は完全な形式（宛名から署名まで）で作成してください。

それぞれのバリエーションを「案1」「案2」「案3」として明確に区別してください。
"""
        return prompt
    
    def generate_schedule_prompt(self, email_data, sender_info, address, available_slots):
        """日程調整用プロンプトを生成"""
        # 利用可能な日時スロットをフォーマット
        slots_text = "\n".join([f"- {slot}" for slot in available_slots])
        
        prompt = f"""
あなたは、プロフェッショナルなビジネスメールの返信を作成するアシスタントです。
以下の日程調整に関するメールに対して、丁寧かつ適切なビジネスメール形式の返信を3つの異なるバリエーションで作成してください。

# 元のメール情報
件名: {email_data['subject']}
送信者: {email_data['sender']}
本文:
{email_data['body']}

# 利用可能な日時スロット
以下の日時が空いています：
{slots_text}

# 返信の要件
1. 宛名は「{address}」を使用してください。
2. 日本語のビジネスメールとして適切な敬語と構成を使用してください。
3. 元のメールの内容に対して具体的に応答してください。
4. 上記の利用可能な日時スロットから、2〜3の候補日時を提案してください。
5. 簡潔かつ明確な文章を心がけてください。
6. 署名は「株式会社〇〇 山田太郎」としてください。
7. 各バリエーションは異なる表現や構成を持つようにしてください。
8. 返信は完全な形式（宛名から署名まで）で作成してください。

それぞれのバリエーションを「案1」「案2」「案3」として明確に区別してください。
"""
        return prompt