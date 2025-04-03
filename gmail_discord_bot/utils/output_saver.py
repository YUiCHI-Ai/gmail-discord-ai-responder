import os
import json
import datetime
from pathlib import Path

class OutputSaver:
    """LLMの出力結果をテキストファイルとして保存するユーティリティクラス"""
    
    def __init__(self, base_dir=None):
        """
        初期化
        
        Args:
            base_dir: 保存先ディレクトリのパス。指定しない場合はデフォルトのログディレクトリを使用
        """
        if base_dir is None:
            # デフォルトのログディレクトリ
            self.base_dir = Path(__file__).parent.parent / 'logs' / 'llm_outputs'
        else:
            self.base_dir = Path(base_dir)
        
        # ディレクトリが存在しない場合は作成
        os.makedirs(self.base_dir, exist_ok=True)
    
    def save_analysis(self, email_id, analysis_text, analysis_result, provider="unknown"):
        """
        メール分析結果を保存
        
        Args:
            email_id: メールID
            analysis_text: LLMの生の出力テキスト
            analysis_result: 構造化された分析結果
            provider: AIプロバイダー名（"claude"または"chatgpt"など）
        
        Returns:
            保存したファイルのパス
        """
        # 現在時刻を取得
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # ファイル名を生成
        filename = f"{timestamp}_{provider}_analysis_{email_id}.txt"
        filepath = self.base_dir / filename
        
        # 内容を作成
        content = f"# メール分析結果 (ID: {email_id}, Provider: {provider})\n"
        content += f"# 保存日時: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        content += "## 生の出力テキスト\n"
        content += f"{analysis_text}\n\n"
        content += "## 構造化された分析結果\n"
        content += json.dumps(analysis_result, ensure_ascii=False, indent=2)
        
        # ファイルに保存
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        
        return filepath
    
    def save_responses(self, email_id, response_text, responses, provider="unknown", additional_info=None):
        """
        返信候補を保存
        
        Args:
            email_id: メールID
            response_text: LLMの生の出力テキスト
            responses: 抽出された返信候補のリスト
            provider: AIプロバイダー名（"claude"または"chatgpt"など）
            additional_info: 追加情報（カレンダー情報など）
        
        Returns:
            保存したファイルのパス
        """
        # 現在時刻を取得
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # ファイル名を生成
        filename = f"{timestamp}_{provider}_responses_{email_id}.txt"
        filepath = self.base_dir / filename
        
        # 内容を作成
        content = f"# メール返信候補 (ID: {email_id}, Provider: {provider})\n"
        content += f"# 保存日時: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # 追加情報がある場合は記載
        if additional_info:
            content += "## 追加情報\n"
            if isinstance(additional_info, dict):
                content += json.dumps(additional_info, ensure_ascii=False, indent=2)
            else:
                content += str(additional_info)
            content += "\n\n"
        
        content += "## 生の出力テキスト\n"
        content += f"{response_text}\n\n"
        
        content += "## 抽出された返信候補\n"
        for i, response in enumerate(responses, 1):
            content += f"### 候補 {i}\n"
            content += f"{response}\n\n"
        
        # ファイルに保存
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        
        return filepath
    
    def save_email_content(self, email_id, email_data):
        """
        元のメール内容を保存
        
        Args:
            email_id: メールID
            email_data: メールデータ
        
        Returns:
            保存したファイルのパス
        """
        # 現在時刻を取得
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # ファイル名を生成
        filename = f"{timestamp}_original_email_{email_id}.txt"
        filepath = self.base_dir / filename
        
        # 内容を作成
        content = f"# 元のメール内容 (ID: {email_id})\n"
        content += f"# 保存日時: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        content += f"## 件名\n{email_data.get('subject', 'N/A')}\n\n"
        content += f"## 送信者\n{email_data.get('sender', 'N/A')}\n\n"
        content += f"## 本文\n{email_data.get('body', 'N/A')}\n\n"
        
        # 添付ファイル情報があれば追加
        if 'attachments' in email_data and email_data['attachments']:
            content += "## 添付ファイル\n"
            for attachment in email_data['attachments']:
                content += f"- {attachment.get('filename', 'Unknown')}\n"
        
        # ファイルに保存
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        
        return filepath
    
    def get_output_files(self, email_id=None, provider=None, output_type=None):
        """
        保存されたファイルの一覧を取得
        
        Args:
            email_id: フィルタリングするメールID（オプション）
            provider: フィルタリングするプロバイダー（オプション）
            output_type: フィルタリングする出力タイプ（"analysis"、"responses"、"original_email"のいずれか、オプション）
        
        Returns:
            条件に一致するファイルのパスのリスト
        """
        files = []
        
        for file in self.base_dir.glob("*.txt"):
            filename = file.name
            
            # フィルタリング条件に一致するかチェック
            if email_id and email_id not in filename:
                continue
            
            if provider and f"_{provider}_" not in filename:
                continue
            
            if output_type:
                if output_type == "analysis" and "_analysis_" not in filename:
                    continue
                if output_type == "responses" and "_responses_" not in filename:
                    continue
                if output_type == "original_email" and "_original_email_" not in filename:
                    continue
            
            files.append(file)
        
        # 日時順にソート
        files.sort(reverse=True)
        
        return files