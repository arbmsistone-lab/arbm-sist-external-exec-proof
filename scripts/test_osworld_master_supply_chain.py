import json
import re
from pathlib import Path
import unittest


ROOT=Path(__file__).resolve().parents[1]
REG=json.loads((ROOT/"assurance/master-supreme/gate-registry.json").read_text())
RC_BRANCH=REG["release_candidate"]["branch"]


class MasterSupplyChainTests(unittest.TestCase):
    def test_release_candidate_oidc_identity_is_explicitly_allowlisted(self):
        endpoint=(ROOT/"endpoint/index.ts").read_text()
        required=f"refs/heads/{RC_BRANCH}"
        self.assertIn(required,endpoint,
            "RC endpoint identity is not authorized by exact branch ref; remote fallback cannot be certified")

    def test_focal_workflow_pins_official_runtime_identity(self):
        text=(ROOT/".github/workflows/osworld-v32-focal-091-free.yml").read_text()
        required=(
            "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
            "d578d2d4e0dc82b43e270fdaa7fa89d9708cd154",
            "42f8f6f8939b8712997d5891456a575f8a2a5f53465e9e3e6747af5d6efd0915",
            "8213366932c553e5fe758d0f2c8c8b81ffc3be8c",
            "eb737ae70b49849e24af407de6a518439a23de05a8497096a948334ce0a909aa",
            "sha256:0e6497a9295647cf05bf2b2af522fdd79bdeba2737595259cab310a3bcf6baa9",
        )
        for item in required:
            self.assertIn(item,text)

    def test_all_github_actions_uses_are_commit_pinned(self):
        bad=[]
        for path in (ROOT/".github/workflows").glob("*.yml"):
            for line in path.read_text(errors="ignore").splitlines():
                m=re.search(r"\buses:\s*([^\s#]+)",line)
                if not m:
                    continue
                use=m.group(1)
                if use.startswith("./"):
                    continue
                if "@" not in use:
                    bad.append(f"{path.name}:{use}:missing-ref"); continue
                ref=use.rsplit("@",1)[1]
                if not re.fullmatch(r"[0-9a-f]{40}",ref):
                    bad.append(f"{path.name}:{use}:not-commit-pinned")
        self.assertEqual(bad,[])

    def test_python_closure_requirements_are_exactly_pinned(self):
        lines=[x.strip() for x in (ROOT/"scripts/requirements-osworld.txt").read_text().splitlines()
               if x.strip() and not x.lstrip().startswith("#")]
        self.assertTrue(lines)
        bad=[x for x in lines if not re.fullmatch(r"[A-Za-z0-9_.-]+==[^=<>!~\s]+",x)]
        self.assertEqual(bad,[])

    def test_no_obvious_plaintext_secret_tokens_in_runtime_sources(self):
        patterns=(
            re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
            re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
            re.compile(r"\bgsk_[A-Za-z0-9]{20,}\b"),
            re.compile(r"\bhf_[A-Za-z0-9]{20,}\b"),
            re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
        )
        roots=[ROOT/"scripts",ROOT/"endpoint",ROOT/".github/workflows"]
        files=[]
        for base in roots:
            if base.is_file(): files.append(base)
            elif base.exists():
                files.extend(p for p in base.rglob("*") if p.is_file())
        findings=[]
        for path in files:
            if path.suffix not in {".py",".ts",".yml",".yaml",".mjs",".json",".md"}:
                continue
            text=path.read_text(errors="ignore")
            for pat in patterns:
                if pat.search(text):
                    findings.append(f"{path.relative_to(ROOT)}:{pat.pattern}")
        self.assertEqual(findings,[])


if __name__=="__main__":
    unittest.main()
