#!/bin/bash


# Environment variable for GUI compatibility
export LIBGL_ALWAYS_SOFTWARE=1

cd ~/PX4-Autopilot || { echo "❌ PX4-Autopilot directory cannot be found!"; exit 1; }

#Start Qground 
gnome-terminal -- bash -c "
cd ~/PX4-Autopilot || { echo 'PX4-Autopilot directory cannot be found '; exit 1; }
export LIBGL_ALWAYS_SOFTWARE=1
./QGroundControl.AppImage
exec bash
"

sleep 10

gnome-terminal --title="Drone 1 - PX4 Simulation" -- bash -c "
PX4_SYS_AUTOSTART=4001 \
PX4_SIM_MODEL=gz_x500_mono_cam \
PX4_GZ_MODEL_POSE='0,0,0,0,0,0' \
HEADLESS=1 \
./build/px4_sitl_default/bin/px4 -i 1
exec bash
"
sleep 10
gnome-terminal --title="Drone 2 - PX4 Simulation" -- bash -c "
PX4_SYS_AUTOSTART=4001 \
PX4_SIM_MODEL=gz_x500_mono_cam \
PX4_GZ_MODEL_POSE='0,100,0,0,0,0' \
HEADLESS=1 \
./build/px4_sitl_default/bin/px4 -i 2
exec bash
"

sleep 30

gnome-terminal --title="Drone 1" -- bash -c "
python3 /home/arda/Masaüstü/SP-494/drone1.py
exec bash
"
gnome-terminal --title="Drone 2" -- bash -c "
python3 /home/arda/Masaüstü/SP-494/drone2.py
exec bash
"



