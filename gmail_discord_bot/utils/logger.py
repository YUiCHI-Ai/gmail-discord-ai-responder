import logging
import os
import functools
from pathlib import Path
from enum import Enum, auto

class FlowStep(Enum):
    """マーメード図に合わせた処理フローのステップ"""
    RECEIVE_EMAIL = auto()           # Gmailでメール受信
    CHECK_SENDER = auto()            # 送信元アドレスの確認
    EXTRACT_ADDRESS = auto()         # 送信者情報から宛名抽出
    TRANSFER_TO_DISCORD = auto()     # Discordチャンネルへ転送
    CHECK_SCHEDULE = auto()          # 日程調整関連か判定
    GET_CALENDAR = auto()            # Googleカレンダーからスケジュール取得
    GENERATE_PROMPT = auto()         # プロンプト生成
    ANALYZE_EMAIL = auto()           # AIでメール分析
    GENERATE_RESPONSE = auto()       # AI APIで返信生成
    DISPLAY_RESPONSE = auto()        # Discordに返信を表示
    EDIT_RESPONSE = auto()           # ユーザーによる編集
    SEND_RESPONSE = auto()           # ユーザーによる送信
    SEND_EMAIL = auto()              # Gmailで返信メール送信
    REQUEST_APPROVAL = auto()        # 承認リクエスト
    REQUEST_CONFIRMATION = auto()    # 確認リクエスト
    REQUEST_OTHER_INFO = auto()      # その他情報リクエスト
    COMPLETE = auto()                # 処理完了

class FlowFormatter(logging.Formatter):
    """処理フローを視覚的に表現するためのフォーマッター"""
    
    def format(self, record):
        # オリジナルのフォーマットを適用
        result = super().format(record)
        
        # フロー情報が含まれている場合は特別な処理を行う
        if hasattr(record, 'flow_step'):
            # ステップ名を取得
            step_name = record.flow_step.name
            
            # ステップ番号を取得
            step_num = record.flow_step.value
            
            # フォーマット
            prefix = f"[FLOW-{step_num}] {step_name}"
            
            # メッセージを結合
            result = f"{prefix}: {record.getMessage()}"
            
            # 元のフォーマットから時間とレベルだけ抽出して先頭に付ける
            time_level = super().format(record).split(' - ')[0:2]
            time_level_str = ' - '.join(time_level)
            result = f"{time_level_str} - {result}"
            
        return result

class FlowLogger(logging.Logger):
    """処理フローを記録するための拡張ロガー"""
    
    def __init__(self, name, level=logging.NOTSET):
        super().__init__(name, level)
    
    def log_flow(self, step: FlowStep, message: str) -> None:
        """処理フローのステップを記録"""
        # ステップ情報をレコードに追加
        extra = {
            'flow_step': step
        }
        
        # ステップ情報を記録
        self.info(message, extra=extra)

def flow_step(step: FlowStep):
    """処理フローのステップを記録するデコレータ"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # ロガーを取得
            logger_name = func.__module__
            logger = logging.getLogger(logger_name)
            
            # FlowLoggerのインスタンスであればlog_flowを呼び出し
            if isinstance(logger, FlowLogger):
                logger.log_flow(step, f"{func.__name__} 開始")
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    logger.error(f"{step.name} ステップでエラーが発生: {e}")
                    raise
            else:
                # 通常のロガーの場合は単にログを出力
                logger.info(f"[{step.name}] {func.__name__} 開始")
                return func(*args, **kwargs)
        return wrapper
    return decorator

def setup_logger(name):
    """拡張ロガーのセットアップ"""
    # ログレベルの設定
    log_level = os.environ.get('LOG_LEVEL', 'INFO')
    
    # カスタムロガークラスを登録
    logging.setLoggerClass(FlowLogger)
    
    # ロガーの作成
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level))
    
    # 既にハンドラが設定されている場合は追加しない
    if not logger.handlers:
        # コンソールハンドラの設定
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, log_level))
        
        # カスタムフォーマッターの設定
        formatter = FlowFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        
        # ロガーにハンドラを追加
        logger.addHandler(console_handler)
        
        # ファイルハンドラの設定（オプション）
        log_dir = Path(__file__).parent.parent / 'logs'
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        file_handler = logging.FileHandler(log_dir / 'app.log')
        file_handler.setLevel(getattr(logging, log_level))
        file_handler.setFormatter(formatter)
        
        logger.addHandler(file_handler)
    
    return logger