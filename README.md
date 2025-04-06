# Gmail-Discord自動転送・返信システム

![バージョン](https://img.shields.io/badge/バージョン-1.0.0-blue)
![ライセンス](https://img.shields.io/badge/ライセンス-Apache%202.0-green)
![Python](https://img.shields.io/badge/Python-3.8%2B-yellow)

## 📋 概要

このシステムは、Gmailで受信したメールをDiscordに自動転送し、AIを活用して最適な返信文を生成するツールです。ChatGPTまたはClaude APIを利用して、メール内容を分析し、送信元情報から適切な宛名（〇〇会社 〇〇様）を自動設定します。日程調整が必要なメールの場合は、Googleカレンダーと連携して空き時間を確認し、候補日時を含む返信を提案します。

**対象ユーザー**: このシステムは、多数のビジネスメールを効率的に管理し、返信作業を自動化したいチームや個人に最適です。特に、日程調整や定型的な返信が多い業務環境での利用に適しています。

[ざっくり説明書はこちら](https://claude.site/artifacts/efd0d8d8-a30c-4d99-842b-684d509efe6d)

[開発者向けドキュメントはこちら](DEVELOPER.md)

## ✨ 主な機能

- **メール自動転送**: Gmailで受信したメールを送信元のメールアドレスごとに対応するDiscordチャンネルへ自動転送
- **宛名自動設定**: 送信元情報から会社名・担当者名を抽出し、「〇〇会社 〇〇様」の形式で自動設定
- **AI返信生成**: AIがメール内容を分析し、最適な返信文を生成
- **カレンダー連携**: 日程調整が必要な場合、Googleカレンダーと連携して空き時間を確認し、候補日時を提案
- **直感的なUI**: ボタンベースのインターフェースで返信の選択、編集、送信が可能
- **添付ファイル処理**: メールの添付ファイルとURLを抽出し、Discordで確認可能

## 🚀 クイックスタート

### 1. 必要なAPIキーの取得

このシステムを使用するには、以下のAPIキーと認証情報が必要です：

#### 1.1 Google Cloud Platform（Gmail APIとGoogleカレンダーAPI）

1. [Google Cloud Console](https://console.cloud.google.com/)にアクセスし、Googleアカウントでログイン
2. 新しいプロジェクトを作成（右上のプロジェクト選択 → 「新しいプロジェクト」）
3. プロジェクト名を入力し、「作成」をクリック
4. 作成したプロジェクトを選択
5. 左側のメニューから「APIとサービス」→「ライブラリ」を選択
6. 検索バーで「Gmail API」を検索し、選択して「有効にする」をクリック
7. 同様に「Google Calendar API」も検索して有効化
8. 左側のメニューから「APIとサービス」→「認証情報」を選択
9. 「認証情報を作成」→「OAuth クライアント ID」をクリック
10. 「同意画面を構成」をクリック
    - ユーザータイプ: 外部
    - アプリ名、ユーザーサポートメール、デベロッパーの連絡先情報を入力
    - 「保存して次へ」をクリック
11. スコープの追加画面で以下を追加:
    - `https://www.googleapis.com/auth/gmail.readonly`
    - `https://www.googleapis.com/auth/gmail.send`
    - `https://www.googleapis.com/auth/calendar.readonly`
12. テストユーザーにご自身のGmailアドレスを追加
13. 「認証情報」ページに戻り、「認証情報を作成」→「OAuth クライアント ID」を選択
    - アプリケーションの種類: デスクトップアプリ
    - 名前を入力し、「作成」をクリック
14. ダウンロードボタンをクリックして認証情報（JSON）をダウンロード
15. ダウンロードしたファイルの名前を「credentials.json」に変更し、`gmail_discord_bot/config/`ディレクトリに配置
16. 同じファイルをコピーして「calendar_credentials.json」という名前で同じディレクトリに配置

#### 1.2 Discord Bot Token

1. [Discord Developer Portal](https://discord.com/developers/applications)にアクセス
2. 「New Application」をクリックし、アプリケーション名を入力して作成
3. 左側のメニューから「Bot」を選択し、「Add Bot」をクリック
4. 「Reset Token」をクリックしてトークンを表示し、コピー（このトークンは後で`.env`ファイルに設定）
5. 「MESSAGE CONTENT INTENT」を有効化
6. 左側のメニューから「OAuth2」→「URL Generator」を選択
7. 「SCOPES」で「bot」を選択
8. 「BOT PERMISSIONS」で以下の権限を選択:
   - Read Messages/View Channels
   - Send Messages
   - Embed Links
   - Attach Files
   - Read Message History
   - Add Reactions
9. 生成されたURLをコピーしてブラウザで開き、ボットを追加したいDiscordサーバーを選択
10. サーバーのIDをコピー（後で`.env`ファイルに設定）
    - サーバーIDを取得するには、Discordの設定で開発者モードを有効にし、サーバー名を右クリックして「IDをコピー」を選択

#### 1.3 OpenAI API（ChatGPT）

1. [OpenAIのウェブサイト](https://platform.openai.com/)にアクセスし、アカウントを作成またはログイン
2. 右上のプロファイルアイコンをクリックし、「View API keys」を選択
3. 「Create new secret key」をクリックし、新しいAPIキーを生成
4. 生成されたAPIキーをコピー（このキーは後で`.env`ファイルに設定）

#### 1.4 Claude API

1. [Anthropicのウェブサイト](https://console.anthropic.com/)にアクセスし、アカウントを作成またはログイン
2. 「API Keys」セクションに移動
3. 「Create API Key」をクリックし、新しいAPIキーを生成
4. 生成されたAPIキーをコピー（このキーは後で`.env`ファイルに設定）

### 2. リポジトリのクローンとセットアップ

```bash
# リポジトリをクローン
git clone https://github.com/yourusername/gmail-discord-bot.git
cd gmail-discord-bot

# 仮想環境を作成して有効化
python -m venv venv
source venv/bin/activate  # Linuxの場合
# または
venv\Scripts\activate     # Windowsの場合

# 必要なパッケージをインストール
pip install -r requirements.txt
```

### 3. 設定ファイルの作成

#### 自動セットアップスクリプト（推奨）

設定ファイルを簡単に作成するために、自動セットアップスクリプトを用意しています。このスクリプトは対話形式で必要な情報を入力するだけで、すべての設定ファイルを自動的に生成します。

```bash
# 自動セットアップスクリプトを実行
python setup_config.py
```

スクリプトは以下の設定ファイルを生成します：
- `.env` - 環境変数設定
- `email_channel_mapping.json` - メールとDiscordチャンネルのマッピング
- `email_settings.json` - メール署名とカレンダー設定

#### 手動セットアップ（詳細設定）

自動セットアップを使用しない場合は、以下の手順で手動で設定ファイルを作成できます。

##### 3.1 環境変数の設定

`.env.example`ファイルをコピーして`.env`ファイルを作成し、必要な情報を設定します：

```bash
cp gmail_discord_bot/config/.env.example gmail_discord_bot/config/.env
```

`.env`ファイルを編集し、以下の情報を設定します：

```
# Gmail API
GMAIL_CREDENTIALS_FILE=credentials.json
GMAIL_TOKEN_FILE=token.json
GMAIL_SCOPES=https://www.googleapis.com/auth/gmail.readonly,https://www.googleapis.com/auth/gmail.send

# Discord API
DISCORD_BOT_TOKEN=your_discord_bot_token
DISCORD_GUILD_ID=your_discord_guild_id

# AI API設定
OPENAI_API_KEY=your_openai_api_key
CLAUDE_API_KEY=your_claude_api_key
DEFAULT_AI_PROVIDER=chatgpt  # 'chatgpt' または 'claude'

# OpenAIのモデル選択
OPENAI_MODEL=gpt-4o

# Claudeのモデル選択
CLAUDE_MODEL=claude-3-7-sonnet-20250219

# Google Calendar API
CALENDAR_CREDENTIALS_FILE=calendar_credentials.json
CALENDAR_TOKEN_FILE=calendar_token.json
CALENDAR_SCOPES=https://www.googleapis.com/auth/calendar.readonly

# Email Mapping
EMAIL_CHANNEL_MAPPING_FILE=email_channel_mapping.json
```

- `your_discord_bot_token`: Discord Developer Portalで取得したボットトークン
- `your_discord_guild_id`: ボットを追加したDiscordサーバーのID
- `your_openai_api_key`: OpenAIで生成したAPIキー
- `your_claude_api_key`: Anthropicで生成したAPIキー

##### 3.2 メールとチャンネルのマッピング設定

`email_channel_mapping.json.example`ファイルをコピーして`email_channel_mapping.json`ファイルを作成します：

```bash
cp gmail_discord_bot/config/email_channel_mapping.json.example gmail_discord_bot/config/email_channel_mapping.json
```

`email_channel_mapping.json`ファイルを編集し、メールアドレスとDiscordチャンネルIDのマッピングを設定します：

```json
{
  "specific.user@example.com": {
    "email": "specific.user@example.com",
    "name": "山田太郎",
    "company": "Example株式会社",
    "discord_channel_id": "1234567890123456789"
  },
  "*@example.com": {
    "email": "*@example.com",
    "name": "",
    "company": "Example株式会社",
    "discord_channel_id": "1122334455667788990"
  }
}
```

- `email`: メールアドレスまたはワイルドカードパターン
- `name`: 送信者の名前（空でも可）
- `company`: 送信者の会社名（空でも可）
- `discord_channel_id`: 対応するDiscordチャンネルのID
  - チャンネルIDを取得するには、Discordの設定で開発者モードを有効にし、チャンネル名を右クリックして「IDをコピー」を選択

##### 3.3 メール設定の確認

`email_settings.json`ファイルを確認し、必要に応じて編集します：

```json
{
  "calendar": {
    "days": 30,
    "working_hours": {
      "start": 18,
      "end": 23
    },
    "duration_minutes": 60,
    "skip_weekends": true
  },
  "signature": {
    "company_name": "あなたの会社名",
    "name": "あなたの名前",
    "email": "your.email@example.com",
    "url": "https://example.com"
  }
}
```

- `calendar`: カレンダー関連の設定
  - `days`: 何日先までの予定を確認するか
  - `working_hours`: 勤務時間（24時間形式）
  - `duration_minutes`: 会議の標準時間（分）
  - `skip_weekends`: 週末をスキップするかどうか
- `signature`: メール署名の設定
  - `company_name`: 会社名
  - `name`: 名前
  - `email`: メールアドレス
  - `url`: ウェブサイトURL

### 4. 初回実行と認証

```bash
python -m gmail_discord_bot.main
```

初回実行時は、ブラウザが自動的に開き、以下の認証が求められます：

1. **Gmail API認証**:
   - Googleアカウントにログイン
   - アプリへのアクセス許可を承認
   - 認証が完了すると`token.json`ファイルが生成されます

2. **Googleカレンダー API認証**:
   - 同様にGoogleアカウントへのアクセス許可を承認
   - 認証が完了すると`calendar_token.json`ファイルが生成されます

認証が完了すると、Discordボットが起動し、新しいメールの監視が始まります。

## 💬 使用方法

### Discordコマンド

- `!help` - ヘルプメッセージを表示
- `!status` - ボットのステータスを表示
- `!select [番号]` - 提案された返信から選択
- `!edit [番号] [新しい内容]` - 提案された返信を編集
- `!send [番号]` - 選択した返信をメールとして送信

### ボタン操作

- **返信選択ボタン**: 各返信候補に「この返信を選択」と「編集する」ボタンが表示
- **編集モーダル**: 「編集する」ボタンをクリックすると、テキスト編集用のモーダルウィンドウが表示
- **送信確認ボタン**: 「メールを送信する」ボタンをクリックすると、最終確認画面が表示

## 🔧 初期設定のトラブルシューティング

### Gmail API認証エラー

**問題**: Gmail APIの認証に失敗する

**解決策**:
1. `credentials.json`ファイルが正しく配置されているか確認
2. Google Cloud Consoleで正しいスコープが設定されているか確認
3. `token.json`ファイルを削除して再認証を試みる
4. OAuth同意画面でテストユーザーとして自分のメールアドレスが追加されているか確認

### Discord接続エラー

**問題**: Discordボットが接続できない

**解決策**:
1. `.env`ファイルのDISCORD_BOT_TOKENが正しいか確認
2. ボットに必要な権限が付与されているか確認
3. DISCORD_GUILD_IDが正しいか確認
4. MESSAGE CONTENT INTENTが有効になっているか確認

### AI API接続エラー

**問題**: AI APIに接続できない

**解決策**:
1. `.env`ファイルのOPENAI_API_KEYまたはCLAUDE_API_KEYが正しいか確認
2. DEFAULT_AI_PROVIDERが正しく設定されているか確認（`chatgpt`または`claude`）
3. インターネット接続を確認
4. APIキーの利用制限に達していないか確認

### メールチャンネルマッピングエラー

**問題**: メールがDiscordに転送されない

**解決策**:
1. `email_channel_mapping.json`ファイルが正しく設定されているか確認
2. Discordチャンネルが存在し、ボットがアクセスできるか確認
3. メールアドレスのパターンが正しいか確認

## 📄 ライセンス

Apache License 2.0

このプロジェクトは[Apache License 2.0](LICENSE)の下で提供されています。

```
Copyright 2025 YUiCHI

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

**最終更新日**: 2025年4月6日
