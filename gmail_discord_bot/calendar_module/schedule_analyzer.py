import datetime
import pytz
from ..utils.logger import setup_logger
from .calendar_client import CalendarClient
from ..config import config

logger = setup_logger(__name__)

class ScheduleAnalyzer:
    def __init__(self, calendar_client=None):
        self.calendar_client = calendar_client or CalendarClient()
        self.jst = pytz.timezone('Asia/Tokyo')
        self.settings = config.get_email_settings()
    
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