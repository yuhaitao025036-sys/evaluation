#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_DIR="$ROOT_DIR/.pids"

if [ ! -d "$PID_DIR" ]; then
    echo "没有找到 PID 目录: ${PID_DIR}"
    exit 0
fi

stopped=0
for pid_file in "$PID_DIR"/*.pid; do
    [ -e "$pid_file" ] || continue

    name="$(basename "$pid_file" .pid)"
    pid="$(cat "$pid_file")"

    if kill -0 "$pid" >/dev/null 2>&1; then
        echo "停止 ${name}，PID: ${pid}"
        kill "$pid"
        stopped=$((stopped + 1))
    else
        echo "${name} 未运行，清理 PID 文件"
    fi

    rm -f "$pid_file"
done

if [ "$stopped" -eq 0 ]; then
    echo "没有正在运行的服务"
else
    echo "已发送停止信号给 ${stopped} 个进程"
fi
