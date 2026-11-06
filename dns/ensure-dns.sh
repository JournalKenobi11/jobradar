#!/usr/bin/env bash
# ==============================================================================
# Homelab CoreDNS Watchdog & Boot Resilience Script
# ==============================================================================
# Ensures homelab_dns (CoreDNS) is started and remains running once the
# Tailscale IP (100.66.54.63) becomes available on the host interface.
# ==============================================================================

set -u

TARGET_IP="100.66.54.63"
CONTAINER_NAME="homelab_dns"
LOG_TAG="[homelab-dns-watchdog]"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $LOG_TAG $1"
}

is_container_running() {
    local status
    status=$(docker inspect -f '{{.State.Running}}' "$CONTAINER_NAME" 2>/dev/null || echo "false")
    [ "$status" = "true" ]
}

log "Starting CoreDNS boot watchdog..."

# 1. Wait for Tailscale interface IP to be assigned
while ! ip -4 addr show | grep -q "$TARGET_IP"; do
    log "Waiting for Tailscale IP ($TARGET_IP) to be active..."
    sleep 2
done

log "Tailscale IP ($TARGET_IP) is active."

# 2. Start container if stopped
attempts=0
while ! is_container_running && [ $attempts -lt 20 ]; do
    log "Attempting to start container $CONTAINER_NAME (Attempt $((attempts + 1)))..."
    docker start "$CONTAINER_NAME" >/dev/null 2>&1
    sleep 3
    attempts=$((attempts + 1))
done

if is_container_running; then
    log "Container $CONTAINER_NAME is healthy and running on $TARGET_IP:53."
else
    log "Warning: Container $CONTAINER_NAME could not be started after $attempts attempts."
fi

# 3. Persistent background watchdog loop
while true; do
    if ! is_container_running; then
        if ip -4 addr show | grep -q "$TARGET_IP"; then
            log "Container $CONTAINER_NAME was stopped! Reviving..."
            docker start "$CONTAINER_NAME" >/dev/null 2>&1
        fi
    fi
    sleep 15
done
