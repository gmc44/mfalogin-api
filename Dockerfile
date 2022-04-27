FROM python:3.9.1
#ENV https_proxy http://proxy.url:3128
ADD . /python-flask
WORKDIR /python-flask
RUN pip install -r requirements.txt
