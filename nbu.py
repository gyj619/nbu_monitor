import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import hashlib
import pickle
import os
from datetime import datetime
import logging
from typing import List, Dict, Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class NBUMonitor:
    def __init__(self, url: str, email_to: str, state_file: str = 'nbu_state.pkl'):
        self.url = url
        self.email_to = email_to
        self.state_file = state_file

        # 邮件配置：密码从 GitHub Secrets 的环境变量中读取，绝对安全
        self.email_config = {
            'smtp_server': 'smtp.qq.com',
            'smtp_port': 587,
            'sender_email': '2305710134@qq.com',
            'sender_password': os.environ.get('EMAIL_PASS') 
        }
        self.last_notifications = self.load_state()

    def fetch_webpage(self) -> Optional[str]:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            response = requests.get(self.url, headers=headers, timeout=15)
            response.encoding = 'utf-8'
            response.raise_for_status()
            logging.info("成功获取宁波大学网页内容")
            return response.text
        except requests.RequestException as e:
            logging.error(f"获取网页失败: {e}")
            return None

    def parse_notifications(self, html_content: str) -> List[Dict[str, str]]:
        notifications = []
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            entries = soup.find_all('div', class_='entry-header')
            for entry in entries:
                h4 = entry.find('h4')
                if h4 and h4.find('a'):
                    link = h4.find('a')
                    title = link.get('title', link.text.strip())
                    url = link.get('href', '')
                    if not url.startswith('http'):
                        url = 'https://graduate.nbu.edu.cn' + url
                    time_tag = entry.find('time', class_='entry-date')
                    pub_time = time_tag.text.strip() if time_tag else ''

                    notification = {
                        'title': title,
                        'url': url,
                        'pub_time': pub_time,
                        'content_hash': hashlib.md5(f"{title}{url}".encode()).hexdigest()
                    }
                    notifications.append(notification)

            logging.info(f"网页共解析到 {len(notifications)} 条通知")
            return notifications
        except Exception as e:
            logging.error(f"解析网页失败: {e}")
            return []

    def send_email(self, notifications: List[Dict[str, str]]):
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_config['sender_email']
            msg['To'] = self.email_to
            msg['Subject'] = f'【宁波大学】发现 {len(notifications)} 条招生新通知'

            content = f"""
            <html>
            <body>
            <p><strong>宁波大学研究生院硕士生招生最新通知：</strong></p>
            <p>监测时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <hr>
            """
            for notif in notifications:
                content += f"""
                <p><strong>标题：</strong>{notif['title']}</p>
                <p><strong>时间：</strong>{notif['pub_time']}</p>
                <p><strong>链接：</strong><a href="{notif['url']}">{notif['url']}</a></p>
                <hr>
                """
            content += """
            <p><em>本邮件由 GitHub Actions 自动监测系统发送。</em></p>
            </body>
            </html>
            """
            msg.attach(MIMEText(content, 'html', 'utf-8'))

            with smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port']) as server:
                server.starttls()
                server.login(self.email_config['sender_email'], self.email_config['sender_password'])
                server.send_message(msg)
            logging.info(f"成功发送邮件通知到 {self.email_to}")
        except Exception as e:
            logging.error(f"发送邮件失败，请检查环境变量 EMAIL_PASS 是否配置正确。错误信息: {e}")

    def load_state(self) -> set:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'rb') as f:
                    return pickle.load(f)
            except Exception as e:
                logging.error(f"加载状态文件失败: {e}")
        return set()

    def save_state(self, notifications: List[Dict[str, str]]):
        try:
            current_hashes = {n['content_hash'] for n in notifications}
            with open(self.state_file, 'wb') as f:
                pickle.dump(current_hashes, f)
            logging.info("状态保存成功")
        except Exception as e:
            logging.error(f"保存状态失败: {e}")

    def run(self):
        logging.info(f"开始执行宁大通知监测")
        html_content = self.fetch_webpage()
        if not html_content:
            return

        current_notifications = self.parse_notifications(html_content)
        if not current_notifications:
            return

        new_notifications = []
        for notif in current_notifications:
            if notif['content_hash'] not in self.last_notifications:
                new_notifications.append(notif)

        if new_notifications:
            if not self.last_notifications:
                logging.info(f"首次在 GitHub 运行，静默记录现有的 {len(current_notifications)} 条通知，不发送邮件。")
            else:
                logging.info(f"发现 {len(new_notifications)} 条新通知！准备发送邮件。")
                self.send_email(new_notifications)
            
            # 更新状态文件
            self.save_state(current_notifications)
        else:
            logging.info("本次检查未发现新通知。")

def main():
    target_url = "https://graduate.nbu.edu.cn/zsgz/ssszs.htm"
    email_to = "2305710134@qq.com"  # 接收通知的邮箱

    monitor = NBUMonitor(url=target_url, email_to=email_to)
    monitor.run()

if __name__ == "__main__":
    main()
