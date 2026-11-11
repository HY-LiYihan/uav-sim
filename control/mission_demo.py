"""Upload and execute a real MAVSDK Mission, then land near the start."""

import math

from mavsdk_grpc.mission import MissionItem, MissionPlan

from .common import bounded, flight_session, parser, run, wait_for


def mission_item(latitude, longitude, altitude):
    # Constructor matches the published mavsdk-grpc 4.0.5 MissionItem API.
    return MissionItem(
        latitude_deg=latitude,
        longitude_deg=longitude,
        relative_altitude_m=altitude,
        speed_m_s=2.0,
        is_fly_through=False,
        gimbal_pitch_deg=float("nan"),
        gimbal_yaw_deg=float("nan"),
        camera_action=MissionItem.CameraAction.NONE,
        loiter_time_s=1.0,
        camera_photo_interval_s=float("nan"),
        acceptance_radius_m=1.0,
        yaw_deg=float("nan"),
        camera_photo_distance_m=float("nan"),
        vehicle_action=MissionItem.VehicleAction.NONE,
    )


async def main():
    args = parser(__doc__).parse_args()
    async with flight_session(args) as flight:
        drone = flight.drone
        # Anchor to the actual start position; do not hard-code world GPS coordinates.
        origin = await wait_for(drone.telemetry.position(), lambda _: True,
                                args.timeout, "mission origin position")
        earth_radius = 6378137.0
        latitude_scale = 180.0 / (math.pi * earth_radius)
        cosine = math.cos(math.radians(origin.latitude_deg))
        if abs(cosine) < 0.01:
            raise RuntimeError("This short-distance mission example does not support polar origins")
        longitude_scale = latitude_scale / cosine
        points = [(0, 0), (8, 0), (8, 8), (0, 8), (0, 0)]
        items = [mission_item(origin.latitude_deg + north * latitude_scale,
                              origin.longitude_deg + east * longitude_scale, 5.0)
                 for north, east in points]
        await bounded(drone.mission.set_return_to_launch_after_mission(False), 15,
                      "disabling automatic RTL for explicit landing")
        await bounded(drone.mission.upload_mission(MissionPlan(items)), 30,
                      "uploading mission")
        await flight.arm()
        await flight.takeoff(5.0)
        await bounded(drone.mission.start_mission(), 15, "starting mission")

        def report(progress):
            print(f"Mission progress: {progress.current}/{progress.total}", flush=True)
            return progress.total > 0 and progress.current == progress.total

        await wait_for(drone.mission.mission_progress(), report,
                       args.flight_timeout, "finishing uploaded mission")
        await flight.land()


if __name__ == "__main__":
    run(main)
