FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖 (lxml 编译需要, curl 用于健康检查)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libxml2-dev \
    libxslt1-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY pyproject.toml README.md ./
COPY src/ src/

# 安装 Python 依赖
RUN pip install --no-cache-dir .

# 创建数据目录
RUN mkdir -p /app/data

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "feedwise.main:app", "--host", "0.0.0.0", "--port", "8000"]

