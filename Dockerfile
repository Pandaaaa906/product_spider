FROM python:3.6

COPY . /product_spider

WORKDIR /product_spider

RUN mkdir -p ~/.pip
RUN echo "[global]\nindex-url = https://pypi.tuna.tsinghua.edu.cn/simple" | tee ~/.pip/pip.conf
RUN git config --global http.sslverify false
RUN pip install -r requirements


RUN scrapyd

EXPOSE 6800