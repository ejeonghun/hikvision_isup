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
RUN echo "=== SDK files ===" && \
    find /opt/hcisup-sdk -name "*.so*" -type f | sort && \
    echo "=== done ==="

# 앱 소스 복사
COPY config.py run_isup_rtsp.py isup_wrapper.py /app/

# 컨테이너 환경에서 SDK 경로를 환경변수로 지정
ENV HCISUP_SDK_DIR=/opt/hcisup-sdk

# 시작 시 SDK 파일 존재 확인 후 실행
CMD ["sh", "-c", "echo '--- runtime SDK check ---' && ls -la /opt/hcisup-sdk/libHCISUP* 2>&1 && echo '---' && exec python3 run_isup_rtsp.py"]
