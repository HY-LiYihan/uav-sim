#!/usr/bin/env python3
"""Project-owned Docker lifecycle; no shell evaluation of scene configuration."""
import argparse
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
import uuid
import xml.etree.ElementTree as ET

import yaml

ROOT = Path(__file__).resolve().parents[1]
NAME = 'uav-sim-' + hashlib.sha256(str(ROOT).encode()).hexdigest()[:10]
IMAGE = 'uav-sim:jammy-harmonic'
LABEL = 'org.uav-sim.workspace'
LAUNCH_LABEL = 'org.uav-sim.launch'


def positive(value):
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError('must be finite and positive')
    return value


def run(*args, **kwargs):
    return subprocess.run(args, check=True, text=True, **kwargs)


def existing():
    result = subprocess.run(['docker', 'container', 'inspect', NAME], capture_output=True, text=True)
    if result.returncode:
        return None
    data = json.loads(result.stdout)[0]
    if data['Config'].get('Labels', {}).get(LABEL) != str(ROOT):
        raise RuntimeError(f'Container name collision: {NAME}')
    return data


def load_scene(name):
    if not re.fullmatch(r'[a-zA-Z0-9_-]+', name):
        raise ValueError('Scene name may contain only letters, numbers, _ and -')
    config = yaml.safe_load((ROOT / 'scenes' / f'{name}.yaml').read_text())
    world = (ROOT / config['world_file']).resolve()
    if not world.is_relative_to(ROOT) or not world.is_file():
        raise ValueError(f'World file missing or outside project: {world}')
    sdf_world = ET.parse(world).getroot().find('world')
    if sdf_world is None or sdf_world.get('name') != config['world_name']:
        raise ValueError('world_name must match the SDF <world name>')
    vehicle = config['vehicle']
    if vehicle['model'] != 'x500':
        raise ValueError('Initial supported vehicle is x500')
    values = list(vehicle['spawn_xyz']) + [0, 0, vehicle.get('spawn_yaw', 0)]
    if len(values) != 6 or any(not math.isfinite(float(v)) for v in values):
        raise ValueError('Invalid spawn pose')
    if int(config['mavlink']['sdk_port']) != 14540:
        raise ValueError('Single-vehicle launcher currently uses SDK UDP port 14540')
    if config.get('ros', {}).get('enabled'):
        raise ValueError('ROS bridge is reserved; current launcher uses MAVSDK directly')
    return config, world, ','.join(str(float(v)) for v in values)


def assert_ports_free():
    for port in (14540, 14580, 18570):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            try:
                sock.bind(('0.0.0.0', port))
            except OSError as exc:
                raise RuntimeError(f'UDP {port} is occupied; stop the competing SITL/MAVSDK process') from exc


