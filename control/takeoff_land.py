"""Take off, hover, then wait for landing and automatic disarm."""

import asyncio

from .common import flight_session, parser, positive, run


async def main():
    cli = parser(__doc__)
    cli.add_argument("--altitude", type=positive, default=5.0)
    cli.add_argument("--hover", type=positive, default=5.0)
    args = cli.parse_args()
    async with flight_session(args) as flight:
        await flight.arm()
        await flight.takeoff(args.altitude)
        print(f"Hovering for {args.hover:g}s", flush=True)
        await asyncio.sleep(args.hover)
        await flight.land()


if __name__ == "__main__":
    run(main)
