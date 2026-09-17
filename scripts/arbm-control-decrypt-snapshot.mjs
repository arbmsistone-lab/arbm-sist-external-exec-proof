import { createDecipheriv, createHash } from 'node:crypto';
import { mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import path from 'node:path';
const expectedTarget = 'cbbc10bd51e782960afefcde2771e21d729f2da3';
const envelope = JSON.parse(readFileSync('arbm-control-encrypted-snapshot.json', 'utf8'));
if (envelope.schema !== 'arbm-control-encrypted-envelope/v1' || envelope.algorithm !== 'aes-256-gcm') throw new Error('invalid_envelope');
const keyPath = '.arbm-executor/snapshot.key';
const key = Buffer.from(readFileSync(keyPath, 'utf8').trim(), 'hex');
if (key.length !== 32) throw new Error('invalid_key_length');
const decipher = createDecipheriv('aes-256-gcm', key, Buffer.from(envelope.iv, 'base64'));
decipher.setAuthTag(Buffer.from(envelope.tag, 'base64'));
const plain = Buffer.concat([decipher.update(Buffer.from(envelope.ciphertext, 'base64')), decipher.final()]);
if (createHash('sha256').update(plain).digest('hex') !== envelope.plaintext_sha256) throw new Error('plaintext_hash_mismatch');
const payload = JSON.parse(plain.toString('utf8'));
if (payload.schema !== 'arbm-control-private-envelope/v1' || payload.target_sha !== expectedTarget) throw new Error('target_binding_mismatch');
for (const [rel, encoded] of Object.entries(payload.files)) {
  const bytes = Buffer.from(encoded, 'base64');
  if (payload.expected[rel]) {
    const actual = createHash('sha1').update(Buffer.from(`blob ${bytes.length}\0`)).update(bytes).digest('hex');
    if (actual !== payload.expected[rel]) throw new Error(`blob_mismatch:${rel}`);
  }
  const dest = rel.startsWith('.arbm-executor/') ? rel : path.join('.arbm-private-target', rel);
  mkdirSync(path.dirname(dest), { recursive: true });
  writeFileSync(dest, bytes);
}
rmSync(keyPath, { force: true });
console.log(JSON.stringify({ gate: 'ARBM_CONTROL_EXACT_SNAPSHOT_V1', status: 'PASS', target_sha: expectedTarget, files: Object.keys(payload.expected).length }));
