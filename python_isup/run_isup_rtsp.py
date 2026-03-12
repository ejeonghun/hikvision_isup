#!/usr/bin/env python3
from __future__ import annotations

import ctypes
import ipaddress
import os
import platform
import queue
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import traceback
from dataclasses import dataclass
from typing import Any

from config import (
    CFG_AUTO_PUBLIC_IP,
    CFG_CHANNEL,
    CFG_CMS_LISTEN_IP,
    CFG_CMS_LISTEN_PORT,
    CFG_CMS_PUBLIC_IP,
    CFG_CONTROL_SOCKET_HOST,
    CFG_CONTROL_SOCKET_PORT,
    CFG_DAS_PORT,
    CFG_DAS_PUBLIC_IP,
    CFG_DEBUG,
    CFG_EHOME_KEY,
    CFG_ENABLE_CONTROL_SOCKET,
    CFG_ENABLE_PTZ_CONSOLE,
    CFG_HCISUPCMS_PATH,
    CFG_HCISUPSTREAM_PATH,
    CFG_LINK_MODE,
    CFG_LOG_DIR,
    CFG_OPENSSL_LIBCRYPTO_PATH,
    CFG_OPENSSL_LIBSSL_PATH,
    CFG_PTZ_DEFAULT_CHANNEL,
    CFG_PTZ_DEFAULT_DURATION_SEC,
    CFG_PTZ_DEFAULT_SPEED,
    CFG_PUSH_RETRY_COUNT,
    CFG_PUSH_RETRY_DELAY_SEC,
    CFG_QUEUE_MAX_CHUNKS,
    CFG_REG_HEARTBEAT_SEC,
    CFG_REGISTRATION_TIMEOUT_SEC,
    CFG_RTSP_PUBLISH_URL,
    CFG_SDK_DIR,
    CFG_STREAM_LISTEN_IP,
    CFG_STREAM_LISTEN_PORT,
    CFG_STREAM_PUBLIC_IP,
    CFG_STREAM_PUBLIC_PORT,
    CFG_STREAM_TYPE,
    CFG_VOICE_CHANNEL,
    CFG_VOICE_LINK_MODE,
    CFG_VOICE_LINK_WAIT_SEC,
    CFG_VOICE_LISTEN_IP,
    CFG_VOICE_LISTEN_PORT,
    CFG_VOICE_SEND_CHUNK_BYTES,
    CFG_VOICE_SEND_DELAY_MS,
    CFG_VOICE_SERVER_IP,
    CFG_VOICE_SERVER_PORT,
)


MAX_DEVICE_ID_LEN = 256
MAX_MASTER_KEY_LEN = 16
NET_EHOME_SERIAL_LEN = 12

BOOL = ctypes.c_int32
DWORD = ctypes.c_uint32
LONG = ctypes.c_int32
WORD = ctypes.c_uint16

IS_WINDOWS = os.name == "nt"
CALLBACK_FACTORY = (
    getattr(ctypes, "WINFUNCTYPE", ctypes.CFUNCTYPE) if IS_WINDOWS else ctypes.CFUNCTYPE
)
LIB_LOADER = getattr(ctypes, "WinDLL", ctypes.CDLL) if IS_WINDOWS else ctypes.CDLL

ENUM_DEV_ON = 0
ENUM_DEV_OFF = 1
ENUM_DEV_AUTH = 3
ENUM_DEV_SESSIONKEY = 4
ENUM_DEV_DAS_REQ = 5

NET_EHOME_SYSHEAD = 1
NET_EHOME_STREAMDATA = 2
NET_PREVIEW_ERR_CONNECT_SERVER_FAIL = 169
NET_EHOME_PTZ_CTRL = 1000

PTZ_COMMANDS: dict[str, int] = {
    "up": 0,
    "down": 1,
    "left": 2,
    "right": 3,
    "up_left": 4,
    "down_left": 5,
    "up_right": 6,
    "down_right": 7,
    "zoom_in": 8,
    "zoom_out": 9,
    "focus_near": 10,
    "focus_far": 11,
    "iris_open": 12,
    "iris_close": 13,
    "light": 14,
    "wiper": 15,
    "auto": 16,
}

VOICE_ENCODE_NAMES: dict[int, str] = {
    0: "g7221",
    1: "g711u",
    2: "g711a(unsupported)",
    3: "g726",
    4: "aac",
    5: "mp2l2",
    6: "pcm",
    7: "mp3",
    8: "g723",
    9: "mp1l2",
    10: "adpcm",
    99: "raw",
}


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    return int(raw)


@dataclass(frozen=True)
class AppConfig:
    hcisupcms_path: str = CFG_HCISUPCMS_PATH
    hcisupstream_path: str = CFG_HCISUPSTREAM_PATH
    openssl_libcrypto_path: str = CFG_OPENSSL_LIBCRYPTO_PATH
    openssl_libssl_path: str = CFG_OPENSSL_LIBSSL_PATH
    log_dir: str = CFG_LOG_DIR
    ehome_key: str = CFG_EHOME_KEY
    cms_listen_ip: str = CFG_CMS_LISTEN_IP
    cms_public_ip: str = CFG_CMS_PUBLIC_IP
    cms_listen_port: int = CFG_CMS_LISTEN_PORT
    stream_listen_ip: str = CFG_STREAM_LISTEN_IP
    stream_listen_port: int = CFG_STREAM_LISTEN_PORT
    stream_public_ip: str = CFG_STREAM_PUBLIC_IP
    stream_public_port: int = CFG_STREAM_PUBLIC_PORT
    das_public_ip: str = CFG_DAS_PUBLIC_IP
    das_port: int = CFG_DAS_PORT
    channel: int = CFG_CHANNEL
    stream_type: int = CFG_STREAM_TYPE
    link_mode: int = CFG_LINK_MODE
    rtsp_publish_url: str = CFG_RTSP_PUBLISH_URL
    queue_max_chunks: int = CFG_QUEUE_MAX_CHUNKS
    sdk_dir: str = CFG_SDK_DIR
    registration_timeout_sec: int = CFG_REGISTRATION_TIMEOUT_SEC
    debug: bool = CFG_DEBUG
    registration_heartbeat_sec: int = CFG_REG_HEARTBEAT_SEC
    auto_public_ip: str = CFG_AUTO_PUBLIC_IP
    push_retry_count: int = CFG_PUSH_RETRY_COUNT
    push_retry_delay_sec: int = CFG_PUSH_RETRY_DELAY_SEC
    enable_ptz_console: bool = CFG_ENABLE_PTZ_CONSOLE
    ptz_default_channel: int = CFG_PTZ_DEFAULT_CHANNEL
    ptz_default_speed: int = CFG_PTZ_DEFAULT_SPEED
    ptz_default_duration_sec: float = CFG_PTZ_DEFAULT_DURATION_SEC
    enable_control_socket: bool = CFG_ENABLE_CONTROL_SOCKET
    control_socket_host: str = CFG_CONTROL_SOCKET_HOST
    control_socket_port: int = CFG_CONTROL_SOCKET_PORT
    voice_server_ip: str = CFG_VOICE_SERVER_IP
    voice_server_port: int = CFG_VOICE_SERVER_PORT
    voice_listen_ip: str = CFG_VOICE_LISTEN_IP
    voice_listen_port: int = CFG_VOICE_LISTEN_PORT
    voice_channel: int = CFG_VOICE_CHANNEL
    voice_link_mode: int = CFG_VOICE_LINK_MODE
    voice_link_wait_sec: int = CFG_VOICE_LINK_WAIT_SEC
    voice_send_chunk_bytes: int = CFG_VOICE_SEND_CHUNK_BYTES
    voice_send_delay_ms: int = CFG_VOICE_SEND_DELAY_MS


class NET_EHOME_IPADDRESS(ctypes.Structure):
    _fields_ = [
        ("szIP", ctypes.c_char * 128),
        ("wPort", WORD),
        ("byRes", ctypes.c_char * 2),
    ]


class NET_EHOME_DEV_SESSIONKEY(ctypes.Structure):
    _fields_ = [
        ("sDeviceID", ctypes.c_ubyte * MAX_DEVICE_ID_LEN),
        ("sSessionKey", ctypes.c_ubyte * MAX_MASTER_KEY_LEN),
    ]


class NET_EHOME_DEV_REG_INFO(ctypes.Structure):
    _fields_ = [
        ("dwSize", DWORD),
        ("dwNetUnitType", DWORD),
        ("byDeviceID", ctypes.c_ubyte * MAX_DEVICE_ID_LEN),
        ("byFirmwareVersion", ctypes.c_ubyte * 24),
        ("struDevAdd", NET_EHOME_IPADDRESS),
        ("dwDevType", DWORD),
        ("dwManufacture", DWORD),
        ("byPassWord", ctypes.c_ubyte * 32),
        ("sDeviceSerial", ctypes.c_ubyte * NET_EHOME_SERIAL_LEN),
        ("byReliableTransmission", ctypes.c_ubyte),
        ("byWebSocketTransmission", ctypes.c_ubyte),
        ("bySupportRedirect", ctypes.c_ubyte),
        ("byDevProtocolVersion", ctypes.c_ubyte * 6),
        ("bySessionKey", ctypes.c_ubyte * MAX_MASTER_KEY_LEN),
        ("byMarketType", ctypes.c_ubyte),
        ("byRes1", ctypes.c_ubyte),
        ("bySupport", ctypes.c_ubyte),
        ("byRes", ctypes.c_ubyte * 24),
    ]


