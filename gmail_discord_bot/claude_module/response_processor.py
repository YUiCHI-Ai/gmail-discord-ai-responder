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
                
                # メール分析結果から日程候補を抽出し、最適な日程を提案
                analysis_text = analysis_result.get("analysis", "")
                date_suggestions = analysis_result.get("required_info", {}).get("date_suggestions", [])
                
                # 日程候補のログ出力
                logger.info(f"【新処理】日程候補: {date_suggestions}")
                
                # 日程分析を実行
                schedule_suggestion = self.schedule_analyzer.analyze_date_suggestions(
                    analysis_text,
                    available_slots,
                    date_suggestions=date_suggestions
                )
                
                # メッセージから年を確実に削除（メッセージ自体を修正）
                if "message" in schedule_suggestion:
                    original_message = schedule_suggestion["message"]
                    clean_message = re.sub(r'\d{4}年', '', original_message)
                    schedule_suggestion["message"] = clean_message
                    logger.info(f"メッセージから年を削除: '{original_message}' -> '{clean_message}'")
                
                # 提案情報をテキストに変換
                if schedule_suggestion["has_match"]:
                    # 一致するスロットがある場合
                    selected_slot = schedule_suggestion["selected_slot"]
                    
                    if selected_slot:
                        # selected_slotは既に年が削除されているはず（念のため確認）
                        if "年" in selected_slot:
                            logger.warning(f"選択されたスロットに年が含まれています: {selected_slot}")
                            selected_slot = re.sub(r'\d{4}年', '', selected_slot).strip()
                        
                        logger.info(f"【新処理】選択されたスロット: {selected_slot}")
                        additional_info_text = f"\n\n# 日程提案\n{schedule_suggestion['message']}\n\n選択された日程: {selected_slot}"
                    else:
                        additional_info_text = f"\n\n# 日程提案\n{schedule_suggestion['message']}"
                else:
                    # 一致するスロットがない場合、代替案を提示
                    alternative_slots = schedule_suggestion["alternative_slots"]
                    
                    # alternative_slotsは既に年が削除されているはず（念のため確認）
                    clean_alternatives = []
                    for slot in alternative_slots:
                        if "年" in slot:
                            logger.warning(f"代替スロットに年が含まれています: {slot}")
                            clean_slot = re.sub(r'\d{4}年', '', slot).strip()
                            clean_alternatives.append(clean_slot)
                        else:
                            clean_alternatives.append(slot)
                    
                    logger.info(f"【新処理】代替スロット: {clean_alternatives}")
                    
                    if clean_alternatives:
                        # 最大3つの代替スロットを選択
                        selected_alternatives = clean_alternatives[:3]
                        slots_text = "\n".join([f"- {slot}" for slot in selected_alternatives])
                        additional_info_text = f"\n\n# 日程提案\n{schedule_suggestion['message']}\n\n代替日程候補:\n{slots_text}"
                        
                        # schedule_suggestionの内容も更新
                        schedule_suggestion["alternative_slots"] = clean_alternatives
                    else:
                        additional_info_text = f"\n\n# 日程提案\n{schedule_suggestion['message']}"
                
                # 追加情報を設定
                additional_info = {
                    "type": "カレンダー",
                    "schedule_suggestion": schedule_suggestion
                }
            
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
        
        # 本文を抽出
        body_pattern = r'<本文>(.*?)</本文>'
        body_match = re.search(body_pattern, text, re.DOTALL)
        email_body = body_match.group(1).strip() if body_match else ""
        
        # 日程候補を抽出（カレンダー情報の場合）
        date_suggestions = []
        date_pattern = r'<日程候補>(.*?)</日程候補>'
        date_match = re.search(date_pattern, text, re.DOTALL)
        if date_match:
            date_content = date_match.group(1)
            suggestion_pattern = r'<候補>(.*?)</候補>'
            date_suggestions = re.findall(suggestion_pattern, date_content, re.DOTALL)
            date_suggestions = [suggestion.strip() for suggestion in date_suggestions]
            
            # 時間範囲が含まれていない場合、メール本文から補完
            if email_body and date_suggestions:
                # 日付と時間範囲のパターン
                date_time_range_patterns = [
                    r'(\d{1,2}月\d{1,2}日).*?(\d{1,2}:\d{2})[-〜~](\d{1,2}:\d{2})',  # 4月10日21:00〜23:00
                    r'(\d{1,2}/\d{1,2}).*?(\d{1,2}:\d{2})[-〜~](\d{1,2}:\d{2})',     # 4/10 21:00-23:00
                ]
                
                # 各日程候補について時間範囲を確認
                enhanced_suggestions = []
                for suggestion in date_suggestions:
                    # 既に時間範囲が含まれている場合はそのまま使用
                    if re.search(r'\d{1,2}:\d{2}-\d{1,2}:\d{2}', suggestion):
                        enhanced_suggestions.append(suggestion)
                        continue
                    
                    # 日付部分を抽出
                    date_part = re.search(r'(\d{1,2}月\d{1,2}日|\d{1,2}/\d{1,2})', suggestion)
                    if not date_part:
                        enhanced_suggestions.append(suggestion)
                        continue
                    
                    date_str = date_part.group(1)
                    time_range_found = False
                    
                    # メール本文から対応する時間範囲を検索
                    for pattern in date_time_range_patterns:
                        for match in re.finditer(pattern, email_body):
                            if date_str in match.group(1) or match.group(1) in date_str:
                                start_time = match.group(2)
                                end_time = match.group(3)
                                # 時間範囲を含む形式に変換
                                enhanced_suggestion = suggestion.replace(date_str, f"{date_str} {start_time}-{end_time}")
                                enhanced_suggestions.append(enhanced_suggestion)
                                time_range_found = True
                                break
                        if time_range_found:
                            break
                    
                    # 時間範囲が見つからなかった場合は元の候補を使用
                    if not time_range_found:
                        enhanced_suggestions.append(suggestion)
                
                # 拡張された日程候補で置き換え
                if enhanced_suggestions:
                    date_suggestions = enhanced_suggestions
            
            logger.info(f"抽出された日程候補: {date_suggestions}")
        
        if type_match:
            info_type = type_match.group(1).strip()
            details = details_match.group(1).strip() if details_match else ""
            result = {
                "type": info_type,
                "details": details
            }
            
            # カレンダー情報の場合は日程候補も追加
            if info_type == "カレンダー" and date_suggestions:
                result["date_suggestions"] = date_suggestions
                
            return result
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