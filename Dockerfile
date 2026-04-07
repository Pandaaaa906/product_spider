# 使用多阶段构建优化镜像大小和构建速度
FROM python:3.12-bullseye AS builder

VOLUME /ms-playwright

# 设置环境变量
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_CACHE_DIR=/tmp/.uv/ \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PLAYWRIGHT_SKIP_BROWSER_GC=1 \
    UV_DEFAULT_INDEX="https://pypi.tuna.tsinghua.edu.cn/simple" \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_NO_DEV=1


# 安装系统依赖和uv（合并到单个RUN）
RUN sed -i "s/archive.ubuntu.com/mirrors.aliyun.com/g" /etc/apt/sources.list \
    && apt-get update && apt-get install -y --no-install-recommends \
    libnss3 xvfb gconf-service libasound2 libatk1.0-0 libc6 libcairo2 libcups2 \
    libdbus-1-3 libexpat1 libfontconfig1 libgbm1 libgcc1 libgconf-2-4 libgdk-pixbuf2.0-0 libglib2.0-0 libgtk-3-0 \
    libnspr4 libpango-1.0-0 libpangocairo-1.0-0 libstdc++6 libx11-6 libx11-xcb1 libxcb1 cron \
    libxcomposite1 libxcursor1 libxdamage1 libxext6 libxfixes3 libxi6 libxrandr2 libxrender1 libxss1 \
    libxtst6 ca-certificates fonts-liberation libappindicator1 libnss3 lsb-release xdg-utils wget \
    gcc build-essential libssl-dev libffi-dev telnet \
    && mkdir -p ~/.pip \
    && echo "[global]\nindex-url = https://pypi.tuna.tsinghua.edu.cn/simple" | tee ~/.pip/pip.conf \
    && git config --global http.sslverify false \
    && pip install uv \
    && rm -rf /root/.cache/pip

# 创建工作目录
WORKDIR /app

# 复制依赖文件
# 创建虚拟环境并安装Python依赖
RUN --mount=type=cache,target=/tmp/.uv/ \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv venv \
    && . .venv/bin/activate \
    && uv sync --frozen --no-install-project

# 激活虚拟环境
ENV PATH="/app/.venv/bin:$PATH"

# 运行阶段
FROM builder AS runner

COPY . /app/

# 设置入口点
ENTRYPOINT ["scrapyd"]
CMD ["--pidfile="]
# 暴露端口
EXPOSE 6800
EXPOSE 5000