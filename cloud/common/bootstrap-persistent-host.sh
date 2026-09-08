#!/usr/bin/env bash
set -euo pipefail
HOST_ID="${ARBM_HOST_ID:-}"
CLOUD_VENDOR="${ARBM_CLOUD_VENDOR:-}"
TOKEN_FILE="${ARBM_HOST_TOKEN_FILE:-}"
TOKEN="${ARBM_HOST_TOKEN:-}"
if [[ -n "$TOKEN_FILE" ]]; then
  [[ -f "$TOKEN_FILE" ]] || { echo token_file_not_found >&2; exit 5; }
  TOKEN="$(tr -d '\r\n' < "$TOKEN_FILE")"
fi
CONTROL_SHA="${ARBM_CONTROL_SHA:-}"
REPO_URL="${ARBM_REPO_URL:-https://github.com/arbmsistone-lab/arbm-sist-external-exec-proof.git}"
INSTALL_DIR="/opt/arbm-continuity"
STATE_DIR="/var/lib/arbm-continuity"
ENV_FILE="/etc/arbm-continuity.env"

[[ "${EUID}" -eq 0 ]] || { echo root_required >&2; exit 2; }
[[ "$HOST_ID" =~ ^[a-z0-9][a-z0-9.-]{2,63}$ ]] || { echo invalid_host_id >&2; exit 3; }
[[ "$CLOUD_VENDOR" == oci || "$CLOUD_VENDOR" == gcp ]] || { echo invalid_cloud_vendor >&2; exit 4; }
[[ ${#TOKEN} -ge 40 ]] || { echo ARBM_HOST_TOKEN_required >&2; exit 5; }
[[ "$CONTROL_SHA" =~ ^[a-fA-F0-9]{40}$ ]] || { echo exact_control_sha_required >&2; exit 6; }

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y --no-install-recommends ca-certificates git nodejs
NODE_MAJOR="$(node -p "process.versions.node.split('.')[0]" 2>/dev/null || echo 0)"
[[ "$NODE_MAJOR" =~ ^[0-9]+$ && "$NODE_MAJOR" -ge 18 ]] || { echo node_18_plus_required_use_ubuntu_24_04 >&2; exit 8; }
id -u arbm-continuity >/dev/null 2>&1 || useradd --system --home "$STATE_DIR" --shell /usr/sbin/nologin arbm-continuity
install -d -m 0755 "$INSTALL_DIR"
install -d -o arbm-continuity -g arbm-continuity -m 0750 "$STATE_DIR" "$STATE_DIR/run"
rm -rf "$INSTALL_DIR/repo.new"
git init -q "$INSTALL_DIR/repo.new"
git -C "$INSTALL_DIR/repo.new" remote add origin "$REPO_URL"
git -C "$INSTALL_DIR/repo.new" fetch -q --depth 1 origin "$CONTROL_SHA"
git -C "$INSTALL_DIR/repo.new" checkout -q --detach FETCH_HEAD
ACTUAL_SHA="$(git -C "$INSTALL_DIR/repo.new" rev-parse HEAD)"
[[ "${ACTUAL_SHA,,}" == "${CONTROL_SHA,,}" ]] || { echo control_sha_mismatch >&2; exit 7; }
ARBM_CLOUD_VENDOR="$CLOUD_VENDOR" node "$INSTALL_DIR/repo.new/scripts/cloud-host-attestation.mjs" > "$STATE_DIR/bootstrap-attestation.json"

rm -rf "$INSTALL_DIR/repo.prev"
if [[ -d "$INSTALL_DIR/repo" ]]; then mv "$INSTALL_DIR/repo" "$INSTALL_DIR/repo.prev"; fi
mv "$INSTALL_DIR/repo.new" "$INSTALL_DIR/repo"
chown -R root:root "$INSTALL_DIR/repo"
chmod -R a-w "$INSTALL_DIR/repo"
chown arbm-continuity:arbm-continuity "$STATE_DIR/bootstrap-attestation.json"
chmod 0640 "$STATE_DIR/bootstrap-attestation.json"

CPU_QUOTA=80%
MEMORY_MAX=768M
CAPABILITIES=git,tests,cloud,persistent
if [[ "$CLOUD_VENDOR" == oci ]]; then CPU_QUOTA=180%; MEMORY_MAX=2G; CAPABILITIES=git,tests,build,cloud,persistent; fi

umask 077
cat > "$ENV_FILE" <<EOF
ARBM_HOST_ID=$HOST_ID
ARBM_HOST_TOKEN=$TOKEN
ARBM_CLOUD_VENDOR=$CLOUD_VENDOR
ARBM_RUN_ROOT=$STATE_DIR/run
ARBM_CAPABILITIES=$CAPABILITIES
EOF
chmod 0600 "$ENV_FILE"
unset TOKEN ARBM_HOST_TOKEN
if [[ -n "$TOKEN_FILE" ]]; then rm -f -- "$TOKEN_FILE"; fi
cat > /etc/systemd/system/arbm-continuity.service <<EOF
[Unit]
Description=ARBM persistent continuity agent
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
User=arbm-continuity
Group=arbm-continuity
EnvironmentFile=$ENV_FILE
ExecStart=/usr/bin/node $INSTALL_DIR/repo/scripts/persistent-continuity-agent.mjs
Restart=always
RestartSec=10
NoNewPrivileges=true
UMask=0077
PrivateTmp=true
PrivateDevices=true
ProtectHome=true
ProtectSystem=strict
ReadWritePaths=$STATE_DIR
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectKernelLogs=true
ProtectControlGroups=true
ProtectClock=true
RestrictSUIDSGID=true
RestrictRealtime=true
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
CapabilityBoundingSet=
AmbientCapabilities=
LockPersonality=true
CPUQuota=$CPU_QUOTA
MemoryMax=$MEMORY_MAX
EOF
cat >> /etc/systemd/system/arbm-continuity.service <<'EOF'

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now arbm-continuity.service
sleep 3
systemctl is-active --quiet arbm-continuity.service
echo "ARBM_PERSISTENT_HOST_BOOTSTRAP_OK host=$HOST_ID vendor=$CLOUD_VENDOR sha=$ACTUAL_SHA"
