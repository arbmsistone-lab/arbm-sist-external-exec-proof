const OCI_URL='http://169.254.169.254/opc/v2/instance/';
const GCP_BASE='http://metadata.google.internal/computeMetadata/v1/instance';
const GCP_FREE_REGIONS=new Set(['us-west1','us-central1','us-east1']);

async function text(url,headers,fetchImpl){
  const r=await fetchImpl(url,{headers,signal:AbortSignal.timeout(3000)});
  if(!r.ok)throw new Error(`metadata_http_${r.status}`);
  return (await r.text()).trim();
}
async function json(url,headers,fetchImpl){
  const r=await fetchImpl(url,{headers,signal:AbortSignal.timeout(3000)});
  if(!r.ok)throw new Error(`metadata_http_${r.status}`);
  return r.json();
}
export async function collectCloudAttestation(vendor,{fetchImpl=fetch}={}){
  const v=String(vendor||'').trim().toLowerCase();
  if(v==='oci'){
    const d=await json(OCI_URL,{Authorization:'Bearer Oracle'},fetchImpl);
    const profile=String(d.shape||'');
    const ocpus=Number(d.shapeConfig?.ocpus||0),memoryGB=Number(d.shapeConfig?.memoryInGB||0);
    const eligible=profile==='VM.Standard.E2.1.Micro'||(profile==='VM.Standard.A1.Flex'&&ocpus>0&&ocpus<=2&&memoryGB>0&&memoryGB<=12);
    return {cloudVendor:'oci',instanceId:String(d.id||''),profile,region:String(d.region||''),profileEligible:eligible,ocpus,memoryGB,requiresBillingVerification:true};
  }
  if(v==='gcp'){
    const h={'Metadata-Flavor':'Google'};
    const [id,machine,zonePath]=await Promise.all([
      text(`${GCP_BASE}/id`,h,fetchImpl),
      text(`${GCP_BASE}/machine-type`,h,fetchImpl),
      text(`${GCP_BASE}/zone`,h,fetchImpl)
    ]);
    const profile=machine.split('/').pop()||'';
    const zone=zonePath.split('/').pop()||'';
    const region=zone.replace(/-[a-z]$/,'');
    const eligible=profile==='e2-micro'&&GCP_FREE_REGIONS.has(region);
    return {cloudVendor:'gcp',instanceId:id,profile,zone,region,profileEligible:eligible,requiresBillingVerification:true};
  }
  throw new Error('unsupported_cloud_vendor');
}

if(import.meta.url===new URL(`file://${process.argv[1].replaceAll('\\','/')}`).href){
  collectCloudAttestation(process.env.ARBM_CLOUD_VENDOR).then(x=>{
    console.log(JSON.stringify(x));process.exitCode=x.profileEligible?0:2;
  }).catch(e=>{console.error(JSON.stringify({error:String(e?.message||e)}));process.exitCode=1;});
}
