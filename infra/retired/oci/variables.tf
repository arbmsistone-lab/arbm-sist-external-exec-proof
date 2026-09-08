variable "region" {
  type        = string
  description = "OCI home region. Always Free compute must be created in the tenancy home region."
}

variable "availability_domain" {
  type        = string
  description = "Availability domain with Always Free capacity."
}

variable "compartment_id" {
  type        = string
  description = "OCI compartment OCID."
}

variable "subnet_id" {
  type        = string
  description = "Existing public subnet OCID. No new paid network resources are created."
}

variable "image_ocid" {
  type        = string
  description = "Ubuntu image OCID compatible with the selected shape."
}

variable "ssh_public_key" {
  type        = string
  sensitive   = true
  description = "SSH public key used only for one-time bootstrap access."
}

variable "shape" {
  type        = string
  default     = "VM.Standard.A1.Flex"
  description = "Fail-closed Always Free shape allowlist."
  validation {
    condition     = contains(["VM.Standard.A1.Flex", "VM.Standard.E2.1.Micro"], var.shape)
    error_message = "Only documented OCI Always Free shapes are allowed."
  }
}

variable "ocpus" {
  type        = number
  default     = 1
  description = "A1 OCPUs. Hard capped at 2 for zero-spend safety."
  validation {
    condition     = var.ocpus > 0 && var.ocpus <= 2
    error_message = "A1 OCPUs must be >0 and <=2."
  }
}

variable "memory_in_gbs" {
  type        = number
  default     = 6
  description = "A1 memory. Hard capped at 12 GB for zero-spend safety."
  validation {
    condition     = var.memory_in_gbs > 0 && var.memory_in_gbs <= 12
    error_message = "A1 memory must be >0 and <=12 GB."
  }
}

variable "nsg_ids" {
  type        = list(string)
  default     = []
  description = "Existing NSGs. Prefer SSH restricted to the provisioning source."
}

variable "display_name" {
  type    = string
  default = "arbm-continuity-persistent"
}

variable "home_region_verified" {
  type        = bool
  default     = false
  description = "Must be true only after confirming region is the tenancy home region."
}

variable "always_free_inventory_verified" {
  type        = bool
  default     = false
  description = "Must be true only after verifying current tenancy usage leaves free capacity."
}

variable "apply_guard" {
  type        = string
  default     = "BLOCKED"
  description = "Explicit deployment gate. Never set automatically in CI."
  sensitive   = true
}
