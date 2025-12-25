# RSS Monitor

一个基于Python的RSS监控工具，可以定期检查安全社区的更新，并通过多种渠道推送通知。

## 功能特点

- 支持多个RSS源监控
- 多种推送渠道：钉钉、飞书、Telegram Bot、Discard
- 支持夜间休眠（北京时间0-7点），避免打扰
- 支持通过GitHub Action定时运行
- 支持通过提交Issue添加新的RSS源
- 环境变量优先级高于配置文件
- 数据持久化存储

## 安装

1. 克隆仓库
```bash
git clone https://github.com/adminlove520/Rss_monitor.git
cd Rss_monitor
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

## 配置

### 1. 配置文件 (`config.yaml`)

```yaml
# 配置推送
push:
  dingding:
    webhook: "https://oapi.dingtalk.com/robot/send?access_token=你的token"
    secret_key: "你的Key"
    app_name: "钉钉"
    switch: "ON"  # 设置开关为 "ON" 进行推送，设置为其他值则不进行推送
  feishu:
    webhook: "飞书的webhook地址"
    app_name: "飞书"
    switch: "OFF"
  tg_bot:
    token: "Telegram Bot的token"
    group_id: "Telegram Bot的group_id"
    app_name: "Telegram Bot"
    switch: "OFF"
  discard:
    webhook: "discard的webhook地址"
    app_name: "Discard"
    switch: "OFF"  # 总开关
    send_daily_report: "OFF"  # 推送日报开关
    send_normal_msg: "ON"  # 推送普通消息开关

# 夜间休眠配置
night_sleep:
  switch: "ON"  # 设置开关为 "ON" 开启夜间休眠，设置为其他值则关闭
```

### 2. RSS源配置 (`rss.yaml`)

```yaml
"示例网站":
  "rss_url": "https://example.com/feed.xml"
  "website_name": "示例网站"
```

### 3. 环境变量

环境变量优先级高于配置文件，可以通过环境变量覆盖配置：

| 环境变量名 | 说明 |
| --- | --- |
| DINGDING_WEBHOOK | 钉钉机器人Webhook |
| DINGDING_SECRET | 钉钉机器人密钥 |
| DINGDING_SWITCH | 钉钉推送开关（ON/OFF） |
| FEISHU_WEBHOOK | 飞书机器人Webhook |
| FEISHU_SWITCH | 飞书推送开关（ON/OFF） |
| TELEGRAM_TOKEN | Telegram Bot Token |
| TELEGRAM_GROUP_ID | Telegram群组ID |
| TELEGRAM_SWITCH | Telegram推送开关（ON/OFF） |
| DISCARD_WEBHOOK | Discard Webhook |
| DISCARD_SWITCH | Discard总推送开关（ON/OFF） |
| DISCARD_SEND_DAILY_REPORT | Discard推送日报开关（ON/OFF） |
| DISCARD_SEND_NORMAL_MSG | Discard推送普通消息开关（ON/OFF） |
| NIGHT_SLEEP_SWITCH | 夜间休眠开关（ON/OFF） |

## 使用

### 1. 本地运行

#### 单次执行模式
```bash
python Rss_monitor.py --once
```

#### 循环执行模式
```bash
python Rss_monitor.py
```

### 2. GitHub Action

项目包含两个GitHub Action工作流：

1. **RSS_Monitor.yml**：定期运行RSS监控
   - 执行时间：北京时间9:00-23:00，每小时执行一次
   - 运行时长：每个工作流运行59分钟
   - 夜间休眠：完全跳过北京时间0-7点的触发
   - 运行模式：默认使用循环模式，每2小时检查一次

2. **add-rss-from-issue.yml**：通过提交Issue添加新的RSS源
   - 支持两种格式提交
   - 自动更新rss.yaml
   - 自动回复并关闭Issue

### 3. 夜间休眠功能

- **默认开启**：在北京时间0-7点之间自动休眠
- **双重保障**：
  1. GitHub Action工作流在0-7点不触发
  2. 脚本内置夜间休眠功能
- **灵活控制**：支持通过配置文件和环境变量控制

### 4. 数据存储

监控的数据会存储在 `articles.db` SQLite数据库中，包含以下字段：
- id：自增主键
- title：文章标题
- link：文章链接
- timestamp：添加时间

### 5. 推送格式

推送内容格式示例：
```
奇安信威胁情报中心今日更新
标题: 【附IOC】Next.js RCE漏洞在野利用事件分析
链接: `https://mp.weixin.qq.com/s?__biz=MzI2MDc2MDA4OA==&mid=2247517208&idx=1&sn=92ee1ae869f212bb8cec41dc715ac438`
推送时间：2025-12-09 14:22:32
```

### 6. 通过Issue添加RSS源

您可以通过提交Issue来添加新的RSS源，支持两种格式：

#### 格式1
```
网站名称: 示例网站
RSS URL: https://example.com/feed.xml
```

#### 格式2
直接在标题或正文中包含网站名称和URL，例如：

标题：添加示例网站
正文：https://example.com/feed.xml

### 7. 配置优先级

配置项的优先级从高到低：
1. 命令行参数
2. 环境变量
3. 配置文件 (`config.yaml`)
4. 默认值

### 8. 异常处理

- 出现异常时，等待1分钟后继续执行
- 确保数据库连接正确关闭
- 详细的错误日志输出

### 9. 性能优化

- 每2小时检查一次所有RSS源
- 夜间自动休眠，节省资源
- 数据库缓存，避免重复推送
- 高效的异常处理机制

### 10. 资源消耗

- 内存占用：约50-100MB
- CPU使用率：低，主要在检查RSS源时占用
- 网络请求：每次检查RSS源时发送请求
- 存储占用：随着时间增长，articles.db会逐渐增大

## 开发说明

### 1. 目录结构

```
Rss_monitor/
├── Rss_monitor.py         # 主脚本
├── add_rss_from_issue.py  # Issue处理脚本
├── config.yaml            # 配置文件
├── rss.yaml               # RSS源配置
├── articles.db            # 数据存储
├── requirements.txt       # 依赖列表
├── .gitignore            # Git忽略文件
├── README.md             # 项目说明
└── .github/
    └── workflows/
        ├── RSS_Monitor.yml           # 主工作流
        └── add-rss-from-issue.yml    # Issue处理工作流
