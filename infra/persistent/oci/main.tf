locals {
  is_a1 = var.shape == "VM.Standard.A1.Flex"
}

resource "oci_core_instance" "arbm_persistent" {
  availability_domain = var.availability_domain
  compartment_id      = var.compartment_id
  display_name        = var.display_name
  shape               = var.shape
  preserve_boot_volume = false

  dynamic "shape_config" {
    for_each = local.is_a1 ? [1] : []
    content {
      ocpus         = var.ocpus
      memory_in_gbs = var.memory_in_gbs
    }
  }

  source_details {
    source_id   = var.image_ocid
    source_type = "image"
  }

  create_vnic_details {
    assign_public_ip = true
    display_name     = "arbm-continuity-vnic"
    nsg_ids          = var.nsg_ids
    subnet_id        = var.subnet_id
  }

  metadata = {
    ssh_authorized_keys = var.ssh_public_key
  }

  freeform_tags = {
    "ARBM-Role"       = "persistent-continuity"
    "ARBM-CostPolicy" = "zero-spend-only"
  }

  lifecycle {
    precondition {
      condition     = var.home_region_verified
      error_message = "Blocked: OCI home region was not independently verified."
    }
    precondition {
      condition     = var.always_free_inventory_verified
      error_message = "Blocked: Always Free tenancy inventory was not verified."
    }
    precondition {
      condition     = var.apply_guard == "ARBM_ZERO_SPEND_OCI_APPLY"
      error_message = "Blocked: explicit zero-spend apply guard is missing."
    }
    precondition {
      condition     = !local.is_a1 || (var.ocpus <= 2 && var.memory_in_gbs <= 12)
      error_message = "Blocked: A1 exceeds the 2 OCPU / 12 GB fail-closed ceiling."
    }
  }
}
