const GCP_BASE='http://metadata.google.internal/computeMetadata/v1/instance';
const GCP_FREE_REGIONS=new Set(['us-west1','us-central1','us-east1']);

async function text(url,headers,fetchImpl){
  const r=await fetchImpl(url,{headers,signal:AbortSignal.timeout(3000)});
  if(!r.ok)throw new Error(`metadata_http_${r.status}`);
  return (await r.text()).trim();
}
function envNumber(name,def){const n=Number(process.env[name]??def);return Number.isFinite(n)?n:NaN;}
function containerIdentity(){return String(process.env.ARBM_INSTANCE_ID||process.env.K_REVISION||process.env.HOSTNAME||'').trim();}

export async function collectCloudAttestation(vendor,{fetchImpl=fetch}={}){
  const v=String(vendor||'').trim().toLowerCase();
  if(v==='modal'){
    const instanceId=String(process.env.ARBM_INSTANCE_ID||process.env.MODAL_TASK_ID||process.env.HOSTNAME||'').trim();
    const cpuCores=envNumber('ARBM_CPU_CORES',0.125),memoryMiB=envNumber('ARBM_MEMORY_MIB',512);
    const profile='modal-starter-cpu-0.125-mem-512';
    const eligible=!!instanceId&&cpuCores>0&&cpuCores<=0.125&&memoryMiB>0&&memoryMiB<=512;
    return {cloudVendor:'modal',instanceId,profile,profileEligible:eligible,cpuCores,memoryMiB,requiresBillingVerification:true};
  }
  if(v==='back4app'){
    const instanceId=containerIdentity();
    const cpuCores=envNumber('ARBM_CPU_CORES',0.25),memoryMiB=envNumber('ARBM_MEMORY_MIB',256);
    const profile='back4app-free-container';
    const eligible=!!instanceId&&cpuCores>0&&cpuCores<=0.25&&memoryMiB>0&&memoryMiB<=256;
    return {cloudVendor:'back4app',instanceId,profile,profileEligible:eligible,cpuCores,memoryMiB,requiresBillingVerification:true};
  }
  if(v==='hostless'){
    const instanceId=containerIdentity();
    const cpuCores=envNumber('ARBM_CPU_CORES',0.25),memoryMiB=envNumber('ARBM_MEMORY_MIB',1024);
    const profile='hostless-free-container';
    const eligible=!!instanceId&&cpuCores>0&&cpuCores<=0.25&&memoryMiB>0&&memoryMiB<=1024;
    return {cloudVendor:'hostless',instanceId,profile,profileEligible:eligible,cpuCores,memoryMiB,requiresBillingVerification:true};
  }
  if(v==='gcp'){
    const h={'Metadata-Flavor':'Google'};
    const [id,machine,zonePath]=await Promise.all([
      text(`${GCP_BASE}/id`,h,fetchImpl),text(`${GCP_BASE}/machine-type`,h,fetchImpl),text(`${GCP_BASE}/zone`,h,fetchImpl)]);
    const profile=machine.split('/').pop()||'',zone=zonePath.split('/').pop()||'',region=zone.replace(/-[a-z]$/,'');
    const eligible=profile==='e2-micro'&&GCP_FREE_REGIONS.has(region);
    return {cloudVendor:'gcp',instanceId:id,profile,zone,region,profileEligible:eligible,requiresBillingVerification:true};
  }
  throw new Error('unsupported_cloud_vendor');
}

if(import.meta.url===new URL(`file://${process.argv[1].replaceAll('\\','/')}`).href){
  collectCloudAttestation(process.env.ARBM_CLOUD_VENDOR).then(x=>{console.log(JSON.stringify(x));process.exitCode=x.profileEligible?0:2;}).catch(e=>{console.error(JSON.stringify({error:String(e?.message||e)}));process.exitCode=1;});
}
