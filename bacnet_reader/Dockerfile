ARG BUILD_ARCH
ARG BUILD_FROM=ghcr.io/home-assistant/${BUILD_ARCH}-base-python:3.13-alpine3.21
FROM ${BUILD_FROM}
ARG BUILD_VERSION
ARG BUILD_ARCH
LABEL io.hass.version="${BUILD_VERSION}" io.hass.type="addon" io.hass.arch="${BUILD_ARCH}"
RUN apk add --no-cache bash iproute2 iputils tcpdump
COPY requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r /tmp/requirements.txt
COPY run.sh /run.sh
COPY bacnet_reader.py /bacnet_reader.py
COPY phase2.py mct.html /
RUN chmod a+x /run.sh
CMD ["/run.sh"]
