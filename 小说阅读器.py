import os
from pathlib import Path

class StorageManager:
    def __init__(self, base_dir='storage'):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
    
    def save_novel(self, author, title, content):
        author_dir = self.base_dir / author
        author_dir.mkdir(exist_ok=True)
        
        novel_path = author_dir / f"{title}.txt"
        with open(novel_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def get_novel_path(self, author, title):
        return self.base_dir / author / f"{title}.txt"
from dataclasses import dataclass
from datetime import datetime

@dataclass
class NovelInfo:
    title: str
    author: str
    chapter_count: int
    word_count: int
    update_time: datetime
    file_path: str

class NovelInfoManager:
    def __init__(self, db_path='novels.db'):
        self.db_path = db_path
    
    def add_novel(self, novel_info):
        # 添加到数据库
        pass
    
    def search_by_title(self, title):
        # 按标题搜索
        pass
    
    def search_by_author(self, author):
        # 按作者搜索
        pass
import sqlite3

class NovelSearcher:
    def __init__(self, db_path='novels.db'):
        self.db_path = db_path
    
    def search(self, keyword):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = """
        SELECT * FROM novels 
        WHERE title LIKE ? OR author LIKE ? OR content LIKE ?
        """
        cursor.execute(query, (f'%{keyword}%', f'%{keyword}%', f'%{keyword}%'))
        return cursor.fetchall()
import os

class NovelCleaner:
    def delete_novel(self, file_path):
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    
    def delete_chapter(self, novel_path, chapter_title):
        # 从小说文件中删除特定章节
        pass

from novel