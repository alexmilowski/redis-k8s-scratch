FROM python:3.8-slim

RUN apt-get update && apt-get install -y curl
RUN pip install kubernetes jsonpath_ng
RUN mkdir -p /app
COPY config.sh /app/
COPY make_request.py /app/
COPY waitfor.py /app/
WORKDIR /app

ENTRYPOINT ["/bin/sh", "/app/config.sh"]
