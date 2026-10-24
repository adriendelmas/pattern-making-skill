# Private offline body catalog and explicit profiles

`scripts/size_catalog.py` is a standalone Python standard-library adapter. Its JSON interface can be consumed by a later workflow integration. It does not call a website, import data as code, run drafting geometry, or authorize geometry export. Keep catalog files, locks, requests, profiles and CLI output in private storage. The repository contains only the generic adapter and invented test records.

## Pin the selected data

The input is the normalized audit format: `templates.jsonl`, `sizes.jsonl`, `measurements.jsonl`, `parameter_catalog.json`, `field_rules.jsonl`, and `sources.json`. `artifact_hashes.json` is an array of `{name, bytes, sha256}` entries. Obtain its expected SHA-256 from an independently retained audit receipt. Pinning checks that hash, verifies the six selected files, and validates their schemas and relationships. Unselected artifacts are never opened. Every manifest path is checked for absolute paths, traversal and symlink escape.

```sh
python scripts/size_catalog.py --catalog "$CATALOG_DIR" pin \
  --manifest-sha256 "$AUDIT_MANIFEST_SHA256" > "$CATALOG_LOCK"

python scripts/size_catalog.py --catalog "$CATALOG_DIR" --lock "$CATALOG_LOCK" list
python scripts/size_catalog.py --catalog "$CATALOG_DIR" --lock "$CATALOG_LOCK" \
  show --template-id "$TEMPLATE_ID"
python scripts/size_catalog.py --catalog "$CATALOG_DIR" --lock "$CATALOG_LOCK" \
  select --template-id "$TEMPLATE_ID" --mannequin-id "$MANNEQUIN_ID" > "$PROFILE_FILE"
```

Commands above assume the skill directory as the working directory. All outputs are UTF-8 JSON on stdout except `audit`, which streams JSONL. Exact template IDs and mannequin IDs are required. Titles and size labels are display text, including numeric-looking labels; the adapter never uses them to choose a model. It does not resolve ambiguous category links or infer chart equivalences.

The lock has discriminator `size-catalog-lock/v1`, the original manifest hash, the selected file hashes/lengths, and independently computed counts. Loading verifies selected bytes against this lock on every CLI invocation. `sources.json` supplies bound provenance metadata; original source files, database queries, URLs and historical messages are **not reopened or reverified**. A raw-record hash is retained as audited provenance, not represented as a newly recomputed hash of the absent raw source object.

## Explicit requests

Python entry points are `pin_catalog(root, manifest_sha256)`, `Catalog.load(root, lock)`, `catalog.resolve(request)`, `resolve_many(requests)`, `verify_profile(profile, expected_sha256=None)`, `project(profile, request)`, `verify_projection(result, expected_sha256=None)`, and `audit()`. They return fresh plain JSON-compatible values. Invalid schemas, identities or bindings raise `CatalogError`.

A standard request has exactly these fields:

```json
{
  "schema": "size-catalog-request/v1",
  "operation": "standard",
  "template_id": "<exact-template-id>",
  "mannequin_id": "<exact-mannequin-id>",
  "rule_sample": null
}
```

A custom request has exactly these fields:

```json
{
  "schema": "size-catalog-request/v1",
  "operation": "custom",
  "template_id": "<exact-template-id>",
  "target_id": "my-independent-target",
  "target_label": "My explicit proposal",
  "base_mannequin_id": "<exact-base-mannequin-id>",
  "measurements": [
    {
      "param_uid": "<exact-parameter-uid>",
      "value": 12.375,
      "unit": "cm",
      "provenance": {
        "source": "user:proposal-not-a-measured-person",
        "method": "Explicit illustrative target value"
      }
    }
  ],
  "rule_sample": null
}
```

With an explicit base, the measurement list overrides only fields belonging to that base. All other base fields are independently inherited into the resulting profile. A target ID must differ from every stored mannequin ID. The result has `kind: custom`, `standard_model: null`, a separate `base_model`, a target identity, the original request and an overrides hash. It never claims the custom target exists in the source catalog, even if its values equal a stored row.

With `base_mannequin_id: null`, every field observed anywhere in the selected template must be supplied. This is the adapter's explicit completeness convention, not a recovered website requirement. There is no implicit base, interpolation, nearest-size choice, default size or grading increment.

