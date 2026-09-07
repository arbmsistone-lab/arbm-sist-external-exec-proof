import fs from 'node:fs';
const file=new URL('./provider-capabilities.json',import.meta.url);
const data=JSON.parse(fs.readFileSync(file,'utf8').replace(/^\uFEFF/,''));
const providers=data.providers??[];
const invalidActive=providers.filter(p=>p.state==='ACTIVE'&&(
  p.zeroCostVerified!==true||p.liveExecutionProven!==true||!p.providerDomain
));
const active=providers.filter(p=>p.state==='ACTIVE'&&p.zeroCostVerified===true&&p.liveExecutionProven===true&&p.providerDomain);
const domains=[...new Set(active.map(p=>p.providerDomain))];
const required=3;
const prepared=providers.filter(p=>p.state==='PREPARED_NOT_LIVE').map(p=>p.id);
const report={
  schema:'arbm-provider-operational-quorum-v1',failClosed:true,
  requiredIndependentDomains:required,activeIndependentDomains:domains.length,
  activeDomains:domains,activeProviders:active.map(p=>p.id),invalidActive:invalidActive.map(p=>p.id),
  preparedNotLive:prepared,pass:invalidActive.length===0&&domains.length>=required
};
console.log(JSON.stringify(report,null,2));
if(process.env.ARBM_ENFORCE_PROVIDER_QUORUM==='1'&&!report.pass) process.exit(1);
