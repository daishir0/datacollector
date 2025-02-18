#!/usr/bin/env python3
import os
import sys
import yaml
import sqlite3
import hashlib
import logging
import requests
import datetime
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from markitdown import MarkItDown

# ロギング設定
logging.basicConfig(
    filename='log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'  # UTF-8エンコーディングを指定
)

class DataCollector:
    # ファイルタイプの定義を更新
    FILE_TYPES = {
        'html': {
            'content_types': [
                'text/html',
                'application/xhtml+xml'
            ],
            'extensions': ['.html', '.htm', '.xhtml'],
            'magic_numbers': [
                b'<!DOCTYPE html>',
                b'<html',
                b'<?xml'
            ]
        },
        'text': {
            'content_types': [
                'text/plain',
                'text/txt'
            ],
            'extensions': ['.txt'],
            'magic_numbers': []
        },
        'pdf': {
            'content_types': [
                'application/pdf',
                'application/x-pdf',
                'application/acrobat',
                'application/vnd.pdf'
            ],
            'extensions': ['.pdf'],
            'magic_numbers': [b'%PDF']
        },
        'word': {
            'content_types': [
                'application/msword',
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'application/vnd.ms-word',
                'application/vnd.ms-word.document.macroEnabled.12'
            ],
            'extensions': ['.doc', '.docx'],
            'magic_numbers': [
                b'\xD0\xCF\x11\xE0',  # DOC
                b'PK\x03\x04'         # DOCX (ZIP-based)
            ],
            'converter_map': {
                '.doc': 'doc',
                '.docx': 'docx'
            }
        },
        'excel': {
            'content_types': [
                'application/vnd.ms-excel',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'application/vnd.ms-excel.sheet.macroEnabled.12'
            ],
            'extensions': ['.xls', '.xlsx'],
            'magic_numbers': [
                b'\xD0\xCF\x11\xE0',  # XLS
                b'PK\x03\x04'         # XLSX (ZIP-based)
            ],
            'converter_map': {
                '.xls': 'xls',
                '.xlsx': 'xlsx'
            }
        },
        'powerpoint': {
            'content_types': [
                'application/vnd.ms-powerpoint',
                'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                'application/vnd.ms-powerpoint.presentation.macroEnabled.12'
            ],
            'extensions': ['.ppt', '.pptx'],
            'magic_numbers': [
                b'\xD0\xCF\x11\xE0',  # PPT
                b'PK\x03\x04'         # PPTX (ZIP-based)
            ],
            'converter_map': {
                '.ppt': 'ppt',
                '.pptx': 'pptx'
            }
        }
    }

    def __init__(self):
        self.load_config()
        self.init_database()
        self.md = MarkItDown()

    def load_config(self):
        try:
            with open('config.yaml', 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                self.api_key = config['api']['bearer_token']
                self.group_id = config['api']['group_id']
                self.bulk_api_url = config['api']['bulk_api_url']
                self.debug_enabled = config.get('debug', {}).get('enabled', False)
                logging.info('設定ファイルを読み込みました')
        except Exception as e:
            logging.error(f'設定ファイルの読み込みに失敗: {str(e)}')
            sys.exit(1)

    def debug_log(self, message):
        if self.debug_enabled:
            logging.info(f'[DEBUG] {message}')

    def init_database(self):
        try:
            timestamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
            
            # 既存のDBファイルがある場合はリネーム
            if os.path.exists('data.db'):
                os.rename('data.db', f'{timestamp}data.db')
                logging.info(f'既存のDBファイルを{timestamp}data.dbにリネームしました')

            # ロギング設定を一旦クリア
            for handler in logging.getLogger().handlers[:]:
                handler.close()
                logging.getLogger().removeHandler(handler)

            # 既存のlogファイルがある場合はリネーム
            if os.path.exists('log.txt'):
                try:
                    os.rename('log.txt', f'{timestamp}log.txt')
                except OSError:
                    # リネームに失敗した場合は新しいファイル名で作成
                    pass

            # ロギング設定を再初期化
            logging.basicConfig(
                filename='log.txt',
                level=logging.INFO,
                format='%(asctime)s - %(levelname)s - %(message)s',
                encoding='utf-8'
            )
            logging.info(f'ログファイルを初期化しました')

            # 新しいDBファイルを作成
            self.conn = sqlite3.connect('data.db')
            self.cursor = self.conn.cursor()
            
            # テーブル作成
            self.cursor.execute('''
                CREATE TABLE record (
                    id INTEGER UNIQUE,
                    title TEXT NOT NULL,
                    text TEXT NOT NULL,
                    reference TEXT,
                    group_id INTEGER,
                    created_by TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    deleted INTEGER DEFAULT 0,
                    hash TEXT,
                    update_flg INTEGER DEFAULT 0,
                    error TEXT
                )
            ''')
            self.conn.commit()
            logging.info('データベースを初期化しました')

        except Exception as e:
            logging.error(f'データベースの初期化に失敗: {str(e)}')
            sys.exit(1)

    def sync_records(self):
        try:
            headers = {'Authorization': f'Bearer {self.api_key}'}
            response = requests.get(
                f'{self.bulk_api_url}?action=get_records&group_id={self.group_id}',
                headers=headers
            )
            response.raise_for_status()
            records = response.json()['records']

            for record in records:
                hash_value = hashlib.sha1(record['text'].encode()).hexdigest() if record['text'] else ''
                
                # 既存レコードの確認
                self.cursor.execute('SELECT id FROM record WHERE id = ?', (record['id'],))
                exists = self.cursor.fetchone()

                if exists:
                    # 更新
                    self.cursor.execute('''
                        UPDATE record 
                        SET title = ?, text = ?, reference = ?, group_id = ?,
                            created_by = ?, created_at = ?, updated_at = ?, hash = ?
                        WHERE id = ?
                    ''', (
                        record['title'], record['text'], record['reference'],
                        record['group_id'], record['created_by'], record['created_at'],
                        record['updated_at'], hash_value, record['id']
                    ))
                else:
                    # 新規追加
                    self.cursor.execute('''
                        INSERT INTO record (id, title, text, reference, group_id,
                                         created_by, created_at, updated_at, hash)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        record['id'], record['title'], record['text'], record['reference'],
                        record['group_id'], record['created_by'], record['created_at'],
                        record['updated_at'], hash_value
                    ))

            self.conn.commit()
            logging.info('レコードの同期が完了しました')
        except Exception as e:
            logging.error(f'レコードの同期に失敗: {str(e)}')

    def detect_file_type(self, content, content_type=None):
        """
        コンテンツのファイルタイプを検出する
        """
        self.debug_log(f'ファイルタイプ検出開始 - Content-Type: {content_type}')
        
        # Content-Typeによる判定
        if content_type:
            for file_type, type_info in self.FILE_TYPES.items():
                if any(ct in content_type.lower() for ct in type_info['content_types']):
                    self.debug_log(f'Content-Typeによる判定結果: {file_type}')
                    return file_type

        # 拡張子による判定（テキストファイル用）
        if content_type and 'text/plain' in content_type.lower():
            self.debug_log('Content-Typeによるテキストファイル判定')
            return 'text'

        # マジックナンバーによる判定
        content_start = content[:32]  # 先頭32バイトを確認
        for file_type, type_info in self.FILE_TYPES.items():
            if any(content_start.startswith(magic) for magic in type_info['magic_numbers']):
                self.debug_log(f'マジックナンバーによる判定結果: {file_type}')
                return file_type

        self.debug_log('ファイルタイプを特定できませんでした')
        return None

    def detect_file_extension(self, content, content_type):
        """
        コンテンツの実際の拡張子を検出する
        """
        # マジックナンバーでの判定
        if content.startswith(b'PK\x03\x04'):  # ZIP-based (新しい形式)
            if content_type:
                if 'wordprocessingml' in content_type:
                    return '.docx'
                elif 'spreadsheetml' in content_type:
                    return '.xlsx'
                elif 'presentationml' in content_type:
                    return '.pptx'
        elif content.startswith(b'\xD0\xCF\x11\xE0'):  # OLE2 (古い形式)
            if content_type:
                if 'msword' in content_type:
                    return '.doc'
                elif 'ms-excel' in content_type:
                    return '.xls'
                elif 'ms-powerpoint' in content_type:
                    return '.ppt'
        
        return None

    def save_temp_file(self, content, file_type):
        """
        一時ファイルを保存する
        """
        extension = self.FILE_TYPES[file_type]['extensions'][0]
        temp_file = f'temp_{datetime.datetime.now().strftime("%Y%m%d%H%M%S")}{extension}'
        
        self.debug_log(f'一時ファイル作成: {temp_file}')
        with open(temp_file, 'wb') as f:
            f.write(content)
        
        return temp_file

    def convert_content(self, content, content_type, id):
        """
        コンテンツを変換する
        """
        try:
            file_type = self.detect_file_type(content, content_type)
            if not file_type:
                raise ValueError("未対応のファイル形式です")

            self.debug_log(f'ID {id}: ファイルタイプ: {file_type}')
            
            # テキストファイルの場合は変換せずにそのまま返す
            if file_type == 'text':
                if isinstance(content, bytes):
                    content = content.decode('utf-8', errors='ignore')
                return type('ConversionResult', (), {'text_content': content})()

            # 一時ファイルの作成
            temp_file = self.save_temp_file(content, file_type)
            
            try:
                # ファイル変換処理
                self.debug_log(f'ID {id}: {file_type.upper()}ファイルの変換開始')
                conversion_result = self.md.convert(temp_file)
                
                if conversion_result is None:
                    raise ValueError("コンテンツの変換に失敗しました")
                
                return conversion_result

            except markitdown._markitdown.FileConversionException as e:
                # markitdownの変換エラーを詳細に記録
                error_details = str(e)
                if hasattr(e, '__cause__') and e.__cause__:
                    error_details += f"\n原因: {str(e.__cause__)}"
                self.debug_log(f'ID {id}: 変換エラー: {error_details}')
                
                # エラー内容をDBに保存
                self.cursor.execute(
                    'UPDATE record SET error = ? WHERE id = ?',
                    (error_details, id)
                )
                self.conn.commit()
                return None

            finally:
                # 一時ファイルの削除
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                    self.debug_log(f'一時ファイル削除: {temp_file}')

        except Exception as e:
            self.debug_log(f'変換処理でエラー: {str(e)}')
            # その他のエラーもDBに保存
            self.cursor.execute(
                'UPDATE record SET error = ? WHERE id = ?',
                (str(e), id)
            )
            self.conn.commit()
            return None

    def check_content_type(self, content_type):
        """
        Content-Typeが対応しているものかチェックする
        """
        if not content_type:
            return False
            
        content_type = content_type.lower()
        
        # 全ての対応するContent-Typeをチェック
        for file_type, type_info in self.FILE_TYPES.items():
            if any(ct in content_type for ct in type_info['content_types']):
                self.debug_log(f'Content-Type {content_type} は {file_type} として対応しています')
                return True
                
        self.debug_log(f'Content-Type {content_type} は未対応です')
        return False

    def process_content(self):
        try:
            self.cursor.execute('SELECT * FROM record')
            records = self.cursor.fetchall()
            self.debug_log(f'処理対象レコード数: {len(records)}')
            
            for record in records:
                id, title, text, reference = record[0:4]
                updated_at = record[7]
                
                self.debug_log(f'処理開始: ID {id}, タイトル: {title}')
                self.debug_log(f'ID {id}: レコードの更新日時: {updated_at}')
                self.debug_log(f'ID {id}: テキストの状態: {"空" if not text else f"{len(text)}文字"}')
                
                if not reference:
                    self.debug_log(f'ID {id}: referenceが空のためスキップ')
                    continue

                try:
                    if os.path.exists(reference):  # ローカルファイルの処理
                        self.debug_log(f'ID {id}: ローカルファイルの処理開始: {reference}')
                        file_time = datetime.datetime.fromtimestamp(os.path.getmtime(reference))
                        record_time = datetime.datetime.strptime(updated_at, '%Y-%m-%d %H:%M:%S')
                        
                        if text and file_time <= record_time:
                            message = f'ファイルは最新です（ファイル更新: {file_time}, レコード更新: {record_time}）'
                            self.debug_log(f'ID {id}: {message}')
                            self.cursor.execute(
                                'UPDATE record SET error = ? WHERE id = ?',
                                (message, id)
                            )
                            self.conn.commit()
                            continue

                        # ファイルの内容を読み込む
                        with open(reference, 'rb') as f:
                            content = f.read()
                        
                        # ファイル拡張子からContent-Typeを推測
                        ext = os.path.splitext(reference)[1].lower()
                        content_type = {
                            '.doc': 'application/msword',
                            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                            '.xls': 'application/vnd.ms-excel',
                            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                            '.ppt': 'application/vnd.ms-powerpoint',
                            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                            '.txt': 'text/plain'
                        }.get(ext, 'application/octet-stream')

                        # コンテンツの変換
                        conversion_result = self.convert_content(content, content_type, id)
                        if conversion_result is None:
                            raise ValueError("コンテンツの変換に失敗しました")
                        
                        markdown_text = conversion_result.text_content
                        
                        # テキストの更新
                        self.cursor.execute('''
                            UPDATE record 
                            SET text = ?, hash = ?, update_flg = 1 
                            WHERE id = ?
                        ''', (
                            markdown_text,
                            hashlib.sha1(markdown_text.encode()).hexdigest(),
                            id
                        ))
                        self.conn.commit()
                        self.debug_log(f'ID {id}: テキスト更新完了')
                        logging.info(f'ID {id}のコンテンツを更新しました')

                    elif ',' in reference and reference.lower().startswith('http'):
                        self.debug_log(f'ID {id}: URL+XPATHの処理開始')
                        url, xpath = reference.split(',', 1)
                        self.debug_log(f'ID {id}: URL={url}, XPATH={xpath}')
                        response = requests.get(url)
                        soup = BeautifulSoup(response.text, 'lxml')
                        content = soup.select_one(xpath.strip())
                        if content:
                            self.debug_log(f'ID {id}: コンテンツ取得成功')
                            conversion_result = self.convert_content(
                                content.get_text(),
                                response.headers.get('content-type', ''),
                                id
                            )
                            self.debug_log(f'ID {id}: 変換結果={conversion_result is not None}')
                            if conversion_result is None:
                                raise ValueError("コンテンツの変換に失敗しました")
                            markdown_text = conversion_result.text_content
                    else:
                        if reference.lower().startswith('http'):
                            self.debug_log(f'ID {id}: URLの処理開始: {reference}')
                            try:
                                response = requests.head(reference)
                                self.debug_log(f'ID {id}: HEADリクエスト完了 - ステータスコード: {response.status_code}')
                            except Exception as e:
                                self.debug_log(f'ID {id}: HEADリクエスト失敗 - エラー: {str(e)}')
                                raise

                            last_modified = response.headers.get('last-modified')
                            self.debug_log(f'ID {id}: Last-Modified: {last_modified}')

                            # テキストが空でない場合のみ、更新日時をチェック
                            if text and last_modified:
                                last_modified_date = datetime.datetime.strptime(
                                    last_modified, '%a, %d %b %Y %H:%M:%S GMT'
                                )
                                record_update_date = datetime.datetime.strptime(updated_at, '%Y-%m-%d %H:%M:%S')
                                self.debug_log(f'ID {id}: 日時比較 - URL更新日時: {last_modified_date}, レコード更新日時: {record_update_date}')
                                
                                if last_modified_date <= record_update_date:
                                    message = f'コンテンツは最新です（URL最終更新: {last_modified_date}, レコード更新: {record_update_date}）'
                                    self.debug_log(f'ID {id}: {message}')
                                    self.cursor.execute(
                                        'UPDATE record SET error = ? WHERE id = ?',
                                        (message, id)
                                    )
                                    self.conn.commit()
                                    continue
                            elif not text:
                                self.debug_log(f'ID {id}: テキストが空のため、更新日時チェックをスキップして処理を続行')

                            content_type = response.headers.get('content-type', '')
                            self.debug_log(f'ID {id}: Content-Type: {content_type}')

                            # Content-Typeのチェックを実行
                            if not self.check_content_type(content_type):
                                message = f'未対応のコンテンツタイプです: {content_type}'
                                self.debug_log(f'ID {id}: {message}')
                                self.cursor.execute(
                                    'UPDATE record SET error = ? WHERE id = ?',
                                    (message, id)
                                )
                                self.conn.commit()
                                continue

                            try:
                                response = requests.get(reference)
                                self.debug_log(f'ID {id}: GETリクエスト完了 - ステータスコード: {response.status_code}')
                                self.debug_log(f'ID {id}: レスポンスサイズ: {len(response.content)} bytes')
                                
                                content_text = response.content.decode('utf-8', errors='ignore')
                                
                                self.debug_log(f'ID {id}: コンテンツ取得成功')
                                
                                # コンテンツの変換
                                conversion_result = self.convert_content(
                                    response.content,
                                    response.headers.get('content-type', ''),
                                    id
                                )

                                if conversion_result is None:
                                    raise ValueError("コンテンツの変換に失敗しました")
                                
                                markdown_text = conversion_result.text_content
                            except Exception as e:
                                self.debug_log(f'ID {id}: GETリクエスト失敗 - エラー: {str(e)}')
                                raise
                        else:
                            self.debug_log(f'ID {id}: ローカルファイルの処理開始: {reference}')
                            if not os.path.exists(reference):
                                self.cursor.execute(
                                    'UPDATE record SET error = ? WHERE id = ?',
                                    ('ファイルが存在しません', id)
                                )
                                self.conn.commit()
                                continue

                            file_time = datetime.datetime.fromtimestamp(os.path.getmtime(reference))
                            if file_time <= datetime.datetime.strptime(updated_at, '%Y-%m-%d %H:%M:%S'):
                                self.cursor.execute(
                                    'UPDATE record SET error = ? WHERE id = ?',
                                    (f'ファイルは最新です（ファイル更新: {file_time}, レコード更新: {updated_at}）', id)
                                )
                                self.conn.commit()
                                continue

                            conversion_result = self.convert_content(
                                reference,
                                response.headers.get('content-type', ''),
                                id
                            )
                            self.debug_log(f'ID {id}: 変換結果={conversion_result is not None}')
                            if conversion_result is None:
                                raise ValueError("コンテンツの変換に失敗しました")
                            markdown_text = conversion_result.text_content

                    self.debug_log(f'ID {id}: テキスト更新開始')
                    # テキストの更新
                    self.cursor.execute('''
                        UPDATE record 
                        SET text = ?, hash = ?, update_flg = 1 
                        WHERE id = ?
                    ''', (
                        markdown_text,
                        hashlib.sha1(markdown_text.encode()).hexdigest(),
                        id
                    ))
                    self.conn.commit()
                    self.debug_log(f'ID {id}: テキスト更新完了')
                    logging.info(f'ID {id}のコンテンツを更新しました')

                except Exception as e:
                    self.debug_log(f'ID {id}: エラー発生: {str(e)}')
                    self.cursor.execute(
                        'UPDATE record SET error = ? WHERE id = ?',
                        (str(e), id)
                    )
                    self.conn.commit()
                    logging.error(f'ID {id}の処理中にエラー: {str(e)}')
                    self.debug_log(f'ID {id}: 次のレコードに進みます')
                    self.conn.commit()
                    continue

            self.debug_log('全レコードの処理が完了しました')

        except Exception as e:
            logging.error(f'コンテンツ処理中にエラー: {str(e)}')

    def update_records(self):
        try:
            self.cursor.execute('SELECT id, text FROM record WHERE update_flg = 1')
            records = self.cursor.fetchall()

            headers = {'Authorization': f'Bearer {self.api_key}'}
            for record in records:
                id, text = record
                try:
                    response = requests.post(
                        f'{self.bulk_api_url}?action=update_record',
                        headers=headers,
                        json={'id': id, 'text': text}
                    )
                    response.raise_for_status()
                    logging.info(f'ID {id}のレコードをサーバーに更新しました')
                except Exception as e:
                    logging.error(f'ID {id}のサーバー更新に失敗: {str(e)}')

        except Exception as e:
            logging.error(f'レコード更新中にエラー: {str(e)}')

    def close(self):
        self.conn.close()

def main():
    collector = DataCollector()
    try:
        collector.sync_records()
        collector.process_content()
        collector.update_records()
    finally:
        collector.close()

if __name__ == '__main__':
    main()