PYTHON ?= python3

.PHONY: patch-shim-mesh test-shim-mesh-isolated

patch-shim-mesh:
	$(PYTHON) scripts/patch_shim_mesh_top3_v2.py

test-shim-mesh-isolated: patch-shim-mesh
	ZERO_SPEND_MODE=HARD ARBM_ENABLE_LOCAL_VLM=1 ARBM_VALIDATION_SPEND_MODE=zero $(PYTHON) scripts/osworld_free_mesh_shim.py --test-isolated-run --run-id 35265789297 --task 091 --verify-budget --enforce-session-isolation
