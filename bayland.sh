#!/bin/bash

# Environment variable for GUI compatibility
export LIBGL_ALWAYS_SOFTWARE=1

cd ~/PX4-Autopilot || { echo "PX4-Autopilot directory could not be found!"; exit 1; }

gnome-terminal -- bash -c "
cd ~/PX4-Autopilot || { echo 'PX4-Autopilot directory could not be found!'; exit 1; }
export LIBGL_ALWAYS_SOFTWARE=1;
./QGroundControl.AppImage;
exec bash
"
sleep 10
# Start the second drone instance (ID 1)
gnome-terminal --title="Drone 1" -- bash -c "
PX4_SYS_AUTOSTART=4001 PX4_SIM_MODEL=gz_x500_mono_cam PX4_GZ_WORLD=baylands ./build/px4_sitl_default/bin/px4 -i 1;
exec bash
"
sleep 25
# Start the second drone instance (ID 2) with initial position set to "0,5" 
gnome-terminal --title="Drone 2" -- bash -c "
PX4_SYS_AUTOSTART=4001 PX4_SIM_MODEL=gz_x500_mono_cam PX4_GZ_WORLD=baylands PX4_GZ_MODEL_POSE='0,10' ./build/px4_sitl_default/bin/px4 -i 2;
exec bash
"

sleep 60
gnome-terminal --title="Drone 1 - Python" -- bash -c "
python3 /home/arda/Masaüstü/SP-494/drone1.py;
exec bash
"
gnome-terminal --title="Drone 2 - Python" -- bash -c "
python3 /home/arda/Masaüstü/SP-494/drone2.py;
exec bash
"
