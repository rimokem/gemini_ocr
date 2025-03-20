"""
PDFからOCRテキストを抽出するツール

Gemini 2.0 Flash APIを使用してPDF内の文字をOCRで抽出します。
"""

import os
import sys
import argparse
import shutil
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Callable
from functools import partial

import fitz  # PyMuPDF
from google import genai
from PIL import Image
from dotenv import load_dotenv


# 定数定義
TEMP_DIR = "tmp_ocr_images"
DEFAULT_ZOOM = 2.0
DEFAULT_OUTPUT_FORMAT = "png"
GEMINI_MODEL = "gemini-2.0-flash"
DEFAULT_OCR_PROMPT = "この画像に含まれるすべてのテキストを抽出してください。改行や段落構造を維持し、完全かつ正確に文字起こしをしてください。"


def parse_arguments() -> argparse.Namespace:
    """コマンドライン引数を解析する"""
    parser = argparse.ArgumentParser(description='PDFファイルからテキストを抽出するOCRツール')
    # 必須引数
    parser.add_argument('pdf_file', help='OCR処理するPDFファイルのパス')
    
    # ページ範囲の指定
    page_group = parser.add_argument_group('ページ範囲オプション')
    page_group.add_argument('-f', '--first-page', type=int, help='開始ページ番号（1始まり）')
    page_group.add_argument('-l', '--last-page', type=int, help='終了ページ番号（1始まり）')
    
    # 出力関連
    output_group = parser.add_argument_group('出力オプション')
    output_group.add_argument('-o', '--output', help='出力テキストファイルのパス（指定しない場合はPDFファイル名_ocr.txtになります）')
    output_group.add_argument('-k', '--keep-images', action='store_true', help='処理後に一時画像ファイルを保持する')
    
    # 処理設定
    process_group = parser.add_argument_group('処理オプション')
    process_group.add_argument('-z', '--zoom', type=float, default=DEFAULT_ZOOM, help=f'PDFの拡大率（デフォルト: {DEFAULT_ZOOM}）')
    process_group.add_argument('-p', '--prompt', help='デフォルトのプロンプトに追加するテキスト')
    
    return parser.parse_args()


def get_output_filename(args: argparse.Namespace) -> str:
    """出力ファイル名を取得する"""
    if args.output:
        return args.output
    
    pdf_base = os.path.splitext(os.path.basename(args.pdf_file))[0]
    return f"{pdf_base}_ocr.txt"


def validate_pdf_exists(pdf_path: str) -> str:
    """PDFファイルの存在を確認し、存在すれば同じパスを返す"""
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(f"PDFファイル '{pdf_path}' が見つかりません")
    return pdf_path


def convert_page_to_image(
    pdf_document: fitz.Document,
    page_num: int,
    pdf_name: str,
    output_dir: str,
    output_format: str,
    zoom: float,
    total_pages: int,
    page_offset: int
) -> str:
    """PDFの1ページを画像に変換して保存する"""
    page = pdf_document[page_num]
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    
    output_file = os.path.join(output_dir, f"{pdf_name}_page_{page_num+1:04d}.{output_format}")
    pix.save(output_file)
    
    print(f"ページ {page_num-page_offset+1}/{total_pages} を保存しました: {os.path.basename(output_file)}")
    return output_file


def convert_pdf_to_images(
    pdf_path: str,
    output_dir: str,
    output_format: str = DEFAULT_OUTPUT_FORMAT,
    zoom: float = DEFAULT_ZOOM,
    first_page: Optional[int] = None,
    last_page: Optional[int] = None
) -> List[str]:
    """PDFファイルを画像に変換して保存する"""
    os.makedirs(output_dir, exist_ok=True)
    pdf_name = Path(pdf_path).stem
    
    with fitz.open(pdf_path) as pdf_document:
        start_page = 0 if first_page is None else first_page
        end_page = len(pdf_document) - 1 if last_page is None else last_page
        total_pages = end_page - start_page + 1
        
        print(f"PDFファイル '{pdf_path}' から {total_pages} ページを変換しています...")
        
        # ページごとの変換処理を部分適用した関数を作成
        convert_page = partial(
            convert_page_to_image,
            pdf_document,
            pdf_name=pdf_name,
            output_dir=output_dir,
            output_format=output_format,
            zoom=zoom,
            total_pages=total_pages,
            page_offset=start_page
        )
        
        # 各ページに変換関数を適用
        return [convert_page(page_num=page_num) for page_num in range(start_page, end_page + 1)]