class NET_EHOME_DEV_REG_INFO_V12(ctypes.Structure):
    _fields_ = [
        ("struRegInfo", NET_EHOME_DEV_REG_INFO),
        ("struRegAddr", NET_EHOME_IPADDRESS),
        ("sDevName", ctypes.c_ubyte * 64),
        ("byDeviceFullSerial", ctypes.c_ubyte * 64),
        ("byRes", ctypes.c_ubyte * 128),
    ]


class NET_EHOME_SERVER_INFO(ctypes.Structure):
    _fields_ = [
        ("dwSize", DWORD),
        ("dwKeepAliveSec", DWORD),
        ("dwTimeOutCount", DWORD),
        ("struTCPAlarmSever", NET_EHOME_IPADDRESS),
        ("struUDPAlarmSever", NET_EHOME_IPADDRESS),
        ("dwAlarmServerType", DWORD),
        ("struNTPSever", NET_EHOME_IPADDRESS),
        ("dwNTPInterval", DWORD),
        ("struPictureSever", NET_EHOME_IPADDRESS),
        ("dwPicServerType", DWORD),
        ("byRes", ctypes.c_ubyte * 420),
    ]


class NET_EHOME_SERVER_INFO_HEAD(ctypes.Structure):
    _fields_ = [("dwSize", DWORD), ("dwKeepAliveSec", DWORD), ("dwTimeOutCount", DWORD)]


class NET_EHOME_CMS_LISTEN_PARAM(ctypes.Structure):
    pass


DEVICE_REGISTER_CB = CALLBACK_FACTORY(
    BOOL,
    LONG,
    DWORD,
    ctypes.c_void_p,
    DWORD,
    ctypes.c_void_p,
    DWORD,
    ctypes.c_void_p,
)

NET_EHOME_CMS_LISTEN_PARAM._fields_ = [
    ("struAddress", NET_EHOME_IPADDRESS),
    ("fnCB", DEVICE_REGISTER_CB),
    ("pUserData", ctypes.c_void_p),
    ("dwKeepAliveSec", DWORD),
    ("dwTimeOutCount", DWORD),
    ("byRes", ctypes.c_ubyte * 24),
]


class NET_EHOME_PREVIEWINFO_IN_V11(ctypes.Structure):
    _fields_ = [
        ("iChannel", ctypes.c_int),
        ("dwStreamType", DWORD),
        ("dwLinkMode", DWORD),
        ("struStreamSever", NET_EHOME_IPADDRESS),
        ("byDelayPreview", ctypes.c_ubyte),
        ("byEncrypt", ctypes.c_ubyte),
        ("byRes", ctypes.c_ubyte * 30),
    ]


class NET_EHOME_PREVIEWINFO_OUT(ctypes.Structure):
    _fields_ = [
        ("lSessionID", LONG),
        ("lHandle", LONG),
        ("byRes", ctypes.c_ubyte * 124),
    ]


class NET_EHOME_PUSHSTREAM_IN(ctypes.Structure):
    _fields_ = [
        ("dwSize", DWORD),
        ("lSessionID", LONG),
        ("byRes", ctypes.c_ubyte * 128),
    ]


class NET_EHOME_PUSHSTREAM_OUT(ctypes.Structure):
    _fields_ = [
        ("dwSize", DWORD),
        ("lHandle", LONG),
        ("byRes", ctypes.c_ubyte * 124),
    ]


class NET_EHOME_REMOTE_CTRL_PARAM(ctypes.Structure):
    _fields_ = [
        ("dwSize", DWORD),
        ("lpCondBuffer", ctypes.c_void_p),
        ("dwCondBufferSize", DWORD),
        ("lpInbuffer", ctypes.c_void_p),
        ("dwInBufferSize", DWORD),
        ("byRes", ctypes.c_ubyte * 32),
    ]


class NET_EHOME_PTZ_PARAM(ctypes.Structure):
    _fields_ = [
        ("dwSize", DWORD),
        ("byPTZCmd", ctypes.c_ubyte),
        ("byAction", ctypes.c_ubyte),
        ("bySpeed", ctypes.c_ubyte),
        ("byRes", ctypes.c_ubyte * 29),
    ]


class NET_EHOME_VOICE_TALK_IN(ctypes.Structure):
    _fields_ = [
        ("dwVoiceChan", DWORD),
        ("struStreamSever", NET_EHOME_IPADDRESS),
        ("byEncodingType", ctypes.c_ubyte * 9),
        ("byLinkEncrypt", ctypes.c_ubyte),
        ("byBroadcast", ctypes.c_ubyte),
        ("byBroadLevel", ctypes.c_ubyte),
        ("byBroadVolume", ctypes.c_ubyte),
        ("byAudioSamplingRate", ctypes.c_ubyte),
        ("byRes", ctypes.c_ubyte * 114),
    ]


class NET_EHOME_VOICE_TALK_OUT(ctypes.Structure):
    _fields_ = [
        ("lSessionID", LONG),
        ("lHandle", LONG),
        ("byRes", ctypes.c_ubyte * 124),
    ]


class NET_EHOME_PUSHVOICE_IN(ctypes.Structure):
    _fields_ = [
        ("dwSize", DWORD),
        ("lSessionID", LONG),
        ("byToken", ctypes.c_ubyte * 64),
        ("byRes", ctypes.c_ubyte * 64),
    ]


class NET_EHOME_PUSHVOICE_OUT(ctypes.Structure):
    _fields_ = [("dwSize", DWORD), ("lHandle", LONG), ("byRes", ctypes.c_ubyte * 124)]


class NET_EHOME_VOICETALK_DATA_CB_INFO(ctypes.Structure):
    _fields_ = [
        ("pData", ctypes.c_void_p),
        ("dwDataLen", DWORD),
        ("byRes", ctypes.c_ubyte * 128),
    ]


VOICETALK_DATA_CB = CALLBACK_FACTORY(
    BOOL,
    LONG,
    ctypes.POINTER(NET_EHOME_VOICETALK_DATA_CB_INFO),
    ctypes.c_void_p,
)


class NET_EHOME_VOICETALK_NEWLINK_CB_INFO(ctypes.Structure):
    _fields_ = [
        ("szDeviceID", ctypes.c_ubyte * 256),
        ("dwEncodeType", DWORD),
        ("sDeviceSerial", ctypes.c_char * 12),
        ("dwAudioChan", DWORD),
        ("lSessionID", LONG),
        ("byToken", ctypes.c_ubyte * 64),
        ("fnVoiceTalkDataCB", VOICETALK_DATA_CB),
        ("pUserData", ctypes.c_void_p),
        ("byRes", ctypes.c_ubyte * 48),
    ]


VOICETALK_NEWLINK_CB = CALLBACK_FACTORY(
    BOOL,
    LONG,
    ctypes.POINTER(NET_EHOME_VOICETALK_NEWLINK_CB_INFO),
    ctypes.c_void_p,
)


class NET_EHOME_LISTEN_VOICETALK_CFG(ctypes.Structure):
    _fields_ = [
        ("struIPAdress", NET_EHOME_IPADDRESS),
        ("fnNewLinkCB", VOICETALK_NEWLINK_CB),
        ("pUser", ctypes.c_void_p),
        ("byLinkMode", ctypes.c_ubyte),
        ("byLinkEncrypt", ctypes.c_ubyte),
        ("byRes", ctypes.c_ubyte * 126),
    ]


class NET_EHOME_VOICETALK_DATA_CB_PARAM(ctypes.Structure):
    _fields_ = [
        ("fnVoiceTalkDataCB", VOICETALK_DATA_CB),
        ("pUserData", ctypes.c_void_p),
        ("byRes", ctypes.c_ubyte * 128),
    ]


class NET_EHOME_VOICETALK_DATA(ctypes.Structure):
    _fields_ = [
        ("pSendBuf", ctypes.c_void_p),
        ("dwDataLen", DWORD),
        ("dwTimeout", DWORD),
        ("byRes", ctypes.c_ubyte * 124),
    ]


class NET_EHOME_PREVIEW_CB_MSG(ctypes.Structure):
    _fields_ = [
        ("byDataType", ctypes.c_ubyte),
        ("byRes1", ctypes.c_ubyte * 3),
        ("pRecvdata", ctypes.c_void_p),
        ("dwDataLen", DWORD),
        ("byRes2", ctypes.c_ubyte * 128),
    ]


PREVIEW_DATA_CB = CALLBACK_FACTORY(
    None,
    LONG,
    ctypes.POINTER(NET_EHOME_PREVIEW_CB_MSG),
    ctypes.c_void_p,
)


class NET_EHOME_NEWLINK_CB_MSG(ctypes.Structure):
    _fields_ = [
        ("szDeviceID", ctypes.c_ubyte * MAX_DEVICE_ID_LEN),
        ("iSessionID", LONG),
        ("dwChannelNo", DWORD),
        ("byStreamType", ctypes.c_ubyte),
        ("byRes1", ctypes.c_ubyte * 2),
        ("byStreamFormat", ctypes.c_ubyte),
        ("sDeviceSerial", ctypes.c_char * NET_EHOME_SERIAL_LEN),
        ("fnPreviewDataCB", PREVIEW_DATA_CB),
        ("pUserData", ctypes.c_void_p),
        ("byRes", ctypes.c_ubyte * 96),
    ]


PREVIEW_NEWLINK_CB = CALLBACK_FACTORY(
    BOOL,
    LONG,
    ctypes.POINTER(NET_EHOME_NEWLINK_CB_MSG),
    ctypes.c_void_p,
)


