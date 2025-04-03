import re
import asyncio
import anthropic
from ..config import config
from ..utils.logger import setup_logger
from ..calendar_module.schedule_analyzer import ScheduleAnalyzer
from ..utils.output_saver import OutputSaver

logger = setup_logger(__name__)

class ClaudeResponseProcessor:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=config.CLAUDE_API_KEY)
        self.async_client = anthropic.AsyncAnthropic(api_key=config.CLAUDE_API_KEY)
        self.model = config.CLAUDE_MODEL  # .envファイルで設定されたモデル
        self.schedule_analyzer = ScheduleAnalyzer()
        self.output_saver = OutputSaver()  # LLM出力保存用
        self.settings = config.get_email_settings()
    
    async def analyze_email(self, prompt, email_id=None):
        """Claude APIを使用してメールを分析"""
        try:
            # メール分析用のシステムプロンプトを取得
            system_prompt = config.get_email_analyzer_prompt()
            
            # 非同期クライアントを使用
            response = await self.async_client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.7,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # レスポンスから分析テキストを抽出
            analysis_text = response.content[0].text
            
            # 分析結果を抽出
            analysis = self._extract_analysis(analysis_text)
            
            # 必要情報を抽出
            required_info = self._extract_required_info(analysis_text)
            
            # 結果を構造化
            analysis_result = {
                "analysis": analysis,
                "required_info": required_info
            }
            
            # 結果をファイルに保存（メールIDがある場合のみ）
            if email_id:
                try:
                    filepath = self.output_saver.save_analysis(
                        email_id=email_id,
                        analysis_text=analysis_text,
                        analysis_result=analysis_result,
                        provider="claude"
                    )
                    logger.info(f"メール分析結果を保存しました: {filepath}")
                except Exception as save_error:
                    logger.error(f"メール分析結果の保存に失敗しました: {save_error}")
            
            logger.info(f"メール分析完了: 必要情報タイプ={required_info.get('type', 'なし')}")
            return analysis_result
        
        except Exception as e:
            logger.error(f"メール分析API呼び出しエラー: {e}")
            return {
                "analysis": "分析中にエラーが発生しました。",
                "required_info": {"type": None}
            }
    
    async def generate_responses(self, prompt, analysis_result=None, num_responses=1, email_id=None):
        """Claude APIを使用して返信を生成"""
        try:
            # 追加情報の取得
            additional_info = {}
            additional_info_text = ""
            
            if analysis_result and analysis_result.get("required_info", {}).get("type") == "カレンダー":
                # カレンダー情報が必要な場合、利用可能なスロットを取得
                available_slots = self.schedule_analyzer.get_available_slots()
                slots_text = "\n".join([f"- {slot}" for slot in available_slots])
                additional_info_text = f"\n\n# 利用可能な日時スロット\n以下の日時が空いています：\n{slots_text}"
                additional_info = {"type": "カレンダー", "available_slots": available_slots}
            
            # 返信生成用のシステムプロンプトを取得
            system_prompt = config.get_email_responder_prompt()
            
            # 署名情報を取得
            signature_settings = self.settings.get("signature", {})
            company_name = signature_settings.get("company_name")
            name = signature_settings.get("name")
            email = signature_settings.get("email")
            url = signature_settings.get("url")
            
            # 署名情報をプロンプトに追加
            signature_info = f"\n\n# 署名情報\n会社名: {company_name}\n名前: {name}\nEmail: {email}\nURL: {url}"
            
            # 分析結果を含めたプロンプトを作成
            full_prompt = prompt
            if analysis_result:
                analysis = analysis_result.get("analysis", "")
                full_prompt = f"{prompt}\n\n# メール分析結果\n{analysis}{additional_info_text}{signature_info}"
            
            # 非同期クライアントを使用
            response = await self.async_client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0.7,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": full_prompt}
                ]
            )
            
            # レスポンスから返信テキストを抽出
            response_text = response.content[0].text
            
            # 返信を抽出
            responses = self._split_responses(response_text)
            
            # 結果をファイルに保存（メールIDがある場合のみ）
            if email_id:
                try:
                    filepath = self.output_saver.save_responses(
                        email_id=email_id,
                        response_text=response_text,
                        responses=responses,
                        provider="claude",
                        additional_info=additional_info
                    )
                    logger.info(f"返信候補を保存しました: {filepath}")
                except Exception as save_error:
                    logger.error(f"返信候補の保存に失敗しました: {save_error}")
            
            logger.info(f"{len(responses)}件の返信候補を生成しました")
            return responses
        
        except Exception as e:
            logger.error(f"Claude API呼び出しエラー: {e}")
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
        # タイプを抽出
        type_pattern = r'<必要情報>.*?<タイプ>(.*?)</タイプ>.*?</必要情報>'
        type_match = re.search(type_pattern, text, re.DOTALL)
        
        # 詳細情報を抽出（存在する場合）
        details_pattern = r'<必要情報>.*?<詳細>(.*?)</詳細>.*?</必要情報>'
        details_match = re.search(details_pattern, text, re.DOTALL)
        
        if type_match:
            info_type = type_match.group(1).strip()
            details = details_match.group(1).strip() if details_match else ""
            return {
                "type": info_type,
                "details": details
            }
        return {"type": None, "details": ""}
    
    def _split_responses(self, response_text):
        """Claudeの応答から返信を抽出"""
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