FROM python:3.6 as prd_spider_base

RUN mkdir -p ~/.pip
RUN echo "[global]\nindex-url = https://pypi.tuna.tsinghua.edu.cn/simple" | tee ~/.pip/pip.conf
RUN git config --global http.sslverify false
COPY requirements /tmp/requirements
RUN pip install -r /tmp/requirements

FROM prd_spider_base

COPY . /app
WORKDIR /app

ENTRYPOINT scrapyd

EXPOSE 6800
EXPOSE 5000