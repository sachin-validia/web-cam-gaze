#!/bin/bash
# Start backend with correct Python environment

# Use the main project venv Python directly
PYTHON_BIN="/Users/sachinadlakha/Desktop/Validia/web-cam-gaze/venv/bin/python"

# Set environment variable to avoid protobuf issues
export PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

# Run the backend
echo "Starting backend with Python: $PYTHON_BIN"
$PYTHON_BIN app.py