#!/bin/bash

# Start the FastAPI Backend on Port 8000
echo "Starting Backend on Port 8000..."
cd /app/backend

# Memory Optimizations for Free Tiers
export OMP_NUM_THREADS="1"
export MKL_NUM_THREADS="1"
export OPENBLAS_NUM_THREADS="1"
export VECLIB_MAXIMUM_THREADS="1"
export NUMEXPR_NUM_THREADS="1"
export MALLOC_ARENA_MAX="2"
export ENVIRONMENT="production"

# If NEXT_PUBLIC_API_URL isn't set, default it to the container's public URL
if [ -z "$NEXT_PUBLIC_API_URL" ]; then
    export NEXT_PUBLIC_API_URL=$API_URL
fi

# Start uvicorn in the background
uvicorn main:app --host 0.0.0.0 --port 8000 &

# Start the Next.js Frontend on Port 8080 (The port exposed to the internet)
echo "Starting Frontend on Port 8080..."
cd /app/frontend

export PORT=8080
export HOSTNAME="0.0.0.0"

# Start the standalone Next.js server
node server.js