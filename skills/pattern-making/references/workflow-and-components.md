# Component workflow v1

`../scripts/workflow.py` coordinates explicit named-piece recipes using the existing `pattern.py` and
`validation.py` math. It does not contain a catalog adapter, image model, body estimator, garment block
replacement, new DXF exporter or whole-garment recipe library. Public examples under
`tests/fixtures/workflow/` are **synthetic attachment coupons**, not shirts, trousers or user garments.

The [JSON schemas](workflow.schema.json) describe proposal, size-target and bundle records. The CLI
executes these structural schemas with a bounded standard-library checker, then performs semantic and
geometry checks. Merely satisfying JSON Schema is insufficient for acceptance. Input objects reject
unknown fields, duplicate JSON keys, nonfinite/boolean numeric inputs and unsupported operations.

## State and pipeline

1. **Evidence analysis:** record source identities, visible construction, hidden-construction assumptions,
   relative landmarks, uncertainty and scale. GPT/image analysis is an untrusted structured proposal;
   it cannot execute code or supply trusted measurements/pass flags. No image-analysis API is called.
2. **Select a model/body profile:** freeze the explicit template/model identifiers, raw parameter UIDs,
   raw units, provenance and either an exact selected standard row or a custom target.
3. **Select finished targets:** freeze finished lengths/girths, ease, material assumptions and construction
   quantities before generating geometry. Link body and finished quantities through independent typed
   equality constraints where applicable. Use explicit back/arm/rise/leg lengths; height is not a geometry
   input and does not scale all components.
4. **Resolve inventory and attachments:** declare construction features, named components, cut quantities,
   per-component dependencies, seam ports, paired relations and landmarks. `validate --inventory-only`
   checks structure and reports missing roles before all components exist; it does not certify geometry.
5. **Generate and check:** evaluate the named recipe and recompute actual seam lengths and dimensions.
   `validate` can report `proposal-ready`, with `geometry_checked: true`; no files have yet been exported.
6. **Export and reopen:** `export` stages the existing core's SVG/mmDXF output, reopens JSON/SVG/DXF, checks
   every geometry/mark segment and quantity label, binds hashes, then publishes a fresh bundle.
   Only this path reports `exported-2D-verified`.
7. **Extend size:** `extend` creates a fresh proposal from a completely frozen target. Reevaluate every
   expression and every companion contract; then export and verify the new proposal. Changing a label is
   not size extension. Const geometry cannot silently satisfy an incompatible new attachment target.
8. **Review:** inspect visual construction and a physical toile. Every result remains
   `physical-fit-not-approved`; neither an inventory nor 2D verification proves sewing completeness or fit.

`assembly_scope: declared-attachments-only` applies to every result. An omitted seam cannot be discovered
from arbitrary 2D outlines. A catalog entry/knowledge sheet cannot claim to be a complete executable
recipe. `support` is `inventory-only`, `synthetic-attachment-control`, or `authored-named-piece-recipe`;
there is deliberately no automatic “complete garment” status. An inventory-only proposal cannot export.

## Analysis and explicit sizes

`analysis.sources` gives each photo/document an ID and identity. `observations` and `assumptions` are
separate arrays with `source_id`, `description`, and qualitative `uncertainty`. `landmarks` have a range,
unit and `observed`/`inferred` basis. In uncalibrated images only relative `ratio` landmarks are accepted.
`scale.kind: measured-coplanar` requires a named physical reference, measured length and perspective
handling. Its length must be strictly positive, use cm/mm, have kind `body_length` or
`finished_length`, and basis `observed`. A zero allowance, nominal target, or girth cannot serve as
this measured length reference. A head/hand estimate, declared height or projected width is not calibration. There is no
projected-width-to-half-girth conversion. Source descriptions are assertions to review, not authenticated
measurements or a claim that the software examined the source image.

