import cv2
import asyncio
from mavsdk import System
import time
import os
from mavsdk.offboard import OffboardError
from mavsdk.offboard import PositionNedYaw, VelocityNedYaw

# GPS verilerini almak için
async def get_gps_data(drone):
    async for gps in drone.telemetry.position():
        return gps.latitude_deg, gps.longitude_deg, gps.absolute_altitude_m

# Drone hareket edince videoyu başlat
async def wait_for_motion_start(drone, threshold=0.5):
    print("[INFO] Drone'un hareket etmesi bekleniyor...")
    async for velocity in drone.telemetry.velocity_ned():
        total_speed = abs(velocity.north_m_s) + abs(velocity.east_m_s) + abs(velocity.down_m_s)
        if total_speed >= threshold:
            print(f"[INFO] Drone hareket etti! Toplam hız: {total_speed:.2f} m/s")
            break
        await asyncio.sleep(0.1)

# GPS'li video kaydı fonksiyonu
async def process_video(drone, input_video_path, output_video_path, flight_duration):
    output_dir = os.path.dirname(output_video_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    cap = cv2.VideoCapture(input_video_path)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = 30
    print(f"[INFO] Using fixed FPS: {fps}")

    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(output_video_path, fourcc, fps, (width, height))

    start_time = time.time()
    last_gps_time = 0
    lat, lon, alt = 0.0, 0.0, 0.0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            print("[INFO] Video dosyasının sonuna ulaşıldı.")
            break

        elapsed = time.time() - start_time
        if elapsed > flight_duration:
            print("[INFO] Belirtilen uçuş süresi doldu.")
            break

        if elapsed - last_gps_time >= 0.5:
            lat, lon, alt = await get_gps_data(drone)
            last_gps_time = elapsed

        gps_text = f"Lat: {lat:.6f}, Lon: {lon:.6f}, Alt: {alt:.2f}m"
        cv2.putText(frame, gps_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                    1, (0, 255, 0), 2, cv2.LINE_AA)

        out.write(frame)
        cv2.imshow("Video with GPS", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("[INFO] 'q' ile çıkış yapıldı.")
            break

    cap.release()
    out.release()
    cv2.destroyAllWindows()
    print("[INFO] Video kaydı tamamlandı.")

# Ana kontrol fonksiyonu
async def run():
    drone = System(port=50052)
    print("Connecting to drone...")
    await drone.connect(system_address="udp://:14542")

    print("Waiting for drone to connect...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print("Drone connected!")
            break

    print("QGroundControl üzerinden kalkış yapabilirsiniz.")
    print("Drone hareket ettiğinde video otomatik başlatılacak...")

    # Hareketi bekle
    await wait_for_motion_start(drone)

    # Video kaydı
    flight_duration = 30
    output_video_path = "/home/arda/Masaüstü/SP-494/Video_Output/output_video_with_gps_2.avi"
    input_video_path = "/home/arda/Masaüstü/SP-494/Video_Output/Models_video_02.mp4"

    await process_video(drone, input_video_path, output_video_path, flight_duration)

    print("[INFO] Görev tamamlandı. İnişi manuel olarak gerçekleştirebilirsiniz.")

# Başlat
asyncio.run(run())
