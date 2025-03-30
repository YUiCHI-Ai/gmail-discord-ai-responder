import logging
import os
from pathlib import Path

def setup_logger(name):
    """ロガーのセットアップ"""
    # ログレベルの設定
    log_level = os.environ.get('LOG_LEVEL', 'INFO')
    
    # ロガーの作成
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level))
    
    # 既にハンドラが設定されている場合は追加しない
    if not logger.handlers:
        # コンソールハンドラの設定
        console_handler = logging.StreamHandler()
        console_handler.setLevel(getattr(logging, log_level))
        
        # フォーマットの設定
        formatter = logging.Formatter(
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