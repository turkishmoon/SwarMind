#!/usr/bin/env python3

import asyncio
import configparser
import multiprocessing.shared_memory as shm
import json
from mavsdk import System
from mavsdk.offboard import VelocityNedYaw
import os
import math
from datetime import datetime

GREEN, YELLOW, RED, BLUE, CYAN, ENDC = "\033[92m", "\033[93m", "\033[91m", "\033[94m", "\033[96m", "\033[0m"
SHM_NAME = "telemetry_shared"
SHM_SIZE = 4096

async def telemetry_collector(drone, drone_id, telemetry_shm):
    """
    It follows all telemetry streams in parallel and writes them to shared memory.
    """
    last = {}
    lock = asyncio.Lock()

    async def update_position():
        async for pos in drone.telemetry.position():
            async with lock:
                last['latitude'] = pos.latitude_deg
                last['longitude'] = pos.longitude_deg
                last['absolute_altitude'] = pos.absolute_altitude_m

    async def update_velocity():
        async for vel in drone.telemetry.position_velocity_ned():
            async with lock:
                last['speed'] = math.hypot(vel.velocity.north_m_s, vel.velocity.east_m_s)

    async def update_attitude():
        async for att in drone.telemetry.attitude_euler():
            async with lock:
                last['roll'] = att.roll_deg
                last['pitch'] = att.pitch_deg
                last['yaw'] = att.yaw_deg

    async def update_flight_mode():
        async for fm in drone.telemetry.flight_mode():
            async with lock:
                last['flight_mode'] = str(fm)

    async def update_battery():
        async for bat in drone.telemetry.battery():
            async with lock:
                last['battery_percent'] = bat.remaining_percent * 100

    async def update_gps():
        async for gps in drone.telemetry.raw_gps():
            async with lock:
                last['satellites_visible'] = getattr(gps, "satellites_visible", "N/A")

    # Secure writer to SHM
    async def publisher():
        while True:
            async with lock:
                try:
                    raw = bytes(telemetry_shm.buf[:]).split(b'\x00', 1)[0]
                    try:
                        current = json.loads(raw.decode("utf-8")) if raw else {}
                    except Exception:
                        current = {}
                except Exception:
                    current = {}

                current[drone_id] = last.copy()
                encoded = json.dumps(current).encode("utf-8")
                if len(encoded) < SHM_SIZE:
                    telemetry_shm.buf[:len(encoded)] = encoded
                    telemetry_shm.buf[len(encoded):] = b'\x00' * (SHM_SIZE - len(encoded))
                else:
                    print(f"{RED}[SHM] Data is too big!{ENDC}")
            await asyncio.sleep(0.01)

    await asyncio.gather(
        update_position(),
        update_velocity(),
        update_attitude(),
        update_flight_mode(),
        update_battery(),
        update_gps(),
        publisher()
    )

