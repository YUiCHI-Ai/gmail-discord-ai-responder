import re
import openai
from ..config import config
from ..utils.logger import setup_logger

logger = setup_logger(__name__)

class ResponseProcessor:
    def __init__(self):
        openai.api_key = config.OPENAI_API_KEY
    
    async def generate_responses(self, prompt, num_responses=3):
        """ChatGPT APIを使用して返信を生成"""
        try:
            response = openai.ChatCompletion.create(
                model="gpt-4",  # または利用可能な最新モデル
                messages=[
                    {"role": "system", "content": "あなたはプロフェッショナルなビジネスメール返信を作成するアシスタントです。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000,
                n=1
            )
            
            # レスポンスから返信テキストを抽出
            response_text = response.choices[0].message.content
            
            # 返信を分割（「案1」「案2」「案3」で区切る）
            responses = self._split_responses(response_text)
            
            logger.info(f"{len(responses)}件の返信候補を生成しました")
            return responses
        
        except Exception as e:
            logger.error(f"ChatGPT API呼び出しエラー: {e}")
            # エラー時のフォールバック
            return [
                "申し訳ありません。返信の生成中にエラーが発生しました。",
                "しばらく経ってからもう一度お試しください。"
            ]
    
    def _split_responses(self, response_text):
        """ChatGPTの応答から個別の返信案を抽出"""
        # 「案1」「案2」「案3」などのパターンで分割
        pattern = r'(?:^|\n)(?:案|パターン|返信案|バリエーション)\s*(\d+)[：:]\s*\n'
        splits = re.split(pattern, response_text, flags=re.MULTILINE)
        
        if len(splits) <= 1:
            # パターンが見つからない場合は、全体を1つの返信として扱う
            return [response_text.strip()]
        
        # 最初の要素はヘッダー部分なので除外
        splits = splits[1:]
        
        # 番号と内容のペアに整形
        responses = []
        for i in range(0, len(splits), 2):
            if i + 1 < len(splits):
                responses.append(splits[i + 1].strip())
        
        # 返信が取得できなかった場合
        if not responses:
            return [response_text.strip()]
        
        return responses
    
    def clean_response(self, response_text):
        """返信テキストをクリーンアップ"""
        # 余分な空白行を削除
        cleaned = re.sub(r'\n{3,}', '\n\n', response_text)
        
        # 「案X:」などのプレフィックスを削除
        cleaned = re.sub(r'^(?:案|パターン|返信案|バリエーション)\s*\d+[：:]\s*\n', '', cleaned, flags=re.MULTILINE)
        
        return cleaned.strip()