Custom values must be finite JSON numbers, excluding booleans and numeric strings. Length/circumference fields must be positive as an **adapter input policy**. Website-defined body-shape scalars require only a finite number: zero is supplied data, and the adapter invents no sign/range/enum restrictions. Every explicit value needs a nonempty unit label and `{source, method}` provenance. Unit labels are preserved verbatim; their physical meaning is not certified. Unknown units in inherited source fields remain unknown. No magnitude-based unit inference or physical unit conversion occurs.

```sh
python scripts/size_catalog.py --catalog "$CATALOG_DIR" --lock "$CATALOG_LOCK" \
  resolve --request "$REQUEST_FILE" > "$PROFILE_FILE"
python scripts/size_catalog.py --catalog "$CATALOG_DIR" --lock "$CATALOG_LOCK" \
  resolve-many --request "$BATCH_FILE" > "$BATCH_OUTPUT"
```

The batch request is `{ "schema": "size-catalog-batch-request/v1", "requests": [...] }`. Output uses `size-catalog-batch/v1` and `profiles`. Duplicate target/model identities fail the entire batch. Each profile is separately resolved and hashed; one target never supplies another target's inherited values.

## Profile, units and separate checks

`size-catalog-profile/v1` carries the exact template, standard/base model identity, original request, catalog binding, measurements, source evidence, statuses and `profile_sha256`. Each measurement retains its original UID, label, parameter definition, selected value and JSON number type, unit/status, origin, and either the complete normalized `source_observation` or explicit user provenance. Origins are `standard`, `inherited` and `explicit`.

Captured display cm/in data stays inside `source_observation` with its own provenance. Raw units remain null if the source did not specify them, even when a separate display value exists. Decimal display strings and fractional-inch strings remain strings in recorded profiles. Numeric display text can be parsed for a same-unit range comparison, without replacing the stored text or converting units.

| Check | Result and meaning |
| --- | --- |
| `status.schema` | `checked`: exact supported structure and typed data |
| `status.identity` | `exact_stored_standard` or `explicit_custom` |
| `status.constraints.coverage` | `unavailable` without a selected sample; `partial` with captured sample rules |
| `status.constraints.universal` | Always `unavailable` in this format |
| `status.constraints.comparison` | `unavailable`, `within_selected_sample`, `outside_selected_sample`, or `boundary_unknown` |
| `status.units.status` | `complete`, `partial`, or `unavailable` for unit-label presence on selected values; not physical interpretation |
| `status.mapping` | `not_requested` on a profile; projection reports its own completeness |
| Anatomy / sewability | Always `not_assessed` |
| Geometry export | Always `not_authorized` |

There is no aggregate `valid` field. `parameter_catalog` observed minima/maxima are descriptive extrema, never permitted ranges. Its global limits must be null. The normalized model flag `full_field_rules_captured` means every field has a captured sample rule; it does not establish complete constraints.

To opt into a captured sample comparison, supply `rule_sample: {"template_id": "<exact-template-id>", "mannequin_id": "<exact-sample-id>"}`. The sample must have captured rules and belong to the requested template. This is an explicit comparison to that sample, even if the target inherits another model. No sample is chosen automatically. `select` accepts the same object via `--rule-sample FILE`.

Every comparison field retains its rule and source binding. Unsupported unit comparisons and absent fields remain unavailable. Known cm/in labels are compared only in that same unit. Equality with an endpoint is `boundary_unknown`; inclusivity, precision, steps and cross-field/server behavior remain unknown. The aggregate prioritizes outside, then boundary, then inside among comparable fields. Read field results and coverage alongside it: `within_selected_sample` never asserts all fields or other constraints passed.

## Explicit engine projection

Projection records an independently declared input contract. It neither discovers engine requirements nor integrates with an existing engine. An example request:

```json
{
  "schema": "size-catalog-projection-request/v1",
  "engine": "my-explicit-engine-contract",
  "required_inputs": [
    {
      "name": "body_length",
      "unit": "cm",
      "landmark": "<exact-source-label>",
      "kind": "length",
      "provenance": {"source": "user:engine-contract", "method": "Documented input definition"}
    }
  ],
  "mappings": [
    {
      "input": "body_length",
      "param_uid": "<exact-parameter-uid>",
      "source_value": "raw",
      "landmark": "<exact-source-label>",
      "unit_interpretation": null,
      "provenance": {"source": "user:landmark-review", "method": "Caller asserts identical landmarks"}
    }
  ],
  "assumptions": []
}
```

