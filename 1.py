import requests
from bs4 import BeautifulSoup
import threading
import os
from fake_useragent import UserAgent
from tqdm import tqdm
import time
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import queue
import sys


class NovelDownloader:
    def __init__(self):
        self.session = requests.Session()
        self.ua = UserAgent()
        self.session.headers = {
            'User-Agent': self.ua.random,
            'Referer': 'https://www.qidian.com/'
        }
        self.chapter_progress = {}

    def download_novel(self, url, save_path, start_chapter=None, end_chapter=None, progress_callback=None):
        # 实现获取小说信息的逻辑
        novel_info = self.get_novel_info(url)
        if not os.path.exists(save_path):
            os.makedirs(save_path)

        # 实现获取章节列表的逻辑
        chapter_list = self.get_chapter_list(url)
        if start_chapter is not None:
            chapter_list = chapter_list[start_chapter - 1:]
        if end_chapter is not None:
            chapter_list = chapter_list[:end_chapter - start_chapter + 1]

        total_chapters = len(chapter_list)
        # 初始化进度跟踪
        self.chapter_progress = {chapter['title']: '等待中' for chapter in chapter_list}
        self.completed_chapters = 0
        self.progress_callback = progress_callback
        
        # 多线程下载章节并显示进度
        max_threads = 5  # 限制最大线程数
        threads = []
        
        with tqdm(total=total_chapters, desc=f"下载《{novel_info['title']}") as pbar:
            for i, chapter in enumerate(chapter_list):
                # 控制线程数量
                while len(threading.enumerate()) > max_threads + 1:
                    time.sleep(0.1)
                
                thread = threading.Thread(
                    target=self._download_with_progress,
                    args=(chapter, save_path, pbar, total_chapters)
                )
                threads.append(thread)
                thread.start()
                
            # 等待所有线程完成
            for thread in threads:
                thread.join()

    def _download_with_progress(self, chapter, save_path, pbar, total_chapters):
        """带进度条的下载辅助函数"""
        try:
            result = self.download_chapter(chapter, save_path)
            pbar.update(1)
            pbar.set_postfix_str(f"当前: {chapter['title'][:10]}...")
            
            # 更新完成章节数和进度
            self.completed_chapters += 1
            progress_percent = (self.completed_chapters / total_chapters) * 100
            
            # 调用进度回调函数
            if self.progress_callback:
                self.progress_callback(progress_percent, chapter['title'])
        except Exception as e:
            print(f"线程错误: {str(e)}")
            pbar.update(1)

    def get_novel_info(self, url):
        """获取小说信息，支持起点中文网和晋江文学城"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 起点中文网解析
            if 'qidian.com' in url:
                title = soup.find('h1', class_='book-title').text.strip()
                author = soup.find('a', class_='writer').text.strip()
            # 晋江文学城解析
            elif 'jjwxc.net' in url:
                title = soup.find('span', property='v:itemreviewed').text.strip()
                author = soup.find('span', class_='authorname').text.strip()
            else:
                print(f"不支持的网站: {url}")
                return None
            
            return {
                'title': title,
                'author': author,
                'url': url
            }
        except Exception as e:
            print(f"获取小说信息失败: {str(e)}")
            return None

    def get_chapter_list(self, url):
        """获取章节列表，支持起点中文网和晋江文学城"""
        chapter_list = []
        try:
            # 起点中文网解析
            if 'qidian.com' in url:
                novel_id = url.split('/')[-1]
                chapters_url = f"https://book.qidian.com/info/{novel_id}#Catalog"
                response = self.session.get(chapters_url, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 解析章节列表
                volume_list = soup.find_all('div', class_='volume')
                for volume in volume_list:
                    chapters = volume.find_all('a', class_='chapter-name')
                    for chapter in chapters:
                        chapter_title = chapter.text.strip()
                        chapter_url = 'https:' + chapter['href']
                        chapter_list.append({
                            'title': chapter_title,
                            'url': chapter_url
                        })
            # 晋江文学城解析
            elif 'jjwxc.net' in url:
                novel_id = url.split('/')[-1].split('.')[0]
                chapters_url = f"https://www.jjwxc.net/onebook.php?novelid={novel_id}"
                response = self.session.get(chapters_url, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # 解析章节列表
                chapter_table = soup.find('table', class_='cytable')
                if chapter_table:
                    chapters = chapter_table.find_all('tr')[1:]
                    for chapter in chapters:
                        a_tag = chapter.find('a')
                        if a_tag:
                            chapter_title = a_tag.text.strip()
                            chapter_url = f"https://www.jjwxc.net/{a_tag['href']}"
                            chapter_list.append({
                                'title': chapter_title,
                                'url': chapter_url
                            })
            else:
                print(f"不支持的网站: {url}")
                return []
            
            return chapter_list
        except Exception as e:
            print(f"获取章节列表失败: {str(e)}")
            return []

    def download_chapter(self, chapter, save_path):
        """下载章节内容并支持断点续传"""
        chapter_url = chapter['url']
        chapter_title = chapter['title'].replace('?', '').replace(':', '：')
        file_path = os.path.join(save_path, f'{chapter_title}.txt')
        
        # 断点续传检查：如果文件已存在则跳过
        if os.path.exists(file_path):
            self.chapter_progress[chapter_title] = '已完成'
            return True
        
        try:
            response = self.session.get(chapter_url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 解析章节内容
            if 'qidian.com' in chapter_url:
                content_div = soup.find('div', class_='read-content j_readContent')
                if not content_div:
                    print(f"无法解析章节内容: {chapter_title}")
                    return False
                
                # 提取并清理文本内容
                p_tags = content_div.find_all('p')
                chapter_content = '\n'.join([p.text.strip() for p in p_tags if p.text.strip()])
            elif 'jjwxc.net' in chapter_url:
                content_div = soup.find('div', id='content')
                if not content_div:
                    print(f"无法解析章节内容: {chapter_title}")
                    return False
                
                # 提取并清理文本内容
                chapter_content = content_div.text.strip()
                # 移除晋江特有的广告和导航文本
                chapter_content = chapter_content.replace('晋江文学城', '').replace('www.jjwxc.net', '').strip()
                # 处理换行
                chapter_content = '\n'.join([line.strip() for line in chapter_content.splitlines() if line.strip()])
            else:
                print(f"不支持的网站章节: {chapter_url}")
                return False
            
            # 保存章节内容
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(chapter_content)
            
            self.chapter_progress[chapter_title] = '已完成'
            return True
        except Exception as e:
            print(f"下载章节失败 {chapter_title}: {str(e)}")
            # 保存未完成标记以便后续重试
            if os.path.exists(file_path):
                os.remove(file_path)
            self.chapter_progress[chapter_title] = '失败'
            return False


class NovelDownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title('小说下载器')
        self.root.geometry('800x600')
        self.root.resizable(True, True)
        
        # 创建下载器实例
        self.downloader = NovelDownloader()
        self.downloader.chapter_progress = {}
        
        # 创建消息队列用于线程间通信
        self.queue = queue.Queue()
        
        # 创建UI
        self._create_widgets()
        
        # 启动消息处理循环
        self._process_queue()
    
    def _create_widgets(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding='10')
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # URL输入区域
        url_frame = ttk.LabelFrame(main_frame, text='小说信息', padding='10')
        url_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(url_frame, text='小说URL:').grid(row=0, column=0, sticky=tk.W, pady=5)
        self.url_entry = ttk.Entry(url_frame, width=70)
        self.url_entry.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)
        url_frame.columnconfigure(1, weight=1)
        
        # 下载选项区域
        options_frame = ttk.LabelFrame(main_frame, text='下载选项', padding='10')
        options_frame.pack(fill=tk.X, pady=5)
        
        # 章节范围选择
        ttk.Label(options_frame, text='章节范围:').grid(row=0, column=0, sticky=tk.W, pady=5)
        
        self.chapter_var = tk.StringVar(value='all')
        all_radio = ttk.Radiobutton(options_frame, text='全部章节', variable=self.chapter_var, value='all', command=self._toggle_chapter_input)
        all_radio.grid(row=0, column=1, sticky=tk.W, padx=5)
        
        range_radio = ttk.Radiobutton(options_frame, text='指定范围', variable=self.chapter_var, value='range', command=self._toggle_chapter_input)
        range_radio.grid(row=0, column=2, sticky=tk.W)
        
        ttk.Label(options_frame, text='从:').grid(row=0, column=3, sticky=tk.W)
        self.start_chapter = ttk.Entry(options_frame, width=5, state=tk.DISABLED)
        self.start_chapter.grid(row=0, column=4, sticky=tk.W)
        
        ttk.Label(options_frame, text='到:').grid(row=0, column=5, sticky=tk.W)
        self.end_chapter = ttk.Entry(options_frame, width=5, state=tk.DISABLED)
        self.end_chapter.grid(row=0, column=6, sticky=tk.W)
        
        # 保存路径选择
        ttk.Label(options_frame, text='保存路径:').grid(row=1, column=0, sticky=tk.W, pady=5)
        self.path_entry = ttk.Entry(options_frame, width=50)
        self.path_entry.grid(row=1, column=1, columnspan=4, sticky=tk.EW, padx=5, pady=5)
        self.path_entry.insert(0, os.path.join(os.getcwd(), 'novels'))
        
        browse_btn = ttk.Button(options_frame, text='浏览', command=self._browse_path)
        browse_btn.grid(row=1, column=5, sticky=tk.W)
        
        options_frame.columnconfigure(1, weight=1)
        
        # 控制按钮区域
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=10)
        
        self.start_btn = ttk.Button(btn_frame, text='开始下载', command=self._start_download)
        self.start_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(btn_frame, text='停止下载', command=self._stop_download, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # 进度显示区域
        progress_frame = ttk.LabelFrame(main_frame, text='下载进度', padding='10')
        progress_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, length=100, mode='determinate')
        self.progress_bar.pack(fill=tk.X, pady=5)
        
        self.status_label = ttk.Label(progress_frame, text='就绪', anchor=tk.W)
        self.status_label.pack(fill=tk.X, pady=5)
        
        # 日志区域
        log_frame = ttk.LabelFrame(main_frame, text='下载日志', padding='10')
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # 创建滚动条
        scrollbar = ttk.Scrollbar(log_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.log_text = tk.Text(log_frame, wrap=tk.WORD, yscrollcommand=scrollbar.set, height=10)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.log_text.yview)
        
        # 重定向stdout到文本框
        sys.stdout = TextRedirector(self.log_text, 'stdout')
        sys.stderr = TextRedirector(self.log_text, 'stderr')
    
    def _toggle_chapter_input(self):
        if self.chapter_var.get() == 'range':
            self.start_chapter.config(state=tk.NORMAL)
            self.end_chapter.config(state=tk.NORMAL)
        else:
            self.start_chapter.config(state=tk.DISABLED)
            self.end_chapter.config(state=tk.DISABLED)
    
    def _browse_path(self):
        path = filedialog.askdirectory()
        if path:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, path)
    
    def _start_download(self):
        url = self.url_entry.get().strip()
        save_path = self.path_entry.get().strip()
        
        if not url:
            messagebox.showerror('错误', '请输入小说URL')
            return
        
        if not save_path:
            messagebox.showerror('错误', '请选择保存路径')
            return
        
        start_chapter = None
        end_chapter = None
        
        if self.chapter_var.get() == 'range':
            try:
                start_chapter = int(self.start_chapter.get()) if self.start_chapter.get() else None
                end_chapter = int(self.end_chapter.get()) if self.end_chapter.get() else None
                
                if start_chapter and end_chapter and start_chapter > end_chapter:
                    messagebox.showerror('错误', '起始章节不能大于结束章节')
                    return
            except ValueError:
                messagebox.showerror('错误', '章节号必须为数字')
                return
        
        # 禁用开始按钮，启用停止按钮
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        
        # 在新线程中开始下载
        self.download_thread = threading.Thread(
            target=self._download_novel_thread,
            args=(url, save_path, start_chapter, end_chapter),
            daemon=True
        )
        self.download_thread.start()
    
    def _download_novel_thread(self, url, save_path, start_chapter, end_chapter):
        try:
            # 获取小说信息
            novel_info = self.downloader.get_novel_info(url)
            if not novel_info:
                self.queue.put(('error', '获取小说信息失败'))
                return
            
            # 获取章节列表
            chapter_list = self.downloader.get_chapter_list(url)
            if not chapter_list:
                self.queue.put(('error', '获取章节列表失败'))
                return
            
            total_chapters = len(chapter_list)
            self.queue.put(('total', total_chapters))
            self.queue.put(('status', f'开始下载《{novel_info["title"]}》，共{total_chapters}章'))
            
            # 定义进度回调函数
            def progress_callback(percent, chapter_title):
                self.queue.put(('progress', percent))
                self.queue.put(('status', f'正在下载: {chapter_title} ({percent:.1f}%)'))
            
            # 执行下载并传入进度回调
            self.downloader.download_novel(url, save_path, start_chapter, end_chapter, progress_callback)
            self.queue.put(('complete', '下载完成'))
        except Exception as e:
            self.queue.put(('error', f'下载出错: {str(e)}'))
        finally:
            # 恢复按钮状态
            self.queue.put(('enable_buttons', None))
    
    def _stop_download(self):
        # 这里可以实现停止下载的逻辑
        self.queue.put(('status', '正在停止下载...'))
        self.stop_btn.config(state=tk.DISABLED)
    
    def _process_queue(self):
        while not self.queue.empty():
            message_type, data = self.queue.get()
            
            if message_type == 'status':
                self.status_label.config(text=data)
                self.log_text.insert(tk.END, data + '\n')
                self.log_text.see(tk.END)
            elif message_type == 'progress':
                self.progress_var.set(data)
            elif message_type == 'total':
                self.progress_bar['maximum'] = data
            elif message_type == 'complete':
                self.status_label.config(text=data)
                self.log_text.insert(tk.END, data + '\n')
                self.log_text.see(tk.END)
                messagebox.showinfo('完成', data)
                self.start_btn.config(state=tk.NORMAL)
                self.stop_btn.config(state=tk.DISABLED)
            elif message_type == 'error':
                self.status_label.config(text=data)
                self.log_text.insert(tk.END, data + '\n')
                self.log_text.see(tk.END)
                messagebox.showerror('错误', data)
                self.start_btn.config(state=tk.NORMAL)
                self.stop_btn.config(state=tk.DISABLED)
            elif message_type == 'enable_buttons':
                self.start_btn.config(state=tk.NORMAL)
                self.stop_btn.config(state=tk.DISABLED)
        
        self.root.after(100, self._process_queue)


class TextRedirector:
    def __init__(self, widget, tag='stdout'):
        self.widget = widget
        self.tag = tag

    def write(self, str):
        self.widget.configure(state=tk.NORMAL)
        self.widget.insert(tk.END, str)
        self.widget.configure(state=tk.DISABLED)
        self.widget.see(tk.END)

    def flush(self):
        pass