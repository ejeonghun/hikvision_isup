FROM --platform=linux/amd64 python:3.11-slim-bookworm

# Hikvision SDK 의존 시스템 라이브러리
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# SDK 라이브러리를 고정 경로에 복사
COPY include/linux/ /opt/hcisup-sdk/

# .so 파일들을 ld가 찾을 수 있도록 설정
RUN echo "/opt/hcisup-sdk" > /etc/ld.so.conf.d/hcisup.conf && \
    echo "/opt/hcisup-sdk/HCAapSDKCom" >> /etc/ld.so.conf.d/hcisup.conf && \
    echo "/opt/hcisup-sdk/netsdk" >> /etc/ld.so.conf.d/hcisup.conf && \
    echo "/opt/hcisup-sdk/netsdk/HCNetSDKCom" >> /etc/ld.so.conf.d/hcisup.conf && \
    ldconfig

# SDK 경로 확인 (빌드 시 디버깅용)
RUN ls -la /opt/hcisup-sdk/ && echo "--- SDK files verified ---"

# 앱 소스 복사
COPY config.py run_isup_rtsp.py isup_wrapper.py /app/

# 컨테이너 환경에서 SDK 경로를 환경변수로 지정
ENV HCISUP_SDK_DIR=/opt/hcisup-sdk

# CMS(7660), Stream(8003), Control(19090), Voice(7500)
EXPOSE 7660 8003 19090 7500

CMD ["python3", "run_isup_rtsp.py"]
