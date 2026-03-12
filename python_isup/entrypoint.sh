#!/bin/bash
set -e

echo "=== Starting MediaMTX ==="
mediamtx /app/mediamtx.yml &
MEDIAMTX_PID=$!

# MediaMTX가 준비될 때까지 대기
sleep 2
echo "=== MediaMTX started (PID: $MEDIAMTX_PID) ==="

echo "=== Starting ISUP Server ==="
python3 /app/run_isup_rtsp.py &
ISUP_PID=$!

# 둘 중 하나가 죽으면 전체 종료
wait -n $MEDIAMTX_PID $ISUP_PID
EXIT_CODE=$?
echo "=== Process exited with code $EXIT_CODE, shutting down ==="
kill $MEDIAMTX_PID $ISUP_PID 2>/dev/null || true
wait
exit $EXIT_CODE
