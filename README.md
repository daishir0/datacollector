# datacollector

## Overview
A Python-based data collection and conversion tool that extracts content from various file formats and synchronizes it with a central database through an API. The tool supports multiple file formats including HTML, PDF, Microsoft Office documents, and plain text files, converting them into a standardized markdown format.

## Installation
1. Clone the repository:
```bash
git clone https://github.com/daishir0/datacollector
cd datacollector
```

2. Create and activate a Python virtual environment:
```bash
# Using Anaconda/Miniconda
conda create -n client python=3.10
conda activate client

# Or using venv
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure the application:
```bash
cp config.sample.yaml config.yaml
# Edit config.yaml with your settings
```

## Usage
### Data Collector
The main data collection tool supports two modes of operation:

1. Process local files:
```bash
python data_collector.py
```
This will:
- Scan configured directories for supported files
- Convert content to markdown format
- Sync with the API server

2. Process URLs:
- Add URLs to the database through the API
- The collector will automatically fetch and convert content

### File Path Collector
A utility tool to collect all file paths in a directory:
```bash
python fullpath_collector.py <directory_path>
```
This will:
- Recursively scan the specified directory
- Output paths to console and out.txt

## Notes
- Supported file formats:
  - HTML/XHTML
  - PDF
  - Microsoft Word (.doc, .docx)
  - Microsoft Excel (.xls, .xlsx)
  - Microsoft PowerPoint (.ppt, .pptx)
  - Plain text (.txt)
- Content changes are tracked using SHA-1 hashes
- Automatic backup of database and log files
- Debug mode available for detailed logging

## License
This project is licensed under the MIT License - see the LICENSE file for details.

---

# データコレクター

## 概要
様々なファイル形式からコンテンツを抽出し、APIを介して中央データベースと同期するPythonベースのデータ収集・変換ツールです。HTML、PDF、Microsoft Office文書、プレーンテキストファイルなど、多様なファイル形式に対応し、標準化されたマークダウン形式に変換します。

## インストール方法
1. レポジトリをクローン：
```bash
git clone https://github.com/daishir0/datacollector
cd datacollector
```

2. Python仮想環境の作成と有効化：
```bash
# Anaconda/Minicondaを使用する場合
conda create -n client python=3.10
conda activate client

# または venvを使用する場合
python -m venv venv
source venv/bin/activate  # Linux/Mac
# または
.\venv\Scripts\activate  # Windows
```

3. 依存パッケージのインストール：
```bash
pip install -r requirements.txt
```

4. アプリケーションの設定：
```bash
cp config.sample.yaml config.yaml
# config.yamlを編集して必要な設定を行う
```

## 使い方
### データコレクター
メインのデータ収集ツールは2つの動作モードをサポートしています：

1. ローカルファイルの処理：
```bash
python data_collector.py
```
これにより：
- 設定されたディレクトリ内のサポートされているファイルをスキャン
- コンテンツをマークダウン形式に変換
- APIサーバーと同期

2. URLの処理：
- API経由でURLをデータベースに追加
- コレクターが自動的にコンテンツを取得して変換

### ファイルパスコレクター
ディレクトリ内のすべてのファイルパスを収集するユーティリティツール：
```bash
python fullpath_collector.py <ディレクトリパス>
```
これにより：
- 指定されたディレクトリを再帰的にスキャン
- パスをコンソールとout.txtに出力

## 注意点
- 対応ファイル形式：
  - HTML/XHTML
  - PDF
  - Microsoft Word (.doc, .docx)
  - Microsoft Excel (.xls, .xlsx)
  - Microsoft PowerPoint (.ppt, .pptx)
  - プレーンテキスト (.txt)
- SHA-1ハッシュによるコンテンツ変更の追跡
- データベースとログファイルの自動バックアップ
- 詳細なログ出力が可能なデバッグモード

## ライセンス
このプロジェクトはMITライセンスの下でライセンスされています。詳細はLICENSEファイルを参照してください。