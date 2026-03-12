FROM --platform=linux/amd64 python:3.11-slim-bookworm

# Hikvision SDK 의존 시스템 라이브러리
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# SDK 라이브러리 복사
COPY include/linux/ /app/include/linux/

# .so 파일들을 ld가 찾을 수 있도록 설정
RUN echo "/app/include/linux" > /etc/ld.so.conf.d/hcisup.conf && \
    echo "/app/include/linux/HCAapSDKCom" >> /etc/ld.so.conf.d/hcisup.conf && \
    echo "/app/include/linux/netsdk" >> /etc/ld.so.conf.d/hcisup.conf && \
    echo "/app/include/linux/netsdk/HCNetSDKCom" >> /etc/ld.so.conf.d/hcisup.conf && \
    ldconfig

# 앱 소스 복사
COPY config.py run_isup_rtsp.py isup_wrapper.py /app/

# CMS(7660), Stream(8003), Control(19090), Voice(7500)
EXPOSE 7660 8003 19090 7500

CMD ["python3", "run_isup_rtsp.py"]
