# Gmail-Discord自動転送・返信システム

GmailからDiscordへのメール自動転送と、ChatGPT APIを活用した返信候補生成システム。

## 機能

- Gmailで受信したメールをDiscordチャンネルへ自動転送
- 送信元情報から適切な宛名（〇〇会社 〇〇様）を自動設定
- ChatGPT APIを使用した複数の返信パターン生成
- 日程調整メールの場合はGoogleカレンダーと連携した候補日時の提案

## セットアップ

1. 必要なパッケージのインストール
   ```
   pip install -r requirements.txt
   ```

2. 各APIの認証情報を設定
   - Gmail API
   - Discord API
   - OpenAI API
   - Googleカレンダー API

3. 設定ファイルの作成
   - `.env`ファイルを`config/.env.example`を参考に作成
   - メールアドレスとDiscordチャンネルのマッピングを設定

4. 実行
   ```
   python -m gmail_discord_bot.main
   ```

## 使用方法

1. Discordボットを招待したサーバーでコマンドを使用
   - `!help` - ヘルプを表示
   - `!select [番号]` - 返信候補を選択
   - `!send [番号]` - 選択した返信を送信

## プロジェクト構造

```
gmail_discord_bot/
├── __init__.py
├── main.py                      # アプリケーションのエントリーポイント
├── gmail_module/                # Gmailとの連携を担当
│   ├── __init__.py
│   ├── gmail_client.py          # Gmail APIクライアント
│   └── email_processor.py       # メール処理ロジック
├── discord_module/              # Discordとの連携を担当
│   ├── __init__.py
│   ├── discord_bot.py           # Discordボットの実装
│   └── message_formatter.py     # メッセージフォーマット処理
├── name_module/                 # 宛名管理を担当
│   ├── __init__.py
│   ├── name_extractor.py        # メールから宛名情報を抽出
│   └── name_manager.py          # 宛名情報の管理
├── chatgpt_module/              # ChatGPT連携を担当
│   ├── __init__.py
│   ├── prompt_generator.py      # プロンプト生成
│   └── response_processor.py    # 応答処理
├── calendar_module/             # Googleカレンダー連携を担当
│   ├── __init__.py
│   ├── calendar_client.py       # カレンダーAPIクライアント
│   └── schedule_analyzer.py     # スケジュール分析
├── database/                    # データベース関連
│   ├── __init__.py
│   ├── models.py                # データモデル
│   └── db_manager.py            # DB操作
├── utils/                       # ユーティリティ関数
│   ├── __init__.py
│   ├── logger.py                # ロギング
│   └── error_handler.py         # エラーハンドリング
├── config/                      # 設定関連
│   ├── config.py                # 設定管理
│   └── .env                     # 環境変数
└── tests/                       # テスト
    ├── __init__.py
    ├── test_gmail.py
    ├── test_discord.py
    ├── test_name.py
    ├── test_chatgpt.py
    └── test_calendar.py
```

## ライセンス

MIT
