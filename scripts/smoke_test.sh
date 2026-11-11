#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
scene=default
full=0
launch=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --scene) scene="${2:?--scene requires a value}"; shift 2 ;;
        --full) full=1; shift ;;
        --gui|--software-rendering) launch+=("$1"); shift ;;
        --help|-h) echo 'Usage: smoke_test.sh [--scene default|obstacle_course] [--full] [--gui] [--software-rendering]'; exit 0 ;;
        *) echo "Unknown option: $1" >&2; exit 2 ;;
    esac
done
./scripts/start.sh --scene "$scene" --cleanup-on-failure "${launch[@]}"
# The trap is installed only after we successfully create our simulation.
trap './scripts/stop.sh' EXIT
mkdir -p logs
report="logs/smoke-${scene}-$(date +%Y%m%d-%H%M%S).log"
{
    uv run --locked python -m control.telemetry --duration 5
    uv run --locked python -m control.takeoff_land --altitude 3 --hover 2
    if [[ "$full" == 1 ]]; then
        uv run --locked python -m control.offboard_demo
        uv run --locked python -m control.mission_demo
    fi
    echo "PASS: scene=$scene full=$full telemetry and completed flight(s)"
} 2>&1 | tee "$report"
echo "Report: $ROOT/$report"
