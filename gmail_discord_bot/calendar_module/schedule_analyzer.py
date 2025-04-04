import datetime
import pytz
import re
from ..utils.logger import setup_logger
from .calendar_client import CalendarClient
from ..config import config

logger = setup_logger(__name__)

class ScheduleAnalyzer:
    def __init__(self, calendar_client=None):
        self.calendar_client = calendar_client or CalendarClient()
        self.jst = pytz.timezone('Asia/Tokyo')
        self.settings = config.get_email_settings()
    
    def analyze_date_suggestions(self, email_analysis, available_slots, date_suggestions=None):
        """
        メール分析から日程候補を抽出し、利用可能なスロットと照合して最適な日程を提案する
        
        Args:
            email_analysis (str): メール分析結果のテキスト
            available_slots (list): 利用可能な時間枠のリスト
            date_suggestions (list, optional): LLM01から抽出された日程候補のリスト
        
        Returns:
            dict: 提案日程の情報
        """
        try:
            logger.info("メール分析から日程候補を抽出して最適な日程を提案します")
            
            # 現在時刻（JST）
            now = datetime.datetime.now(self.jst)
            
            # 日程候補を取得
            suggested_dates = []
            
            # XMLタグから抽出された日程候補がある場合はそれを優先
            if date_suggestions and len(date_suggestions) > 0:
                suggested_dates = date_suggestions
                logger.info(f"XMLタグから抽出された日程候補: {suggested_dates}")
            else:
                # XMLタグがない場合は正規表現で抽出
                suggested_dates = self._extract_date_suggestions(email_analysis)
                logger.info(f"正規表現で抽出された日程候補: {suggested_dates}")
            
            # 日程候補がある場合
            if suggested_dates:
                # 日程候補と利用可能なスロットを照合
                matched_slots = []
                for date_str in suggested_dates:
                    for slot in available_slots:
                        # 日付文字列が利用可能なスロットに含まれているか確認
                        if self._is_date_in_slot(date_str, slot):
                            matched_slots.append(slot)
                
                # マッチするスロットがある場合は最も直近のものを選択
                if matched_slots:
                    matched_slots.sort()  # 日付順にソート
                    selected_slot = matched_slots[0]
                    logger.info(f"提案された日程と一致するスロットが見つかりました: {selected_slot}")
                    
                    return {
                        "has_match": True,
                        "selected_slot": selected_slot,
                        "alternative_slots": [],
                        "message": f"提案された日程の中で利用可能なスロットが見つかりました: {selected_slot}"
                    }
                
                # マッチするスロットがない場合は代替案を提案
                else:
                    # 提案日以外の最も近い日程を3つ選択
                    alternative_slots = self._find_alternative_slots(suggested_dates, available_slots, now)
                    logger.info(f"代替スロットを提案します: {alternative_slots}")
                    
                    return {
                        "has_match": False,
                        "selected_slot": None,
                        "alternative_slots": alternative_slots,
                        "message": "提案された日程では予定が埋まっています。代わりに以下の日程はいかがでしょうか。"
                    }
            
            # 日程候補がない場合は最も直近の利用可能なスロットを提案
            else:
                if available_slots:
                    selected_slot = available_slots[0]  # 最も直近のスロット
                    logger.info(f"日程候補がないため、最も直近のスロットを提案します: {selected_slot}")
                    
                    return {
                        "has_match": True,
                        "selected_slot": selected_slot,
                        "alternative_slots": [],
                        "message": f"最も直近の利用可能な日程を提案します: {selected_slot}"
                    }
                else:
                    logger.warning("利用可能なスロットが見つかりませんでした")
                    return {
                        "has_match": False,
                        "selected_slot": None,
                        "alternative_slots": [],
                        "message": "利用可能な日程が見つかりませんでした。"
                    }
        
        except Exception as e:
            logger.error(f"日程分析エラー: {e}")
            return {
                "has_match": False,
                "selected_slot": None,
                "alternative_slots": [],
                "message": "日程分析中にエラーが発生しました。"
            }
    
    def _extract_date_suggestions(self, email_analysis):
        """メール分析から日程候補を抽出する"""
        # 日付パターンを検出する正規表現
        # 例: 「2023年5月10日」「5/10」「5月10日(水)」など
        date_patterns = [
            r'\d{4}年\d{1,2}月\d{1,2}日',  # 2023年5月10日
            r'\d{1,2}月\d{1,2}日(?:\([月火水木金土日]\))?',  # 5月10日 or 5月10日(水)
            r'\d{1,2}/\d{1,2}(?:\([月火水木金土日]\))?',  # 5/10 or 5/10(水)
        ]
        
        # 時間パターンを検出する正規表現
        # 例: 「14:00」「14時」「午後2時」など
        time_patterns = [
            r'\d{1,2}:\d{2}(?:-\d{1,2}:\d{2})?',  # 14:00 or 14:00-15:00
            r'\d{1,2}時(?:\d{1,2}分)?(?:-\d{1,2}時(?:\d{1,2}分)?)?',  # 14時 or 14時30分 or 14時-15時
            r'午前\d{1,2}時(?:\d{1,2}分)?(?:-午前\d{1,2}時(?:\d{1,2}分)?)?',  # 午前10時 or 午前10時30分
            r'午後\d{1,2}時(?:\d{1,2}分)?(?:-午後\d{1,2}時(?:\d{1,2}分)?)?',  # 午後2時 or 午後2時30分
        ]
        
        # 日付と時間の組み合わせを検出
        suggested_dates = []
        
        # 日付パターンを検索
        for pattern in date_patterns:
            matches = re.findall(pattern, email_analysis)
            suggested_dates.extend(matches)
        
        # 時間パターンを検索して日付と組み合わせる
        time_matches = []
        for pattern in time_patterns:
            matches = re.findall(pattern, email_analysis)
            time_matches.extend(matches)
        
        # 日付と時間の組み合わせを作成
        combined_dates = []
        for date in suggested_dates:
            for time in time_matches:
                combined_dates.append(f"{date} {time}")
        
        # 組み合わせがある場合は追加
        if combined_dates:
            suggested_dates.extend(combined_dates)
        
        return suggested_dates
    
    def _is_date_in_slot(self, date_str, slot):
        """日付文字列が利用可能なスロットに含まれているか確認"""
        # 日付文字列から年、月、日を抽出
        year_match = re.search(r'(\d{4})年', date_str)
        month_match = re.search(r'(\d{1,2})月', date_str)
        day_match = re.search(r'(\d{1,2})日', date_str)
        
        # スラッシュ形式の日付も対応
        if not month_match:
            slash_match = re.search(r'(\d{1,2})/(\d{1,2})', date_str)
            if slash_match:
                month_match = slash_match.group(1)
                day_match = slash_match.group(2)
        
        # 月と日が抽出できた場合
        if month_match and day_match:
            # スロットから年、月、日を抽出
            slot_year_match = re.search(r'(\d{4})年', slot)
            slot_month_match = re.search(r'(\d{1,2})月', slot)
            slot_day_match = re.search(r'(\d{1,2})日', slot)
            
            if slot_year_match and slot_month_match and slot_day_match:
                # 年が指定されていない場合はスロットの年を使用
                year = year_match.group(1) if year_match else slot_year_match.group(1)
                
                # 月と日を比較
                if isinstance(month_match, str):
                    month = month_match
                else:
                    month = month_match.group(1)
                    
                if isinstance(day_match, str):
                    day = day_match
                else:
                    day = day_match.group(1)
                
                slot_month = slot_month_match.group(1)
                slot_day = slot_day_match.group(1)
                
                # 月と日が一致するか確認
                if month == slot_month and day == slot_day:
                    # 時間も確認（指定されている場合）
                    time_match = re.search(r'(\d{1,2})[:時](\d{0,2})', date_str)
                    slot_time_match = re.search(r'(\d{1,2}):(\d{2})-', slot)
                    
                    if time_match and slot_time_match:
                        hour = time_match.group(1)
                        minute = time_match.group(2) or '00'
                        slot_hour = slot_time_match.group(1)
                        slot_minute = slot_time_match.group(2)
                        
                        # 午後の場合は12を加算
                        if '午後' in date_str and int(hour) < 12:
                            hour = str(int(hour) + 12)
                        
                        # 時間が一致または近いか確認（30分以内）
                        time_diff = abs(int(hour) * 60 + int(minute) - (int(slot_hour) * 60 + int(slot_minute)))
                        if time_diff <= 30:
                            return True
                    else:
                        # 時間が指定されていない場合は日付のみで一致とみなす
                        return True
        
        # 日付文字列がスロットに含まれているか単純に確認
        date_parts = date_str.split()
        if len(date_parts) > 0:
            date_only = date_parts[0]
            if date_only in slot:
                return True
        
        return False
    
    def _find_alternative_slots(self, suggested_dates, available_slots, now, max_alternatives=3):
        """提案日以外の最も近い日程を選択"""
        # 提案された日付を日付オブジェクトに変換
        suggested_date_objs = []
        for date_str in suggested_dates:
            try:
                # 年月日を抽出
                year_match = re.search(r'(\d{4})年', date_str)
                month_match = re.search(r'(\d{1,2})月', date_str)
                day_match = re.search(r'(\d{1,2})日', date_str)
                
                # スラッシュ形式の日付も対応
                if not month_match:
                    slash_match = re.search(r'(\d{1,2})/(\d{1,2})', date_str)
                    if slash_match:
                        month = int(slash_match.group(1))
                        day = int(slash_match.group(2))
                    else:
                        continue
                else:
                    month = int(month_match.group(1))
                    day = int(day_match.group(1))
                
                # 年が指定されていない場合は現在の年を使用
                year = int(year_match.group(1)) if year_match else now.year
                
                # 日付オブジェクトを作成
                date_obj = datetime.date(year, month, day)
                suggested_date_objs.append(date_obj)
            except (ValueError, AttributeError):
                continue
        
        # 利用可能なスロットを日付オブジェクトに変換
        available_date_objs = []
        for slot in available_slots:
            try:
                # 年月日を抽出
                slot_match = re.match(r'(\d{4})年(\d{1,2})月(\d{1,2})日', slot)
                if slot_match:
                    year = int(slot_match.group(1))
                    month = int(slot_match.group(2))
                    day = int(slot_match.group(3))
                    
                    # 日付オブジェクトを作成
                    date_obj = datetime.date(year, month, day)
                    available_date_objs.append((date_obj, slot))
            except (ValueError, AttributeError):
                continue
        
        # 提案日以外のスロットをフィルタリング
        filtered_slots = []
        for date_obj, slot in available_date_objs:
            if not any(date_obj == suggested_date for suggested_date in suggested_date_objs):
                filtered_slots.append((date_obj, slot))
        
        # 現在日時からの差分でソート
        filtered_slots.sort(key=lambda x: abs((x[0] - now.date()).days))
        
        # 最も近い日程を最大3つ選択
        alternative_slots = [slot for _, slot in filtered_slots[:max_alternatives]]
        
        return alternative_slots
    
    def get_available_slots(self, days=None, working_hours=None, duration_minutes=None):
        """利用可能な時間枠を取得"""
        try:
            # 設定ファイルから値を取得（引数で上書き可能）
            calendar_settings = self.settings.get("calendar", {})
            days = days or calendar_settings.get("days", 30)
            
            working_hours_settings = calendar_settings.get("working_hours", {})
            start_hour = working_hours_settings.get("start", 18)
            end_hour = working_hours_settings.get("end", 23)
            working_hours = working_hours or (start_hour, end_hour)
            
            duration_minutes = duration_minutes or calendar_settings.get("duration_minutes", 60)
            skip_weekends = calendar_settings.get("skip_weekends", True)
            
            # 現在時刻（JST）
            now = datetime.datetime.now(self.jst)
            
            # 検索期間の設定
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = (start_date + datetime.timedelta(days=days)).replace(hour=23, minute=59, second=59)
            
            # UTC形式に変換
            time_min = start_date.astimezone(pytz.UTC).isoformat()
            time_max = end_date.astimezone(pytz.UTC).isoformat()
            
            # 予定を取得
            events = self.calendar_client.get_events(
                time_min=time_min,
                time_max=time_max,
                max_results=100
            )
            
            # 予定のある時間帯をリストアップ
            busy_slots = []
            for event in events:
                # 終日イベントの場合
                if 'date' in event.get('start', {}):
                    start_date_str = event['start']['date']
                    end_date_str = event['end']['date']
                    start_dt = datetime.datetime.fromisoformat(start_date_str)
                    end_dt = datetime.datetime.fromisoformat(end_date_str)
                    
                    # 終日イベントは営業時間全体を埋める
                    current_date = start_dt
                    while current_date < end_dt:
                        busy_slots.append((
                            self.jst.localize(datetime.datetime.combine(current_date, datetime.time(working_hours[0], 0))),
                            self.jst.localize(datetime.datetime.combine(current_date, datetime.time(working_hours[1], 0)))
                        ))
                        current_date += datetime.timedelta(days=1)
                
                # 通常のイベントの場合
                elif 'dateTime' in event.get('start', {}) and 'dateTime' in event.get('end', {}):
                    start_dt = datetime.datetime.fromisoformat(event['start']['dateTime'].replace('Z', '+00:00'))
                    end_dt = datetime.datetime.fromisoformat(event['end']['dateTime'].replace('Z', '+00:00'))
                    
                    # JSTに変換
                    start_dt = start_dt.astimezone(self.jst)
                    end_dt = end_dt.astimezone(self.jst)
                    
                    busy_slots.append((start_dt, end_dt))
            
            # 利用可能な時間枠を生成
            available_slots = []
            current_date = start_date
            
            # 指定日数分ループ
            for day in range(days):
                current_date = start_date + datetime.timedelta(days=day)
                
                # 土日はスキップ（設定ファイルで制御可能）
                if skip_weekends and current_date.weekday() >= 5:  # 5=土曜日, 6=日曜日
                    continue
                
                # 営業時間内で30分ごとにスロットを生成
                for hour in range(working_hours[0], working_hours[1]):
                    for minute in [0, 30]:  # 30分単位でスロットを生成
                        # 最後の時間帯で、スロットが営業時間を超える場合はスキップ
                        if hour == working_hours[1] - 1 and minute + duration_minutes > 60:
                            continue
                        
                        slot_start = self.jst.localize(datetime.datetime.combine(
                            current_date.date(), datetime.time(hour, minute)
                        ))
                        
                        # 現在時刻より前のスロットはスキップ
                        if slot_start <= now:
                            continue
                        
                        slot_end = slot_start + datetime.timedelta(minutes=duration_minutes)
                        
                        # 予定と重複しないかチェック
                        is_available = True
                        for busy_start, busy_end in busy_slots:
                            # スロットが予定と重複する場合
                            if (slot_start < busy_end and slot_end > busy_start):
                                is_available = False
                                break
                        
                        if is_available:
                            # フォーマット: "2023年1月15日(月) 14:00-15:00"
                            weekday_names = ["月", "火", "水", "木", "金", "土", "日"]
                            weekday = weekday_names[slot_start.weekday()]
                            
                            slot_str = f"{slot_start.year}年{slot_start.month}月{slot_start.day}日({weekday}) "
                            slot_str += f"{slot_start.hour:02d}:{slot_start.minute:02d}-"
                            slot_str += f"{slot_end.hour:02d}:{slot_end.minute:02d}"
                            
                            available_slots.append(slot_str)
            
            logger.info(f"{len(available_slots)}件の利用可能なスロットを見つけました")
            return available_slots
        
        except Exception as e:
            logger.error(f"スケジュール分析エラー: {e}")
            # エラー時は仮のスロットを返す（18:00-23:00の時間帯に合わせて）
            return [
                f"{(now + datetime.timedelta(days=i)).strftime('%Y年%m月%d日')}の夜（18:00-20:00）",
                f"{(now + datetime.timedelta(days=i+1)).strftime('%Y年%m月%d日')}の夜（20:00-22:00）"
            ]
    
    # 未使用のメソッドを削除