Each concrete quantity has `value`, `unit`, `source`, `basis`, `kind`, and optional uncertainty `range`.
The frozen value must fall inside its range; ranges never widen the 1 mm seam tolerance. Accepted frozen
bases are `observed` (actual measurement), `nominal`, and `engineering-selected`. An `inferred` quantity
is unresolved and rejected for geometry: retain the inference under analysis, then explicitly select
an engineering target or acquire a measurement. Nominal/template dimensions can support a concrete
engineering choice without claiming an observed wearer size. Absolute ranges in calibrated image analysis
remain design evidence, not automatic body measurements.

Body quantities live in `profile.parameters`, additionally carrying raw `uid`. Finished design and
construction quantities live in `design.dimensions`. Kinds separate `body_length`, `body_girth`,
`finished_length`, `finished_girth`, `seam_allowance`, `closure_overlap`, `dart_takeup`, `pleat_takeup`,
`ease`, `shrink`, `stretch`, and `gather`. Lengths use cm/mm; material ratios use `ratio`. Lengths and
body dimensions must be positive; allowances/take-up may be zero, and signed ease is permitted only
with an independently fixed relation and construction/material reason. Bool, NaN and infinity are rejected.

## Template and custom-target provenance

`profile.template` retains `provider`, `model_id`, `template_id`, `source`, `parameters`, `standard_rows`,
`rule_state` and `custom_allowed`. Each parameter specification carries a raw `uid`, `unit`, `required`
flag and optional known `min`/`max`. No missing bound is invented. All selected row values must exactly
match the frozen parameter values in the declared raw units. UIDs and template/model identity survive
size extension unchanged; cm conversion occurs only during expression evaluation.

- `synthetic-declared` requires an explicitly `synthetic-*` provider. Supplied test rules and bounds are
  checked. The portable control row is invented, clearly labeled, and has no brand/size equivalence.
- `external-unintegrated` requires `custom_allowed: null`. It can preserve supplied records and check
  their structural/dimensional consistency but reports `*-template-rules-unverified`. It cannot certify
  actual PatternFast standard/custom compatibility. The real catalog adapter is a separate integration.

Results distinguish `selected-standard-row-*` and `custom-target-*`. A custom target has no `row_id`;
there is no nearest-size inference, three-size restriction or ±4 cm rule. A synthetic template with
`custom_allowed: false` rejects custom targets. External-unintegrated geometry may export while explicitly
retaining its unverified template status. That means its seam checks passed, not that a brand authorized it.

## Construction inventory

`blueprints` prints the supported inventory vocabulary. Families include tops (tee/vest/shirt), bottoms
(trousers/shorts/skirt), one-piece (dress/jumpsuit), and outerwear (jacket/blazer/coat/hooded). These are
construction blueprints, not whole-garment generators. New recipes use the same schema and APIs; choose a
base family/style and a new `recipe_id`, then name its components and geometry.

| Declared feature | Additional required roles |
|---|---|
| `paneling: front-back` | `front`, `back` |
| `paneling: alternative` | Every explicit `alternative_roles` entry |
| Set-in or raglan sleeves | `sleeve` |
| Neck facing / collar / collar-stand / hood / rib | `neck_facing` / `collar` / `collar` + `collar_stand` / `hood` / `rib` |
| Cuffs | `sleeve`, `cuff` (a missing sleeve declaration cannot silently omit the sleeve) |
| Waist band / facing / elastic | `waistband` / `waist_facing` / `elastic_casing` |
| Patch / inseam / welt pocket | `pocket` / `pocket_bag` / `pocket_bag` + `pocket_facing` + `welt` |
| Lining, placket, button/zip closure, band hem | `lining`, `placket`, `closure`, `hem_band`, respectively |
| Any `extra_roles` | Every declared entry |

