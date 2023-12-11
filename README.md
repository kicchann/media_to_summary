# video_to_summary_prod

- 2023/11/28
  - 作成
- 2023/12/06
  - AudioDataのDurationをミリ秒から秒に変更
  - 15分で音声を分割
  - 0.2s以下の音声を削除
- 2023/12/11
  - 10分で音声を分割
  - 0.3s以下の音声を削除
  - GPT4からGPT3.5に切り替え
  - finish_reasonが"length"なのに切り上げてしまう問題を解消
  - whisperのprompt入れ忘れ解消
  - クライアントが入力した事前情報は、keywordにしてpromptへ流すことにした
  - 音声を分割した場合は直前の音声情報もkeywordにしてpromptへ流すことにした

## 概要

`video_to_summary_prod` は指定されたディレクトリを監視して，動画ファイルが投稿されたら音声データの抽出・文字起こしをした上で，要約を行うモジュール．作者はMS Forms上に動画と要約の条件を入力するフォームを作成して，
このモジュールで動画を変換した．ファイルの移動や作成にはPowerAutomateを使用している．  
モジュールでは，

- 動画からの音声抽出（ffmpeg）
- 音声の分割（pydub）
- 分割された音声の文字起こし（whisper）
- 文字起こしの要約（GPT）

を行う．

## インストール

To install `video_to_summary_prod`, follow these steps:

1. Clone the repository: `git clone https://github.com/yourusername/video_to_summary_prod.git`
2. Navigate to the project directory: `cd video_to_summary_prod`
3. Install the required packages: `pip install -r requirements.txt`

## 使い方

以下の手順を踏みます．

1. 管理するフォルダを準備
   ```directory
    root_dir
    ├── response ← MS Formsの回答保管
    ├── video ← 動画保管
    └── result ← 要約結果保管
   ```
2. 環境変数としてOPENAI_API_KEYと，OPENAI_API_WHISPER_KEYを準備．  
   （なお，OPENAI_API_WHISPER_KEYはfaster-whisperを使う場合は不要）
3. MS Formsでフォームを準備．
4. モジュール立ち上げ．
    ```bash
    python main.py --root_dir root_dir --num_workers n

    root_dirは1.で準備したディレクトリ
    nは並列処理の数(defaultは3)
    ```

