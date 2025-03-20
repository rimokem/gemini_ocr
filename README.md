# Gemini OCR

GeminiのAPIを活用した、PDFからのテキスト抽出ツール

## 概要

Gemini OCRは、Google Gemini 2.0 Flash APIを使用して、PDFファイルからテキストを抽出するOCRツールです。PDFをページごとに画像に変換し、それぞれをGemini AIに送信して高精度なテキスト認識を行います。日本語を含む複数言語のテキスト抽出に対応しています。

## インストール

### 前提条件

- uv
- Google AI APIキー

### セットアップ

1. リポジトリをクローン

```bash
git clone https://github.com/yourusername/gemini_ocr.git
cd gemini_ocr
```

2. `.env`ファイルを作成し、APIキーを設定

```
GOOGLE_API_KEY=your_api_key_here
```

## 使い方

基本的な使用方法:

```bash
uv run main.py your_pdf_file.pdf
```

### オプション

```
usage: main.py [-h] [-o OUTPUT] [-z ZOOM] [-f FIRST_PAGE] [-l LAST_PAGE] [-k] pdf_file

PDFファイルからテキストを抽出するOCRツール

positional arguments:
  pdf_file              OCR処理するPDFファイルのパス

options:
  -h, --help            ヘルプメッセージを表示して終了
  -o OUTPUT, --output OUTPUT
                        出力テキストファイルのパス（指定しない場合はPDFファイル名_ocr.txtになります）
  -z ZOOM, --zoom ZOOM  PDFの拡大率（デフォルト: 2.0）
  -f FIRST_PAGE, --first-page FIRST_PAGE
                        開始ページ番号（1始まり）
  -l LAST_PAGE, --last-page LAST_PAGE
                        終了ページ番号（1始まり）
  -k, --keep-images     処理後に一時画像ファイルを保持する
```

### 使用例

特定のページ範囲を処理:
```bash
uv run main.py document.pdf -f 5 -l 10
```

高解像度で処理（拡大率を上げる）:
```bash
uv run main.py document.pdf -z 3.0
```

出力ファイル名を指定:
```bash
uv run main.py document.pdf -o extracted_text.txt
```
