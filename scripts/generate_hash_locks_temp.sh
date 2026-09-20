#!/usr/bin/env bash
set -euo pipefail

python -m pip install --disable-pip-version-check -q uv==0.8.15
mkdir -p audit/locks

cat > scripts/requirements-osworld.in <<'EOF'
Pillow==12.3.0
ijson==3.4.0
defusedxml==0.7.1
EOF
uv pip compile --generate-hashes scripts/requirements-osworld.in -o scripts/requirements-osworld.txt

cat > audit/locks/world-free-scanners.in <<'EOF'
semgrep==1.177.0
bandit==1.9.4
pip-audit==2.10.1
EOF
uv pip compile --generate-hashes audit/locks/world-free-scanners.in -o audit/locks/world-free-scanners.txt

cat > audit/locks/osworld-ml.in <<'EOF'
torch==2.7.1
transformers==4.52.4
safetensors==0.8.0
EOF
uv pip compile --generate-hashes audit/locks/osworld-ml.in -o audit/locks/osworld-ml.txt

cat > audit/locks/uv-hf.in <<'EOF'
uv==0.8.15
huggingface_hub==0.35.3
EOF
uv pip compile --generate-hashes audit/locks/uv-hf.in -o audit/locks/uv-hf.txt

cat > audit/locks/openai-probe.in <<'EOF'
openai>=1.50,<3
Pillow==12.3.0
PyYAML==6.0.2
EOF
uv pip compile --generate-hashes audit/locks/openai-probe.in -o audit/locks/openai-probe.txt

cat > audit/locks/provider-preflight.in <<'EOF'
docker
psutil
requests
filelock
EOF
uv pip compile --generate-hashes audit/locks/provider-preflight.in -o audit/locks/provider-preflight.txt

cat > audit/locks/datasets.in <<'EOF'
datasets
EOF
uv pip compile --generate-hashes audit/locks/datasets.in -o audit/locks/datasets.txt

cat > audit/locks/psycopg.in <<'EOF'
psycopg[binary]==3.2.10
EOF
uv pip compile --generate-hashes audit/locks/psycopg.in -o audit/locks/psycopg.txt

if test -s swe-rebench-v2/requirements.txt; then
  uv pip compile --generate-hashes swe-rebench-v2/requirements.txt -o audit/locks/swe-rebench-v2.txt
fi
