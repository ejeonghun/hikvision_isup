#!/usr/bin/env python3
from __future__ import annotations

import argparse
import socket
import sys

from config import CFG_CONTROL_SOCKET_HOST, CFG_CONTROL_SOCKET_PORT


CONTROL_HOST = CFG_CONTROL_SOCKET_HOST
CONTROL_PORT = CFG_CONTROL_SOCKET_PORT


class ControlClient:
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port

    def send(self, command: str, timeout_sec: float = 5.0) -> str:
        with socket.create_connection((self.host, self.port), timeout=timeout_sec) as s:
            s.sendall((command.strip() + "\n").encode("utf-8"))
            data = s.recv(4096)
            if not data:
                return ""
            return data.decode("utf-8", errors="ignore").strip()


def _run_and_print(client: ControlClient, command: str) -> int:
    try:
        out = client.send(command)
    except Exception as exc:
        print(f"failed to connect control socket {client.host}:{client.port}: {exc}")
        return 2
    print(out)
    return 1 if out.startswith("ERR:") else 0


def _interactive_shell(client: ControlClient) -> int:
    print("ISUP wrapper shell. type help, ptz_help, voice_help, or exit")
    while True:
        try:
            raw = input("isup> ").strip()
        except EOFError:
            return 0
        if not raw:
            continue
        if raw in {"exit", "quit"}:
            return 0
        if raw == "help":
            print("ptz <cmd> [duration] [speed] [channel]")
            print("ptz_start <cmd> [speed] [channel]")
            print("ptz_stop <cmd> [speed] [channel]")
            print(
                "voice_start [server_ip] [server_port] [listen_ip] [listen_port] [channel]"
            )
            print("voice_send_file <path> [chunk_bytes] [delay_ms]")
            print(
                "voice_send_wav <path> [codec:auto|g711u|pcm] [chunk_bytes] [delay_ms]"
            )
            print("voice_status")
            print("voice_stop")
            continue
        code = _run_and_print(client, raw)
        if code != 0:
            continue


def main() -> int:
    parser = argparse.ArgumentParser(description="ISUP PTZ/Voice wrapper")
    parser.add_argument("--host", default=CONTROL_HOST)
    parser.add_argument("--port", default=CONTROL_PORT, type=int)

    sub = parser.add_subparsers(dest="subcmd")

    sub.add_parser("shell")
    sub.add_parser("status")
    sub.add_parser("ptz-help")
    sub.add_parser("voice-help")

    p_ptz = sub.add_parser("ptz")
    p_ptz.add_argument("command")
    p_ptz.add_argument("duration", nargs="?", default="0.3")
    p_ptz.add_argument("speed", nargs="?", default="5")
    p_ptz.add_argument("channel", nargs="?", default="1")

    p_ptz_start = sub.add_parser("ptz-start")
    p_ptz_start.add_argument("command")
    p_ptz_start.add_argument("speed", nargs="?", default="5")
    p_ptz_start.add_argument("channel", nargs="?", default="1")

    p_ptz_stop = sub.add_parser("ptz-stop")
    p_ptz_stop.add_argument("command")
    p_ptz_stop.add_argument("speed", nargs="?", default="5")
    p_ptz_stop.add_argument("channel", nargs="?", default="1")

    p_voice_start = sub.add_parser("voice-start")
    p_voice_start.add_argument("server_ip", nargs="?", default=None)
    p_voice_start.add_argument("server_port", nargs="?", default=None)
    p_voice_start.add_argument("listen_ip", nargs="?", default=None)
    p_voice_start.add_argument("listen_port", nargs="?", default=None)
    p_voice_start.add_argument("channel", nargs="?", default=None)

    p_voice_send_file = sub.add_parser("voice-send-file")
    p_voice_send_file.add_argument("path")
    p_voice_send_file.add_argument("chunk_bytes", nargs="?", default="160")
    p_voice_send_file.add_argument("delay_ms", nargs="?", default="20")

    p_voice_send_wav = sub.add_parser("voice-send-wav")
    p_voice_send_wav.add_argument("path")
    p_voice_send_wav.add_argument("codec", nargs="?", default="auto")
    p_voice_send_wav.add_argument("chunk_bytes", nargs="?", default="0")
    p_voice_send_wav.add_argument("delay_ms", nargs="?", default="0")

    sub.add_parser("voice-status")
    sub.add_parser("voice-stop")

    p_voice_play_file = sub.add_parser("voice-play-file")
    p_voice_play_file.add_argument("path")
    p_voice_play_file.add_argument("chunk_bytes", nargs="?", default="160")
    p_voice_play_file.add_argument("delay_ms", nargs="?", default="20")

    p_voice_play_wav = sub.add_parser("voice-play-wav")
    p_voice_play_wav.add_argument("path")
    p_voice_play_wav.add_argument("codec", nargs="?", default="auto")
    p_voice_play_wav.add_argument("chunk_bytes", nargs="?", default="0")
    p_voice_play_wav.add_argument("delay_ms", nargs="?", default="0")

    args = parser.parse_args()
    client = ControlClient(args.host, args.port)

    if args.subcmd is None:
        return _interactive_shell(client)
    if args.subcmd == "shell":
        return _interactive_shell(client)
    if args.subcmd == "status":
        return _run_and_print(client, "voice_status")
    if args.subcmd == "ptz-help":
        return _run_and_print(client, "ptz_help")
    if args.subcmd == "voice-help":
        return _run_and_print(client, "voice_help")
    if args.subcmd == "ptz":
        return _run_and_print(
            client,
            f"ptz {args.command} {args.duration} {args.speed} {args.channel}",
        )
    if args.subcmd == "ptz-start":
        return _run_and_print(
            client, f"ptz_start {args.command} {args.speed} {args.channel}"
        )
    if args.subcmd == "ptz-stop":
        return _run_and_print(
            client, f"ptz_stop {args.command} {args.speed} {args.channel}"
        )
    if args.subcmd == "voice-start":
        parts = ["voice_start"]
        for item in [
            args.server_ip,
            args.server_port,
            args.listen_ip,
            args.listen_port,
            args.channel,
        ]:
            if item is not None:
                parts.append(str(item))
        return _run_and_print(client, " ".join(parts))
    if args.subcmd == "voice-send-file":
        return _run_and_print(
            client,
            f"voice_send_file {args.path} {args.chunk_bytes} {args.delay_ms}",
        )
    if args.subcmd == "voice-send-wav":
        return _run_and_print(
            client,
            f"voice_send_wav {args.path} {args.codec} {args.chunk_bytes} {args.delay_ms}",
        )
    if args.subcmd == "voice-status":
        return _run_and_print(client, "voice_status")
    if args.subcmd == "voice-stop":
        return _run_and_print(client, "voice_stop")
    if args.subcmd == "voice-play-file":
        if _run_and_print(client, "voice_start") != 0:
            return 1
        code = _run_and_print(
            client,
            f"voice_send_file {args.path} {args.chunk_bytes} {args.delay_ms}",
        )
        _run_and_print(client, "voice_stop")
        return code
    if args.subcmd == "voice-play-wav":
        if _run_and_print(client, "voice_start") != 0:
            return 1
        code = _run_and_print(
            client,
            f"voice_send_wav {args.path} {args.codec} {args.chunk_bytes} {args.delay_ms}",
        )
        _run_and_print(client, "voice_stop")
        return code

    print("unknown subcommand")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
