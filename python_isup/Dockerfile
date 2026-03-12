FROM --platform=linux/amd64 python:3.11-slim-bookworm

# Hikvision SDK 의존 시스템 라이브러리
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libglib2.0-0 \
    wget \
    tar \
    && rm -rf /var/lib/apt/lists/*

# MediaMTX 설치
ARG MEDIAMTX_VERSION=1.16.3
RUN wget -q "https://github.com/bluenviron/mediamtx/releases/download/v${MEDIAMTX_VERSION}/mediamtx_v${MEDIAMTX_VERSION}_linux_amd64.tar.gz" \
    -O /tmp/mediamtx.tar.gz && \
    tar -xzf /tmp/mediamtx.tar.gz -C /usr/local/bin mediamtx && \
    chmod +x /usr/local/bin/mediamtx && \
    rm /tmp/mediamtx.tar.gz

WORKDIR /app

# SDK 라이브러리를 고정 경로에 복사
COPY include/linux/ /opt/hcisup-sdk/

# .so 파일들을 ld가 찾을 수 있도록 설정
RUN echo "/opt/hcisup-sdk" > /etc/ld.so.conf.d/hcisup.conf && \
    echo "/opt/hcisup-sdk/HCAapSDKCom" >> /etc/ld.so.conf.d/hcisup.conf && \
    echo "/opt/hcisup-sdk/netsdk" >> /etc/ld.so.conf.d/hcisup.conf && \
    echo "/opt/hcisup-sdk/netsdk/HCNetSDKCom" >> /etc/ld.so.conf.d/hcisup.conf && \
    ldconfig

# SDK 경로 확인
RUN echo "=== SDK files ===" && \
    find /opt/hcisup-sdk -name "*.so*" -type f | sort && \
    echo "=== done ==="

# MediaMTX 설정
COPY mediamtx.yml /app/mediamtx.yml

# 앱 소스 복사
COPY config.py run_isup_rtsp.py isup_wrapper.py /app/

# 시작 스크립트
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

ENV HCISUP_SDK_DIR=/opt/hcisup-sdk

# RTSP(8554), RTMP(1935), HLS(8888), WebRTC(8889), CMS(7660), Stream(8003), Control(19090), Voice(7500)
EXPOSE 8554 1935 8888 8889 7660 8003 19090 7500

CMD ["/app/entrypoint.sh"]
