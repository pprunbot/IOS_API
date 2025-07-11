import os
import re
import requests
from flask import Flask, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import time

app = Flask(__name__)

# 要抓取源码的 URL 列表
URLS = [
    'https://ccbaohe.com/appleID/',
    'https://ccbaohe.com/appleID2/',
    'https://tkbaohe.com/Shadowrocket/',
]

OUTPUT_DIR = "/tmp/site_sources"  # 更改存储路径以避免权限问题
LOG_FILE = "/tmp/fetch_log.txt"  # 使用 /tmp 目录

# 解密 Cloudflare 邮件保护的函数
def decode_cf_email(encoded_string):
    try:
        r = int(encoded_string[:2], 16)
        email = ''.join(
            chr(int(encoded_string[i:i+2], 16) ^ r)
            for i in range(2, len(encoded_string), 2)
        )
        return email
    except Exception as e:
        return f"解密失败: {str(e)}"

# 匹配邮箱和密码
def extract_emails_and_passwords(html_content):
    accounts_password_pairs = []

    # 匹配每个card-body的内容
    card_body_pattern = r'<div class="card-body">.*?<a href="/cdn-cgi/l/email-protection#([a-fA-F0-9]+)" class="__cf_email__" style="display: none;">.*?</a>.*?<button.*?onclick=".*?copy\(\'([^\']+)\'\)".*?>复制密码</button>.*?</div>'
    matches = re.findall(card_body_pattern, html_content, re.DOTALL)

    for match in matches:
        encoded_email = match[0]
        password = match[1]

        # 解密邮箱
        email = decode_cf_email(encoded_email)

        # 判断密码是否为“暂无可用账号”，如果是则标记状态为“异常”
        status = "正常" if password != "暂无可用账号" else "异常"

        if email != "解密失败":
            # 给每个账号密码对一个ID
            accounts_password_pairs.append({
                "id": str(int(time.time() * 1000)),  # 生成一个唯一的ID
                "email": email,
                "password": password,
                "status": status,
            })
        else:
            accounts_password_pairs.append({
                "id": str(int(time.time() * 1000)),
                "email": "解密失败",
                "password": password,
                "status": "异常",
            })

    return accounts_password_pairs

# 抓取数据的函数
def fetch_sources():
    os.makedirs(OUTPUT_DIR, exist_ok=True)  # 确保输出目录存在
    logs = []
    results = []

    print("开始抓取网站源码...\n")

    for url in URLS:
        print(f"处理 URL: {url}")
        try:
            response = requests.get(url)
            response.raise_for_status()
            response.encoding = 'utf-8'  # 设置正确的字符编码
            html_content = response.text
            print(f"成功抓取 URL: {url}")

            # 保存 HTML 文件
            filename = os.path.join(OUTPUT_DIR, f"{url.split('/')[-2]}.html")
            with open(filename, 'w', encoding='utf-8') as file:
                file.write(html_content)
            print(f"HTML 内容已保存到: {filename}")

            # 提取邮箱和密码
            accounts_passwords = extract_emails_and_passwords(html_content)
            print(f"提取到的账号和密码: {accounts_passwords}")

            logs.append({
                "url": url,
                "status": "成功",
                "account_password_pairs": accounts_passwords,
            })
            results.extend(accounts_passwords)
            print(f"完成 URL: {url}\n")
        except Exception as e:
            error_msg = str(e)
            logs.append({
                "url": url,
                "status": "错误",
                "error": error_msg,
            })
            print(f"处理 URL 时出错: {url}")
            print(f"错误信息: {error_msg}\n")

    # 写入日志文件
    print(f"抓取完成，写入日志到 {LOG_FILE}...")
    with open(LOG_FILE, 'w', encoding='utf-8') as log_file:
        for log in logs:
            log_file.write(str(log) + "\n")

    print(f"日志写入完成，服务已返回结果。\n")

    # 格式化返回数据
    response_data = {
        "id": results,
        "message": "获取成功"
    }
    return response_data

# 定时任务：每半小时抓取一次
def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=fetch_sources,
        trigger=IntervalTrigger(minutes=30),  # 每30分钟执行一次
        id='fetch_sources_job',
        name='每半小时抓取网站',
        replace_existing=True
    )
    scheduler.start()
    print("定时任务已启动，每半小时抓取一次网站。")

@app.route('/api/v1/xhj', methods=['GET'])
def fetch_sources_route():
    results = fetch_sources()
    return jsonify(results), 200

if __name__ == '__main__':
    # 启动定时任务
    start_scheduler()
    app.run(host='0.0.0.0', port=5000)
