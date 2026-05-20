#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$ROOT_DIR/logs"
PID_DIR="$ROOT_DIR/.pids"
WORKER_COUNT="${WORKER_COUNT:-10}"

mkdir -p "$LOG_DIR" "$PID_DIR"

start_service() {
    local name="$1"
    local workdir="$2"
    shift 2

    local pid_file="$PID_DIR/${name}.pid"
    local log_file="$LOG_DIR/${name}.log"

    if [ -f "$pid_file" ]; then
        local old_pid
        old_pid="$(cat "$pid_file")"
        if kill -0 "$old_pid" >/dev/null 2>&1; then
            echo "${name} 已在运行，PID: ${old_pid}，日志: ${log_file}"
            return
        fi
        rm -f "$pid_file"
    fi

    echo "启动 ${name}，日志: ${log_file}"
    (
        cd "$workdir"
        exec "$@"
    ) >>"$log_file" 2>&1 &

    local pid=$!
    echo "$pid" >"$pid_file"
    echo "${name} PID: ${pid}"
}

start_worker() {
    local index="$1"
    local name="worker-${index}"
    local pid_file="$PID_DIR/${name}.pid"
    local log_file="$LOG_DIR/${name}.log"

    if [ -f "$pid_file" ]; then
        local old_pid
        old_pid="$(cat "$pid_file")"
        if kill -0 "$old_pid" >/dev/null 2>&1; then
            echo "${name} 已在运行，PID: ${old_pid}，日志: ${log_file}"
            return
        fi
        rm -f "$pid_file"
    fi

    echo "启动 ${name}，日志: ${log_file}"
    (
        cd "$ROOT_DIR/backend"
        export WORKER_ID="worker-${index}"
        exec ./start_worker.sh
    ) >>"$log_file" 2>&1 &

    local pid=$!
    echo "$pid" >"$pid_file"
    echo "${name} PID: ${pid}"
}

echo "======================================"
echo "启动 DUCC Evaluation 全部服务"
echo "======================================"
echo "项目目录: ${ROOT_DIR}"
echo "日志目录: ${LOG_DIR}"
echo "Worker 数量: ${WORKER_COUNT}"
echo ""

start_service "backend" "$ROOT_DIR/backend" ./start_backend.sh
start_service "frontend" "$ROOT_DIR/frontend" ./start_dev.sh

for index in $(seq 1 "$WORKER_COUNT"); do
    start_worker "$index"
done

echo ""
echo "======================================"
echo "启动完成"
echo "======================================"
echo "Backend:  http://localhost:8080"
echo "Frontend: http://localhost:5173"
echo ""
echo "查看日志:"
echo "  tail -f ${LOG_DIR}/backend.log"
echo "  tail -f ${LOG_DIR}/frontend.log"
echo "  tail -f ${LOG_DIR}/worker-1.log"
echo "  tail -f ${LOG_DIR}/worker-*.log"
echo ""
echo "停止服务:"
echo "  ./stop_all.sh"
