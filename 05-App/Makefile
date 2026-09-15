.PHONY: validate contracts pipeline api web demo dev clean

# CP0 -- run the frozen-contract validator with real teeth (self-test included)
validate:
	python3 contracts/validate.py
	python3 contracts/validate.py --self-test

# Generate pydantic + TypeScript types from the JSON Schemas.
# Eng review task T4: contracts/*.schema.json is the single source of truth.
# Never hand-edit api/src/nidhinetra_api/models.py or web/lib/contracts.ts --
# both are regenerated here.
contracts:
	uv run datamodel-codegen \
		--input contracts/normalized_record.schema.json \
		--input-file-type jsonschema \
		--output api/src/nidhinetra_api/generated/normalized_record.py \
		--class-name NormalizedRecord
	uv run datamodel-codegen \
		--input contracts/risk_scored_record.schema.json \
		--input-file-type jsonschema \
		--output api/src/nidhinetra_api/generated/risk_scored_record.py \
		--class-name RiskScoredRecord
	uv run datamodel-codegen \
		--input contracts/fund_flow_graph.schema.json \
		--input-file-type jsonschema \
		--output api/src/nidhinetra_api/generated/fund_flow_graph.py \
		--class-name FundFlowGraph
	cd web && npx json-schema-to-typescript ../contracts/normalized_record.schema.json > lib/generated/normalized-record.ts
	cd web && npx json-schema-to-typescript ../contracts/risk_scored_record.schema.json > lib/generated/risk-scored-record.ts
	cd web && npx json-schema-to-typescript ../contracts/fund_flow_graph.schema.json > lib/generated/fund-flow-graph.ts

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

clean:
	rm -rf data/interim/* data/raw/*
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
