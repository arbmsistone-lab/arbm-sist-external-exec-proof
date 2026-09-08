import {collectAll} from './universal-radar-collector.mjs';
import {analyzeCollection} from './universal-radar-change-intelligence.mjs';
import {mergeCollection} from './universal-radar-registry.mjs';
import {applyEvents} from './universal-radar-event-applier.mjs';
import {appendEvidence,verifyLedger} from './universal-radar-evidence-ledger.mjs';
export async function runRadarCycle(){
  const started=Date.now();
  const collection=await collectAll();
  const changeReport=analyzeCollection(collection);
  const registry=mergeCollection(collection);
  const applied=applyEvents(changeReport);
  const summary={
    schema:'arbm-universal-radar-cycle-v1',
    sourceCount:collection.sourceCount,healthySources:collection.healthySources,
    requiredFailures:collection.requiredFailures,itemCount:collection.items.length,
    events:changeReport.totalEvents,critical:changeReport.critical,high:changeReport.high,medium:changeReport.medium,
    discovered:registry.discovered,changed:registry.changed,seen:registry.seen,
    applied:applied.applied,quarantined:applied.quarantined,reopened:applied.reopened,
    durationMs:Date.now()-started,pass:collection.requiredFailures.length===0
  };
  const evidence=appendEvidence(summary); const ledger=verifyLedger();
  return {...summary,evidenceSequence:evidence.sequence,evidenceHash:evidence.entryHash,ledgerOk:ledger.ok};
}
if(import.meta.url===`file://${process.argv[1].replace(/\\/g,'/')}`) console.log(JSON.stringify(await runRadarCycle(),null,2));