Every required input needs a name, unit, landmark, kind (`length` or `site_scalar`) and provenance. Each mapping needs exact source/target landmark equality, its own provenance, and a value selector: `raw`, `display_cm` or `display_in`. Existing unit labels must match exactly. Unknown raw units can only be filled by an explicit `unit_interpretation: {"unit": "cm", "provenance": {"source": "...", "method": "..."}}`; output labels this `caller_assumption`, while the source profile retains null units. Interpretation cannot replace an already known or explicitly supplied unit.

The adapter performs no conversion or representation coercion into engine inputs. Decimal-text displays and inch fractions produce `unsupported_value_representation`; unavailable displays produce `source_value_unavailable`. The original fields stay available in the projection's embedded profile and unmapped field list.

Shoulder width and shoulder diameter, back width and back length, bust-height datums, and front-length datums are distinct. Mismatched landmarks fail. Conventional `shoulder_width`, `shoulder_diameter`, `back_length` and `back_width` input names additionally require their corresponding exact labels. Ambiguous `front_length` and `bust_height` mapping names are unsupported; use a fully specified input datum or an individually sourced assumption. A shape scalar cannot map to a physical length. For an engine identifier of `pattern` or `pattern.py`, `height` is unsupported, including supplied assumptions; this adapter makes no height-scaling claim.

Missing arm length, rise, inseam, bust-point spacing, garment length or ease are never inferred. To supply an independent engine assumption, use an entry with exactly `{input, value, unit, landmark, kind, provenance}`. Its definition must match the required input and its provenance must explain that individual assumption. A field cannot have both a mapping and an assumption. These are caller declarations, not recovered body observations or independently approved engineering measurements.

```sh
python scripts/size_catalog.py --catalog "$CATALOG_DIR" --lock "$CATALOG_LOCK" \
  project --profile "$PROFILE_FILE" --request "$PROJECTION_REQUEST" > "$PROJECTION_OUTPUT"
```

`size-catalog-projection/v1` includes the full profile, request, `engine_values`, `missing_inputs` with reasons, `unmapped_measurements`, separate statuses and a projection hash. A complete mapping only establishes completeness against the caller's supplied contract. Geometry export remains unauthorized. Known sample rejections remain attached to the profile and retain a nonzero CLI exit code.

## Replay, coverage and exits

```sh
python scripts/size_catalog.py --catalog "$CATALOG_DIR" --lock "$CATALOG_LOCK" \
  check --profile "$PROFILE_FILE" --expected-sha256 "$RETAINED_PROFILE_SHA256"
python scripts/size_catalog.py --catalog "$CATALOG_DIR" --lock "$CATALOG_LOCK" audit > "$AUDIT_OUTPUT"
```

`check` accepts a profile or projection. It validates the hash, exact catalog binding and deterministic replay of the saved request. It rejects modified values, status claims, schema versions, operations and unexpected fields, including a rehashed result inconsistent with its request. Hashing uses sorted-key compact UTF-8 JSON with no NaN/infinity. Int/float types participate in the hash; object-key order does not. Keep an external expected hash to detect replacement of both a custom request and its completely re-resolved/rehashed result. Hashes bind bytes/content; they are not signatures proving who created a new request or lock.

`audit` yields one `template_batch` per pinned template followed by an `aggregate`. It resolves and replays every standard profile, compares every typed original observation, accumulates exact visited identities, and checks totals against the validated catalog. Each batch includes per-model profile and observation hashes. Coverage means the pinned saved catalog only, never current website coverage.

Exit codes: `0` means the requested record/check was completed; `2` means schema, identity, binding, parsing or I/O rejection; `3` preserves a resolved result with a selected-sample rejection or incomplete projection. Missing range knowledge alone permits profile recording with exit `0` and explicit unavailable statuses. Endpoint ambiguity is recorded, not treated as established invalidity. Consumers must inspect the separate statuses; no exit code approves anatomy, drafting or sewing.
