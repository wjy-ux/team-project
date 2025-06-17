import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                           QHBoxLayout, QLineEdit, QPushButton, QListWidget,
                           QTextEdit, QProgressBar, QMessageBox)
import requests
from bs4 import BeautifulSoup
from novel_downloader import download_chapter

class QidianSpider:
    def search_novel(self, keyword):
        try:
            # 错误行：url = ' `https://www.qidian.com/search?kw=` ' + keyword
            # 修正为：
            url = 'https://www.qidian.com/search?kw=' + keyword
            response = requests.get(url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            # 解析搜索结果逻辑...
            return []
        except Exception as e:
            raise

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.spider = QidianSpider()
        self.init_ui()

    def init_ui(self):
        # 创建搜索输入框和按钮
        self.search_input = QLineEdit()
        self.search_btn = QPushButton('搜索')
        # 新增下载按钮
        self.download_btn = QPushButton('下载选中章节')
        self.download_btn.clicked.connect(self.handle_download)

    def handle_download(self):
        selected_item = self.novel_list.currentItem()
        if selected_item:
            novel_id = selected_item.data(32)  # 假设存储了小说ID
            download_chapter(novel_id, 1)  # 下载第一章
        
        # 创建布局并添加组件
        search_layout = QHBoxLayout()
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(self.search_btn)
        
        # 将搜索布局添加到主布局
        main_layout = QVBoxLayout()
        main_layout.addLayout(search_layout)
        self.search_btn.clicked.connect(self.handle_search)

    def handle_search(self):
        try:
            keyword = self.search_input.text()
            results = self.spider.search_novel(keyword)
            # 更新列表逻辑...
        except Exception as e:
            self.show_error(str(e))

    def show_error(self, message):
        QMessageBox.critical(self, '错误', message)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())