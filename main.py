import os
import fitz  # PyMuPDF
from pathlib import Path
from google import genai
from PIL import Image
from dotenv import load_dotenv
import shutil

def ocr_images_in_folder(folder_path, output_file_path):
    """
    フォルダ内の画像に対してGemini 2.0 FlashでOCRを実行し、結果を一つのファイルに連結する
    
    Args:
        folder_path (str): 画像ファイルが格納されているフォルダのパス
        output_file_path (str): 抽出されたテキストを保存するファイルのパス
    
    Returns:
        bool: 処理が成功した場合はTrue、失敗した場合はFalse
    """
    try:
        # .envファイルから環境変数を読み込む
        load_dotenv()
        
        # 環境変数からAPIキーを取得
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("環境変数 'GOOGLE_API_KEY' が設定されていません。.envファイルを確認してください。")
        
        # Google AIのクライアントを初期化
        client = genai.Client(api_key=api_key)
        
        image_files = sorted([os.path.join(folder_path, file) for file in os.listdir(folder_path) 
                      if os.path.isfile(os.path.join(folder_path, file))])

        all_text_results = []
        
        print(f"処理する画像ファイル数: {len(image_files)}")
        
        # 各画像ファイルを処理
        for image_path in image_files:
            print(f"処理中: {image_path}")
            
            # 画像を開く
            img = Image.open(image_path)
            
            # プロンプトの設定
            prompt = "この画像に含まれるすべてのテキストを抽出してください。改行や段落構造を維持し、完全かつ正確に文字起こしをしてください。"
            
            # Gemini APIを呼び出して画像からテキストを抽出
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=[prompt, img]
            )
            
            # 結果のテキストを取得
            extracted_text = response.text
            
            # ファイル名とテキスト結果をリストに追加
            all_text_results.append(f"### ファイル: {os.path.basename(image_path)} ###\n{extracted_text}\n\n")
            
        # すべての結果を連結
        concatenated_text = "".join(all_text_results)
        
        # 結果をファイルに書き込む
        with open(output_file_path, 'w', encoding='utf-8') as output_file:
            output_file.write(concatenated_text)
            
        print(f"OCR処理が完了しました。結果は {output_file_path} に保存されています。")
        return True
        
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        return False


def convert_pdf_to_images_with_pymupdf(pdf_path, output_dir=None, output_format="png", zoom=2.0, first_page=None, last_page=None):
    """
    PyMuPDFを使用してPDFファイルを画像に変換して保存する関数
    
    引数:
        pdf_path (str): 変換するPDFファイルのパス
        output_dir (str, optional): 出力先ディレクトリ。Noneの場合はPDFと同じディレクトリに保存
        output_format (str, optional): 出力画像形式 (png, jpg)
        zoom (float, optional): 拡大率（解像度に影響）
        first_page (int, optional): 変換を開始するページ番号（0始まり）
        last_page (int, optional): 変換を終了するページ番号（0始まり）
    
    戻り値:
        list: 保存された画像ファイルのパスのリスト
    """
    # 出力ディレクトリの設定
    if output_dir is None:
        output_dir = os.path.dirname(pdf_path)
    
    # 出力ディレクトリが存在しない場合は作成
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    # PDFファイル名（拡張子なし）を取得
    pdf_filename = os.path.splitext(os.path.basename(pdf_path))[0]
    
    # PDFを開く
    pdf_document = fitz.open(pdf_path)
    
    # ページ範囲の調整
    if first_page is None:
        first_page = 0
    if last_page is None:
        last_page = len(pdf_document) - 1
    
    # マトリックスを作成（拡大率を設定）
    mat = fitz.Matrix(zoom, zoom)
    
    output_paths = []
    for page_num in range(first_page, last_page + 1):
        # ページを取得
        page = pdf_document[page_num]
        
        # ページを画像（ピクセルマップ）として取得
        pix = page.get_pixmap(matrix=mat, alpha=False)
        
        # 出力ファイル名
        output_file = os.path.join(output_dir, f"{pdf_filename}_page_{page_num+1:04d}.{output_format}")
        
        # 画像を保存
        pix.save(output_file)
        output_paths.append(output_file)
        print(f"ページ {page_num+1}/{last_page+1} を保存しました: {output_file}")
    
    # PDFを閉じる
    pdf_document.close()
    
    return output_paths

def main():
    print("Hello from gemini-ocr!")
    convert_pdf_to_images_with_pymupdf("incompleteness.pdf", output_dir="tmp", output_format="png", zoom=2.0, first_page=0, last_page=None)
    ocr_images_in_folder("tmp", "ocr_results.txt")
    shutil.rmtree("tmp")

if __name__ == "__main__":
    main()
