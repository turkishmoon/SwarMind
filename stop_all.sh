#!/bin/bash

echo "🛑 All drone processes are being shut down..."

# Tüm tmux oturumlarını sonlandır
tmux kill-server 2>/dev/null
echo "✅ All tmux sessions are terminated."

# MAVSDK server süreçlerini kapat
pkill -f mavsdk_server
echo "✅ MAVSDK server was shut down."

# PX4 SITL süreçlerini kapat
pkill -f px4
echo "✅ PX4 processes are closed."

# Python logger scriptlerini kapat
pkill -f drone_logger.py
echo "✅ drone_logger.py is closed."

# QGroundControl (isteğe bağlı)
pkill -f QGroundControl.AppImage && echo "✅ QGroundControl is closed."

echo "🚨 The entire system is stopped."
