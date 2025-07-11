# CrowdWorks AI案件マッチングシステム

CrowdWorksのAI・機械学習関連案件を自動収集し、ユーザープロファイルとのマッチング評価を行うシステムです。

## 機能

- CrowdWorksからのAI関連案件の自動収集
- 案件情報の構造化抽出
- LLMを使用したユーザープロファイルとのマッチング評価
- 結果の保存とレポート生成

## セットアップ

1. 必要なパッケージのインストール:
```bash
pip install -r requirements.txt
```

2. Playwrightのセットアップ:
```bash
playwright install
```

3. 環境変数の設定:
`.env`ファイルを作成し、以下の内容を設定してください：
```
DEEPSEEK_API_KEY=your_api_key_here
```

## 使用方法

1. プログラムの実行:
```bash
python main.py
```

2. 出力ファイル:
- HTMLファイル: `data/html/`
- 抽出された案件情報: `data/jobs/`
- マッチング結果: `data/matches/`
- ログファイル: `logs/`

## プロジェクト構造

```
.
├── data/
│   ├── html/      # スクレイピングしたHTMLファイル
│   ├── jobs/      # 抽出された案件情報
│   └── matches/   # マッチング結果
├── logs/          # ログファイル
├── src/
│   ├── models/    # データモデル
│   ├── scrapers/  # スクレイピング機能
│   ├── processors/# データ処理機能
│   └── utils/     # ユーティリティ
├── main.py        # メインスクリプト
├── requirements.txt
└── README.md
```

## 注意事項

- スクレイピングの際は、対象サイトの利用規約を確認してください
- APIキーは適切に管理してください
- 大量のリクエストは避けてください 