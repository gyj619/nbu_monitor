import requests
from bs4 import BeautifulSoup
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import hashlib
import pickle
import os
from datetime import datetime
import schedule
import logging
from typing import List, Dict, Optional

# 配置日志
logging.basicConfig(
	level=logging.INFO,
	format='%(asctime)s - %(levelname)s - %(message)s',
	handlers=[
		logging.FileHandler('notification_monitor.log', encoding='utf-8'),
		logging.StreamHandler()
	]
)


class NotificationMonitor:
	def __init__(self, url: str, email_to: str, check_interval_minutes: int = 10, report_interval_hours: int = 3,
	             state_file: str = 'monitor_state.pkl'):
		self.url = url
		self.email_to = email_to
		self.check_interval_minutes = check_interval_minutes
		self.report_interval_hours = report_interval_hours
		self.state_file = state_file

		# 邮件发送配置
		self.email_config = {
			'smtp_server': 'smtp.qq.com',
			'smtp_port': 587,
			'sender_email': '2305710134@qq.com',
			'sender_password': 'bgumwldjzbfedjee'  # 请确保这是您应用专用密码
		}
		self.last_notifications = self.load_state()

	def fetch_webpage(self) -> Optional[str]:
		try:
			headers = {
				'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
			}
			response = requests.get(self.url, headers=headers, timeout=10)
			response.encoding = 'utf-8'
			response.raise_for_status()
			logging.info("成功获取网页内容")
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
			return notifications[:3]  # 只保留最新3条
		except Exception as e:
			logging.error(f"解析网页失败: {e}")
			return []

	def send_email(self, notifications: List[Dict[str, str]], has_new: bool = True):
		try:
			msg = MIMEMultipart()
			msg['From'] = self.email_config['sender_email']
			msg['To'] = self.email_to

			# 根据是否有新通知设置不同的邮件主题
			if has_new:
				msg['Subject'] = f'【宁波大学研究生院】发现 {len(notifications)} 条新通知'
				status_text = f"发现 {len(notifications)} 条新通知（最多展示最新3条）："
			else:
				msg['Subject'] = '【宁波大学研究生院】常规监测汇报：暂无新通知'
				status_text = "本次检查未发现新通知。以下是当前最新的 3 条通知存档："

			content = f"""
            <html>
            <body>
            <p><strong>宁波大学研究生院硕士生招生监测反馈</strong></p>
            <p>监测时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>{status_text}</p>
            """
			for notif in notifications:
				content += f"""
                <p><strong>标题：</strong>{notif['title']}</p>
                <p><strong>时间：</strong>{notif['pub_time']}</p>
                <p><strong>链接：</strong><a href="{notif['url']}">{notif['url']}</a></p>
                <hr>
                """
			content += """
            <p><em>本邮件由自动监测系统发送，请勿回复。</em></p>
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
			logging.error(f"发送邮件失败: {e}")

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

	def check_for_updates(self):
		"""
		通用的检查更新逻辑，返回新通知列表和所有通知列表
		"""
		logging.info(f"开始检查更新 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
		html_content = self.fetch_webpage()
		if not html_content:
			return [], []

		current_notifications = self.parse_notifications(html_content)
		if not current_notifications:
			return [], []

		new_notifications = []
		for notif in current_notifications:
			if notif['content_hash'] not in self.last_notifications:
				new_notifications.append(notif)

		return new_notifications, current_notifications

	def check_and_send_if_updated(self):
		"""
		检查是否有新通知，如果有则立即发送邮件
		"""
		new_notifications, current_notifications = self.check_for_updates()

		if new_notifications:
			logging.info(f"发现 {len(new_notifications)} 条新通知")
			self.send_email(new_notifications, has_new=True)
			# 更新本地状态为最新的所有通知
			self.save_state(current_notifications)
			self.last_notifications = {n['content_hash'] for n in current_notifications}
		else:
			logging.info("本次检查未发现新通知")

	def send_regular_report(self):
		"""
		发送3小时一次的常规汇报邮件
		"""
		logging.info(f"发送3小时常规监测汇报 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
		html_content = self.fetch_webpage()
		if not html_content:
			# 如果获取失败，至少发个空汇报
			self.send_email([], has_new=False)
			return

		current_notifications = self.parse_notifications(html_content)
		# 仅发送汇报，不更新状态，以免错过在汇报周期内新增的通知
		self.send_email(current_notifications, has_new=False)

	def start_monitoring(self):
		logging.info(f"开始监测 - URL: {self.url}")
		logging.info(f"新通知检查间隔: {self.check_interval_minutes} 分钟")
		logging.info(f"常规汇报间隔: {self.report_interval_hours} 小时")
		logging.info(f"通知邮箱: {self.email_to}")

		# 启动时先进行一次检查和汇报
		self.check_and_send_if_updated()
		self.send_regular_report()  # 假设启动时也想收到一次汇报

		# 设置定时任务
		schedule.every(self.check_interval_minutes).minutes.do(self.check_and_send_if_updated)
		schedule.every(self.report_interval_hours).hours.do(self.send_regular_report)

		while True:
			try:
				schedule.run_pending()
				time.sleep(10)  # 保持较短的睡眠时间以响应调度
			except KeyboardInterrupt:
				logging.info("监测程序已停止")
				break
			except Exception as e:
				logging.error(f"程序运行错误: {e}")
				time.sleep(60)  # 出错后等待一段时间再继续


def main():
	target_url = "https://graduate.nbu.edu.cn/zsgz/ssszs.htm"
	email_to = "2305710134@qq.com"

	# 创建监控实例，参数：URL, 邮箱, 新通知检查间隔(分钟), 常规汇报间隔(小时)
	monitor = NotificationMonitor(
		url=target_url,
		email_to=email_to,
		check_interval_minutes=10,  # 每10分钟检查一次新通知
		report_interval_hours=3  # 每3小时发送一次常规汇报
	)

	print("=" * 50)
	print("宁波大学研究生院硕士生招生通知监测系统")
	print("=" * 50)
	print("\n重要提示：")
	print(f"程序将每 {monitor.check_interval_minutes} 分钟检查一次新通知")
	print(f"程序将每 {monitor.report_interval_hours} 小时发送一次常规汇报")
	print("按 Ctrl+C 停止程序")
	print("=" * 50)

	monitor.start_monitoring()


if __name__ == "__main__":
	main()