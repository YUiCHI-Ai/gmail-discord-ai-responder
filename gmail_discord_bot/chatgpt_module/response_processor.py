import re
import openai
from ..config import config
from ..utils.logger import setup_logger
from ..calendar_module.schedule_analyzer import ScheduleAnalyzer

logger = setup_logger(__name__)

class ResponseProcessor:
    def __init__(self):
        openai.api_key = config.OPENAI_API_KEY
        self.schedule_analyzer = ScheduleAnalyzer()
    
    async def analyze_email(self, prompt):
        """ChatGPT APIを使用してメールを分析"""
        try:
            # メール分析用のシステムプロンプトを取得
            system_prompt = config.get_email_analyzer_prompt()
            
            response = openai.ChatCompletion.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1000,
                n=1
            )
            
            # レスポンスから分析テキストを抽出
            analysis_text = response.choices[0].message.content
            
            # 分析結果を抽出
            analysis = self._extract_analysis(analysis_text)
            
            # 必要情報を抽出
            required_info = self._extract_required_info(analysis_text)
            
            logger.info(f"メール分析完了: 必要情報タイプ={required_info.get('type', 'なし')}")
            return {
                "analysis": analysis,
                "required_info": required_info
            }
        
        except Exception as e:
            logger.error(f"メール分析API呼び出しエラー: {e}")
            return {
                "analysis": "分析中にエラーが発生しました。",
                "required_info": {"type": None}
            }
    
    async def generate_responses(self, prompt, analysis_result=None, num_responses=1):
        """ChatGPT APIを使用して返信を生成"""
        try:
            # 追加情報の取得
            additional_info = ""
            if analysis_result and analysis_result.get("required_info", {}).get("type") == "カレンダー":
                # カレンダー情報が必要な場合、利用可能なスロットを取得
                available_slots = self.schedule_analyzer.get_available_slots()
                slots_text = "\n".join([f"- {slot}" for slot in available_slots])
                additional_info = f"\n\n# 利用可能な日時スロット\n以下の日時が空いています：\n{slots_text}"
            
            # 返信生成用のシステムプロンプトを取得
            system_prompt = config.get_email_responder_prompt()
            
            # 分析結果を含めたプロンプトを作成
            full_prompt = prompt
            if analysis_result:
                analysis = analysis_result.get("analysis", "")
                full_prompt = f"{prompt}\n\n# メール分析結果\n{analysis}{additional_info}"
            
            response = openai.ChatCompletion.create(
                model=config.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": full_prompt}
                ],
                temperature=0.7,
                max_tokens=2000,
                n=1
            )
            
            # レスポンスから返信テキストを抽出
            response_text = response.choices[0].message.content
            
            # 返信を抽出
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
    
    def _extract_analysis(self, text):
        """分析結果を抽出"""
        pattern = r'<分析>(.*?)</分析>'
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return text
    
    def _extract_required_info(self, text):
        """必要情報を抽出"""
        pattern = r'<必要情報>.*?<タイプ>(.*?)</タイプ>.*?</必要情報>'
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return {"type": match.group(1).strip()}
        return {"type": None}
    
    def _split_responses(self, response_text):
        """ChatGPTの応答から返信を抽出"""
        # XMLタグで囲まれた返信を抽出
        pattern = r'<返信>(.*?)</返信>'
        matches = re.findall(pattern, response_text, re.DOTALL)
        
        if matches:
            # 返信タグが見つかった場合
            return [match.strip() for match in matches]
        else:
            # 返信タグが見つからない場合は、全体を1つの返信として扱う
            return [response_text.strip()]
    
    def clean_response(self, response_text):
        """返信テキストをクリーンアップ"""
        # 余分な空白行を削除
        cleaned = re.sub(r'\n{3,}', '\n\n', response_text)
        return cleaned.strip()