class NET_EHOME_LISTEN_PREVIEW_CFG(ctypes.Structure):
    _fields_ = [
        ("struIPAdress", NET_EHOME_IPADDRESS),
        ("fnNewLinkCB", PREVIEW_NEWLINK_CB),
        ("pUser", ctypes.c_void_p),
        ("byLinkMode", ctypes.c_ubyte),
        ("byLinkEncrypt", ctypes.c_ubyte),
        ("byRes", ctypes.c_ubyte * 126),
    ]


class NET_EHOME_PREVIEW_DATA_CB_PARAM(ctypes.Structure):
    _fields_ = [
        ("fnPreviewDataCB", PREVIEW_DATA_CB),
        ("pUserData", ctypes.c_void_p),
        ("byStreamFormat", ctypes.c_ubyte),
        ("byRes", ctypes.c_ubyte * 127),
    ]


class IsupError(RuntimeError):
    pass


def _write_ip(addr: NET_EHOME_IPADDRESS, ip: str) -> None:
    data = ip.encode("ascii")[:127]
    addr.szIP = data


def _bytes_from_ubyte_array(arr: Any) -> bytes:
    return bytes(arr).split(b"\x00", 1)[0]


class RtspPublisher:
    def __init__(self, cfg: AppConfig):
        self.cfg = cfg
        self._proc: subprocess.Popen[bytes] | None = None
        self._queue: queue.Queue[bytes] = queue.Queue(maxsize=cfg.queue_max_chunks)
        self._writer_thread: threading.Thread | None = None
        self._stop = threading.Event()

    def start(self) -> None:
        self._spawn_ffmpeg()
        self._writer_thread = threading.Thread(
            target=self._writer_loop, name="rtsp-pipe-writer", daemon=True
        )
        self._writer_thread.start()

    def _spawn_ffmpeg(self) -> None:
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "warning",
            "-fflags",
            "+nobuffer",
            "-flags",
            "low_delay",
            "-f",
            "mpeg",
            "-i",
            "pipe:0",
            "-c",
            "copy",
            "-f",
            "rtsp",
            "-rtsp_transport",
            "tcp",
            self.cfg.rtsp_publish_url,
        ]
        self._proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if self._proc.stdin is None:
            raise IsupError("ffmpeg stdin pipe not available")

    def _restart_ffmpeg(self) -> bool:
        if self._stop.is_set():
            return False
        if self._proc is not None:
            if self._proc.stdin is not None:
                try:
                    self._proc.stdin.close()
                except OSError:
                    pass
            if self._proc.poll() is None:
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    self._proc.kill()
        try:
            self._spawn_ffmpeg()
            return True
        except Exception:
            time.sleep(1.0)
            return False

    def push(self, chunk: bytes) -> None:
        if self._stop.is_set() or not chunk:
            return
        try:
            self._queue.put_nowait(chunk)
        except queue.Full:
            pass

    def _writer_loop(self) -> None:
        assert self._proc is not None and self._proc.stdin is not None
        while not self._stop.is_set():
            try:
                data = self._queue.get(timeout=0.2)
            except queue.Empty:
                if self._proc.poll() is not None and not self._restart_ffmpeg():
                    return
                continue

            if self._proc.poll() is not None and not self._restart_ffmpeg():
                return
            try:
                self._proc.stdin.write(data)
                self._proc.stdin.flush()
            except BrokenPipeError:
                if not self._restart_ffmpeg():
                    return

    def stop(self) -> None:
        self._stop.set()
        if self._writer_thread is not None:
            self._writer_thread.join(timeout=1.0)
        if self._proc is not None:
            if self._proc.stdin is not None:
                try:
                    self._proc.stdin.close()
                except OSError:
                    pass
            self._proc.terminate()
            try:
                self._proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._proc.kill()


