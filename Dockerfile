# 使用多阶段构建优化镜像大小和构建速度
FROM python:3.11-bullseye AS builder

VOLUME /ms-playwright

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_CACHE_DIR=/tmp/.uv/ \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PLAYWRIGHT_SKIP_BROWSER_GC=1


# 安装系统依赖和uv（合并到单个RUN）
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 xvfb gconf-service libasound2 libatk1.0-0 libc6 libcairo2 libcups2 \
    libdbus-1-3 libexpat1 libfontconfig1 libgbm1 libgcc1 libgconf-2-4 libgdk-pixbuf2.0-0 libglib2.0-0 libgtk-3-0 \
    libnspr4 libpango-1.0-0 libpangocairo-1.0-0 libstdc++6 libx11-6 libx11-xcb1 libxcb1 cron \
    libxcomposite1 libxcursor1 libxdamage1 libxext6 libxfixes3 libxi6 libxrandr2 libxrender1 libxss1 \
    libxtst6 ca-certificates fonts-liberation libappindicator1 libnss3 lsb-release xdg-utils wget \
    gcc build-essential libssl-dev libffi-dev telnet \
    && sed -i "s/archive.ubuntu.com/mirrors.aliyun.com/g" /etc/apt/sources.list \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p ~/.pip \
    && echo "[global]\nindex-url = https://pypi.tuna.tsinghua.edu.cn/simple" | tee ~/.pip/pip.conf \
    && git config --global http.sslverify false \
    && pip install uv \
    && rm -rf /root/.cache/pip \

# 创建工作目录
WORKDIR /app

# 复制依赖文件
COPY pyproject.toml uv.lock* ./

# 创建虚拟环境并安装Python依赖
RUN --mount=type=cache,target=/tmp/.uv/ uv venv \
    && . .venv/bin/activate \
    && uv pip install . \
    && playwright install chrome \
    && playwright install-deps

# 运行阶段
FROM builder AS runner

COPY . /app/

# 激活虚拟环境
ENV PATH="/app/.venv/bin:/app/.venv/Scripts:$PATH"

# 设置入口点
ENTRYPOINT ["scrapyd"]
CMD ["--pidfile="]
# 暴露端口
EXPOSE 6800
EXPOSE 5000