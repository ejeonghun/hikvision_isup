# Python ISUP -> RTSP Bridge

This directory contains a Python implementation that follows the same ISUP5.0 flow as the C++ sample and republishes incoming Hikvision stream data to RTSP via `ffmpeg`.

## What it does

- Starts CMS listen server (`NET_ECMS_StartListen`) for device register/auth.
- Starts stream listen server (`NET_ESTREAM_StartListenPreview`) for preview link.
- Registers preview callback (`NET_ESTREAM_SetPreviewDataCB`) and receives bytes from `NET_EHOME_PREVIEW_CB_MSG`.
- Pipes callback bytes to `ffmpeg` stdin and publishes RTSP URL.

## Prerequisites

- Linux x86_64 with Hikvision HCISUP SDK shared libraries.
- `ffmpeg` installed.
- Camera configured to connect to your ISUP server.

## Environment variables

- `HCISUPCMS_PATH` (default: `libHCISUPCMS.so`)
- `HCISUPSTREAM_PATH` (default: `libHCISUPStream.so`)
- `HCISUP_SDK_DIR` (optional, directory containing HCISUP shared libraries)
- `OPENSSL_LIBCRYPTO_PATH` (optional, path to `libcrypto.so`)
- `OPENSSL_LIBSSL_PATH` (optional, path to `libssl.so`)
- `ISUP_EHOME_KEY` (default: `abc123456`)
- `ISUP_CMS_LISTEN_IP` (default: `0.0.0.0`)
- `ISUP_CMS_LISTEN_PORT` (default: `7660`)
- `ISUP_CMS_PUBLIC_IP` (optional, camera-facing CMS address for logs/checklist)
- `ISUP_STREAM_LISTEN_IP` (default: `0.0.0.0`)
- `ISUP_STREAM_LISTEN_PORT` (default: `8003`)
- `ISUP_STREAM_PUBLIC_IP` (the IP address camera can reach)
- `ISUP_STREAM_PUBLIC_PORT` (default: `8003`)
- `ISUP_DAS_PUBLIC_IP` (optional, DAS address returned during registration; use reachable public/LAN IP)
- `ISUP_DAS_PORT` (optional, DAS port returned during registration; default uses CMS listen port)
- `ISUP_AUTO_PUBLIC_IP` (optional, force auto-selected camera-reachable IP)
- `ISUP_CHANNEL` (default: `1`)
- `ISUP_STREAM_TYPE` (default: `0`, main stream)
- `ISUP_LINK_MODE` (default: `0`, TCP)
- `RTSP_PUBLISH_URL` (default: `rtsp://127.0.0.1:8554/isup`)
- `ISUP_REGISTRATION_TIMEOUT_SEC` (default: `0` = no fail, keep waiting)
- `ISUP_DEBUG` (default: `1`, prints SDK path/init/callback diagnostics)
- `ISUP_REG_HEARTBEAT_SEC` (default: `10`, wait-status print interval)
- `ISUP_PUSH_RETRY_COUNT` (default: `5`, retries for `StartPushRealStream`)
- `ISUP_PUSH_RETRY_DELAY_SEC` (default: `1`, retry interval)

Current runtime uses `python_isup/config.py` as single source of configuration constants (`CFG_*`).

## Run

```bash
python3 python_isup/run_isup_rtsp.py
```

Example with explicit SDK directory:

```bash
HCISUP_SDK_DIR=/opt/hikvision/isup/lib \
python3 python_isup/run_isup_rtsp.py
```

If you are publishing to local MediaMTX:

```bash
RTSP_PUBLISH_URL=rtsp://127.0.0.1:8554/isup python3 python_isup/run_isup_rtsp.py
```

Then play from:

```bash
ffplay rtsp://127.0.0.1:8554/isup
```

## Windows with HK_ISUP_SDK

Clone SDK under `python_isup/include/HK_ISUP_SDK` and use `lib64` path:

```bat
set HCISUP_SDK_DIR=C:\path\to\hikvision_isup\python_isup\include\HK_ISUP_SDK\lib64
set HCISUPCMS_PATH=C:\path\to\hikvision_isup\python_isup\include\HK_ISUP_SDK\lib64\HCISUPCMS.dll
set HCISUPSTREAM_PATH=C:\path\to\hikvision_isup\python_isup\include\HK_ISUP_SDK\lib64\HCISUPStream.dll
set OPENSSL_LIBCRYPTO_PATH=C:\path\to\hikvision_isup\python_isup\include\HK_ISUP_SDK\lib64\libeay32.dll
set OPENSSL_LIBSSL_PATH=C:\path\to\hikvision_isup\python_isup\include\HK_ISUP_SDK\lib64\ssleay32.dll
python python_isup\run_isup_rtsp.py
```

Default behavior: if `HCISUP_SDK_DIR` is not set, the script automatically tries `python_isup/include/HK_ISUP_SDK/lib64`.

