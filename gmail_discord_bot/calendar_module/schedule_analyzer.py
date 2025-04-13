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
        （完全に新しいアプローチ）
        
        Args:
            email_analysis (str): メール分析結果のテキスト
            available_slots (list): 利用可能な時間枠のリスト
            date_suggestions (list, optional): LLM01から抽出された日程候補のリスト
        
        Returns:
            dict: 提案日程の情報
        """
        try:
            logger.info("【新アプローチ】メール分析から日程候補を抽出して最適な日程を提案します")
            
            # 現在時刻（JST）
            now = datetime.datetime.now(self.jst)
            
            # 1. 日程候補の取得と正規化
            suggested_dates = []
            
            # XMLタグから抽出された日程候補がある場合はそれを優先
            if date_suggestions and len(date_suggestions) > 0:
                suggested_dates = date_suggestions
                logger.info(f"XMLタグから抽出された日程候補: {suggested_dates}")
            else:
                # XMLタグがない場合は正規表現で抽出
                suggested_dates = self._extract_date_suggestions(email_analysis)
                logger.info(f"正規表現で抽出された日程候補: {suggested_dates}")
            
            # 日程候補がない場合
            if not suggested_dates:
                if available_slots:
                    # 年を削除したスロット
                    clean_slot = self._remove_year_from_slot(available_slots[0])
                    logger.info(f"日程候補がないため、最も直近のスロットを提案します: {clean_slot}")
                    
                    return {
                        "has_match": True,
                        "selected_slot": clean_slot,
                        "alternative_slots": [],
                        "message": f"最も直近の利用可能な日程を提案します: {clean_slot}"
                    }
                else:
                    logger.warning("利用可能なスロットが見つかりませんでした")
                    return {
                        "has_match": False,
                        "selected_slot": None,
                        "alternative_slots": [],
                        "message": "利用可能な日程が見つかりませんでした。"
                    }
            
            # 2. 日程候補を構造化データに変換
            structured_suggestions = []
            for date_str in suggested_dates:
                parsed = self._parse_date_suggestion(date_str)
                if parsed:
                    structured_suggestions.append(parsed)
            
            logger.info(f"構造化された日程候補: {structured_suggestions}")
            
            # 3. 利用可能なスロットを構造化データに変換
            structured_slots = []
            for slot in available_slots:
                parsed = self._parse_available_slot(slot)
                if parsed:
                    structured_slots.append(parsed)
            
            # 4. 構造化データ同士を照合して最適なスロットを見つける
            best_matches = []
            for suggestion in structured_suggestions:
                for slot in structured_slots:
                    match_score = self._calculate_match_score(suggestion, slot)
                    if match_score > 0:
                        best_matches.append({
                            "slot": slot["original"],
                            "clean_slot": self._remove_year_from_slot(slot["original"]),
                            "score": match_score,
                            "suggestion": suggestion["original"]
                        })
            
            # スコアでソート（高いスコア順）
            best_matches.sort(key=lambda x: x["score"], reverse=True)
            logger.info(f"マッチングスコア上位: {best_matches[:3]}")
            
            # 5. 結果の生成
            if best_matches:
                # 最適なスロットを選択
                best_match = best_matches[0]
                selected_slot = best_match["clean_slot"]
                
                # 日程候補が1つだけの場合は代替スロットを提案しない
                if len(suggested_dates) == 1:
                    logger.info(f"相手から1つの日程のみ指定されており、その日程が空いています: {selected_slot}")
                    alternative_slots = []
                else:
                    # 代替スロットを選択（最適なスロットと同じ日付のものは除外）
                    alternative_slots = []
                    best_date = self._extract_date_from_slot(best_match["slot"])
                    
                    for match in best_matches[1:4]:  # 2位〜4位のマッチを確認
                        match_date = self._extract_date_from_slot(match["slot"])
                        if match_date != best_date:  # 最適なスロットと異なる日付のみ
                            alternative_slots.append(match["clean_slot"])
                    
                    # 代替スロットが足りない場合は、他の利用可能なスロットから補完
                    if len(alternative_slots) < 2:
                        # 日付でグループ化して、各日付から1つずつ選ぶ
                        date_groups = {}
                        for slot in structured_slots:
                            slot_date = self._extract_date_from_slot(slot["original"])
                            if slot_date != best_date and slot_date not in [self._extract_date_from_slot(alt) for alt in alternative_slots]:
                                if slot_date not in date_groups:
                                    date_groups[slot_date] = []
                                date_groups[slot_date].append(self._remove_year_from_slot(slot["original"]))
                        
                        # 各日付グループから1つずつ選択
                        for date, slots in sorted(date_groups.items())[:3-len(alternative_slots)]:
                            alternative_slots.append(slots[0])
                    
                    # 最大3つまで
                    alternative_slots = alternative_slots[:3]
                
                logger.info(f"最適なスロット: {selected_slot}, 代替スロット: {alternative_slots}")
                
                # メッセージを生成（年を含まない）
                if len(suggested_dates) == 1 and not alternative_slots:
                    message = f"ご希望の日程（{selected_slot}）で承りました。"
                else:
                    message = f"提案された日程の中で利用可能なスロットが見つかりました: {selected_slot}"
                
                return {
                    "has_match": True,
                    "selected_slot": selected_slot,
                    "alternative_slots": alternative_slots,
                    "message": message
                }
            else:
                # マッチするスロットがない場合は代替案を提案
                # 日付の近さと時間帯の類似性でスロットを選択
                alternative_slots = self._select_alternative_slots(structured_suggestions, structured_slots, now)
                clean_alternatives = [self._remove_year_from_slot(slot) for slot in alternative_slots]
                
                logger.info(f"代替スロットを提案します: {clean_alternatives}")
                
                return {
                    "has_match": False,
                    "selected_slot": None,
                    "alternative_slots": clean_alternatives,
                    "message": "提案された日程では予定が埋まっています。代わりに以下の日程はいかがでしょうか。"
                }
        
        except Exception as e:
            logger.error(f"日程分析エラー: {e}", exc_info=True)
            return {
                "has_match": False,
                "selected_slot": None,
                "alternative_slots": [],
                "message": "日程分析中にエラーが発生しました。"
            }
    
    def _parse_date_suggestion(self, date_str):
        """日程候補を構造化データに変換"""
        try:
            # 年月日を抽出
            year = None
            month = None
            day = None
            
            # 年の抽出
            year_match = re.search(r'(\d{4})年', date_str)
            if year_match:
                year = int(year_match.group(1))
            
            # 月日の抽出（複数パターン対応）
            month_day_patterns = [
                (r'(\d{1,2})月(\d{1,2})日', lambda m: (int(m.group(1)), int(m.group(2)))),  # 5月10日
                (r'(\d{1,2})/(\d{1,2})', lambda m: (int(m.group(1)), int(m.group(2))))      # 5/10
            ]
            
            for pattern, extractor in month_day_patterns:
                match = re.search(pattern, date_str)
                if match:
                    month, day = extractor(match)
                    break
            
            if not month or not day:
                return None
            
            # 現在の年を使用（指定がない場合）
            if not year:
                year = datetime.datetime.now(self.jst).year
            
            # 時間範囲の抽出
            start_hour = None
            start_minute = 0
            end_hour = None
            end_minute = 0
            
            # 時間範囲パターン（例: 21:00-23:00, 21:00〜23:00）
            time_range_patterns = [
                r'(\d{1,2}):(\d{2})[-〜~](\d{1,2}):(\d{2})',  # 21:00-23:00
                r'(\d{1,2})時(\d{0,2})分?[-〜~](\d{1,2})時(\d{0,2})分?'  # 21時-23時, 21時30分〜23時
            ]
            
            for pattern in time_range_patterns:
                match = re.search(pattern, date_str)
                if match:
                    start_hour = int(match.group(1))
                    start_minute = int(match.group(2) or 0)
                    end_hour = int(match.group(3))
                    end_minute = int(match.group(4) or 0)
                    
                    # 午前/午後の処理
                    if '午後' in date_str and start_hour < 12:
                        start_hour += 12
                    if '午後' in date_str and end_hour < 12:
                        end_hour += 12
                    
                    break
            
            # 単一時間パターン（例: 21:00, 21時）
            if not start_hour:
                single_time_patterns = [
                    r'(\d{1,2}):(\d{2})',  # 21:00
                    r'(\d{1,2})時(\d{0,2})分?'  # 21時, 21時30分
                ]
                
                for pattern in single_time_patterns:
                    match = re.search(pattern, date_str)
                    if match:
                        start_hour = int(match.group(1))
                        start_minute = int(match.group(2) or 0)
                        
                        # 午前/午後の処理
                        if '午後' in date_str and start_hour < 12:
                            start_hour += 12
                        
                        # 単一時間の場合は1時間後を終了時間とする
                        end_hour = start_hour + 1
                        end_minute = start_minute
                        break
            
            # 日付オブジェクトを作成
            date_obj = datetime.date(year, month, day)
            
            # 曜日を取得
            weekday = date_obj.weekday()  # 0=月曜日, 6=日曜日
            
            result = {
                "original": date_str,
                "year": year,
                "month": month,
                "day": day,
                "date": date_obj,
                "weekday": weekday,
                "has_time": start_hour is not None
            }
            
            # 時間情報がある場合
            if start_hour is not None:
                result.update({
                    "start_hour": start_hour,
                    "start_minute": start_minute,
                    "end_hour": end_hour,
                    "end_minute": end_minute,
                    "start_minutes": start_hour * 60 + start_minute,
                    "end_minutes": end_hour * 60 + end_minute
                })
            
            return result
        
        except Exception as e:
            logger.error(f"日程候補の解析エラー: {date_str}, {e}")
            return None
    
    def _parse_available_slot(self, slot):
        """利用可能なスロットを構造化データに変換"""
        try:
            # 年月日を抽出
            date_match = re.match(r'(\d{4})年(\d{1,2})月(\d{1,2})日\(([月火水木金土日])\)', slot)
            if not date_match:
                return None
            
            year = int(date_match.group(1))
            month = int(date_match.group(2))
            day = int(date_match.group(3))
            weekday_str = date_match.group(4)
            
            # 曜日を数値に変換（0=月曜日, 6=日曜日）
            weekday_map = {"月": 0, "火": 1, "水": 2, "木": 3, "金": 4, "土": 5, "日": 6}
            weekday = weekday_map.get(weekday_str, -1)
            
            # 時間範囲を抽出
            time_match = re.search(r'(\d{1,2}):(\d{2})-(\d{1,2}):(\d{2})', slot)
            if not time_match:
                return None
            
            start_hour = int(time_match.group(1))
            start_minute = int(time_match.group(2))
            end_hour = int(time_match.group(3))
            end_minute = int(time_match.group(4))
            
            # 日付オブジェクトを作成
            date_obj = datetime.date(year, month, day)
            
            return {
                "original": slot,
                "year": year,
                "month": month,
                "day": day,
                "date": date_obj,
                "weekday": weekday,
                "start_hour": start_hour,
                "start_minute": start_minute,
                "end_hour": end_hour,
                "end_minute": end_minute,
                "start_minutes": start_hour * 60 + start_minute,
                "end_minutes": end_hour * 60 + end_minute
            }
        
        except Exception as e:
            logger.error(f"利用可能なスロットの解析エラー: {slot}, {e}")
            return None
    
    def _calculate_match_score(self, suggestion, slot):
        """日程候補と利用可能なスロットのマッチングスコアを計算"""
        # 日付が一致しない場合はスコア0
        if suggestion["date"] != slot["date"]:
            return 0
        
        # 時間情報がない場合は日付のみで一致（基本スコア50）
        if not suggestion.get("has_time", False):
            return 50
        
        # 時間範囲の重なりを計算
        suggestion_start = suggestion["start_minutes"]
        suggestion_end = suggestion["end_minutes"]
        slot_start = slot["start_minutes"]
        slot_end = slot["end_minutes"]
        
        # 重なりがない場合はスコア0
        if suggestion_end <= slot_start or suggestion_start >= slot_end:
            return 0
        
        # 重なりの開始と終了
        overlap_start = max(suggestion_start, slot_start)
        overlap_end = min(suggestion_end, slot_end)
        
        # 重なりの時間（分）
        overlap_minutes = overlap_end - overlap_start
        
        # スロットの時間（分）
        slot_minutes = slot_end - slot_start
        
        # 重なり率（0.0〜1.0）
        overlap_ratio = overlap_minutes / slot_minutes
        
        # 基本スコア（最大100）
        base_score = int(overlap_ratio * 100)
        
        # 完全一致の場合はボーナス
        if suggestion_start == slot_start and suggestion_end == slot_end:
            base_score += 20
        
        # 開始時間が一致する場合もボーナス
        elif suggestion_start == slot_start:
            base_score += 10
        
        return base_score
    
    def _select_alternative_slots(self, suggestions, available_slots, now, max_alternatives=3):
        """代替スロットを選択（日付の近さと時間帯の類似性を考慮）"""
        # 提案された日程から優先時間帯を抽出
        preferred_times = []
        for suggestion in suggestions:
            if suggestion.get("has_time", False):
                preferred_times.append((
                    suggestion.get("start_hour", 0),
                    suggestion.get("end_hour", 0)
                ))
        
        # 優先時間帯がない場合はデフォルト（夜間）
        if not preferred_times:
            preferred_times = [(19, 22)]
        
        # 各スロットにスコアを付ける
        scored_slots = []
        for slot in available_slots:
            # 基本スコア: 現在日からの日数差（小さいほど良い）
            days_diff = (slot["date"] - now.date()).days
            if days_diff < 0:  # 過去の日付はスキップ
                continue
            
            date_score = max(30 - days_diff, 0)  # 最大30点
            
            # 時間帯スコア
            time_score = 0
            for start_hour, end_hour in preferred_times:
                # 時間帯の重なり
                if slot["start_hour"] <= end_hour and slot["end_hour"] >= start_hour:
                    overlap = min(slot["end_hour"], end_hour) - max(slot["start_hour"], start_hour)
                    time_score = max(time_score, overlap * 5)  # 重なりが多いほど高スコア
            
            # 曜日スコア（提案された日程と同じ曜日を優先）
            weekday_score = 0
            suggested_weekdays = [s.get("weekday", -1) for s in suggestions]
            if slot["weekday"] in suggested_weekdays:
                weekday_score = 15
            elif slot["weekday"] < 5:  # 平日
                weekday_score = 10
            else:  # 週末
                weekday_score = 5
            
            # 総合スコア
            total_score = date_score + time_score + weekday_score
            
            scored_slots.append({
                "slot": slot["original"],
                "score": total_score,
                "date": slot["date"]
            })
        
        # スコアでソート（高いスコア順）
        scored_slots.sort(key=lambda x: x["score"], reverse=True)
        
        # 日付の重複を避けて選択
        selected_dates = set()
        alternative_slots = []
        
        for slot_info in scored_slots:
            date_str = slot_info["date"].strftime("%Y-%m-%d")
            if date_str not in selected_dates:
                alternative_slots.append(slot_info["slot"])
                selected_dates.add(date_str)
                
                if len(alternative_slots) >= max_alternatives:
                    break
        
        return alternative_slots
    
    def _remove_year_from_slot(self, slot):
        """スロットから年を削除"""
        return re.sub(r'\d{4}年', '', slot).strip()
    
    def _extract_date_from_slot(self, slot):
        """スロットから日付部分を抽出（YYYY-MM-DD形式）"""
        match = re.match(r'(\d{4})年(\d{1,2})月(\d{1,2})日', slot)
        if match:
            year = match.group(1)
            month = match.group(2).zfill(2)
            day = match.group(3).zfill(2)
            return f"{year}-{month}-{day}"
        return None
    
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
            r'\d{1,2}:\d{2}[-〜~]\d{1,2}:\d{2}',  # 14:00-15:00 or 14:00〜15:00
            r'\d{1,2}時(?:\d{1,2}分)?[-〜~]\d{1,2}時(?:\d{1,2}分)?',  # 14時-15時 or 14時30分〜15時30分
            r'午前\d{1,2}時(?:\d{1,2}分)?[-〜~]午前\d{1,2}時(?:\d{1,2}分)?',  # 午前10時〜午前11時
            r'午後\d{1,2}時(?:\d{1,2}分)?[-〜~]午後\d{1,2}時(?:\d{1,2}分)?',  # 午後2時〜午後3時
            r'午前\d{1,2}時(?:\d{1,2}分)?[-〜~]午後\d{1,2}時(?:\d{1,2}分)?',  # 午前11時〜午後1時
            r'\d{1,2}:\d{2}',  # 単一時間: 14:00
            r'\d{1,2}時(?:\d{1,2}分)?',  # 単一時間: 14時 or 14時30分
            r'午前\d{1,2}時(?:\d{1,2}分)?',  # 単一時間: 午前10時
            r'午後\d{1,2}時(?:\d{1,2}分)?',  # 単一時間: 午後2時
        ]
        
        # 日付と時間の組み合わせを直接検出
        combined_patterns = []
        for date_pattern in date_patterns:
            for time_pattern in time_patterns:
                # 日付と時間が近接している場合のパターン
                combined_patterns.append(f"{date_pattern}[\\s　]*{time_pattern}")
                # 日付と時間の間に「の」や「に」などがある場合
                combined_patterns.append(f"{date_pattern}[\\s　]*[のにはで][\\s　]*{time_pattern}")
        
        # 直接組み合わせを検出
        suggested_dates = []
        for pattern in combined_patterns:
            matches = re.findall(pattern, email_analysis)
            if matches:
                suggested_dates.extend(matches)
        
        # 日付のみと時間のみも検出
        date_only_matches = []
        for pattern in date_patterns:
            matches = re.findall(pattern, email_analysis)
            date_only_matches.extend(matches)
        
        time_only_matches = []
        for pattern in time_patterns:
            matches = re.findall(pattern, email_analysis)
            time_only_matches.extend(matches)
        
        # 日付と時間が別々に記載されている場合、近接する日付と時間を組み合わせる
        if date_only_matches and time_only_matches:
            # 日付と時間の位置を特定
            date_positions = []
            for date in date_only_matches:
                pos = email_analysis.find(date)
                if pos != -1:
                    date_positions.append((date, pos))
            
            time_positions = []
            for time in time_only_matches:
                pos = email_analysis.find(time)
                if pos != -1:
                    time_positions.append((time, pos))
            
            # 各日付に対して最も近い時間を見つける
            for date, date_pos in date_positions:
                closest_time = None
                min_distance = float('inf')
                
                for time, time_pos in time_positions:
                    distance = abs(date_pos - time_pos)
                    if distance < min_distance:
                        min_distance = distance
                        closest_time = time
                
                # 距離が一定以内なら組み合わせる（例: 100文字以内）
                if min_distance < 100 and closest_time:
                    suggested_dates.append(f"{date} {closest_time}")
        
        # 日付のみの候補も追加（時間が指定されていない場合に備えて）
        suggested_dates.extend(date_only_matches)
        
        # 重複を削除
        return list(set(suggested_dates))
    
    # 未使用のメソッドを削除しました
    
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