def start(args):
    previous = existing()
    if previous:
        if previous['State']['Running']:
            raise RuntimeError(f'Simulation already running ({NAME}); use stop.sh first')
        run('docker', 'rm', NAME)
    config, world, pose = load_scene(args.scene)
    binary = ROOT / 'third_party/PX4-Autopilot/build/px4_sitl_default/bin/px4'
    if not binary.is_file():
        raise RuntimeError('PX4 binary missing; run ./scripts/build.sh first')
    assert_ports_free()
    stamp = dt.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    log_dir = ROOT / 'logs' / stamp
    log_dir.mkdir(parents=True)
    (ROOT / '.cache/container-home').mkdir(parents=True, exist_ok=True)
    env = {
        'HOME': '/workspace/.cache/container-home',
        'GZ_PARTITION': NAME,
        'SIM_WORLD_FILE': '/workspace/' + str(world.relative_to(ROOT)),
        'PX4_GZ_WORLD': config['world_name'],
        'PX4_GZ_MODEL_POSE': pose,
        'SIM_LOG_DIR': '/workspace/logs/' + stamp,
        'SIM_GUI': '1' if args.gui else '0',
        'QT_X11_NO_MITSHM': '1',
    }
    args.launch_id = uuid.uuid4().hex
    command = ['docker', 'run', '-d', '--init', '--name', NAME,
               '--label', f'{LABEL}={ROOT}', '--label', f'{LAUNCH_LABEL}={args.launch_id}',
               '--network', 'host', '--shm-size', '512m',
               '--user', f'{os.getuid()}:{os.getgid()}',
               '--security-opt', 'no-new-privileges', '--cap-drop', 'ALL',
               '-v', f'{ROOT}:/workspace', '-w', '/workspace']
    if args.gui:
        display = os.environ.get('DISPLAY')
        auth = Path(os.environ.get('XAUTHORITY', str(Path.home() / '.Xauthority')))
        if not display or not auth.is_file():
            raise RuntimeError('GUI needs DISPLAY and readable XAUTHORITY; use the desktop terminal or omit --gui')
        command += ['-v', '/tmp/.X11-unix:/tmp/.X11-unix:ro',
                    '-v', f'{auth}:/tmp/uav-sim-xauthority:ro']
        env.update(DISPLAY=display, XAUTHORITY='/tmp/uav-sim-xauthority')
    if args.software_rendering:
        env['LIBGL_ALWAYS_SOFTWARE'] = '1'
    elif args.gui:
        runtimes = run('docker', 'info', '--format', '{{json .Runtimes}}', capture_output=True).stdout
        if '"nvidia"' in runtimes:
            command += ['--gpus', 'all']
            env['NVIDIA_DRIVER_CAPABILITIES'] = 'graphics,display,utility,compute'
        else:
            raise RuntimeError('NVIDIA Docker runtime missing. Run scripts/setup_gpu.sh or use --software-rendering')
    for key, value in env.items():
        command += ['-e', f'{key}={value}']
    command += [IMAGE, 'bash', 'scripts/container_start.sh']
    cid = run(*command, capture_output=True).stdout.strip()
    metadata = {'container': NAME, 'container_id': cid, 'scene': args.scene,
                'log_dir': str(log_dir), 'gui': args.gui, 'world': config['world_name']}
    (ROOT / '.cache/session.json').write_text(json.dumps(metadata, indent=2) + '\n')
    deadline = time.monotonic() + args.timeout
    while time.monotonic() < deadline:
        state = existing()
        if not state or not state['State']['Running']:
            run('docker', 'logs', '--tail', '60', NAME)
            raise RuntimeError('Simulation container exited during startup; see logs')
        log = log_dir / 'px4.log'
        if log.exists() and 'Startup script returned successfully' in log.read_text(errors='replace'):
            if args.gui:
                probe = subprocess.run(['docker', 'exec', NAME, 'gz', 'service', '-i',
                                        '--service', '/gui/move_to'],
                                       capture_output=True, text=True, timeout=5)
                if 'Service providers' not in probe.stdout:
                    time.sleep(1)
                    continue
            print(f'Simulation ready: {args.scene} ({NAME})\nLogs: {log_dir}')
            print('Control: uv run python -m control.takeoff_land')
            return
        time.sleep(1)
    disposition = 'this launch will be removed' if args.cleanup_on_failure else 'container retained for diagnostics'
    raise RuntimeError(f'Startup timed out; {disposition}; logs in {log_dir}')


def stop(args):
    state = existing()
    if not state:
        print('No project simulation container exists')
        return
    if state['State']['Running']:
        run('docker', 'stop', '--time', '15', NAME)
    # Verify the workspace label again before removing this specific container.
    if existing():
        run('docker', 'rm', NAME)
    print('Project simulation stopped; logs preserved')


def status(args):
    state = existing()
    if not state:
        print('Simulation is stopped')
        return
    print(f'{NAME}: {state["State"]["Status"]}')
    run('docker', 'logs', '--tail', '35', NAME)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    launch = commands.add_parser('start')
    launch.add_argument('--scene', default='default')
    launch.add_argument('--gui', action='store_true')
    launch.add_argument('--software-rendering', action='store_true')
    launch.add_argument('--timeout', type=positive, default=90)
    launch.add_argument('--cleanup-on-failure', action='store_true',
                        help='remove only this launch on startup failure (used by smoke_test.sh)')
    commands.add_parser('stop')
    commands.add_parser('status')
    args = parser.parse_args()
    try:
        {'start': start, 'stop': stop, 'status': status}[args.command](args)
    except (RuntimeError, ValueError, KeyError, OSError, subprocess.SubprocessError, KeyboardInterrupt) as exc:
        if getattr(args, 'cleanup_on_failure', False) and getattr(args, 'launch_id', None):
            candidate = existing()
            if candidate and candidate['Config']['Labels'].get(LAUNCH_LABEL) == args.launch_id:
                stop(args)
        print(f'ERROR: {exc or "Interrupted"}', file=sys.stderr)
        raise SystemExit(130 if isinstance(exc, KeyboardInterrupt) else 1)


if __name__ == '__main__':
    main()