`closure` means the drafted closure assembly (e.g. a fly/facing), not a paper pattern for purchased zipper
hardware. This version does not model a separate purchased-parts bill of materials. Features are explicit;
the software cannot infer hidden facings or sewing techniques from a photograph. Roles can span multiple
named pieces. Alternative paneling and extra roles extend inventory without hardcoding case IDs. Review
whether the declared features actually represent the intended construction.

## Recipe, common profile, and dependencies

All components reference exactly `profile.id`. Piece and node names must be unique in their namespaces;
component/port/attachment IDs cannot collide. Each piece has exactly one component owner. `pieces` records
an integer cut quantity and requires the matching `cut: "2x"` label. This wrapper accepts already explicit
named pieces; implicit `mirror`, `{side}` and on-fold quantity strings are rejected. Expand mirrored pieces
with the existing core before authoring a wrapper recipe. `fold` edges and their marks remain supported.

The recipe reuses the [piece format](piece-format.md), with supported fields enumerated by the schema.
Coordinates, allowances and mark dimensions are numbers in cm or typed expressions; there is no executable
Python, shell, `eval` or `exec` in a recipe. Example:

```json
{"op":"add","args":[
  {"op":"param","id":"body.chest"},
  {"op":"param","id":"finished.chest_ease"}
]}
```

Expressions support `param`, `literal` (`value` + cm/mm/ratio `unit`), and binary `add`, `sub`, `mul`, `div`.
Addition/subtraction require matching dimensions. Multiplication needs a scalar operand; division may
produce length or ratio. Squared/inverse lengths, unknown references, division by zero and excessive
nesting are rejected. A recipe coordinate must resolve to length; notch `t` must resolve to ratio.
Body/finished constraints use the same operations and compare frozen values independently of geometry.

Notch distances retain the core's signed cm semantics: positive `d` walks from the edge start,
negative `d` counts from its end, and `t` must lie in `[0,1]`. Distance admission uses the edge's
64-sample length `L`. If `abs(d) > L`, the only compatible value is exactly `round(L,3)`, matching
`garment.notch_on`'s 0.001 cm storage precision. This permits a rounded endpoint to overshoot by
at most half that quantum (subject to binary floating-point rounding). There is no comparison
epsilon or general overshoot allowance, including between `L` and its rounded endpoint. Out-of-range
values one representable float beyond the rounded endpoint still reject. The recipe's notch values are
preserved; the unchanged core places them using its existing endpoint clamping and writer sampling.
This admission rule does not use the separate 1 mm sewing tolerance.

`component.depends_on` must exactly enumerate the parameter references found in that component's piece
expressions. Every supplied body/design dimension must be consumed by geometry, a frozen constraint,
port/deduction/relation target, or explicitly listed in `profile.unused` / `design.unused` with a reason.
An unused field is disclosed, never silently treated as consumed. Fixed literal cm dimensions are authored
engineering selections, not inferred body scaling. Every bundle binds the entire profile/design/recipe.

`extend` requires every current profile parameter and design dimension in the target; it does not merge
partial dimensions. It preserves template identity, recipe, inventory, material, explicit dependencies,
construction targets and allowances. Changed lengths evaluate only the expressions that depend on them;
resolved default and explicit per-edge allowance values, including the effective fold/seam/hem values,
must remain unchanged across sizes. This is checked after resolving expressions, even if the named
`seam_allowance` dimension itself did not change. Constant-valued expressions remain supported.
All companions and paired seams are then checked anew. A redesign of take-up/overlap/material/allowance
needs an explicit new proposal, not a size extension. Notch dimensions retain the core's fixed mark size;
constant mark positions in the controls remain unchanged.

## Geometry-derived paired contracts

Each port owns an ordered `chain` of adjacent named edge references (`piece`, `from`, `to`) on its own
component. Reversed edges are supported. Same-piece consecutive edges must join; cross-piece references
explicitly sum assembled segments. No nearest-edge/name guessing occurs. Edge lengths come from
`pattern.edge(...,64)` and `pattern.length`, including Bezier curves, during proposal validation.
Export/verify recompute them from the actual saved representation as described below. One geometric edge cannot be reused
by different ports. Use separate explicit pieces/ports when cut copies need different attachments.

