"""Audit GitHub workflow supply-chain hardening for ARBM SIST."""
from __future__ import annotations
import json, re
from pathlib import Path

SHA40=re.compile(r"@[0-9a-f]{40}$",re.I)
USES=re.compile(r"^\s*(?:-\s*)?uses:\s*([^\s#]+)",re.M)
PIP=re.compile(r"\b(?:python\s+-m\s+)?pip(?:3)?\s+install\b",re.I)

def top_permissions(text):
    lines=text.splitlines()
    for i,line in enumerate(lines):
        if line.startswith("permissions:"):
            value=line.split(":",1)[1].strip()
            if value:
                return value, i+1
            block=[]
            for j in range(i+1,len(lines)):
                raw=lines[j]
                if raw and not raw[0].isspace():
                    break
                if raw.strip():
                    block.append(raw.strip())
            return "\n".join(block), i+1
    return "",0

def audit_file(path):
    text=path.read_text(encoding="utf-8",errors="replace")
    perms,line=top_permissions(text)
    top_write=bool(re.search(r"(?m)(?:^|\n)[A-Za-z-]+:\s*write\b",perms))
    acceptable_top=(perms=="read-all" or perms=="{}" or
                    (bool(perms) and not top_write and "write-all" not in perms))
    uses=USES.findall(text)
    unpinned=[u for u in uses
              if not u.startswith("./") and not u.startswith("docker://")
              and not SHA40.search(u)]
    pip_lines=[]
    for n,raw in enumerate(text.splitlines(),1):
        if PIP.search(raw) and "--require-hashes" not in raw:
            pip_lines.append({"line":n,"text":raw.strip()[:240]})
    return {
        "path":str(path),
        "top_permissions_present":bool(perms),
        "top_permissions_line":line,
        "top_permissions":perms,
        "top_permissions_least_privilege":acceptable_top,
        "unpinned_actions":unpinned,
        "pip_without_require_hashes":pip_lines,
    }

def main():
    root=Path(".github/workflows")
    rows=[audit_file(p) for p in sorted(root.glob("*.y*ml"))]
    findings={
        "workflow_count":len(rows),
        "missing_or_unsafe_top_permissions":[r["path"] for r in rows
            if not r["top_permissions_least_privilege"]],
        "unpinned_actions":[{"path":r["path"],"uses":r["unpinned_actions"]}
            for r in rows if r["unpinned_actions"]],
        "pip_without_require_hashes":[{"path":r["path"],"items":r["pip_without_require_hashes"]}
            for r in rows if r["pip_without_require_hashes"]],
    }
    findings["counts"]={
        "permissions":len(findings["missing_or_unsafe_top_permissions"]),
        "actions":sum(len(x["uses"]) for x in findings["unpinned_actions"]),
        "pip":sum(len(x["items"]) for x in findings["pip_without_require_hashes"]),
    }
    findings["pass"]=all(v==0 for v in findings["counts"].values())
    print(json.dumps(findings,indent=2,sort_keys=True))
    raise SystemExit(0 if findings["pass"] else 1)

if __name__=="__main__":
    main()
