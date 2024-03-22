FROM mcr.microsoft.com/playwright:v1.24.0-focal as prd_spider_base

RUN sed -i "s/archive.ubuntu.com/mirrors.aliyun.com/g" /etc/apt/sources.list \
  && apt-get update && apt-get install python3-dev python3-pip -y \
  && mkdir -p ~/.pip \
  && echo "[global]\nindex-url = https://pypi.tuna.tsinghua.edu.cn/simple" | tee ~/.pip/pip.conf \
  && git config --global http.sslverify false
COPY requirements.txt /tmp/requirements
RUN pip install -r /tmp/requirements
RUN playwright install chrome && playwright install-deps

FROM prd_spider_base

COPY . /app
WORKDIR /app

ENTRYPOINT scrapyd

EXPOSE 6800
EXPOSE 5000