Ports declare a frozen finished target, positive assembly quantity, purpose, deduction records, and named
landmarks at chain boundaries (`after: 0` is the start). Cut quantities bound assembly quantities. Paired
ports must have equal assembly quantities, matching purpose, and identical ordered landmark inventories.
Each port must be paired exactly once. Conditional sleeve/neck/cuff/waist/closure/pocket-bag companions
must expose an appropriate port. A cuff-only coupon may isolate the sleeve's cuff port; it still cannot
claim a verified sleeve-cap joint. Full authored recipes require the sleeve armhole port.

Relations pair sleeve-cap/armhole, collar/stand/rib/hood/neck, sleeve/cuff, waist/waistband, front closures,
and pocket openings/bags/facings through this one implementation. Ordinary relations are equal within
**1 mm**, consistent with the existing core. Intentional `ease` requires a fixed signed cm delta;
`stretch` and `gather` use a fixed **A/B multiplier**, not percent stretch. Every non-equal relation names
its target, material ID and independent construction reason. A and B's frozen targets must agree with the
relation before the measured lengths are compared. The validator never infers permission from mismatch.
Side and inseam purposes only permit equality. Shoulder and closure also permit explicitly declared
`relation.mode: "ease"` for intentional shoulder ease and closure/facing turn-of-cloth, respectively;
their purpose remains `shoulder` or `closure`. Stretch and gather remain unsupported for these four
purposes. Shoulder/closure ease requires the same nonblank `reason`, matching `material_id`, and
named target of kind `ease` with cm/mm length units as other ease relations. The signed delta is
independently specified as A minus B; both ports retain their separately frozen length targets.
No mismatch supplies implicit permission, and measured port, pair, and landmark residuals retain
the 1 mm limit during validation and saved DXF/SVG verification and reexport.
For nonuniform easing/gathering,
split into separate independently contracted ports: within a port, landmark correspondence distributes
the fixed delta proportionally to B's frozen target.

Sewn girths are explicit sums, not raw bounding-box widths. A `deductions` entry names a chain segment,
independent target and construction source. The supported straight-seam closure forms are:

- `pleat` or `overlap`: subtract the actual distance between named span endpoints on that straight
  segment. A whole segment may collapse to zero effective length while the complete port remains positive.
- `dart`: subtract the measured mouth of a referenced `darts_in` triangle/fish dart via `dart_index`;
  the mouth must lie on the straight attachment segment, and existing dart-leg checks still run.

The target kind must match the deduction. Duplicate/overlapping spans, deductions on curved seams,
unsupported projection/closure formulas, and boundary-dart-leg attachment measurements fail. Boundary
darts remain supported by the core's straight-leg validation, but the wrapper does not invent their sewn
attachment topology. A fish dart wholly inside a panel is not a boundary deduction. Reports expose raw
geometry-derived effective lengths and deducted cm. Allowances are never included in seam length.

## Export, verification and reexport

A successful fresh bundle contains `pattern.svg`, `pattern_one.dxf`, `pieces_one.json`, `workflow.json`,
and `workflow-bundle.json`. The DXF is the existing R2010/mm exporter, not a new writer. This workflow
suppresses CLO3D shell transfer because its scope is 2D. The sidecar binds exact SHA-256 values for the
four artifacts, canonical proposal content, current geometry/export modules, workflow code and schema.
Artifact paths are a fixed local allowlist; missing files, symlinks, missing discriminators and unknown
statuses fail closed. Source changes require regeneration.

