import datetime
import pytz
from ..utils.logger import setup_logger
from .calendar_client import CalendarClient

logger = setup_logger(__name__)

class ScheduleAnalyzer:
    def __init__(self, calendar_client=None):
        self.calendar_client = calendar_client or CalendarClient()
        self.jst = pytz.timezone('Asia/Tokyo')
    
    def get_available_slots(self, days=7, working_hours=(9, 18), duration_minutes=60):
        """利用可能な時間枠を取得"""
        try:
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
                
                # 土日はスキップ
                if current_date.weekday() >= 5:  # 5=土曜日, 6=日曜日
                    continue
                
                # 営業時間内で1時間ごとにスロットを生成
                for hour in range(working_hours[0], working_hours[1] - (duration_minutes // 60)):
                    for minute in [0, 30]:  # 30分単位でスロットを生成
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
            # エラー時は仮のスロットを返す
            return [
                f"{(now + datetime.timedelta(days=i)).strftime('%Y年%m月%d日')}の午後",
                f"{(now + datetime.timedelta(days=i+1)).strftime('%Y年%m月%d日')}の午前"
            ]
    
    def analyze_email_for_dates(self, email_body):
        """メール本文から日付に関する情報を抽出"""
        # 実装例：正規表現で日付を抽出する
        # この部分は必要に応じて拡張可能
        return []