class IsupServer:
    def __init__(self, cfg: AppConfig):
        self.cfg = cfg
        self._dll_path_handles: list[Any] = []
        cms_path = self._resolve_library_path(cfg.hcisupcms_path, "HCISUPCMS")
        stream_path = self._resolve_library_path(cfg.hcisupstream_path, "HCISUPStream")
        self._prepare_windows_dll_paths([cms_path, stream_path])
        try:
            self.cms = LIB_LOADER(cms_path)
            self.stream = LIB_LOADER(stream_path)
        except OSError as exc:
            raise IsupError(
                "Failed to load HCISUP native libraries. "
                f"cms='{cms_path}', stream='{stream_path}', error='{exc}'. "
                "Check OS/architecture compatibility (Windows DLLs need Windows runtime) "
                "and ensure dependency libraries are present."
            ) from exc
        self.publisher = RtspPublisher(cfg)

        self.user_id = LONG(-1)
        self.cms_listen_handle = LONG(-1)
        self.stream_listen_handle = LONG(-1)
        self.preview_handle = LONG(-1)
        self.session_id = LONG(-1)
        self.voice_listen_handle = LONG(-1)
        self.voice_link_handle = LONG(-1)
        self.voice_session_id = LONG(-1)
        self.voice_device_encode_type = -1
        self.voice_device_audio_chan = -1

        self._registered = threading.Event()
        self._register_type_counts: dict[int, int] = {}
        self._cached_local_ips: list[str] = []

        self._register_cb = DEVICE_REGISTER_CB(self._on_register)
        self._preview_data_cb = PREVIEW_DATA_CB(self._on_preview_data)
        self._preview_newlink_cb = PREVIEW_NEWLINK_CB(self._on_preview_newlink)
        self._voice_data_cb = VOICETALK_DATA_CB(self._on_voice_data)
        self._voice_newlink_cb = VOICETALK_NEWLINK_CB(self._on_voice_newlink)
        self._debug(
            f"callback_ptrs register={ctypes.cast(self._register_cb, ctypes.c_void_p).value} "
            f"preview_data={ctypes.cast(self._preview_data_cb, ctypes.c_void_p).value} "
            f"preview_newlink={ctypes.cast(self._preview_newlink_cb, ctypes.c_void_p).value}"
        )

        self._bind_functions()
        self._assert_abi()

    def _debug(self, msg: str) -> None:
        if self.cfg.debug:
            print(f"[DEBUG] {msg}", flush=True)

    def _resolve_library_path(self, configured: str, key: str) -> str:
        if os.path.isabs(configured) and os.path.exists(configured):
            return configured
        if os.path.exists(configured):
            return os.path.abspath(configured)

        names: list[str] = []
        if key == "HCISUPCMS":
            if IS_WINDOWS:
                names = ["HCISUPCMS.dll"]
            elif platform.system().lower() == "darwin":
                names = ["libHCISUPCMS.dylib", "libHCISUPCMS.so"]
            else:
                names = ["libHCISUPCMS.so", "libHCISUPCMS.dylib"]
        elif key == "HCISUPStream":
            if IS_WINDOWS:
                names = ["HCISUPStream.dll"]
            elif platform.system().lower() == "darwin":
                names = ["libHCISUPStream.dylib", "libHCISUPStream.so"]
            else:
                names = ["libHCISUPStream.so", "libHCISUPStream.dylib"]

        search_dirs: list[str] = []
        if self.cfg.sdk_dir:
            search_dirs.append(self.cfg.sdk_dir)
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        project_dir = os.path.abspath(os.path.join(base_dir, ".."))
        script_dir = os.path.dirname(__file__)
        # 플랫폼별 SDK 디렉토리 우선 검색
        if IS_WINDOWS:
            search_dirs.append(os.path.join(script_dir, "include", "lib64"))
        else:
            search_dirs.append(os.path.join(script_dir, "include", "linux"))
        search_dirs.extend(
            [
                os.getcwd(),
                script_dir,
                os.path.join(script_dir, ".."),
                os.path.join(script_dir, "include", "lib64"),
                os.path.join(script_dir, "include", "linux"),
                os.path.join(
                    script_dir, "include", "HK_ISUP_SDK", "lib64"
                ),
                os.path.join(
                    script_dir, "include", "HK_ISUP_SDK", "lib"
                ),
                os.path.join(base_dir, "lib"),
                os.path.join(base_dir, "HK_ISUP_SDK", "lib64"),
                os.path.join(base_dir, "HK_ISUP_SDK", "lib"),
                os.path.join(project_dir, "HK_ISUP_SDK", "lib64"),
                os.path.join(project_dir, "HK_ISUP_SDK", "lib"),
                "/usr/local/lib",
                "/opt/homebrew/lib",
                "/usr/lib",
            ]
        )

        for d in search_dirs:
            if not d:
                continue
            for n in names:
                p = os.path.abspath(os.path.join(d, n))
                if os.path.exists(p):
                    return p

        os_name = platform.system().lower()
        arch = platform.machine().lower()
        raise IsupError(
            f"Missing {key} shared library. configured='{configured}', "
            f"HCISUP_SDK_DIR='{self.cfg.sdk_dir}'. "
            f"Detected OS={os_name}, arch={arch}. "
            "This repository only includes headers; vendor SDK binaries are required. "
            "Set absolute paths with HCISUPCMS_PATH/HCISUPSTREAM_PATH or HCISUP_SDK_DIR. "
            "For Linux vendor package use .so files. On macOS, .dylib binaries are required; "
            "if vendor provides Linux-only SDK, run this service on Linux instead."
        )

    def _prepare_windows_dll_paths(self, dll_paths: list[str]) -> None:
        if not IS_WINDOWS:
            return
        add_dir = getattr(os, "add_dll_directory", None)
        if add_dir is None:
            return
        candidate_dirs: list[str] = []
        for p in dll_paths:
            candidate_dirs.append(os.path.dirname(p))
        if self.cfg.sdk_dir:
            candidate_dirs.append(self.cfg.sdk_dir)
        for p in dll_paths:
            candidate_dirs.append(os.path.join(os.path.dirname(p), "HCAapSDKCom"))

        seen: set[str] = set()
        for d in candidate_dirs:
            ad = os.path.abspath(d)
            if ad in seen or not os.path.isdir(ad):
                continue
            seen.add(ad)
            try:
                self._dll_path_handles.append(add_dir(ad))
                self._debug(f"add_dll_directory: {ad}")
            except OSError:
                continue

    def _assert_abi(self) -> None:
        if ctypes.sizeof(LONG) != 4:
            raise IsupError("ABI mismatch: LONG must be 4 bytes")
        if ctypes.sizeof(DWORD) != 4:
            raise IsupError("ABI mismatch: DWORD must be 4 bytes")
        if ctypes.sizeof(NET_EHOME_IPADDRESS) != 132:
            raise IsupError("ABI mismatch: NET_EHOME_IPADDRESS size != 132")

    def _bind_functions(self) -> None:
        self.cms.NET_ECMS_Init.restype = ctypes.c_int
        self.cms.NET_ECMS_Fini.restype = ctypes.c_int
        self.cms.NET_ECMS_GetLastError.restype = DWORD
        self.cms.NET_ECMS_SetLogToFile.argtypes = [
            DWORD,
            ctypes.c_char_p,
            BOOL,
        ]
        self.cms.NET_ECMS_SetLogToFile.restype = BOOL
        self.cms.NET_ECMS_SetSDKInitCfg.argtypes = [ctypes.c_int, ctypes.c_void_p]
        self.cms.NET_ECMS_SetSDKInitCfg.restype = BOOL
        self.cms.NET_ECMS_SetSDKLocalCfg.argtypes = [ctypes.c_int, ctypes.c_void_p]
        self.cms.NET_ECMS_SetSDKLocalCfg.restype = BOOL
        self.cms.NET_ECMS_StartListen.argtypes = [
            ctypes.POINTER(NET_EHOME_CMS_LISTEN_PARAM)
        ]
        self.cms.NET_ECMS_StartListen.restype = LONG
        self.cms.NET_ECMS_StopListen.argtypes = [LONG]
        self.cms.NET_ECMS_StopListen.restype = BOOL
        self.cms.NET_ECMS_ForceLogout.argtypes = [LONG]
        self.cms.NET_ECMS_ForceLogout.restype = BOOL
        self.cms.NET_ECMS_SetDeviceSessionKey.argtypes = [
            ctypes.POINTER(NET_EHOME_DEV_SESSIONKEY)
        ]
        self.cms.NET_ECMS_SetDeviceSessionKey.restype = BOOL
        self.cms.NET_ECMS_StartGetRealStreamV11.argtypes = [
            LONG,
            ctypes.POINTER(NET_EHOME_PREVIEWINFO_IN_V11),
            ctypes.POINTER(NET_EHOME_PREVIEWINFO_OUT),
        ]
        self.cms.NET_ECMS_StartGetRealStreamV11.restype = BOOL
        self.cms.NET_ECMS_StartPushRealStream.argtypes = [
            LONG,
            ctypes.POINTER(NET_EHOME_PUSHSTREAM_IN),
            ctypes.POINTER(NET_EHOME_PUSHSTREAM_OUT),
        ]
        self.cms.NET_ECMS_StartPushRealStream.restype = BOOL
        self.cms.NET_ECMS_StopGetRealStream.argtypes = [LONG, LONG]
        self.cms.NET_ECMS_StopGetRealStream.restype = BOOL
        self.cms.NET_ECMS_RemoteControl.argtypes = [
            LONG,
            DWORD,
            ctypes.POINTER(NET_EHOME_REMOTE_CTRL_PARAM),
        ]
        self.cms.NET_ECMS_RemoteControl.restype = BOOL
        self.cms.NET_ECMS_StartVoiceWithStmServer.argtypes = [
            LONG,
            ctypes.POINTER(NET_EHOME_VOICE_TALK_IN),
            ctypes.POINTER(NET_EHOME_VOICE_TALK_OUT),
        ]
        self.cms.NET_ECMS_StartVoiceWithStmServer.restype = BOOL
        self.cms.NET_ECMS_StartPushVoiceStream.argtypes = [
            LONG,
            ctypes.POINTER(NET_EHOME_PUSHVOICE_IN),
            ctypes.POINTER(NET_EHOME_PUSHVOICE_OUT),
        ]
        self.cms.NET_ECMS_StartPushVoiceStream.restype = BOOL
        self.cms.NET_ECMS_StopVoiceTalkWithStmServer.argtypes = [LONG, LONG]
        self.cms.NET_ECMS_StopVoiceTalkWithStmServer.restype = BOOL

        self.stream.NET_ESTREAM_Init.restype = ctypes.c_int
        self.stream.NET_ESTREAM_Fini.restype = ctypes.c_int
        self.stream.NET_ESTREAM_GetLastError.restype = DWORD
        self.stream.NET_ESTREAM_SetLogToFile.argtypes = [
            LONG,
            ctypes.c_char_p,
            BOOL,
        ]
        self.stream.NET_ESTREAM_SetLogToFile.restype = BOOL
        self.stream.NET_ESTREAM_SetSDKInitCfg.argtypes = [ctypes.c_int, ctypes.c_void_p]
        self.stream.NET_ESTREAM_SetSDKInitCfg.restype = BOOL
        self.stream.NET_ESTREAM_SetSDKLocalCfg.argtypes = [
            ctypes.c_int,
            ctypes.c_void_p,
        ]
        self.stream.NET_ESTREAM_SetSDKLocalCfg.restype = BOOL
        self.stream.NET_ESTREAM_StartListenPreview.argtypes = [
            ctypes.POINTER(NET_EHOME_LISTEN_PREVIEW_CFG)
        ]
        self.stream.NET_ESTREAM_StartListenPreview.restype = LONG
        self.stream.NET_ESTREAM_StopListenPreview.argtypes = [LONG]
        self.stream.NET_ESTREAM_StopListenPreview.restype = BOOL
        self.stream.NET_ESTREAM_StopPreview.argtypes = [LONG]
        self.stream.NET_ESTREAM_StopPreview.restype = BOOL
        self.stream.NET_ESTREAM_SetPreviewDataCB.argtypes = [
            LONG,
            ctypes.POINTER(NET_EHOME_PREVIEW_DATA_CB_PARAM),
        ]
        self.stream.NET_ESTREAM_SetPreviewDataCB.restype = BOOL
        self.stream.NET_ESTREAM_StartListenVoiceTalk.argtypes = [
            ctypes.POINTER(NET_EHOME_LISTEN_VOICETALK_CFG)
        ]
        self.stream.NET_ESTREAM_StartListenVoiceTalk.restype = LONG
        self.stream.NET_ESTREAM_StopListenVoiceTalk.argtypes = [LONG]
        self.stream.NET_ESTREAM_StopListenVoiceTalk.restype = BOOL
        self.stream.NET_ESTREAM_SetVoiceTalkDataCB.argtypes = [
            LONG,
            ctypes.POINTER(NET_EHOME_VOICETALK_DATA_CB_PARAM),
        ]
        self.stream.NET_ESTREAM_SetVoiceTalkDataCB.restype = BOOL
        self.stream.NET_ESTREAM_SendVoiceTalkData.argtypes = [
            LONG,
            ctypes.POINTER(NET_EHOME_VOICETALK_DATA),
        ]
        self.stream.NET_ESTREAM_SendVoiceTalkData.restype = LONG
        self.stream.NET_ESTREAM_StopVoiceTalk.argtypes = [LONG]
        self.stream.NET_ESTREAM_StopVoiceTalk.restype = BOOL

    def _last_ecms_error(self) -> int:
        return int(self.cms.NET_ECMS_GetLastError())

    def _last_estream_error(self) -> int:
        return int(self.stream.NET_ESTREAM_GetLastError())

    def _detect_sdk_dir(self) -> str:
        if self.cfg.sdk_dir:
            return self.cfg.sdk_dir
        cms_abs = self._resolve_library_path(self.cfg.hcisupcms_path, "HCISUPCMS")
        return os.path.dirname(cms_abs)

    def _apply_sdk_paths(self) -> None:
        sdk_hint_dir = self._detect_sdk_dir()

        crypto_path = self.cfg.openssl_libcrypto_path
        ssl_path = self.cfg.openssl_libssl_path
        if not crypto_path and sdk_hint_dir:
            candidate = os.path.join(
                sdk_hint_dir, "libeay32.dll" if IS_WINDOWS else "libcrypto.so"
            )
            if os.path.exists(candidate):
                crypto_path = candidate
        if not ssl_path and sdk_hint_dir:
            candidate = os.path.join(
                sdk_hint_dir, "ssleay32.dll" if IS_WINDOWS else "libssl.so"
            )
            if os.path.exists(candidate):
                ssl_path = candidate

        if crypto_path:
            libcrypto = ctypes.create_string_buffer(crypto_path.encode("ascii"))
            ok1 = self.cms.NET_ECMS_SetSDKInitCfg(
                0, ctypes.cast(libcrypto, ctypes.c_void_p)
            )
            ok2 = self.stream.NET_ESTREAM_SetSDKInitCfg(
                0, ctypes.cast(libcrypto, ctypes.c_void_p)
            )
            self._debug(
                f"SetSDKInitCfg(libcrypto) cms={ok1} err={self._last_ecms_error()} "
                f"stream={ok2} err={self._last_estream_error()} path={crypto_path}"
            )
        if ssl_path:
            libssl = ctypes.create_string_buffer(ssl_path.encode("ascii"))
            ok1 = self.cms.NET_ECMS_SetSDKInitCfg(
                1, ctypes.cast(libssl, ctypes.c_void_p)
            )
            ok2 = self.stream.NET_ESTREAM_SetSDKInitCfg(
                1, ctypes.cast(libssl, ctypes.c_void_p)
            )
            self._debug(
                f"SetSDKInitCfg(libssl) cms={ok1} err={self._last_ecms_error()} "
                f"stream={ok2} err={self._last_estream_error()} path={ssl_path}"
            )

    def _apply_local_cfg_paths(self) -> None:
        sdk_hint_dir = self._detect_sdk_dir()
        if not sdk_hint_dir:
            return
        com_dir = os.path.join(sdk_hint_dir, "HCAapSDKCom")
        if os.path.isdir(com_dir):
            com_cfg = ctypes.create_string_buffer(com_dir.encode("ascii"))
            ok1 = self.cms.NET_ECMS_SetSDKLocalCfg(
                5, ctypes.cast(com_cfg, ctypes.c_void_p)
            )
            ok2 = self.stream.NET_ESTREAM_SetSDKLocalCfg(
                5, ctypes.cast(com_cfg, ctypes.c_void_p)
            )
            self._debug(
                f"SetSDKLocalCfg(COM_PATH) cms={ok1} err={self._last_ecms_error()} "
                f"stream={ok2} err={self._last_estream_error()} path={com_dir}"
            )
        else:
            self._debug(f"COM_PATH not found: {com_dir}")

    def _dump_network_context(self) -> None:
        host = socket.gethostname()
        ips: list[str] = []
        try:
            ips = list(dict.fromkeys(socket.gethostbyname_ex(host)[2]))
        except OSError:
            pass
        self._cached_local_ips = ips
        self._debug(
            f"host={host}, local_ips={ips}, cms_listen={self.cfg.cms_listen_ip}:{self.cfg.cms_listen_port}, "
            f"stream_listen={self.cfg.stream_listen_ip}:{self.cfg.stream_listen_port}, "
            f"stream_public={self.cfg.stream_public_ip}:{self.cfg.stream_public_port}, "
            f"das_public={self._das_address()}:{self._das_port()}"
        )
        effective_stream_ip = self._effective_stream_public_ip()
        if self._is_loopback_or_any(effective_stream_ip):
            print(
                "[WARN] ISUP_STREAM_PUBLIC_IP is loopback/any-address. External camera cannot push stream there.",
                flush=True,
            )
        elif effective_stream_ip != self.cfg.stream_public_ip:
            print(
                f"[INFO] Auto-selected stream public IP: {effective_stream_ip}",
                flush=True,
            )
        das_addr = self._das_address()
        if das_addr in {"127.0.0.1", "0.0.0.0", "localhost", ""}:
            print(
                "[WARN] DAS address is loopback/empty. Camera may repeat AUTH/SESSIONKEY/DAS without going online.",
                flush=True,
            )

    def _is_loopback_or_any(self, ip: str) -> bool:
        return ip.strip() in {"", "127.0.0.1", "0.0.0.0", "localhost"}

    def _best_reachable_ip(self) -> str:
        if self.cfg.auto_public_ip:
            return self.cfg.auto_public_ip
        if not self._cached_local_ips:
            try:
                self._cached_local_ips = list(
                    dict.fromkeys(socket.gethostbyname_ex(socket.gethostname())[2])
                )
            except OSError:
                self._cached_local_ips = []

        candidates: list[str] = []
        for raw in self._cached_local_ips:
            try:
                ip = ipaddress.ip_address(raw)
            except ValueError:
                continue
            if not isinstance(ip, ipaddress.IPv4Address):
                continue
            if ip.is_loopback or ip.is_link_local or ip.is_unspecified:
                continue
            candidates.append(raw)
        if not candidates:
            return ""

        public_candidates: list[str] = []
        private_candidates: list[str] = []
        for c in candidates:
            ip = ipaddress.ip_address(c)
            if ip.is_private:
                private_candidates.append(c)
            else:
                public_candidates.append(c)
        if public_candidates:
            return public_candidates[0]
        return private_candidates[0]

    def _effective_stream_public_ip(self) -> str:
        if not self._is_loopback_or_any(self.cfg.stream_public_ip):
            return self.cfg.stream_public_ip
        guessed = self._best_reachable_ip()
        if guessed:
            self._debug(
                f"auto-selected stream_public_ip={guessed} (from {self.cfg.stream_public_ip})"
            )
            return guessed
        return self.cfg.stream_public_ip

    def _das_address(self) -> str:
        if self.cfg.das_public_ip:
            return self.cfg.das_public_ip
        stream_ip = self._effective_stream_public_ip()
        if stream_ip:
            return stream_ip
        return self.cfg.cms_listen_ip

    def _das_port(self) -> int:
        if self.cfg.das_port > 0:
            return self.cfg.das_port
        return self.cfg.cms_listen_port

    def _cms_target_address(self) -> str:
        if self.cfg.cms_public_ip:
            return self.cfg.cms_public_ip
        if self._is_loopback_or_any(self.cfg.cms_listen_ip):
            guessed = self._best_reachable_ip()
            if guessed:
                return guessed
        return self.cfg.cms_listen_ip

    def _probe_local_stream_port(self) -> bool:
        targets: list[str] = ["127.0.0.1"]
        guessed = self._best_reachable_ip()
        if guessed:
            targets.append(guessed)
        for ip in targets:
            try:
                with socket.create_connection(
                    (ip, self.cfg.stream_listen_port), timeout=1.0
                ):
                    self._debug(
                        f"local probe success: {ip}:{self.cfg.stream_listen_port} is accepting TCP"
                    )
                    return True
            except OSError:
                continue
        self._debug(
            f"local probe failed: stream listen port {self.cfg.stream_listen_port} not reachable locally"
        )
        return False

    def _on_register(
        self,
        l_user_id: int,
        data_type: int,
        p_out: int,
        _dw_out_len: int,
        p_in: int,
        _dw_in_len: int,
        _p_user: int,
    ) -> int:
        try:
            self._debug(
                f"register-callback: user_id={l_user_id}, data_type={data_type}, "
                f"out_len={_dw_out_len}, in_len={_dw_in_len}"
            )
            self._register_type_counts[data_type] = (
                self._register_type_counts.get(data_type, 0) + 1
            )
            if data_type == ENUM_DEV_AUTH:
                key = self.cfg.ehome_key.encode("ascii")[:31]
                ctypes.memset(p_in, 0, 32)
                ctypes.memmove(p_in, key, len(key))
                return 1

            if data_type == ENUM_DEV_SESSIONKEY and p_out:
                dev_v12 = ctypes.cast(
                    p_out, ctypes.POINTER(NET_EHOME_DEV_REG_INFO_V12)
                ).contents
                sess = NET_EHOME_DEV_SESSIONKEY()
                ctypes.memmove(
                    sess.sDeviceID, dev_v12.struRegInfo.byDeviceID, MAX_DEVICE_ID_LEN
                )
                ctypes.memmove(
                    sess.sSessionKey,
                    dev_v12.struRegInfo.bySessionKey,
                    MAX_MASTER_KEY_LEN,
                )
                self.cms.NET_ECMS_SetDeviceSessionKey(ctypes.byref(sess))
                return 1

            if data_type == ENUM_DEV_DAS_REQ:
                das_addr = self._das_address()
                das_port = self._das_port()
                payload = (
                    '{"Type":"DAS","DasInfo":{"Address":"%s","Domain":"isup.local",'
                    '"ServerID":"das_%s_%d","Port":%d,"UdpPort":%d}}'
                    % (
                        das_addr,
                        das_addr,
                        das_port,
                        das_port,
                        das_port,
                    )
                ).encode("ascii")
                ctypes.memmove(p_in, payload, len(payload) + 1)
                self._debug(f"DAS response: {payload.decode('ascii', errors='ignore')}")
                if (
                    self._register_type_counts.get(ENUM_DEV_DAS_REQ, 0) >= 3
                    and self._register_type_counts.get(ENUM_DEV_ON, 0) == 0
                ):
                    print(
                        "[HINT] Repeated DAS_REQ without DEV_ON: verify ISUP_DAS_PUBLIC_IP/ISUP_DAS_PORT are reachable from camera.",
                        flush=True,
                    )
                return 1

            if data_type == ENUM_DEV_ON:
                dev = ctypes.cast(
                    p_out, ctypes.POINTER(NET_EHOME_DEV_REG_INFO)
                ).contents
                self.user_id = LONG(l_user_id)
                self._registered.set()
                device_id = _bytes_from_ubyte_array(dev.byDeviceID).decode(
                    "ascii", errors="ignore"
                )
                dev_ip = dev.struDevAdd.szIP.split(b"\x00", 1)[0].decode(
                    "ascii", errors="ignore"
                )
                print(
                    f"device online: user_id={l_user_id}, device_id={device_id}, ip={dev_ip}",
                    flush=True,
                )

                if p_in:
                    server_info = ctypes.cast(
                        p_in, ctypes.POINTER(NET_EHOME_SERVER_INFO_HEAD)
                    ).contents
                    server_info.dwSize = ctypes.sizeof(NET_EHOME_SERVER_INFO)
                    server_info.dwKeepAliveSec = 15
                    server_info.dwTimeOutCount = 6
                return 1

            if data_type == ENUM_DEV_OFF:
                print(f"device offline: user_id={l_user_id}", flush=True)
                return 1

            self._debug(f"register-callback unhandled data_type={data_type}")
            return 1
        except Exception as exc:
            print(f"[ERROR] register-callback exception: {exc}", flush=True)
            print(traceback.format_exc(), flush=True)
            return 0

    def _on_preview_data(
        self,
        preview_handle: int,
        p_msg: Any,
        _p_user: int,
    ) -> None:
        if not p_msg:
            return
        msg = ctypes.cast(p_msg, ctypes.POINTER(NET_EHOME_PREVIEW_CB_MSG)).contents
        self.preview_handle = LONG(preview_handle)
        if msg.byDataType not in (NET_EHOME_SYSHEAD, NET_EHOME_STREAMDATA):
            return
        if not msg.pRecvdata or msg.dwDataLen == 0:
            return
        chunk = ctypes.string_at(msg.pRecvdata, msg.dwDataLen)
        self.publisher.push(chunk)

    def _on_preview_newlink(
        self,
        link_handle: int,
        p_new: Any,
        _p_user: int,
    ) -> int:
        if not p_new:
            return 0

        cb_param = NET_EHOME_PREVIEW_DATA_CB_PARAM()
        cb_param.fnPreviewDataCB = self._preview_data_cb
        cb_param.pUserData = None
        cb_param.byStreamFormat = 0

        ok = self.stream.NET_ESTREAM_SetPreviewDataCB(
            LONG(link_handle), ctypes.byref(cb_param)
        )
        if ok == 0:
            print(f"SetPreviewDataCB failed: {self._last_estream_error()}", flush=True)
            return 0
        print("preview callback registered", flush=True)
        return 1

    def _on_voice_data(
        self,
        _handle: int,
        _info: Any,
        _user_data: int,
    ) -> int:
        return 1

    def _on_voice_newlink(
        self,
        handle: int,
        _new_link: Any,
        _user_data: int,
    ) -> int:
        if _new_link:
            info = ctypes.cast(
                _new_link, ctypes.POINTER(NET_EHOME_VOICETALK_NEWLINK_CB_INFO)
            ).contents
            self.voice_device_encode_type = int(info.dwEncodeType)
            self.voice_device_audio_chan = int(info.dwAudioChan)
            codec_name = VOICE_ENCODE_NAMES.get(
                self.voice_device_encode_type, "unknown"
            )
            print(
                f"voice newlink: encode_type={self.voice_device_encode_type}({codec_name}), audio_chan={self.voice_device_audio_chan}",
                flush=True,
            )
        cb_param = NET_EHOME_VOICETALK_DATA_CB_PARAM()
        cb_param.fnVoiceTalkDataCB = self._voice_data_cb
        cb_param.pUserData = None
        ok = self.stream.NET_ESTREAM_SetVoiceTalkDataCB(
            LONG(handle), ctypes.byref(cb_param)
        )
        if ok == 0:
            print(
                f"NET_ESTREAM_SetVoiceTalkDataCB failed: {self._last_estream_error()}",
                flush=True,
            )
            return 0
        self.voice_link_handle = LONG(handle)
        print(f"voice link ready: handle={handle}", flush=True)
        return 1

    def _wait_voice_link_ready(self, timeout_sec: int) -> bool:
        end_at = time.time() + max(1, timeout_sec)
        while time.time() < end_at:
            if self.voice_link_handle.value >= 0:
                return True
            time.sleep(0.1)
        return self.voice_link_handle.value >= 0

    def voice_start(
        self,
        voice_server_ip: str | None = None,
        voice_server_port: int | None = None,
        voice_listen_ip: str | None = None,
        voice_listen_port: int | None = None,
        voice_channel: int | None = None,
    ) -> None:
        if self.user_id.value < 0:
            raise IsupError("device is not online")
        if self.voice_session_id.value >= 0:
            if not self._wait_voice_link_ready(self.cfg.voice_link_wait_sec):
                raise IsupError(
                    "voice session exists but link is not ready; run voice_stop then voice_start"
                )
            return

        vs_ip = voice_server_ip if voice_server_ip else self.cfg.voice_server_ip
        vs_port = (
            voice_server_port
            if voice_server_port is not None
            else self.cfg.voice_server_port
        )
        vl_ip = voice_listen_ip if voice_listen_ip else self.cfg.voice_listen_ip
        vl_port = (
            voice_listen_port
            if voice_listen_port is not None
            else self.cfg.voice_listen_port
        )
        v_channel = (
            voice_channel if voice_channel is not None else self.cfg.voice_channel
        )

        listen_cfg = NET_EHOME_LISTEN_VOICETALK_CFG()
        _write_ip(listen_cfg.struIPAdress, vl_ip)
        listen_cfg.struIPAdress.wPort = WORD(vl_port)
        listen_cfg.fnNewLinkCB = self._voice_newlink_cb
        listen_cfg.pUser = None
        listen_cfg.byLinkMode = self.cfg.voice_link_mode
        listen_cfg.byLinkEncrypt = 0

        try:
            self.voice_listen_handle = LONG(
                self.stream.NET_ESTREAM_StartListenVoiceTalk(ctypes.byref(listen_cfg))
            )
            if self.voice_listen_handle.value < 0:
                raise IsupError(
                    f"NET_ESTREAM_StartListenVoiceTalk failed: {self._last_estream_error()}"
                )

            talk_in = NET_EHOME_VOICE_TALK_IN()
            talk_in.dwVoiceChan = DWORD(v_channel)
            _write_ip(talk_in.struStreamSever, vs_ip)
            talk_in.struStreamSever.wPort = WORD(vs_port)
            talk_out = NET_EHOME_VOICE_TALK_OUT()

            ok = self.cms.NET_ECMS_StartVoiceWithStmServer(
                self.user_id,
                ctypes.byref(talk_in),
                ctypes.byref(talk_out),
            )
            if ok == 0:
                raise IsupError(
                    f"NET_ECMS_StartVoiceWithStmServer failed: {self._last_ecms_error()}"
                )
            self.voice_session_id = LONG(talk_out.lSessionID)

            push_in = NET_EHOME_PUSHVOICE_IN()
            push_in.dwSize = DWORD(ctypes.sizeof(NET_EHOME_PUSHVOICE_IN))
            push_in.lSessionID = self.voice_session_id
            push_out = NET_EHOME_PUSHVOICE_OUT()
            push_out.dwSize = DWORD(ctypes.sizeof(NET_EHOME_PUSHVOICE_OUT))

            ok = self.cms.NET_ECMS_StartPushVoiceStream(
                self.user_id,
                ctypes.byref(push_in),
                ctypes.byref(push_out),
            )
            if ok == 0:
                err = self._last_ecms_error()
                raise IsupError(
                    "NET_ECMS_StartPushVoiceStream failed: "
                    f"{err} (server={vs_ip}:{vs_port}, listen={vl_ip}:{vl_port}, channel={v_channel}). "
                    "Check voice server port reachability from camera and device voice capability."
                )
        except Exception:
            self.voice_stop()
            raise

        print(
            f"voice talk started: session_id={self.voice_session_id.value}, "
            f"listen={vl_ip}:{vl_port}, server={vs_ip}:{vs_port}, channel={v_channel}",
            flush=True,
        )
        if not self._wait_voice_link_ready(self.cfg.voice_link_wait_sec):
            raise IsupError(
                "voice link is not ready yet (no new-link callback). "
                "Check VoiceSmsServerIP/VoiceSmsServerPort reachability from camera."
            )

    def voice_send_bytes(self, payload: bytes, timeout_ms: int = 5000) -> None:
        if self.voice_link_handle.value < 0:
            raise IsupError("voice link is not ready")
        if not payload:
            return
        buf = ctypes.create_string_buffer(payload)
        data = NET_EHOME_VOICETALK_DATA()
        data.pSendBuf = ctypes.cast(buf, ctypes.c_void_p)
        data.dwDataLen = DWORD(len(payload))
        data.dwTimeout = DWORD(timeout_ms)
        sent = self.stream.NET_ESTREAM_SendVoiceTalkData(
            self.voice_link_handle,
            ctypes.byref(data),
        )
        if sent <= 0:
            raise IsupError(
                f"NET_ESTREAM_SendVoiceTalkData failed: {self._last_estream_error()}"
            )

    def voice_send_file(
        self,
        file_path: str,
        chunk_bytes: int = 640,
        delay_ms: int = 40,
    ) -> int:
        if not os.path.exists(file_path):
            raise IsupError(f"voice file not found: {file_path}")
        total = 0
        with open(file_path, "rb") as f:
            while True:
                data = f.read(max(1, chunk_bytes))
                if not data:
                    break
                self.voice_send_bytes(data)
                total += len(data)
                time.sleep(max(0, delay_ms) / 1000.0)
        return total

    def _codec_to_ffmpeg(self, codec: str) -> tuple[str, int, int]:
        name = codec.lower()
        if name in {"g711u", "ulaw"}:
            return ("mulaw", 160, 20)
        if name in {"pcm", "pcm16", "s16le"}:
            return ("s16le", 320, 20)
        raise IsupError(f"unsupported codec for wav conversion: {codec}")

    def _auto_codec(self) -> str:
        if self.voice_device_encode_type == 1:
            return "g711u"
        if self.voice_device_encode_type == 2:
            raise IsupError(
                "device requested G.711A (encode_type=2), but this build is G.711U-only"
            )
        if self.voice_device_encode_type == 6:
            return "pcm"
        return "g711u"

    def voice_send_wav(
        self,
        wav_path: str,
        codec: str = "auto",
        chunk_bytes: int = 0,
        delay_ms: int = 0,
    ) -> int:
        if not os.path.exists(wav_path):
            raise IsupError(f"wav file not found: {wav_path}")
        codec_final = self._auto_codec() if codec == "auto" else codec
        ffmpeg_fmt, def_chunk, def_delay = self._codec_to_ffmpeg(codec_final)
        chunk = chunk_bytes if chunk_bytes > 0 else def_chunk
        delay = delay_ms if delay_ms > 0 else def_delay

        fd, temp_raw = tempfile.mkstemp(prefix="voice_", suffix=".raw")
        os.close(fd)
        try:
            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                wav_path,
                "-ac",
                "1",
                "-ar",
                "8000",
                "-f",
                ffmpeg_fmt,
                temp_raw,
            ]
            proc = subprocess.run(
                cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            if proc.returncode != 0:
                raise IsupError("ffmpeg wav conversion failed")
            return self.voice_send_file(temp_raw, chunk_bytes=chunk, delay_ms=delay)
        finally:
            try:
                os.remove(temp_raw)
            except OSError:
                pass

    def voice_stop(self) -> None:
        had_voice = (
            self.voice_link_handle.value >= 0 or self.voice_session_id.value >= 0
        )
        if self.voice_link_handle.value >= 0:
            self.stream.NET_ESTREAM_StopVoiceTalk(self.voice_link_handle)
            self.voice_link_handle = LONG(-1)
        if self.voice_session_id.value >= 0 and self.user_id.value >= 0:
            self.cms.NET_ECMS_StopVoiceTalkWithStmServer(
                self.user_id,
                self.voice_session_id,
            )
            self.voice_session_id = LONG(-1)
        if self.voice_listen_handle.value >= 0:
            self.stream.NET_ESTREAM_StopListenVoiceTalk(self.voice_listen_handle)
            self.voice_listen_handle = LONG(-1)
        if had_voice:
            print("voice talk stopped", flush=True)

    def voice_status(self) -> str:
        codec_name = VOICE_ENCODE_NAMES.get(self.voice_device_encode_type, "unknown")
        return (
            f"voice_session_id={self.voice_session_id.value}, "
            f"voice_link_handle={self.voice_link_handle.value}, "
            f"voice_listen_handle={self.voice_listen_handle.value}, "
            f"voice_device_encode_type={self.voice_device_encode_type}({codec_name}), "
            f"voice_device_audio_chan={self.voice_device_audio_chan}"
        )

    def ptz_control(self, channel: int, command: str, action: int, speed: int) -> None:
        if self.user_id.value < 0:
            raise IsupError("device is not online")
        cmd = PTZ_COMMANDS.get(command)
        if cmd is None:
            raise IsupError(f"unknown PTZ command: {command}")

        speed_clamped = max(0, min(7, speed))
        ch = ctypes.c_int(channel)
        ptz = NET_EHOME_PTZ_PARAM()
        ptz.dwSize = DWORD(ctypes.sizeof(NET_EHOME_PTZ_PARAM))
        ptz.byPTZCmd = cmd
        ptz.byAction = action
        ptz.bySpeed = speed_clamped

        ctrl = NET_EHOME_REMOTE_CTRL_PARAM()
        ctrl.dwSize = DWORD(ctypes.sizeof(NET_EHOME_REMOTE_CTRL_PARAM))
        ctrl.lpCondBuffer = ctypes.cast(ctypes.byref(ch), ctypes.c_void_p)
        ctrl.dwCondBufferSize = DWORD(ctypes.sizeof(ch))
        ctrl.lpInbuffer = ctypes.cast(ctypes.byref(ptz), ctypes.c_void_p)
        ctrl.dwInBufferSize = DWORD(ctypes.sizeof(ptz))

        ok = self.cms.NET_ECMS_RemoteControl(
            self.user_id,
            DWORD(NET_EHOME_PTZ_CTRL),
            ctypes.byref(ctrl),
        )
        if ok == 0:
            raise IsupError(f"NET_ECMS_RemoteControl failed: {self._last_ecms_error()}")

    def ptz_move(
        self, channel: int, command: str, duration_sec: float, speed: int
    ) -> None:
        self.ptz_control(channel, command, action=0, speed=speed)
        time.sleep(max(0.05, duration_sec))
        self.ptz_control(channel, command, action=1, speed=speed)

    def start(self) -> None:
        os.makedirs(self.cfg.log_dir, exist_ok=True)
        self._dump_network_context()
        self._apply_sdk_paths()

        if self.cms.NET_ECMS_Init() == 0:
            raise IsupError(f"NET_ECMS_Init failed: {self._last_ecms_error()}")
        if self.stream.NET_ESTREAM_Init() == 0:
            raise IsupError(f"NET_ESTREAM_Init failed: {self._last_estream_error()}")
        self._apply_local_cfg_paths()

        self.cms.NET_ECMS_SetLogToFile(3, self.cfg.log_dir.encode("ascii"), 0)
        self.stream.NET_ESTREAM_SetLogToFile(3, self.cfg.log_dir.encode("ascii"), 0)

        cms_listen = NET_EHOME_CMS_LISTEN_PARAM()
        _write_ip(cms_listen.struAddress, self.cfg.cms_listen_ip)
        cms_listen.struAddress.wPort = self.cfg.cms_listen_port
        cms_listen.fnCB = self._register_cb
        cms_listen.pUserData = None
        cms_listen.dwKeepAliveSec = 30
        cms_listen.dwTimeOutCount = 3

        self.cms_listen_handle = LONG(
            self.cms.NET_ECMS_StartListen(ctypes.byref(cms_listen))
        )
        if self.cms_listen_handle.value < 0:
            raise IsupError(f"NET_ECMS_StartListen failed: {self._last_ecms_error()}")
        print(
            f"CMS listening on {self.cfg.cms_listen_ip}:{self.cfg.cms_listen_port}",
            flush=True,
        )
        print(
            "waiting for device registration... "
            f"(camera -> {self._cms_target_address()}:{self.cfg.cms_listen_port})",
            flush=True,
        )
        timeout = self.cfg.registration_timeout_sec
        wait_start = time.time()
        next_heartbeat = wait_start + max(1, self.cfg.registration_heartbeat_sec)
        if timeout > 0 and not self._registered.wait(timeout=timeout):
            print(
                f"registration timeout ({timeout}s), keep waiting...",
                flush=True,
            )
        while not self._registered.wait(timeout=1):
            now = time.time()
            if now >= next_heartbeat:
                elapsed = int(now - wait_start)
                print(
                    "[WAIT] no device registration yet "
                    f"({elapsed}s). expected camera target: {self._cms_target_address()}:{self.cfg.cms_listen_port}, "
                    f"cms_last_error={self._last_ecms_error()}",
                    flush=True,
                )
                next_heartbeat = now + max(1, self.cfg.registration_heartbeat_sec)
            continue

        self.publisher.start()

        stream_listen = NET_EHOME_LISTEN_PREVIEW_CFG()
        _write_ip(stream_listen.struIPAdress, self.cfg.stream_listen_ip)
        stream_listen.struIPAdress.wPort = self.cfg.stream_listen_port
        stream_listen.fnNewLinkCB = self._preview_newlink_cb
        stream_listen.pUser = None
        stream_listen.byLinkMode = self.cfg.link_mode
        stream_listen.byLinkEncrypt = 0

        self.stream_listen_handle = LONG(
            self.stream.NET_ESTREAM_StartListenPreview(ctypes.byref(stream_listen))
        )
        if self.stream_listen_handle.value < 0:
            raise IsupError(
                f"NET_ESTREAM_StartListenPreview failed: {self._last_estream_error()}"
            )
        print(
            f"stream listen on {self.cfg.stream_listen_ip}:{self.cfg.stream_listen_port}",
            flush=True,
        )
        self._probe_local_stream_port()

        pre_in = NET_EHOME_PREVIEWINFO_IN_V11()
        pre_in.iChannel = self.cfg.channel
        pre_in.dwLinkMode = self.cfg.link_mode
        pre_in.dwStreamType = self.cfg.stream_type
        effective_stream_ip = self._effective_stream_public_ip()
        _write_ip(pre_in.struStreamSever, effective_stream_ip)
        pre_in.struStreamSever.wPort = self.cfg.stream_public_port
        pre_out = NET_EHOME_PREVIEWINFO_OUT()
        self._debug(
            "StartGetRealStreamV11 target "
            f"stream_server={effective_stream_ip}:{self.cfg.stream_public_port}, "
            f"channel={self.cfg.channel}, stream_type={self.cfg.stream_type}, link_mode={self.cfg.link_mode}"
        )

        ok = self.cms.NET_ECMS_StartGetRealStreamV11(
            self.user_id, ctypes.byref(pre_in), ctypes.byref(pre_out)
        )
        if ok == 0:
            raise IsupError(
                f"NET_ECMS_StartGetRealStreamV11 failed: {self._last_ecms_error()}"
            )

        self.session_id = LONG(pre_out.lSessionID)
        self._debug(f"StartGetRealStreamV11 success session_id={self.session_id.value}")
        push_in = NET_EHOME_PUSHSTREAM_IN()
        push_in.dwSize = ctypes.sizeof(NET_EHOME_PUSHSTREAM_IN)
        push_in.lSessionID = self.session_id
        push_out = NET_EHOME_PUSHSTREAM_OUT()
        push_out.dwSize = ctypes.sizeof(NET_EHOME_PUSHSTREAM_OUT)

        max_tries = max(1, self.cfg.push_retry_count)
        ok = 0
        last_err = 0
        for attempt in range(1, max_tries + 1):
            ok = self.cms.NET_ECMS_StartPushRealStream(
                self.user_id, ctypes.byref(push_in), ctypes.byref(push_out)
            )
            if ok != 0:
                break
            last_err = self._last_ecms_error()
            self._debug(
                f"StartPushRealStream attempt {attempt}/{max_tries} failed: err={last_err}, "
                f"session_id={self.session_id.value}, stream_server={effective_stream_ip}:{self.cfg.stream_public_port}"
            )
            if last_err == NET_PREVIEW_ERR_CONNECT_SERVER_FAIL:
                print(
                    "[HINT] error 169 (NET_PREVIEW_ERR_CONNECT_SERVER_FAIL): "
                    f"device failed to connect stream server {effective_stream_ip}:{self.cfg.stream_public_port}.",
                    flush=True,
                )
            if attempt < max_tries:
                time.sleep(max(0, self.cfg.push_retry_delay_sec))

        if ok == 0:
            raise IsupError(f"NET_ECMS_StartPushRealStream failed: {last_err}")

        print(f"stream push started, session_id={self.session_id.value}", flush=True)
        print(f"RTSP publish target: {self.cfg.rtsp_publish_url}", flush=True)

    def stop(self) -> None:
        self.voice_stop()

        if self.user_id.value >= 0 and self.session_id.value >= 0:
            self.cms.NET_ECMS_StopGetRealStream(self.user_id, self.session_id)

        if self.preview_handle.value >= 0:
            self.stream.NET_ESTREAM_StopPreview(self.preview_handle)

        if self.stream_listen_handle.value >= 0:
            self.stream.NET_ESTREAM_StopListenPreview(self.stream_listen_handle)

        self.publisher.stop()

        if self.user_id.value >= 0:
            self.cms.NET_ECMS_ForceLogout(self.user_id)

        if self.cms_listen_handle.value >= 0:
            self.cms.NET_ECMS_StopListen(self.cms_listen_handle)

        self.stream.NET_ESTREAM_Fini()
        self.cms.NET_ECMS_Fini()


def main() -> int:
    cfg = AppConfig()
    server = IsupServer(cfg)
    stop_event = threading.Event()

    def _execute_control_command(raw: str) -> str:
        raw = raw.strip()
        if not raw:
            return ""
        if raw == "ptz_help":
            return f"PTZ commands: {', '.join(sorted(PTZ_COMMANDS.keys()))}"
        if raw == "voice_help":
            return (
                "voice_start [server_ip] [server_port] [listen_ip] [listen_port] [channel], "
                "voice_send_file <path> [chunk_bytes] [delay_ms], "
                "voice_send_wav <path> [codec:auto|g711u|pcm] [chunk_bytes] [delay_ms], "
                "voice_status, voice_stop"
            )

        parts = raw.split()
        cmd = parts[0].lower()
        if cmd == "ptz":
            if len(parts) < 2:
                raise IsupError("usage: ptz <command> [duration_sec] [speed] [channel]")
            ptz_cmd = parts[1].lower()
            duration = (
                float(parts[2]) if len(parts) >= 3 else cfg.ptz_default_duration_sec
            )
            speed = int(parts[3]) if len(parts) >= 4 else cfg.ptz_default_speed
            channel = int(parts[4]) if len(parts) >= 5 else cfg.ptz_default_channel
            server.ptz_move(
                channel=channel, command=ptz_cmd, duration_sec=duration, speed=speed
            )
            return f"PTZ move sent: cmd={ptz_cmd}, duration={duration}, speed={speed}, channel={channel}"
        if cmd == "ptz_start":
            if len(parts) < 2:
                raise IsupError("usage: ptz_start <command> [speed] [channel]")
            ptz_cmd = parts[1].lower()
            speed = int(parts[2]) if len(parts) >= 3 else cfg.ptz_default_speed
            channel = int(parts[3]) if len(parts) >= 4 else cfg.ptz_default_channel
            server.ptz_control(channel=channel, command=ptz_cmd, action=0, speed=speed)
            return f"PTZ start sent: cmd={ptz_cmd}, speed={speed}, channel={channel}"
        if cmd == "ptz_stop":
            if len(parts) < 2:
                raise IsupError("usage: ptz_stop <command> [speed] [channel]")
            ptz_cmd = parts[1].lower()
            speed = int(parts[2]) if len(parts) >= 3 else cfg.ptz_default_speed
            channel = int(parts[3]) if len(parts) >= 4 else cfg.ptz_default_channel
            server.ptz_control(channel=channel, command=ptz_cmd, action=1, speed=speed)
            return f"PTZ stop sent: cmd={ptz_cmd}, speed={speed}, channel={channel}"
        if cmd == "voice_start":
            vs_ip = parts[1] if len(parts) >= 2 else cfg.voice_server_ip
            vs_port = int(parts[2]) if len(parts) >= 3 else cfg.voice_server_port
            vl_ip = parts[3] if len(parts) >= 4 else cfg.voice_listen_ip
            vl_port = int(parts[4]) if len(parts) >= 5 else cfg.voice_listen_port
            v_channel = int(parts[5]) if len(parts) >= 6 else cfg.voice_channel
            server.voice_start(
                voice_server_ip=vs_ip,
                voice_server_port=vs_port,
                voice_listen_ip=vl_ip,
                voice_listen_port=vl_port,
                voice_channel=v_channel,
            )
            return (
                f"voice started: server={vs_ip}:{vs_port}, "
                f"listen={vl_ip}:{vl_port}, channel={v_channel}"
            )
        if cmd == "voice_send_file":
            if len(parts) < 2:
                raise IsupError(
                    "usage: voice_send_file <path> [chunk_bytes] [delay_ms]"
                )
            path = parts[1]
            chunk_bytes = (
                int(parts[2]) if len(parts) >= 3 else cfg.voice_send_chunk_bytes
            )
            delay_ms = int(parts[3]) if len(parts) >= 4 else cfg.voice_send_delay_ms
            if server.voice_session_id.value < 0:
                server.voice_start()
            total = server.voice_send_file(
                path, chunk_bytes=chunk_bytes, delay_ms=delay_ms
            )
            return f"voice file sent: bytes={total}, chunk={chunk_bytes}, delay_ms={delay_ms}"
        if cmd == "voice_send_wav":
            if len(parts) < 2:
                raise IsupError(
                    "usage: voice_send_wav <path> [codec:auto|g711u|pcm] [chunk_bytes] [delay_ms]"
                )
            path = parts[1]
            codec = parts[2] if len(parts) >= 3 else "auto"
            chunk_bytes = int(parts[3]) if len(parts) >= 4 else 0
            delay_ms = int(parts[4]) if len(parts) >= 5 else 0
            if server.voice_session_id.value < 0:
                server.voice_start()
            total = server.voice_send_wav(
                path,
                codec=codec,
                chunk_bytes=chunk_bytes,
                delay_ms=delay_ms,
            )
            return (
                f"voice wav sent: bytes={total}, codec={codec}, "
                f"chunk={chunk_bytes if chunk_bytes > 0 else 'auto'}, "
                f"delay_ms={delay_ms if delay_ms > 0 else 'auto'}"
            )
        if cmd == "voice_status":
            return server.voice_status()
        if cmd == "voice_stop":
            server.voice_stop()
            return "voice stopped"
        if cmd in {"quit", "exit"}:
            stop_event.set()
            return "shutdown requested"
        raise IsupError("unknown command; use ptz_help or voice_help")

    def _ptz_console_loop() -> None:
        print(
            "control console enabled. use `ptz_help` or `voice_help`",
            flush=True,
        )
        while not stop_event.is_set():
            try:
                raw = input().strip()
            except EOFError:
                return
            except Exception:
                return
            try:
                out = _execute_control_command(raw)
                if out:
                    print(out, flush=True)
            except Exception as exc:
                print(f"PTZ command failed: {exc}", flush=True)

    def _socket_control_loop() -> None:
        try:
            srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            srv.bind((cfg.control_socket_host, cfg.control_socket_port))
            srv.listen(5)
            srv.settimeout(1.0)
        except OSError as exc:
            print(f"control socket disabled: {exc}", flush=True)
            return

        print(
            f"control socket listening on {cfg.control_socket_host}:{cfg.control_socket_port}",
            flush=True,
        )
        while not stop_event.is_set():
            try:
                conn, _addr = srv.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            with conn:
                try:
                    data = conn.recv(4096)
                    raw = data.decode("utf-8", errors="ignore").strip()
                    out = _execute_control_command(raw)
                    conn.sendall((out + "\n").encode("utf-8"))
                except Exception as exc:
                    conn.sendall((f"ERR: {exc}\n").encode("utf-8"))
        srv.close()

    def _handle_signal(_signum: int, _frame: object) -> None:
        stop_event.set()

    signal.signal(signal.SIGINT, _handle_signal)
    signal.signal(signal.SIGTERM, _handle_signal)

    try:
        server.start()
    except Exception as exc:
        print(f"startup failed: {exc}", file=sys.stderr)
        server.stop()
        return 1

    if cfg.enable_ptz_console:
        if os.name == "nt":
            print(
                "Windows console input may block; use control socket commands in another terminal.",
                flush=True,
            )
        else:
            t = threading.Thread(
                target=_ptz_console_loop, name="ptz-console", daemon=True
            )
            t.start()

    if cfg.enable_control_socket:
        print(
            f"starting control socket thread on {cfg.control_socket_host}:{cfg.control_socket_port}",
            flush=True,
        )
        t2 = threading.Thread(
            target=_socket_control_loop, name="ptz-socket", daemon=True
        )
        t2.start()

    try:
        while not stop_event.is_set():
            time.sleep(0.2)
    finally:
        server.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
