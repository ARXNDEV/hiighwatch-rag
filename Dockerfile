# --- STAGE 1: Build the Frontend (Next.js) ---
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ .
# Disable telemetry and build standalone
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build


# --- STAGE 2: Build the Backend & Final Container ---
FROM python:3.10-slim AS final
WORKDIR /app

# Install system dependencies (for FAISS, PyMuPDF, and Node.js)
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    nodejs \
    npm \
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend code
COPY backend/ ./backend/

# Copy built frontend from Stage 1
COPY --from=frontend-builder /app/frontend/.next/standalone ./frontend/
COPY --from=frontend-builder /app/frontend/.next/static ./frontend/.next/static
COPY --from=frontend-builder /app/frontend/public ./frontend/public

# Create a startup script that runs both Frontend and Backend
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# The container will expose exactly one port (8080)
EXPOSE 8080

# Run the startup script
CMD ["/app/start.sh"]