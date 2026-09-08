from pathlib import Path
import subprocess
import modal

ROOT = Path(__file__).resolve().parents[2]
PORT = 8000
CONTINUITY_URL = "https://pvkpkqwdnnpkgvllwqbc.supabase.co/functions/v1/arbm-persistent-continuity-v1"

app = modal.App("arbm-continuity-modal")
image = modal.Image.from_dockerfile(
    ROOT / "Dockerfile",
    context_dir=ROOT,
    add_python="3.12",
)
secret = modal.Secret.from_name("arbm-continuity-modal")

@app.server(
    image=image,
    secrets=[secret],
    env={
        "ARBM_CONTINUITY_URL": CONTINUITY_URL,
        "ARBM_CLOUD_VENDOR": "modal",
        "ARBM_HOST_ID": "modal-starter-persistent",
        "ARBM_CPU_CORES": "0.125",
        "ARBM_MEMORY_MIB": "512",
        "PORT": str(PORT),
    },
    cpu=(0.125, 0.125),
    memory=(512, 512),
    min_containers=1,
    max_containers=1,
    target_concurrency=0,
    port=PORT,
)
class ContinuityServer:
    @modal.enter()
    def start(self):
        self.process = subprocess.Popen(
            ["node", "/opt/arbm/scripts/persistent-container-health.mjs"]
        )

    @modal.exit()
    def stop(self):
        if getattr(self, "process", None) and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=8)
            except subprocess.TimeoutExpired:
                self.process.kill()
