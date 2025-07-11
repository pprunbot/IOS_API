import os
import re
import requests
from flask import Flask, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import time

app = Flask(__name__)

URLS = [
    'https://ccbaohe.com/appleID/',
    'https://ccbaohe.com/appleID2/',
    'https://tkbaohe.com/Shadowrocket/',
    'https://ao.ke/',
]

OUTPUT_DIR = "/tmp/site_sources"
LOG_FILE = "/tmp/fetch_log.txt"

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

def extract_emails_and_passwords(html_content, url):
    accounts_password_pairs = []

    if 'ao.ke' in url:
        # 处理 ao.ke 特定的 HTML 结构
        pattern = r'<a href="/cdn-cgi/l/email-protection" class="__cf_email__" data-cfemail="([a-fA-F0-9]+)">.*?</a>\s*密码：(.*?)<br>'
        matches = re.findall(pattern, html_content, re.DOTALL)
        for match in matches:
            encoded_email = match[0]
            password = match[1].strip()
            email = decode_cf_email(encoded_email)

            password = password.replace("\\u0026", "&")
            status = "正常" if password != "暂无可用账号" else "异常"

            accounts_password_pairs.append({
                "id": str(int(time.time() * 1000)),
                "email": email,
                "password": password,
                "status": status,
            })
    else:
        # 处理其他网站的 HTML 结构
        card_body_pattern = r'<div class="card-body">.*?<a href="/cdn-cgi/l/email-protection#([a-fA-F0-9]+)" class="__cf_email__" style="display: none;">.*?</a>.*?<button.*?onclick=".*?copy\(\'([^\']+)\'\)".*?>复制密码</button>.*?</div>'
        matches = re.findall(card_body_pattern, html_content, re.DOTALL)
        for match in matches:
            encoded_email = match[0]
            password = match[1]

            email = decode_cf_email(encoded_email)
            password = password.replace("\\u0026", "&")
            status = "正常" if password != "暂无可用账号" else "异常"

            accounts_password_pairs.append({
                "id": str(int(time.time() * 1000)),
                "email": email,
                "password": password,
                "status": status,
            })

    return accounts_password_pairs

def fetch_sources():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    logs = []
    results = []

    for url in URLS:
        try:
            response = requests.get(url)
            response.raise_for_status()
            response.encoding = 'utf-8'
            html_content = response.text

            filename = os.path.join(OUTPUT_DIR, f"{url.split('/')[-2]}.html")
            with open(filename, 'w', encoding='utf-8') as file:
                file.write(html_content)

            accounts_passwords = extract_emails_and_passwords(html_content, url)
            logs.append({
                "url": url,
                "status": "成功",
                "account_password_pairs": accounts_passwords,
            })
            results.extend(accounts_passwords)
        except Exception as e:
            error_msg = str(e)
            logs.append({
                "url": url,
                "status": "错误",
                "error": error_msg,
            })

    with open(LOG_FILE, 'w', encoding='utf-8') as log_file:
        for log in logs:
            log_file.write(str(log) + "\n")

    response_data = {
        "id": results,
        "message": "获取成功"
    }
    return response_data

def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        func=fetch_sources,
        trigger=IntervalTrigger(minutes=30),
        id='fetch_sources_job',
        name='每半小时抓取网站',
        replace_existing=True
    )
    scheduler.start()

@app.route('/fetch_sources', methods=['GET'])
def fetch_sources_route():
    results = fetch_sources()
    return jsonify(results), 200

if __name__ == '__main__':
    start_scheduler()
    app.run(host='0.0.0.0', port=5000)
