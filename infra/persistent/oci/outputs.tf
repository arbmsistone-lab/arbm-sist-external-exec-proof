output "instance_id" {
  value = oci_core_instance.arbm_persistent.id
}

output "public_ip" {
  value = oci_core_instance.arbm_persistent.public_ip
}

output "private_ip" {
  value = oci_core_instance.arbm_persistent.private_ip
}

output "shape" {
  value = oci_core_instance.arbm_persistent.shape
}

output "bootstrap_next_step" {
  value = "Run cloud/oci/install-persistent-host.ps1 only after Terraform apply and independent billing/free-tier verification."
}