`verify` always regenerates the recipe, recomputes inventory/edges/targets, compares saved JSON geometry,
and rereads SVG/mmDXF. It compares every CUT/SEAM/hole/mark segment, all piece quantities/text, mm units,
SVG viewBox scale and the 100 mm test square. SVG must match the fixed single-size writer's element tree,
attributes and values, including label positions and rendering properties. DTDs, processing instructions,
scripts, events, foreign elements, transforms, styles, altered viewports and references are unsupported.
The writer uses no references, so local references are also rejected. Checking uses inert XML parsing;
it never opens a browser or loads referenced resources.

DXF LINE/TEXT entities must be planar (zero Z) and have only the writer's supported properties.
Text content, insertion position, layer and height bind each piece/size/quantity role; layer, text-style
and linetype overrides are rejected. Verification does not interpret general CAD semantics.

After binding this format, verification reconstructs named edge chains and deduction mouths from
the actual parsed DXF endpoints and SVG polygon/polyline points. It reruns every port target,
geometry-derived deduction, paired relation and landmark comparison independently for both formats.
The core writer uses **16 segments per curve and coordinates rounded to 0.001 mm**. No tolerance is
widened: output that cannot satisfy the original **1 mm** contract is rejected before publication,
even when the recipe's 64-sample proposal check passes. The unchanged core/exporter is not refined.
`readback.saved_contracts.dxf` and `.svg` identify representation, units, coordinate precision, tolerance,
ports and attachments. Export/verify's top-level port/attachment measurements use the saved DXF chains
in cm; proposal results identify their distinct recipe measurement basis. Stored pass results and
recipe measurements are not proof of saved-file contracts. Reexport verifies its source before writing.
Mutating a bound file
fails the hash check; rebinding a changed geometry file still fails geometry/readback checks. Hashes detect
bundle drift, not malicious authorship: someone replacing the entire proposal and every binding creates
a different contract. There is no signature, external source authentication or production authorization.

`reexport` accepts only a valid `workflow-bundle.json`, verifies the source bundle first, and creates a new
bundle with the same complete proposal and contracts. Bare `pattern.py piece` files do not carry/enforce
these sidecars. Editing a verified workflow requires a new proposal and export; a bare piece reexport
cannot claim workflow verification. Existing legacy CLI behavior is unchanged.

## Exercised commands

Use an existing interpreter with the repository's export dependencies. From the repository root, with
fresh output paths (the runner records its actual absolute interpreter/script paths and exit codes):

```sh
python skills/pattern-making/scripts/workflow.py blueprints
python skills/pattern-making/scripts/workflow.py validate tests/fixtures/workflow/top.json
python skills/pattern-making/scripts/workflow.py export tests/fixtures/workflow/top.json --out /tmp/workflow-top
python skills/pattern-making/scripts/workflow.py verify /tmp/workflow-top/workflow-bundle.json
python skills/pattern-making/scripts/workflow.py extend tests/fixtures/workflow/top.json --target tests/fixtures/workflow/custom-target.json --out /tmp/workflow-custom.json
python skills/pattern-making/scripts/workflow.py export /tmp/workflow-custom.json --out /tmp/workflow-custom
python skills/pattern-making/scripts/workflow.py reexport /tmp/workflow-top/workflow-bundle.json --out /tmp/workflow-roundtrip
python tests/run_workflow_controls.py --out /tmp/workflow-controls
PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider tests
```

All commands can run from an unrelated current directory using absolute input/script paths. CLI success
is 0, invalid input/export/verification is 2. `proposal-incomplete` from the explicitly requested
`--inventory-only` report exits 0 and clearly lists missing roles; normal validate/export rejects it.
The control runner preserves raw stdout/stderr, exact argv/cwd/exit codes, artifact hashes and reopened
readbacks in `results.json`. Its inputs span four construction families and six attachment purposes.
The changed target is 237 mm versus the synthetic 200 mm standard row: companion edge geometry changes,
while depths, allowances and constant marks do not globally scale.

Actual catalog import, real construction recipes and regeneration of the six user garments remain later
integration work. Tests of these invented coupons cannot substitute for that work or visual/toile review.
