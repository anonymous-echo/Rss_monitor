# 使用 Python 3.10作为基础镜像
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 设置时区为上海
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# 创建必要的目录
RUN mkdir -p log cache archive

# 声明卷
VOLUME ["/app/log", "/app/cache", "/app/archive", "/app/articles.db"]

# 设置容器启动命令
CMD ["python", "Rss_monitor.py"]
