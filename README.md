# RSS Monitor

![Version](https://img.shields.io/badge/Version-1.1.1-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Python](https://img.shields.io/badge/python-3.10+-blue)

一个基于 Python 的 RSS 监控工具，旨在定期检查安全社区的更新，并通过多种渠道（钉钉、飞书、Telegram、Discord）推送通知。

## ✨ 功能特点

- **多源监控**：支持监控多个 RSS 源，可灵活配置。
- **多渠道推送**：支持钉钉、飞书、Telegram Bot、Discord (Webhook)。
- **智能避扰**：内置夜间休眠功能（默认北京时间 0-7 点），避免打扰。
- **自动化部署**：支持 GitHub Actions 定时运行，亦支持 Zeabur 一键部署。
- **动态更新**：支持通过 Issue 提交新的 RSS 源，自动更新配置。

## 🚀 快速部署

### Zeabur 一键部署

[![Deploy on Zeabur](https://zeabur.com/button.svg)](https://zeabur.com/templates/XXXXXX)

### Docker 部署

```bash
docker build -t rss_monitor .
docker run -d --name rss_monitor \
  -v $(pwd)/config.yaml:/app/config.yaml \
  -v $(pwd)/rss.yaml:/app/rss.yaml \
  -v $(pwd)/data:/app/data \
  rss_monitor
```

### 本地运行

1.  **克隆仓库**
    ```bash
    git clone https://github.com/adminlove520/Rss_monitor.git
    cd Rss_monitor
    ```

2.  **安装依赖**
    ```bash
    pip install -r requirements.txt
    ```

3.  **运行**
    ```bash
    # 循环监控模式
    python Rss_monitor.py

    # 单次执行模式 (适合定时任务)
    python Rss_monitor.py --once
    ```

## ⚙️ 配置说明

项目主要包含两个配置文件：

-   `config.yaml`：设置推送渠道（钉钉、飞书等）、代理和休眠开关。
-   `rss.yaml`：定义需要监控的 RSS 源列表。

> 环境变量 (`ENV`) 的优先级高于配置文件，可用于容器化部署时的动态配置。

### 推送渠道配置 (示例)

| 渠道 | 关键参数 | 环境变量示例 |
| :--- | :--- | :--- |
| **钉钉** | `webhook`, `secret_key` | `DINGDING_WEBHOOK` |
| **飞书** | `webhook` | `FEISHU_WEBHOOK` |
| **Telegram** | `token`, `group_id` | `TELEGRAM_TOKEN` |
| **Discord** | `webhook` | `DISCARD_WEBHOOK` |

## 🛠️ GitHub Actions

本项目内置了 GitHub Actions 工作流：
1.  **Monitor Workflow**: 每天北京时间 9:00-23:00 定时执行监控。
2.  **Version Bump**: `main` 分支有更新时自动升级版本号。
3.  **Add RSS**: 允许用户通过提交 Issue 的方式自动添加 RSS 源。

## 📝 贡献指南

欢迎提交 Issue 或 Pull Request！

-   **添加 RSS 源**：您可以直接提交 Issue，标题或正文包含 `网站名称` 和 `RSS URL` 即可自动添加。
-   **代码贡献**：请确保代码风格一致，并测试通过后提交。

## 📅 更新日志

查看 [CHANGELOG.md](CHANGELOG.md) 获取详细更新历史。

## 📄 许可证

[MIT License](LICENSE)