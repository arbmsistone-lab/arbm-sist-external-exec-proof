$ErrorActionPreference="Stop"
$Root=Split-Path -Parent $PSScriptRoot
$Out=Join-Path $Root "logs\stage6_m0_quota_probe.json"
$chrome=(Get-Item "C:\Program Files\Google\Chrome\Application\chrome.exe" -ErrorAction SilentlyContinue)
$gcloud=(Get-Command gcloud -ErrorAction SilentlyContinue)
$envNames=@(Get-ChildItem Env: | Where-Object {$_.Name -match 'GOOGLE|GEMINI|GENAI|VERTEX|GCLOUD'} | Select-Object -ExpandProperty Name)
$debug=(netstat -ano | Select-String ':9222|:9223|:9224|:9515' | ForEach-Object {$_.Line})
$obj=[ordered]@{
 captured_at=(Get-Date).ToString("o")
 provider="Google Gemini Developer API"
 public_docs_rate_limits="https://ai.google.dev/gemini-api/docs/rate-limits"
 public_docs_billing="https://ai.google.dev/gemini-api/docs/billing"
 public_docs_models="https://ai.google.dev/gemini-api/docs/models"
 current_public_recommended_model_ids=@("gemini-3.8-flash","gemini-3.5-flash-lite")
 gcloud_installed=[bool]$gcloud
 google_gemini_env_names=$envNames
 chrome_version=if($chrome){$chrome.VersionInfo.ProductVersion}else{$null}
 chrome_debug_port_available=($debug.Count -gt 0)
 account_project_id=$null
 account_model_visible=$null
 account_exact_model_id=$null
 account_usage_tier=$null
 account_active_rpm=$null
 account_active_tpm=$null
 account_active_rpd=$null
 account_billing_state=$null
 free_tier_confirmed_for_account=$false
 thirty_valid_runs_fit=$null
 max_paid_cost_usd=0.00
 auto_paid_upgrade_allowed=$false
 status="BLOCKED_ACCOUNT_SPECIFIC_STATE_NOT_OBSERVED"
}
$obj | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $Out
Get-Content $Out -Raw