```

### 2. 依赖管理

- 使用pip管理依赖
- 依赖列表存储在requirements.txt中
- 定期更新依赖版本

### 3. 测试

- 本地测试：使用--once参数进行单次测试
- 手动触发：通过GitHub Action的workflow_dispatch手动触发
- 日志检查：查看GitHub Action的运行日志

### 4. 贡献指南

- 提交Issue：报告问题或建议
- 提交PR：修复bug或添加新功能
- 遵循Python代码规范
- 添加必要的注释
- 测试通过后提交

## 更新日志

- 2023.10.10：初始版本
- 2025.10.11：
  - 增加夜间休眠功能
  - 支持通过Issue添加RSS源
  - 完善配置文件支持
  - 优化推送逻辑
- 2025.10.15：
  - 调整GitHub Action执行时间为北京时间9:00-23:00
  - 优化工作流运行时长为59分钟
  - 移除--once参数，默认使用循环模式
  - 完善README文档
  - 添加Issue模板
- 2025.12.25：
  - 移除Server酱和PushPlus推送方式
  - 新增Discard推送渠道
  - 支持Discard推送日报功能
  - 支持Discard单独开关控制日报和普通消息推送
  - 更新GitHub Action工作流配置
  - 修复代码缩进问题
  - 完善README文档

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！

## 联系方式

如有问题或建议，欢迎通过以下方式联系：
- GitHub Issue：提交到项目仓库
- 邮箱：your-email@example.com

## 致谢

感谢所有贡献者和使用本项目的用户！

## 通过Issue添加RSS源

您可以通过提交Issue来添加新的RSS源，支持两种格式：

### 格式1
```
网站名称: 示例网站
RSS URL: https://example.com/feed.xml
```

### 格式2
直接在标题或正文中包含网站名称和URL，例如：

标题：添加示例网站
正文：https://example.com/feed.xml

## 夜间休眠功能

默认情况下，脚本会在北京时间0-7点之间自动休眠，跳过推送。您可以通过以下方式控制：

1. 修改 `config.yaml` 中的 `night_sleep.switch` 配置
2. 设置环境变量 `NIGHT_SLEEP_SWITCH`

## 数据存储

监控的数据会存储在 `articles.db` SQLite数据库中，包含以下字段：
- id：自增主键
- title：文章标题
- link：文章链接
- timestamp：添加时间

## 推送渠道

### 1. 钉钉

- 支持签名验证
- 发送文本消息

### 2. 飞书

- 支持飞书机器人API
- 发送文本消息

### 3. Telegram Bot

- 支持Telegram群组推送
- 需创建Bot获取Token

### 4. Discard

- 支持两种推送方式：
  - 普通消息推送（与钉钉格式相同）
  - 日报推送（HTML格式）
- 支持单独开关控制日报和普通消息推送
- 需配置Webhook地址

## 日志

- 控制台输出执行日志
- 错误信息会打印到控制台

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！