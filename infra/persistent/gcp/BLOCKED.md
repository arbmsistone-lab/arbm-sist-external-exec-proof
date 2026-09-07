# GCP persistent runner — blocked by zero-spend policy

This directory intentionally contains no deployable Terraform configuration.

The Compute Engine Free Tier includes one non-preemptible `e2-micro` VM in eligible US regions, but a 24x7 ARBM continuity agent requires outbound internet connectivity to GitHub and Supabase.

Current Google Cloud pricing makes the obvious network paths billable:

- in-use external IPv4 addresses on standard VMs are billed after the small monthly free allowance;
- Cloud NAT has hourly, data-processing, and external-IP charges.

Therefore `gcp-free-persistent` remains disabled and cannot be activated under ARBM's `zero-spend-only` policy.

Re-enable only after an independently verified networking path provides continuous outbound HTTPS with zero monetary charge. Never weaken the control-plane cost gate to make GCP pass.
