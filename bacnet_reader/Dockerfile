ARG BUILD_FROM
FROM ${BUILD_FROM}

RUN apk add --no-cache \
    bash \
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
