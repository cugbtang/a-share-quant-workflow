# 演示镜像：离线跑通 data.cli demo + 低波回测。
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# 先装依赖，利用层缓存
COPY requirements.txt .
RUN pip install -r requirements.txt

# 复制源码
COPY . .

# 默认运行一键演示（离线：数据 demo + 低波回测）
CMD ["python", "scripts/run_demo.py"]