async def flocking_controller(drone_id, drone, telemetry_shm):
    ESCAPE_DISTANCE = 10
    TARGET_DISTANCE = 15   # Fixed distance target (cohesion)
    COHESION_SPEED = 1.2   # Cohesion/constant distance approach speed
    ESCAPE_SPEED = 3.5     # Evasion speed 
    NORMAL_SPEED = 0.8     # Free flight speed

    while True:
        try:
            # Read from SHM
            for _ in range(3):
                try:
                    raw = bytes(telemetry_shm.buf[:]).split(b'\x00', 1)[0]
                    all_data = json.loads(raw.decode("utf-8")) if raw else {}
                    break
                except Exception as e:
                    all_data = {}
                    await asyncio.sleep(0.01)
            else:
                print(f"{RED}[Flocking SHM Error]: JSON cannot be read!{ENDC}")
                await asyncio.sleep(0.02)
                continue

            my = all_data.get(drone_id)
            if not my:
                await asyncio.sleep(0.02)
                continue

            my_lat, my_lon, my_yaw = my.get("latitude"), my.get("longitude"), my.get("yaw")
            others = [d for oid, d in all_data.items() if oid != drone_id and "latitude" in d]
            if not others:
                await drone.offboard.set_velocity_ned(VelocityNedYaw(NORMAL_SPEED, 0.0, 0.0, my_yaw or 0))
                await asyncio.sleep(0.05)
                continue

            # The nearset drone
            nearest = min(
                others,
                key=lambda o: calculate_distance(my_lat, my_lon, o["latitude"], o["longitude"])
            )
            dist = calculate_distance(my_lat, my_lon, nearest["latitude"], nearest["longitude"])
            yaw_to_other = math.degrees(math.atan2(nearest["longitude"] - my_lon, nearest["latitude"] - my_lat))

            if dist < ESCAPE_DISTANCE:
                print(f"{RED}🚨 Avoidance: {dist:.1f}m{ENDC}")
                # Avoidance vector
                angle = math.atan2(my_lon - nearest["longitude"], my_lat - nearest["latitude"])
                vx = ESCAPE_SPEED * math.cos(angle)
                vy = ESCAPE_SPEED * math.sin(angle)
                await drone.offboard.set_velocity_ned(VelocityNedYaw(vx, vy, 0.0, my_yaw or 0))
                await asyncio.sleep(0.2)

            elif ESCAPE_DISTANCE <= dist < (TARGET_DISTANCE - 1):
                # Move away 10-14 m (separation - retreat to a fixed distance)
                print(f"{CYAN}⬅️ Separation (Get Away): {dist:.1f}m{ENDC}")
                angle = math.atan2(my_lon - nearest["longitude"], my_lat - nearest["latitude"])
                vx = COHESION_SPEED * math.cos(angle)
                vy = COHESION_SPEED * math.sin(angle)
                await drone.offboard.set_velocity_ned(VelocityNedYaw(vx, vy, 0.0, yaw_to_other))
                await asyncio.sleep(0.15)

            elif (TARGET_DISTANCE - 1) <= dist <= (TARGET_DISTANCE + 1):
                # Keep it steady 14-16 m 
                print(f"{GREEN}✅ Distance is Fixed: {dist:.1f}m{ENDC}")
                await drone.offboard.set_velocity_ned(VelocityNedYaw(0.0, 0.0, 0.0, my_yaw or 0))
                await asyncio.sleep(0.15)

            elif dist > (TARGET_DISTANCE + 1):
                # Approach when reached 16 m above (cohesion)
                print(f"{BLUE}➡️ Cohesion (Get Closer): {dist:.1f}m{ENDC}")
                angle = math.atan2(nearest["longitude"] - my_lon, nearest["latitude"] - my_lat)
                vx = COHESION_SPEED * math.cos(angle)
                vy = COHESION_SPEED * math.sin(angle)
                await drone.offboard.set_velocity_ned(VelocityNedYaw(vx, vy, 0.0, yaw_to_other))
                await asyncio.sleep(0.15)

            else:
                print(f"{YELLOW}🟢 Free Flight: {dist:.1f}m{ENDC}")
                await drone.offboard.set_velocity_ned(VelocityNedYaw(NORMAL_SPEED, 0.0, 0.0, my_yaw or 0))
                await asyncio.sleep(0.25)

        except Exception as e:
            print(f"{RED}[Flocking Controller Error]: {e}{ENDC}")
            await asyncio.sleep(0.05)

def calculate_distance(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return 1e9
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

async def run():
    config = configparser.ConfigParser()
    config.read(os.path.expanduser("~/Masaüstü/SP-494/drone2_config.ini"))
    drone_id = config.get("swarm", "ID").strip()
    connection_string = config.get("swarm", "Connection").strip()

    print(f"{CYAN}[Drone{drone_id}] Config is read: {connection_string}{ENDC}")
    drone = System(port=50052)
    await drone.connect(system_address=connection_string)

    # Open SHM
    created_new_shm = False
    try:
        telemetry_shm = shm.SharedMemory(name=SHM_NAME, create=True, size=SHM_SIZE)
        created_new_shm = True
        telemetry_shm.buf[:2] = b'{}'
        telemetry_shm.buf[2:] = b'\x00' * (SHM_SIZE - 2)
        print(f"{GREEN}[SHM] Newly created and written empty JSON.{ENDC}")
    except FileExistsError:
        telemetry_shm = shm.SharedMemory(name=SHM_NAME)
        print(f"{YELLOW}[SHM] Connected to existing space.{ENDC}")

    try:
        print(f"{BLUE}[Drone{drone_id}] Arming is being started...{ENDC}")
        await asyncio.sleep(4)
        await drone.action.arm()
        await asyncio.sleep(4)  # Short wait after arming

        print(f"{BLUE}[Drone{drone_id}] Takeoff is being started...{ENDC}")
        await drone.action.takeoff()
        await asyncio.sleep(25)  # Let the drone take off after "Takeoff" condition

        print(f"{BLUE}[Drone{drone_id}] Offboard is being started...{ENDC}")
        await drone.offboard.set_velocity_ned(VelocityNedYaw(0.0, 0.0, 0.0, 0.0))
        await drone.offboard.start()

        await asyncio.gather(
            telemetry_collector(drone, drone_id, telemetry_shm),
            flocking_controller(drone_id, drone, telemetry_shm)
        )
    finally:
        print(f"{CYAN}[SHM] Memory is cleaning...{ENDC}")
        telemetry_shm.close()
        if created_new_shm:
            try:
                telemetry_shm.unlink()
            except FileNotFoundError:
                pass
        print(f"{GREEN}[SHM] Closed and deleted.{ENDC}")

if __name__ == "__main__":
    asyncio.run(run())

