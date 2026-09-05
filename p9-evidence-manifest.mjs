import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';

const sha256File = (file) => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
export function verifyEvidenceManifest(root, manifest) {
  const reasons=[]; const entries=manifest?.files;
  if (!Array.isArray(entries) || entries.length===0) return {pass:false,reasons:['MANIFEST_FILES_MISSING'],verified:[]};
  const verified=[]; const seen=new Set();
  for (const e of entries) {
    const rel=String(e?.path||'').replace(/\\/g,'/');
    const expected=String(e?.sha256||'').toLowerCase();
    if (!rel || rel.startsWith('/') || rel.includes('../')) { reasons.push(`MANIFEST_PATH_INVALID:${rel}`); continue; }
    if (seen.has(rel)) { reasons.push(`MANIFEST_DUPLICATE_PATH:${rel}`); continue; } seen.add(rel);
    if (!/^[a-f0-9]{64}$/.test(expected)) { reasons.push(`MANIFEST_HASH_INVALID:${rel}`); continue; }
    const abs=path.resolve(root,rel); const base=path.resolve(root)+path.sep;
    if (!(abs+path.sep).startsWith(base) && !abs.startsWith(base)) { reasons.push(`MANIFEST_PATH_ESCAPE:${rel}`); continue; }
    if (!fs.existsSync(abs) || !fs.statSync(abs).isFile()) { reasons.push(`MANIFEST_FILE_MISSING:${rel}`); continue; }
    const actual=sha256File(abs);
    if (actual!==expected) reasons.push(`MANIFEST_HASH_MISMATCH:${rel}`); else verified.push({path:rel,sha256:actual});
  }
  return {pass:reasons.length===0,reasons,verified};
}

if (process.argv[1] && process.argv[1].endsWith('p9-evidence-manifest.mjs')) {
  const [root,manifestFile]=process.argv.slice(2);
  if (!root || !manifestFile) process.exit(64);
  let manifest; try { manifest=JSON.parse(fs.readFileSync(manifestFile,'utf8')); } catch { process.exit(65); }
  const result=verifyEvidenceManifest(root,manifest); console.log(JSON.stringify(result,null,2)); process.exit(result.pass?0:2);
}