Keep dependency DLLs in the same `lib64` folder (the script adds that directory and `HCAapSDKCom` to the DLL search path automatically on Windows).

## Notes

- Internal listen IP/port and public stream IP/port must match your network topology (NAT/public IP). This is required by Hikvision ISUP handshake.
- Callback bytes are handled as PS stream by default (`byStreamFormat = 0`) and forwarded to ffmpeg with stream copy.
- This Git repo contains headers only. You must separately install vendor HCISUP shared libs (`.so`/`.dylib`) and point the script to them.
- If you see registration timeout logs, the camera has not connected to CMS (`ISUP_CMS_LISTEN_IP:ISUP_CMS_LISTEN_PORT`) yet; server keeps waiting by default.

## No registration callback troubleshooting

- Confirm camera EHome/ISUP server target exactly matches your reachable public IP and TCP port `7660`.
- Do not set `ISUP_STREAM_PUBLIC_IP` to loopback (`127.0.0.1`) for external cameras.
- Verify inbound rule on Windows host and port-forwarding on upstream router (TCP 7660, 8003).
- Check NAT hairpin/CGNAT: if server is behind CGNAT, external camera cannot reach it directly.
- Ensure camera EHome key equals `ISUP_EHOME_KEY`; auth mismatch can prevent successful online transition.
- Watch debug logs: callback heartbeat and `register-callback` lines should appear once camera reaches CMS.
- If callbacks repeat `data_type=3,4,5` but never `0`, DAS response address/port is usually unreachable from camera. Set `ISUP_DAS_PUBLIC_IP` and `ISUP_DAS_PORT` explicitly.
- If `ISUP_STREAM_PUBLIC_IP` is left as `127.0.0.1`/`0.0.0.0`, the server now auto-selects a non-loopback local IPv4, but explicit public/LAN IP is still recommended.
- Error `169` maps to `NET_PREVIEW_ERR_CONNECT_SERVER_FAIL` (SDK header `HCISUPPublic.h`): camera could not connect to stream server IP/port.

## PTZ while running

After startup, type commands in the same console:

```text
ptz_help
ptz left
ptz up 0.5 6 1
ptz_start right 5 1
ptz_stop right 5 1
```

Format:

- `ptz <command> [duration_sec] [speed:0-7] [channel]`
- `ptz_start <command> [speed:0-7] [channel]`
- `ptz_stop <command> [speed:0-7] [channel]`

## Voice talk while running (PC -> camera)

Control commands:

```text
voice_help
voice_start
voice_start 125.137.53.163 7500 0.0.0.0 7500 1
voice_status
voice_send_file C:\path\to\audio.g711u 160 20
voice_send_wav C:\path\to\audio.wav auto
voice_stop
```

Format:

- `voice_start [voice_server_ip] [voice_server_port] [voice_listen_ip] [voice_listen_port] [voice_channel]`
- `voice_send_file <path> [chunk_bytes] [delay_ms]`
- `voice_send_wav <path> [codec:auto|g711u|pcm] [chunk_bytes] [delay_ms]`
- `voice_status`
- `voice_stop`

Note: `voice_send_file` expects camera-compatible encoded audio payload (G.711U in this build). Raw PCM may not be accepted by device.
For G.711U 8kHz mono, start with `chunk_bytes=160` and `delay_ms=20` for real-time pacing.

For severe distortion, codec mismatch is the top suspect. Use `voice_status` to check device `voice_device_encode_type` and prefer `voice_send_wav ... auto` to convert WAV to matched codec before sending.

If `voice_send_file` returns `voice link is not ready`, it means voice new-link callback has not arrived yet. The script now waits for link readiness after `voice_start`, and `voice_send_file` will auto-start voice session when needed.

When sending Windows path over control socket, prefer `/` or escaped backslashes in the python one-liner.
Example: `voice_send_file C:/audio.g711u 160 20`

On Windows, if stdin input is blocked after stream start, use control socket from another terminal:

```powershell
python -c "import socket; s=socket.create_connection(('127.0.0.1',19090)); s.sendall(b'ptz left 0.3 5 1\n'); print(s.recv(4096).decode()); s.close()"
```

`run_isup_rtsp.py` now binds control socket on `0.0.0.0:19090`, so localhost connection above should work on the same host.

## Wrapper CLI

To avoid long one-line socket commands, use wrapper:

```bash
python python_isup/isup_wrapper.py shell
python python_isup/isup_wrapper.py ptz left 0.3 5 1
python python_isup/isup_wrapper.py voice-start
python python_isup/isup_wrapper.py voice-send-file C:/audio.g711u 160 20
python python_isup/isup_wrapper.py voice-send-wav C:/audio.wav auto
python python_isup/isup_wrapper.py voice-stop
python python_isup/isup_wrapper.py voice-play-wav C:/audio.wav auto
```
