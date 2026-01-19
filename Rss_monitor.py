import sqlite3
import feedparser
import yaml
import requests
import time
import os
import argparse
from datetime import datetime
import dingtalkchatbot.chatbot as cb
from jinja2 import Template



__version__ = "1.1.4"




# 加载配置文件
def load_config():
    # 从文件加载配置
    config = {}
    try:
        with open('config.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f) or {}
    except FileNotFoundError:
        print("未找到config.yaml文件，将使用环境变量配置")
    except Exception as e:
        print(f"加载config.yaml文件出错: {str(e)}")
    
    # 初始化push配置
    push_config = config.get('push', {})
    
    # 钉钉推送配置 - 环境变量优先级高于配置文件
    if 'dingding' not in push_config:
        push_config['dingding'] = {}
    
    push_config['dingding']['webhook'] = os.environ.get('DINGDING_WEBHOOK', push_config['dingding'].get('webhook', ''))
    push_config['dingding']['secret_key'] = os.environ.get('DINGDING_SECRET', push_config['dingding'].get('secret_key', ''))
    push_config['dingding']['switch'] = os.environ.get('DINGDING_SWITCH', push_config['dingding'].get('switch', 'OFF'))
    
    # 飞书推送配置 - 环境变量优先级高于配置文件
    if 'feishu' not in push_config:
        push_config['feishu'] = {}
    
    push_config['feishu']['webhook'] = os.environ.get('FEISHU_WEBHOOK', push_config['feishu'].get('webhook', ''))
    push_config['feishu']['switch'] = os.environ.get('FEISHU_SWITCH', push_config['feishu'].get('switch', 'OFF'))
    
    # Telegram Bot推送配置 - 环境变量优先级高于配置文件
    if 'tg_bot' not in push_config:
        push_config['tg_bot'] = {}
    
    push_config['tg_bot']['token'] = os.environ.get('TELEGRAM_TOKEN', push_config['tg_bot'].get('token', ''))
    push_config['tg_bot']['group_id'] = os.environ.get('TELEGRAM_GROUP_ID', push_config['tg_bot'].get('group_id', ''))
    push_config['tg_bot']['switch'] = os.environ.get('TELEGRAM_SWITCH', push_config['tg_bot'].get('switch', 'OFF'))
    
    # Discard推送配置 - 环境变量优先级高于配置文件
    if 'discard' not in push_config:
        push_config['discard'] = {}
    
    push_config['discard']['webhook'] = os.environ.get('DISCARD_WEBHOOK', push_config['discard'].get('webhook', ''))
    push_config['discard']['switch'] = os.environ.get('DISCARD_SWITCH', push_config['discard'].get('switch', 'OFF'))
    push_config['discard']['send_daily_report'] = os.environ.get('DISCARD_SEND_DAILY_REPORT', push_config['discard'].get('send_daily_report', 'OFF'))
    push_config['discard']['send_normal_msg'] = os.environ.get('DISCARD_SEND_NORMAL_MSG', push_config['discard'].get('send_normal_msg', 'ON'))
    
    # 添加夜间休眠配置
    config['night_sleep'] = {
        'switch': os.environ.get('NIGHT_SLEEP_SWITCH', config.get('night_sleep', {}).get('switch', 'ON'))
    }
    
    # 添加生成日报配置
    config['daily_report'] = {
        'switch': os.environ.get('DAILY_REPORT_SWITCH', config.get('daily_report', {}).get('switch', 'ON'))
    }
    
    # 加载代理配置
    proxy_config = config.get('proxy', {})
    config['proxy'] = {
        'enable': os.environ.get('PROXY_ENABLE', proxy_config.get('enable', 'OFF')),
        'http_proxy': os.environ.get('HTTP_PROXY', proxy_config.get('http_proxy', '')),
        'https_proxy': os.environ.get('HTTPS_PROXY', proxy_config.get('https_proxy', '')),
        'no_proxy': os.environ.get('NO_PROXY', proxy_config.get('no_proxy', ''))
    }
    
    config['push'] = push_config
    return config

# 判断是否应该进行夜间休眠
def should_sleep():
    # 加载配置
    config = load_config()
    # 检查是否开启夜间休眠功能
    sleep_switch = os.environ.get('NIGHT_SLEEP_SWITCH', config.get('night_sleep', {}).get('switch', 'ON'))
    if sleep_switch != 'ON':
        return False
    
    # 判断当前时间（北京时间）是否在0-7点之间
    # 获取当前UTC时间，转换为北京时间（UTC+8）
    now_utc = datetime.utcnow()
    # 转换为北京时间
    now_bj = now_utc.hour + 8
    # 处理跨天情况
    if now_bj >= 24:
        now_bj -= 24
    
    return now_bj < 7

# 初始化数据库
def init_database():
    conn = sqlite3.connect('articles.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        link TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    return conn

# 获取数据并检查更新
def check_for_updates(feed_url, site_name, cursor, conn, send_push=True):
    print(f"{site_name} 监控中... ")
    data_list = []
    file_data = feedparser.parse(feed_url)
    data = file_data.entries
    if data:
        data_title = data[0].get('title')
        data_link = data[0].get('link')
        data_list.append(data_title)
        data_list.append(data_link)

        # 查询数据库中是否存在相同链接的文章
        cursor.execute("SELECT * FROM items WHERE link = ?", (data_link,))
        result = cursor.fetchone()
        if result is None:
            # 未找到相同链接的文章
            push_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
            
            # 只有在send_push为True时才发送推送
            if send_push:
                push_message(f"{site_name}今日更新", f"标题: {data_title}\n链接: {data_link}\n推送时间：{push_time}")

            # 存储到数据库 with a timestamp
            cursor.execute("INSERT INTO items (title, link, timestamp) VALUES (?, ?, CURRENT_TIMESTAMP)", (data_title, data_link))
            conn.commit()
    return data_list

# 获取代理配置

def get_proxies():
    config = load_config()
    proxy_config = config.get('proxy', {})
    
    if proxy_config.get('enable', 'OFF') == 'OFF':
        return None
    
    proxies = {}
    if proxy_config.get('http_proxy'):
        proxies['http'] = proxy_config.get('http_proxy')
    if proxy_config.get('https_proxy'):
        proxies['https'] = proxy_config.get('https_proxy')
    
    return proxies if proxies else None

# 推送函数
def push_message(title, content):
    config = load_config()
    push_config = config.get('push', {})
    
    # 钉钉推送
    if 'dingding' in push_config and push_config['dingding'].get('switch', '') == "ON":
        send_dingding_msg(push_config['dingding'].get('webhook'), push_config['dingding'].get('secret_key'), title,
                          content)

    # 飞书推送
    if 'feishu' in push_config and push_config['feishu'].get('switch', '') == "ON":
        send_feishu_msg(push_config['feishu'].get('webhook'), title, content)

    # Telegram Bot推送
    if 'tg_bot' in push_config and push_config['tg_bot'].get('switch', '') == "ON":
        send_tg_bot_msg(push_config['tg_bot'].get('token'), push_config['tg_bot'].get('group_id'), title, content)
    
    # Discard推送
    if 'discard' in push_config and push_config['discard'].get('switch', '') == "ON" and push_config['discard'].get('send_normal_msg', '') == "ON":
        send_discard_msg(push_config['discard'].get('webhook'), title, content)

# 飞书推送
def send_feishu_msg(webhook, title, content):
    feishu(title, content, webhook)

# Telegram Bot推送
def send_tg_bot_msg(token, group_id, title, content):
    tgbot(title, content, token, group_id)

# 钉钉推送
def dingding(text, msg, webhook, secretKey):
    try:
        if not webhook or webhook == "https://oapi.dingtalk.com/robot/send?access_token=你的token":
            print(f"钉钉推送跳过：webhook地址未配置")
            return
            
        if not secretKey or secretKey == "你的Key":
            print(f"钉钉推送跳过：secret_key未配置")
            return
            
        ding = cb.DingtalkChatbot(webhook, secret=secretKey)
        ding.send_text(msg='{}\r\n{}'.format(text, msg), is_at_all=False)
        print(f"钉钉推送成功: {text}")
    except Exception as e:
        print(f"钉钉推送失败: {str(e)}")

# 飞书推送
def feishu(text, msg, webhook):
    try:
        if not webhook or webhook == "飞书的webhook地址":
            print(f"飞书推送跳过：webhook地址未配置")
            return
            
        headers = {
            "Content-Type": "application/json;charset=utf-8"
        }
        data = {
            "msg_type": "text",
            "content": {
                "text": '{}\n{}'.format(text, msg)
            }
        }
        
        # 飞书推送不需要代理
        response = requests.post(webhook, json=data, headers=headers, timeout=10)
        response.raise_for_status()
        print(f"飞书推送成功: {text}")
    except Exception as e:
        print(f"飞书推送失败: {str(e)}")

# 钉钉推送
def send_dingding_msg(webhook, secret_key, title, content):
    dingding(title, content, webhook, secret_key)

# Discard推送
def send_discard_msg(webhook, title, content, is_daily_report=False, html_file=None, markdown_content=None):
    # 检查是否是占位符
    if not webhook or webhook == "discard的webhook地址":
        print(f"Discard推送跳过：webhook地址未配置")
        return
    
    # 检查webhook地址格式
    if not webhook.startswith('http'):
        print(f"Discard推送失败：webhook地址格式错误，必须以http或https开头")
        return
    
    try:
        headers = {
            "Content-Type": "application/json;charset=utf-8"
        }
        
        if is_daily_report and html_file:
            # 推送日报，Discord Webhook不支持直接发送HTML格式，使用文本格式发送链接
            # 生成GitHub Pages URL
            github_pages_url = f"https://adminlove520.github.io/Rss_monitor/{html_file}"
            
            # 构建推送内容
            # 标题已经包含"RSS日报"，所以这里不再重复添加
            # 使用time.strftime获取当前日期
            current_date = time.strftime('%Y-%m-%d', time.localtime())
            push_content = f"**{title}**\n共收集到 {content.split()[1]} 篇文章\n欢迎提交RSS源：[GitHub Issue](https://github.com/adminlove520/Rss_monitor/issues/new/choose)\nDaily_{current_date}:{github_pages_url}\n\n"
            
            # 添加markdown内容（预览格式）
            if markdown_content:
                # 移除markdown标题和最后更新时间，只保留文章列表
                lines = markdown_content.split('\n')
                preview_content = []
                include_lines = False
                for line in lines:
                    # 从第一个## 开始记录文章列表
                    if line.startswith('## '):
                        include_lines = True
                    # 跳过Power By信息
                    if line.strip().startswith('Power By') or line.strip().startswith('---'):
                        continue
                    if include_lines:
                        preview_content.append(line)
                
                # 拼接预览内容，移除多余空行
            push_content += "日报内容预览：\n"
            filtered_preview = [line for line in preview_content if line.strip()]
            push_content += '\n'.join(filtered_preview)
            push_content += "\n"
        
            # 添加Power By信息（正确格式，避免多余的分隔线和空格）
            push_content += f"Power By 东方隐侠安全团队·Anonymous@ [隐侠安全客栈](https://www.dfyxsec.com/)\n"
            
            data = {
                "content": push_content
            }
        else:
            # 推送普通消息，使用Discord Webhook支持的格式
            data = {
                "content": f"**{title}**\n{content}"
            }
        
        print(f"正在发送Discard推送：{title}")
        print(f"目标地址：{webhook}")
        
        # 获取代理配置
        proxies = get_proxies()
        if proxies:
            print(f"使用代理：{proxies}")
        
        # 使用较短的超时时间，避免长时间阻塞
        response = requests.post(webhook, json=data, headers=headers, timeout=5, proxies=proxies)
        
        print(f"Discard推送响应状态码：{response.status_code}")
        
        # 检查响应状态
        if response.status_code in [200, 204]:
            print(f"Discard推送成功: {title}")
        else:
            print(f"Discard推送失败: HTTP状态码 - {response.status_code}")
            print(f"响应内容: {response.text}")
            
            # 提供解决方案建议
            if response.status_code == 401:
                print("建议：请检查webhook地址是否正确，可能包含无效的token")
            elif response.status_code == 404:
                print("建议：webhook地址不存在，请检查webhook地址是否正确")
            elif response.status_code == 429:
                print("建议：超出Discord API速率限制，请稍后再试")
            elif response.status_code >= 500:
                print("建议：Discord服务器错误，请稍后再试")
    except requests.exceptions.Timeout:
        print(f"Discard推送失败: 连接超时")
        print("建议：检查网络连接，或尝试使用更快的网络环境")
    except requests.exceptions.ConnectionError:
        print(f"Discard推送失败: 网络连接错误")
        print("建议：检查网络连接，确保可以访问discord.com")
        print("可以尝试使用ping命令测试：ping discord.com")
    except requests.exceptions.RequestException as e:
        print(f"Discard推送失败: 请求异常 - {str(e)}")
    except Exception as e:
        print(f"Discard推送失败: 未知错误 - {str(e)}")

# 生成日报

def generate_daily_report(cursor):
    print("开始生成日报...")
    
    # 获取当前日期和时间
    current_date = time.strftime('%Y-%m-%d', time.localtime())
    current_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    
    # 创建目录结构
    archive_dir = f'archive/{current_date}'
    os.makedirs(archive_dir, exist_ok=True)
    
    # 从数据库中获取当天的所有文章
    cursor.execute("SELECT title, link, timestamp FROM items WHERE date(timestamp) = date('now') ORDER BY timestamp DESC")
    articles = cursor.fetchall()
    
    # 生成markdown内容
    markdown_content = f"# RSS日报 {current_date}\n\n"
    markdown_content += f"共收集到 {len(articles)} 篇文章\n"
    markdown_content += f"最后更新时间：{current_time}\n\n"
    
    # 准备文章数据，用于HTML模板
    article_list = []
    for article in articles:
        title, link, timestamp = article
        markdown_content += f"## [{title}]({link})\n"
        markdown_content += f"发布时间：{timestamp}\n\n"
        
        # 添加到文章列表
        article_list.append({
            'title': title,
            'link': link,
            'timestamp': timestamp
        })
    
    # 添加Power By信息（纯markdown格式，避免HTML标签在Discord中显示为文本）
    markdown_content += f"---\n"
    markdown_content += f"Power By 东方隐侠安全团队·Anonymous@ [隐侠安全客栈](https://www.dfyxsec.com/)\n"
    markdown_content += f"---\n"
    
    # 写入markdown文件
    markdown_file = f'{archive_dir}/Daily_{current_date}.md'
    is_update = os.path.exists(markdown_file)
    with open(markdown_file, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    if is_update:
        print(f"Markdown日报已更新：{markdown_file}")
    else:
        print(f"Markdown日报已生成：{markdown_file}")
    
    # 生成HTML内容
    try:
        # 读取HTML模板
        with open('template.html', 'r', encoding='utf-8') as f:
            template_content = f.read()
        
        # 渲染HTML模板
        template = Template(template_content)
        html_content = template.render(
            date=current_date,
            count=len(articles),
            update_time=current_time,
            articles=article_list
        )
        
        # 写入HTML文件
        html_file = f'{archive_dir}/Daily_{current_date}.html'
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        if is_update:
            print(f"HTML日报已更新：{html_file}")
        else:
            print(f"HTML日报已生成：{html_file}")
        
        # 更新index.html
        update_index_html(current_date, article_list, len(articles))
        
        # Discard推送日报
        config = load_config()
        push_config = config.get('push', {})
        if 'discard' in push_config and push_config['discard'].get('switch', '') == "ON" and push_config['discard'].get('send_daily_report', '') == "ON":
            send_discard_msg(
                push_config['discard'].get('webhook'),
                f"RSS日报 {current_date}",
                f"共收集到 {len(articles)} 篇文章",
                is_daily_report=True,
                html_file=html_file,
                markdown_content=markdown_content
            )
        
    except Exception as e:
        print(f"生成HTML日报失败：{str(e)}")
    
    return markdown_file, markdown_content

# 更新index.html
def update_index_html(current_date, article_list, count):
    print("更新index.html...")
    
    # 创建index.html模板
    index_template = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RSS日报</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        header {
            background-color: #4285f4;
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            margin-bottom: 30px;
        }
        h1 {
            margin: 0;
            font-size: 2rem;
        }
        h2 {
            font-size: 1.5rem;
            margin-bottom: 20px;
        }
        .report-list {
            list-style: none;
            padding: 0;
        }
        .report-item {
            background-color: white;
            padding: 20px;
            margin-bottom: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        .report-link {
            color: #4285f4;
            text-decoration: none;
            font-size: 1.2rem;
            font-weight: bold;
        }
        .report-link:hover {
            text-decoration: underline;
        }
        .report-info {
            color: #666;
            font-size: 0.9rem;
            margin-top: 5px;
        }
        footer {
            text-align: center;
            margin-top: 50px;
            color: #666;
            font-size: 0.9rem;
        }
    </style>
</head>
<body>
    <header>
        <h1>RSS日报</h1>
        <div>每日安全社区文章汇总</div>
    </header>
    
    <main>
        <h2>日报列表</h2>
        <ul class="report-list">
            {% for report in reports %}
            <li class="report-item">
                <a href="{{ report.path }}" class="report-link" target="_blank">{{ report.date }}</a>
                <div class="report-info">共 {{ report.count }} 篇文章</div>
            </li>
            {% endfor %}
        </ul>
    </main>
    
    <footer>
        <p>Generated by RSS Monitor</p>
    </footer>
</body>
</html>
    """
    
    # 获取所有已生成的日报
    reports = []
    
    # 遍历archive目录下的所有日期目录
    if os.path.exists('archive'):
        for date_dir in sorted(os.listdir('archive'), reverse=True):
            if os.path.isdir(os.path.join('archive', date_dir)):
                # 检查该日期目录下是否存在HTML文件
                html_file = f'archive/{date_dir}/Daily_{date_dir}.html'
                if os.path.exists(html_file):
                    # 尝试获取文章数量
                    count = 0
                    md_file = f'archive/{date_dir}/Daily_{date_dir}.md'
                    if os.path.exists(md_file):
                        with open(md_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # 从markdown文件中提取文章数量
                            import re
                            match = re.search(r'共收集到 (\d+) 篇文章', content)
                            if match:
                                count = match.group(1)
                    
                    reports.append({
                        'date': date_dir,
                        'path': html_file,
                        'count': count
                    })
    
    # 渲染index.html
    template = Template(index_template)
    html_content = template.render(reports=reports)
    
    # 写入index.html文件
    with open('index.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print("index.html已更新")

# Telegram Bot推送
def tgbot(text, msg, token, group_id):
    import telegram
    try:
        if not token or token == "Telegram Bot的token":
            print(f"Telegram推送跳过：token未配置")
            return
            
        if not group_id or group_id == "Telegram Bot的group_id":
            print(f"Telegram推送跳过：group_id未配置")
            return
            
        # 获取代理配置
        proxies = get_proxies()
        
        if proxies:
            # 配置telegram bot使用代理
            request_kwargs = {'proxies': proxies}
            bot = telegram.Bot(token=token, request_kwargs=request_kwargs)
        else:
            bot = telegram.Bot(token=token)
            
        bot.send_message(chat_id=group_id, text=f'{text}\n{msg}')
        print(f"Telegram推送成功: {text}")
    except Exception as e:
        print(f"Telegram推送失败: {str(e)}")

# 主函数

def main():
    banner = f'''
    +-------------------------------------------+
                   安全社区推送监控
    使用说明：
    1. 修改config.yaml中的推送配置以及开关
    2. 修改rss.yaml中需要增加删除的社区
    3. 可自行去除或增加新的推送渠道代码到本脚本中
                      2023.10.10
                   Powered By：Pings
                   Version：{__version__}
    +-------------------------------------------+
                     开始监控...
    '''

    print(banner)
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='安全社区文章监控脚本')
    parser.add_argument('--once', action='store_true', help='只执行一次，适合GitHub Action运行')
    parser.add_argument('--daily-report', action='store_true', help='生成日报模式，只生成日报不推送')
    parser.add_argument('--version', action='version', version=f'Rss_monitor {__version__}', help='显示版本号')
    args = parser.parse_args()
    
    conn = init_database()
    cursor = conn.cursor()
    rss_config = {}

    try:
        with open('rss.yaml', 'r', encoding='utf-8') as file:
            rss_config = yaml.load(file, Loader=yaml.FullLoader)
    except Exception as e:
        print(f"加载rss.yaml文件出错: {str(e)}")
        conn.close()
        return

    # 发送启动通知消息 - 非日报模式才发送
    if not args.daily_report:
        # 检查是否有任何推送服务的开关是开启的
        config = load_config()
        push_config = config.get('push', {})
        any_push_enabled = False
        
        for service in push_config.values():
            if service.get('switch', 'OFF') == 'ON':
                any_push_enabled = True
                break
        
        if any_push_enabled:
            push_message("安全社区文章监控已启动!", f"启动时间：{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}")

    try:
        if args.daily_report:
            # 日报模式，先收集数据，再生成日报
            print("使用日报模式")
            # 先收集所有RSS源的数据
            for website, config in rss_config.items():
                website_name = config.get("website_name")
                rss_url = config.get("rss_url")
                # 日报模式下不发送推送，send_push=False
                check_for_updates(rss_url, website_name, cursor, conn, send_push=False)
            # 收集完数据后生成日报
            generate_daily_report(cursor)
        elif args.once:
            # 单次执行模式，适合GitHub Action
            print("使用单次执行模式")
            for website, config in rss_config.items():
                website_name = config.get("website_name")
                rss_url = config.get("rss_url")
                check_for_updates(rss_url, website_name, cursor, conn)
            
            # 检查是否需要生成日报
            config = load_config()
            if config.get('daily_report', {}).get('switch', 'ON') == 'ON':
                generate_daily_report(cursor)
        else:
            # 循环执行模式，适合本地运行
            while True:
                try:
                    # 检查是否需要夜间休眠
                    if should_sleep():
                        sleep_hours = 7 - datetime.now().hour
                        print(f"当前时间在0-7点之间，将休眠{sleep_hours}小时")
                        time.sleep(sleep_hours * 3600)
                        continue
                    
                    for website, config in rss_config.items():
                        website_name = config.get("website_name")
                        rss_url = config.get("rss_url")
                        check_for_updates(rss_url, website_name, cursor, conn)

                    # 检查是否需要生成日报
                    config = load_config()
                    if config.get('daily_report', {}).get('switch', 'ON') == 'ON':
                        generate_daily_report(cursor)

                    # 每二小时执行一次
                    time.sleep(10800)

                except Exception as e:
                    print("发生异常：", str(e))
                    time.sleep(60)  # 出现异常，等待1分钟继续执行
    except Exception as e:
        print("主程序发生异常：", str(e))
    finally:
        conn.close()
        print("监控程序已结束")

if __name__ == "__main__":
    main()