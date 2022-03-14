FROM mcr.microsoft.com/playwright:v1.18.1-focal as prd_spider_base

RUN apt update && apt-get install python3-dev -y
RUN mkdir -p ~/.pip
RUN echo "[global]\nindex-url = https://pypi.tuna.tsinghua.edu.cn/simple" | tee ~/.pip/pip.conf
RUN git config --global http.sslverify false
COPY requirements.txt /tmp/requirements
RUN pip install -r /tmp/requirements
RUN playwright install && playwright install-deps

FROM prd_spider_base

COPY . /app
WORKDIR /app

ENTRYPOINT scrapyd

EXPOSE 6800
EXPOSE 5000