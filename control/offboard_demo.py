"""Fly a small NED velocity square in the clear launch area, then land."""

import asyncio

from mavsdk_grpc.offboard import OffboardError, VelocityNedYaw

from .common import bounded, flight_session, parser, run


async def main():
    args = parser(__doc__).parse_args()
    async with flight_session(args) as flight:
        drone = flight.drone
        await flight.arm()
        await flight.takeoff(5.0)
        # MAVSDK resends the latest setpoint at 20 Hz. Seed it before start().
        await bounded(drone.offboard.set_velocity_ned(VelocityNedYaw(0, 0, 0, 0)),
                      10, "seeding Offboard velocity setpoint")
        flight.offboard_active = True  # Also clean up if start RPC times out.
        try:
            await bounded(drone.offboard.start(), 15, "starting Offboard mode")
        except OffboardError as exc:
            raise RuntimeError(f"PX4 rejected Offboard mode: {exc}") from exc

        async def square():
            # NED: north/east/down in m/s, yaw in degrees. 3 m per side.
            for north, east in ((1, 0), (0, 1), (-1, 0), (0, -1)):
                await bounded(drone.offboard.set_velocity_ned(
                    VelocityNedYaw(north, east, 0, 0)), 10, "updating Offboard setpoint")
                await asyncio.sleep(3)
            await bounded(drone.offboard.set_velocity_ned(VelocityNedYaw(0, 0, 0, 0)),
                          10, "commanding hover")
            await asyncio.sleep(2)

        await bounded(square(), args.flight_timeout, "completing Offboard square")
        await bounded(drone.offboard.stop(), 10, "stopping Offboard mode")
        flight.offboard_active = False
        await flight.land()


if __name__ == "__main__":
    run(main)
