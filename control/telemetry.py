"""Print position telemetry for a bounded duration without arming."""

import asyncio
import time

from .common import connect, parser, positive, run, wait_for


async def main():
    cli = parser(__doc__)
    cli.add_argument("--duration", type=positive, default=20.0)
    args = cli.parse_args()
    drone = await connect(args)
    deadline = time.monotonic() + args.duration
    while time.monotonic() < deadline:
        position = await wait_for(drone.telemetry.position(), lambda _: True,
                                  min(args.timeout, max(0.1, deadline - time.monotonic())),
                                  "next position telemetry sample")
        print(f"lat={position.latitude_deg:.7f} lon={position.longitude_deg:.7f} "
              f"relative_alt={position.relative_altitude_m:.2f}m "
              f"absolute_alt={position.absolute_altitude_m:.2f}m", flush=True)
        await asyncio.sleep(min(1.0, max(0.0, deadline - time.monotonic())))


if __name__ == "__main__":
    run(main)
