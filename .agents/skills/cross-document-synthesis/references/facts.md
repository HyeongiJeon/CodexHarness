# Source facts and interpretations
The deterministic engine parses only complete source lines beginning `FACT ` followed by a JSON object. Required: entity (text), attribute (text), value (scalar text/number). Optional: unit, condition, applies_to, exception_to (text). Decimal JSON numbers retain exact precision. Each record inherits the document metadata attached by the index; status must be approved/effective/final/승인/시행 and effective_from must exist. Effective interval is [effective_from,effective_to). Different overlapping values or unit labels conflict; units are not automatically converted. Versions are reported; newest date alone never wins. Conditional alternatives remain explicit and are not automatically applicable.

Example real synthetic record:
`FACT {"entity":"LOT-42","attribute":"limit","value":120,"unit":"kg","condition":"urgent approved","exception_to":"limit"}`

This is a fixture/source-record convention, not a claim that arbitrary prose is automatically understood. Ordinary material stays in the pack and the provided Codex interprets it with citations plus independent audit. Distinguish source_record, user_requested_entity_attribute_binding and model inference. Do not promote a model-produced number into a source fact.

`data aggregate ... --config config.json > result.json` saves a calculation_contract. `evidence compare` reproduces it, compares original source hashes/counts/totals, requires explicit matching units and reports conditional applicability as missing evidence. It does not infer which business entity a CSV column represents.
