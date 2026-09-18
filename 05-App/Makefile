.PHONY: validate contracts pipeline api web demo dev clean

# CP0 -- run the frozen-contract validator with real teeth (self-test included)
validate:
	uv run --package nidhinetra-pipeline python contracts/validate.py
	uv run --package nidhinetra-pipeline python contracts/validate.py --self-test

# F-20 (nemotronreview.md): code generation is NOT wired. The runtime types are
# hand-mirrored (web/lib/types.ts, web/lib/graph-data.ts; the API and the
# pipeline read records as plain dicts), and
# pipeline/tests/test_contract_type_drift.py fails when a mirror drifts from
# its schema. This target says so instead of pretending to generate files.
contracts:
	@echo "make contracts is not wired: types are hand-mirrored from contracts/*.schema.json."
	@echo "Drift is caught by pipeline/tests/test_contract_type_drift.py."
	@exit 1

# Acquisition ladder -> normalized cache in data/raw/ -> served snapshot in
# data/snapshot/ (F-12). It stamps data_as_of with the build time, so run it
# only right after a real `pull-live`.
pipeline:
	cd pipeline && uv run python -m nidhinetra_pipeline.cli build

api:
	cd api && uv run uvicorn nidhinetra_api.main:app --reload --port 8000

web:
	cd web && npm run dev

# the whole product, one command -- brings up API + web against the current
# snapshot, both logging to this terminal; Ctrl+C stops both together
demo:
	@trap 'kill 0' EXIT INT TERM; \
	(cd api && uv run uvicorn nidhinetra_api.main:app --port 8000) & \
	(cd web && npm run dev -- --port 3000) & \
	wait

dev: validate
	@echo "Contracts validated. Run 'make api' and 'make web' in separate terminals."

# Removes derived files only. Never touches data/raw/: it holds the original
# MPLADS captures (including the truncated expenditure capture and its
# salvaged copy), which are audit evidence and may not be re-downloadable
# (F-19). Deleting them needs a separate, deliberate step outside make.
clean:
	rm -rf data/interim/*
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
