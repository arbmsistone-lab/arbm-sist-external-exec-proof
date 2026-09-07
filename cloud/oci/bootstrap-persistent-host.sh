#!/usr/bin/env bash
set -euo pipefail

HOST_ID="${ARBM_HOST_ID:-oci-always-free-persistent}"
TOKEN="${ARBM_HOST_TOKEN:-}"
CONTROL_SHA="${ARBM_CONTROL_SHA:-}"
REPO_URL="${ARBM_REPO_URL:-https://github.com/arbmsistone-lab/arbm-sist-external-exec-proof.git}"
INSTALL_DIR="/opt/arbm-continuity"
STATE_DIR="/var/lib/arbm-continuity"
ENV_FILE="/etc/arbm-continuity.env"

[[ "${EUID}" -eq 0 ]] || { echo 'root_required' >&2; exit 2; }
[[ ${#TOKEN} -ge 40 ]] || { echo 'ARBM_HOST_TOKEN_required' >&2; exit 3; }
[[ "$CONTROL_SHA" =~ ^[a-fA-F0-9]{40}$ ]] || { echo 'ARBM_CONTROL_SHA_exact_40_hex_required' >&2; exit 4; }

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y --no-install-recommends ca-certificates git nodejs
node --version
git --version

id -u arbm-continuity >/dev/null 2>&1 || useradd --system --home "$STATE_DIR" --shell /usr/sbin/nologin arbm-continuity
install -d -m 0755 "$INSTALL_DIR"
install -d -o arbm-continuity -g arbm-continuity -m 0750 "$STATE_DIR" "$STATE_DIR/run"
rm -rf "$INSTALL_DIR/repo.new"
git init -q "$INSTALL_DIR/repo.new"
git -C "$INSTALL_DIR/repo.new" remote add origin "$REPO_URL"
git -C "$INSTALL_DIR/repo.new" fetch -q --depth 1 origin "$CONTROL_SHA"
git -C "$INSTALL_DIR/repo.new" checkout -q --detach FETCH_HEAD
ACTUAL_SHA="$(git -C "$INSTALL_DIR/repo.new" rev-parse HEAD)"
[[ "${ACTUAL_SHA,,}" == "${CONTROL_SHA,,}" ]] || { echo 'control_sha_mismatch' >&2; exit 5; }
rm -rf "$INSTALL_DIR/repo.prev"
if [[ -d "$INSTALL_DIR/repo" ]]; then mv "$INSTALL_DIR/repo" "$INSTALL_DIR/repo.prev"; fi
mv "$INSTALL_DIR/repo.new" "$INSTALL_DIR/repo"
chown -R root:root "$INSTALL_DIR/repo"
chmod -R a-w "$INSTALL_DIR/repo"

umask 077
cat > "$ENV_FILE" <<EOF
ARBM_HOST_ID=$HOST_ID
ARBM_HOST_TOKEN=$TOKEN
ARBM_ZERO_SPEND_VERIFIED=1
ARBM_RUN_ROOT=$STATE_DIR/run
EOF
chmod 0600 "$ENV_FILE"
unset TOKEN ARBM_HOST_TOKEN

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
PrivateTmp=true
ProtectHome=true
ProtectSystem=strict
ReadWritePaths=$STATE_DIR
ProtectKernelTunables=true
ProtectControlGroups=true
RestrictSUIDSGID=true
CPUQuota=180%
MemoryMax=75%
EOF
cat >> /etc/systemd/system/arbm-continuity.service <<'EOF'

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now arbm-continuity.service
sleep 3
systemctl is-active --quiet arbm-continuity.service
systemctl --no-pager --full status arbm-continuity.service | sed -n '1,12p'
echo "ARBM_PERSISTENT_HOST_BOOTSTRAP_OK host=$HOST_ID sha=$ACTUAL_SHA"
