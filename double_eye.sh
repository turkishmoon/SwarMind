#!/bin/bash

# Parallel run of Sena_bash01.py and Sena_bash02.py with frame extraction and inference

PYTHON_CMD=$(command -v python3 || command -v python)
FFMPEG_CMD=$(command -v ffmpeg)

if [ -z "$PYTHON_CMD" ]; then
  echo "[ERROR] Python3 is not installed or not in PATH."
  exit 1
fi

if [ -z "$FFMPEG_CMD" ]; then
  echo "[ERROR] ffmpeg is not installed or not in PATH."
  exit 1
fi

SCRIPT_PATH_1="./start_video_logger1.py"
OUTPUT_VIDEO_1="/home/arda/Masaüstü/SP-494/Video_Output/output_video_with_gps_1.avi"
FRAMES_DIR_1="/home/arda/Masaüstü/SP-494/Video_Output/output_video_with_gps_1_frames"
DETECT_OUTPUT_1="/home/eren/Desktop/Video_Output_Detect_01"

SCRIPT_PATH_2="./start_video_logger2.py"
OUTPUT_VIDEO_2="/home/arda/Masaüstü/SP-494/Video_Output/output_video_with_gps_2.avi"
FRAMES_DIR_2="/home/arda/Masaüstü/SP-494/Video_Output/output_video_with_gps_2_frames"
DETECT_OUTPUT_2="/home/eren/Desktop/Video_Output_Detect_02"

MODEL_INFER_SCRIPT="./model_inference.py"

# Check scripts
if [ ! -f "$SCRIPT_PATH_1" ]; then
  echo "[ERROR] $SCRIPT_PATH_1 not found."
  exit 1
fi

if [ ! -f "$SCRIPT_PATH_2" ]; then
  echo "[ERROR] $SCRIPT_PATH_2 not found."
  exit 1
fi

# Run both scripts in parallel
echo "[INFO] Starting Sena_bash01.py and Sena_bash02.py in parallel..."
$PYTHON_CMD "$SCRIPT_PATH_1" &
PID1=$!
$PYTHON_CMD "$SCRIPT_PATH_2" &
PID2=$!

wait $PID1
EXIT_CODE_1=$?
wait $PID2
EXIT_CODE_2=$?

if [ $EXIT_CODE_1 -ne 0 ]; then
  echo "[ERROR] start_video_logger1.py exited with status $EXIT_CODE_1"
  exit $EXIT_CODE_1
else
  echo "[INFO] start_video_logger1.py finished successfully."
fi

if [ $EXIT_CODE_2 -ne 0 ]; then
  echo "[ERROR] start_video_logger2.py exited with status $EXIT_CODE_2"
  exit $EXIT_CODE_2
else
  echo "[INFO] Sena_bash02.py finished successfully."
fi

# Check output videos
if [ ! -f "$OUTPUT_VIDEO_1" ]; then
  echo "[ERROR] Output video file not found: $OUTPUT_VIDEO_1"
  exit 1
fi
if [ ! -f "$OUTPUT_VIDEO_2" ]; then
  echo "[ERROR] Output video file not found: $OUTPUT_VIDEO_2"
  exit 1
fi

# Extract frames from both videos
for i in 1 2; do
  FRAMES_DIR_VAR="FRAMES_DIR_$i"
  OUTPUT_VIDEO_VAR="OUTPUT_VIDEO_$i"
  echo "[INFO] Extracting frames from video to: ${!FRAMES_DIR_VAR}"
  if [ -d "${!FRAMES_DIR_VAR}" ]; then
    echo "[INFO] Frames directory exists, clearing old frames..."
    rm -f "${!FRAMES_DIR_VAR}"/*
  else
    mkdir -p "${!FRAMES_DIR_VAR}"
  fi

  $FFMPEG_CMD -i "${!OUTPUT_VIDEO_VAR}" -vf fps=30 "${!FRAMES_DIR_VAR}/frame_%06d.png"
  if [ $? -eq 0 ]; then
    echo "[INFO] Frame extraction for video $i completed successfully."
  else
    echo "[ERROR] Frame extraction for video $i failed."
    exit 1
  fi
done


# Run the final script
FINAL_SCRIPT="/home/arda/Masaüstü/SP-494/segment_and_detect_agriculture.py"
if [ -f "$FINAL_SCRIPT" ]; then
  echo "[INFO] Starting SENA.py..."
  $PYTHON_CMD "$FINAL_SCRIPT"
  EXIT_CODE=$?
  if [ $EXIT_CODE -ne 0 ]; then
    echo "[ERROR] SENA.py exited with status $EXIT_CODE"
    exit $EXIT_CODE
  else
    echo "[INFO] SENA.py finished successfully."
  fi
else
  echo "[ERROR] $FINAL_SCRIPT not found."
  exit 1
fi

echo "[INFO] All processes completed successfully."
