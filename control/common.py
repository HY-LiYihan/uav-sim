"""Shared bounded waits and landing cleanup for the simulation examples."""

import argparse
import asyncio
import math
import sys
from contextlib import asynccontextmanager

from mavsdk_grpc import System


DEFAULT_ADDRESS = "udpin://0.0.0.0:14540"


def positive(value):
    result = float(value)
    if not math.isfinite(result) or result <= 0:
        raise argparse.ArgumentTypeError("must be a finite positive number")
    return result


def parser(description):
    result = argparse.ArgumentParser(description=description)
    result.add_argument("--address", default=DEFAULT_ADDRESS)
    result.add_argument("--timeout", type=positive, default=60.0,
                        help="connection and health timeout in seconds (default: 60)")
    result.add_argument("--flight-timeout", type=positive, default=180.0,
                        help="mission completion timeout in seconds (default: 180)")
    result.add_argument("--landing-timeout", type=positive, default=90.0)
    return result


async def bounded(awaitable, timeout, description):
    try:
        return await asyncio.wait_for(awaitable, timeout)
    except asyncio.TimeoutError as exc:
        raise RuntimeError(f"Timed out after {timeout:g}s: {description}") from exc


async def wait_for(stream, predicate, timeout, description):
    async def consume():
        try:
            async for value in stream:
                if predicate(value):
                    return value
            raise RuntimeError(f"Telemetry stream ended: {description}")
        finally:
            await stream.aclose()
    return await bounded(consume(), timeout, description)


async def connect(args):
    drone = System()
    print(f"Connecting to {args.address}", flush=True)
    await bounded(drone.connect(system_address=args.address), args.timeout,
                  "starting MAVSDK and opening MAVLink endpoint")
    await wait_for(drone.core.connection_state(), lambda state: state.is_connected,
                   args.timeout, f"PX4 heartbeat on {args.address}")
    print("Waiting for global and home position health", flush=True)
    await wait_for(drone.telemetry.health(),
                   lambda health: health.is_global_position_ok and health.is_home_position_ok,
                   args.timeout, "global/home position health (check GPS, estimator and simulation)")
    return drone


class Flight:
    def __init__(self, drone, args):
        self.drone = drone
        self.args = args
        self.may_be_armed = False
        self.offboard_active = False

    async def arm(self):
        # An RPC timeout does not prove PX4 rejected the command.
        self.may_be_armed = True
        await bounded(self.drone.action.arm(), 15, "arming")

    async def takeoff(self, altitude=5.0):
        await bounded(self.drone.action.set_takeoff_altitude(altitude), 15,
                      "setting takeoff altitude")
        await bounded(self.drone.action.takeoff(), 15, "requesting takeoff")
        await wait_for(self.drone.telemetry.in_air(), bool, self.args.timeout,
                       "vehicle becoming airborne")
        await wait_for(self.drone.telemetry.position(),
                       lambda position: position.relative_altitude_m >= altitude * 0.9,
                       self.args.timeout, f"climbing to {altitude:g}m")

    async def land(self):
        print("Requesting landing", flush=True)
        await bounded(self.drone.action.land(), 15, "requesting LAND mode")
        await wait_for(self.drone.telemetry.in_air(), lambda airborne: not airborne,
                       self.args.landing_timeout, "touchdown")
        await wait_for(self.drone.telemetry.armed(), lambda armed: not armed,
                       self.args.landing_timeout, "automatic disarm after touchdown")
        self.may_be_armed = False
        self.offboard_active = False
        print("Landed and disarmed", flush=True)


@asynccontextmanager
async def flight_session(args):
    flight = Flight(await connect(args), args)
    try:
        yield flight
    finally:
        if flight.may_be_armed:
            if flight.offboard_active:
                try:
                    await bounded(flight.drone.offboard.stop(), 10, "stopping Offboard")
                except Exception as exc:
                    print(f"Offboard stop failed; requesting LAND: {exc}", file=sys.stderr)
            try:
                await flight.land()
            except Exception as exc:
                print(f"LANDING CLEANUP FAILED: {exc}. Check QGroundControl immediately.",
                      file=sys.stderr)
                # Do not report success if automatic cleanup could not verify landing.
                raise


def run(main):
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Interrupted; flight cleanup was attempted if armed.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
