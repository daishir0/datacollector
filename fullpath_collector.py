"""
指定したディレクトリ内のすべてのファイルパスを収集し、
コンソールとout.txtファイルに出力するプログラム

使い方:
    python fullpath_collector.py <ディレクトリパス>

出力:
    - コンソールに全ファイルパスを表示
    - カレントディレクトリにout.txt（UTF-8）を作成し、全ファイルパスを保存
    - すでにout.txtが存在する場合は上書き

動作環境:
    Windows、Mac、Linux対応
"""
import os
import sys

def collect_file_paths(directory):
    """指定されたディレクトリ内のすべてのファイルパスを収集する"""
    file_paths = []
    
    try:
        # os.walkを使用して再帰的にディレクトリをたどる
        for root, _, files in os.walk(directory):
            print(f"スキャン中: {root}")  # 現在処理中のディレクトリを表示
            for file in files:
                # 絶対パスを作成
                full_path = os.path.abspath(os.path.join(root, file))
                file_paths.append(full_path)
                
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        sys.exit(1)
        
    return file_paths

def main():
    # コマンドライン引数をチェック
    if len(sys.argv) != 2:
        print("使用方法: python fullpath_collector.py <ディレクトリパス>")
        sys.exit(1)
    
    directory = sys.argv[1]
    
    # ディレクトリの存在確認
    if not os.path.isdir(directory):
        print(f"エラー: '{directory}' は有効なディレクトリではありません。")
        sys.exit(1)
    
    # ファイルパスを収集
    file_paths = collect_file_paths(directory)
    
    # 結果を出力
    try:
        # ファイルに書き込み（UTF-8エンコーディング）
        with open('out.txt', 'w', encoding='utf-8') as f:
            for path in file_paths:
                f.write(f"{path}\n")
                print(path)  # コンソールにも出力
                
        print(f"\n合計 {len(file_paths)} 個のファイルが見つかりました。")
        print("結果はout.txtに保存されました。")
        
    except Exception as e:
        print(f"ファイル出力中にエラーが発生しました: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 