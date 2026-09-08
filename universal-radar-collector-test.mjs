import {collectSource} from './universal-radar-collector.mjs';
const src={id:'synthetic',kind:'json',url:'data:application/json,%5B%7B%22id%22%3A%22m1%22%2C%22name%22%3A%22Model%201%22%7D%5D',domain:'llm',primary:true};
const r=await collectSource(src);
if(!r.ok) throw new Error('COLLECT_FAIL');
if(r.count!==1) throw new Error('COUNT_FAIL');
if(r.items[0].name!=='Model 1') throw new Error('PARSE_FAIL');
if(r.items[0].domain!=='llm') throw new Error('DOMAIN_FAIL');
console.log('UNIVERSAL_RADAR_COLLECTOR_PASS');
