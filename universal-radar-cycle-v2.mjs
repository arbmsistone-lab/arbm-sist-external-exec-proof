import {collectAll} from './universal-radar-collector.mjs';
import {analyzeCollection} from './universal-radar-change-intelligence.mjs';
import {analyzeStrategy} from './universal-radar-strategy-brain.mjs';
import {mergeCollection} from './universal-radar-registry.mjs';
import {applyEvents} from './universal-radar-event-applier.mjs';
import {appendEvidence,verifyLedger} from './universal-radar-evidence-ledger.mjs';
export async function runRadarCycleV2(){
  const started=Date.now();
  const collection=await collectAll();
  const changes=analyzeCollection(collection);
  const strategy=analyzeStrategy(changes,collection);
  const registry=mergeCollection(collection);
  const applied=applyEvents(changes);
  const topActions=strategy.decisions.filter(x=>x.action!=='IGNORE').slice(0,20);
  const summary={
    schema:'arbm-universal-radar-cycle-v2',
    sourceCount:collection.sourceCount,healthySources:collection.healthySources,
    requiredFailures:collection.requiredFailures,itemCount:collection.items.length,
    events:changes.totalEvents,critical:changes.critical,high:changes.high,medium:changes.medium,
    discovered:registry.discovered,changed:registry.changed,seen:registry.seen,
    benchmarkNow:strategy.benchmarkNow,replaceCandidates:strategy.replaceCandidates,
    securityReviews:strategy.securityReviews,costReviews:strategy.costReviews,quarantines:strategy.quarantines,
    applied:applied.applied,reopened:applied.reopened,durationMs:Date.now()-started,
    pass:collection.requiredFailures.length===0,topActions
  };
  const evidence=appendEvidence(summary);
  const ledger=verifyLedger();
  return {...summary,evidenceSequence:evidence.sequence,evidenceHash:evidence.entryHash,ledgerOk:ledger.ok};
}
