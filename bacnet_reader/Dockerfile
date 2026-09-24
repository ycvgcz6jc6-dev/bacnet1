ARG BUILD_FROM=ghcr.io/home-assistant/base:3.24-2026.08.0
FROM ${BUILD_FROM}

RUN apk add --no-cache \
    bash \
    python3 \
    py3-pip \
    iproute2 \
    iputils \
    tcpdump

COPY requirements.txt /tmp/requirements.txt

RUN pip3 install \
    --no-cache-dir \
    --break-system-packages \
    -r /tmp/requirements.txt

COPY run.sh /run.sh
COPY bacnet_reader.py /bacnet_reader.py

RUN chmod a+x /run.sh

CMD ["/run.sh"]