def init_genai_client() -> genai.Client:
    """Google Gemini APIクライアントを初期化する"""
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("環境変数 'GOOGLE_API_KEY' が設定されていません。.envファイルを確認してください。")
    return genai.Client(api_key=api_key)


def extract_text_from_image(client: genai.Client, image_path: str) -> str:
    """単一の画像からテキストを抽出する"""
    with Image.open(image_path) as img:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=[OCR_PROMPT, img]
        )
        return response.text


def process_image(client: genai.Client, image_path: str, index: int, total: int) -> Tuple[str, str]:
    """画像を処理してファイル名とテキストのタプルを返す"""
    print(f"OCR処理中 ({index+1}/{total}): {os.path.basename(image_path)}")
    text = extract_text_from_image(client, image_path)
    return os.path.basename(image_path), text


def process_images(folder_path: str, output_file_path: str, prompt: str) -> bool:
    """フォルダ内の画像に対してOCRを実行し、結果をファイルに保存する"""
    try:
        # 画像ファイルを取得してソート
        image_files = sorted([
            os.path.join(folder_path, file) for file in os.listdir(folder_path) 
            if os.path.isfile(os.path.join(folder_path, file)) and 
            any(file.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg'])
        ])
        
        if not image_files:
            print(f"警告: フォルダ '{folder_path}' に画像ファイルが見つかりません")
            return False
        
        print(f"処理する画像ファイル数: {len(image_files)}")
        
        # Google AIクライアントを初期化
        client = init_genai_client()
        
        # 部分適用で画像処理関数を準備
        process = partial(process_image, client)
        
        # 各画像を処理して結果を取得
        results = [
            process(image_path, index, len(image_files))
            for index, image_path in enumerate(image_files)
        ]
        
        # 結果を整形して保存
        with open(output_file_path, 'w', encoding='utf-8') as output_file:
            output_file.write('\n\n'.join([
                f"------------------\n{text}"
                for filename, text in results
            ]))
            
        print(f"OCR処理が完了しました。結果は '{output_file_path}' に保存されています。")
        return True
        
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        return False


def clean_temp_directory(keep_images: bool) -> None:
    """一時ディレクトリを削除する（保持フラグがない場合）"""
    if not keep_images and os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
        print(f"一時ディレクトリ '{TEMP_DIR}' を削除しました。")


def run_ocr_process(args: argparse.Namespace) -> int:
    """OCR処理を実行する"""
    try:
        # PDF存在チェック
        validate_pdf_exists(args.pdf_file)
        
        # 出力ファイル名の設定
        output_file = get_output_filename(args)
        
        # 一時ディレクトリの作成
        os.makedirs(TEMP_DIR, exist_ok=True)
        
        # ページ番号を0ベースに変換
        first_page = None if args.first_page is None else args.first_page - 1
        last_page = None if args.last_page is None else args.last_page - 1
        
        # PDFを画像に変換
        convert_pdf_to_images(
            args.pdf_file,
            output_dir=TEMP_DIR,
            output_format=DEFAULT_OUTPUT_FORMAT,
            zoom=args.zoom,
            first_page=first_page,
            last_page=last_page
        )
        
        # プロンプトの準備
        prompt = DEFAULT_OCR_PROMPT
        if args.prompt:
            prompt = f"{DEFAULT_OCR_PROMPT}\n{args.prompt}"
        
        # 画像からテキストを抽出
        print(f"画像からテキストを抽出しています...")
        result = process_images(TEMP_DIR, output_file, prompt=prompt)
        
        return 0 if result else 1
        
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        return 1
    
    finally:
        # 一時ディレクトリの削除
        clean_temp_directory(args.keep_images)


def main() -> None:
    """メインエントリーポイント"""
    args = parse_arguments()
    sys.exit(run_ocr_process(args))


if __name__ == "__main__":
    main()
