---
name: pattern-making
description: Draft and edit 2D garment pattern blocks and named-piece recipes from explicit measurements, with seam and dart checks, allowances, construction marks, and SVG/mm DXF exports. Includes a clothing construction knowledge base and bounded women's jacket/coat recipes. Use for pattern drafting, reference-photo construction analysis, ease, grading, and toile preparation; exported files do not establish fit or a simulated garment.
---

# Pattern making

Use `scripts/pattern.py` for geometry; load resources relative to this skill's directory, regardless of
working directory. Core drafting uses Python's standard library. Validated exports require **ezdxf and
Shapely**; optional PNG sheets require Pillow. See the repository README for installation and developer checks.

## Before drafting

- Establish the garment inventory, fabric, construction, body dimensions, finished design dimensions,
  and seam/ease contracts. The knowledge base covers more families than the executable recipes.
- For a photo, read [reference-analysis.md](references/reference-analysis.md) and
  [photo-to-pattern.md](references/photo-to-pattern.md). Without a measured coplanar reference, record
  relative landmarks and uncertainty. A guessed head/hand length is not calibration. Projected widths
  are not flat half-girths. Separate observed construction from design assumptions.
- Read [measurements.md](references/measurements.md). Personal fields override the **chosen/default**
  table, not an inferred nearest size. Save explicit body/back, arm, leg and rise lengths appropriate to
  the garment. `height` is not consumed and is rejected. Nominal bodies are assumptions, not wearer measurements.
- Read the relevant `references/techniques/` sheet and [ease.md](references/ease.md). A block is a starting
  point; it is not a finished shirt, jeans, T-shirt, or other complete garment.

## Executable scope

| Task | Starting point and boundary |
|---|---|
| Women's, men's, children's primitive blocks | `block skirt/bodice/sleeve/trousers/all`; indicative proportional tables |
| Glove primitive | Hand resolution and geometry remain available; default Trank/Thumb allowances fail CUT validation and are rejected |
| Personal block | `--measurements me.json --size 38`; records resolved dimensions and provenance |
| Standard grading | `--sizes 36,38,40`; personal measurements combined with `--sizes` are rejected, including gloves |
| Women's outerwear | `garment spec.json`; requires bust and waist dart landmarks. See [garment-spec.md](references/garment-spec.md); the existing velvet-coat allowance is rejected |
| Men's tee, shirts, knit vests, jeans/shorts | Appropriate no-dart/block starting point plus a dedicated named-piece recipe; no complete built-in recipe is claimed |
| Other constructions | Knowledge-base guidance plus explicit [piece format](references/piece-format.md); validate the construction on a toile |
| CLO3D transfer | Outline transfer only; internal-dart sewing topology is unsupported, so fitted shells are suppressed. No simulation or fit validation is implied |

Search construction knowledge with `python /path/to/skill/scripts/pattern.py kb search <words>` or
`kb show <id>`. Read `references/kb/INDEX.md` for the index. For sculptural sketches, read
[design-from-sketch.md](references/design-from-sketch.md).

## Draft and validate

For reusable component coordination and size extension, read
[workflow-and-components.md](references/workflow-and-components.md) and the executable
[schemas](references/workflow.schema.json). Use `scripts/workflow.py validate`, `export`, `extend`,
`verify` and `reexport` for its mandatory profile/inventory/paired-seam sidecar. This path accepts
untrusted structured analysis and authored named-piece recipes. For private offline catalog input, use
the explicit protocol below and read [size-catalog.md](references/size-catalog.md) for exact request
schemas, provenance and exit semantics. Neither module calls an image API or live PatternFast service;
offline data access is not permission for such calls. Bare `pattern.py piece` does not enforce or certify
an absent workflow sidecar.

### Catalog-to-workflow protocol

1. Record image/document identities, observed construction, relative landmarks, uncertainty and individually
   sourced hidden-construction assumptions in `analysis`. Image analysis is an untrusted proposal. Without
   measured coplanar calibration, preserve ratios rather than inventing cm or body girths.
2. Pin the private normalized catalog with `size_catalog.py ... pin --manifest-sha256` using an independently
   retained expected hash, then run `audit`. In Python use `Catalog.load(root, lock)` and
   `catalog.resolve(request)`. Select exact `template_id` and `mannequin_id`, never a title, size label or
   nearest row. Custom requests have a separate `target_id`, explicit values/units/provenance, and an
   optional exact `base_mannequin_id`; preserve inherited values and never relabel a custom target as standard.
3. Declare the dedicated recipe's complete required input contract and call `catalog.project(profile,
   request)`. Map exact parameter UIDs and landmarks, selecting `raw`, `display_cm` or `display_in` explicitly.
   A numeric captured display can supply its recorded unit while the original raw unit remains null.
   Explicit custom overrides use their supplied value/unit via `raw`, not the old base display. The adapter
   performs no physical conversion and rejects display text as an engine value. Unknown raw units need an
   individually sourced `unit_interpretation`; independent missing dimensions need separate assumptions
   with value, unit, landmark, kind and provenance. Individually documented engineering estimates may
   supply initial-toile dimensions, with their assumptions and uncertainty retained; never present them
   as source measurements. Do not silently infer units or landmark equivalence from number magnitude.
   Inspect `missing_inputs` and each reason; incomplete projections
   exit 3 and cannot supply a draft. Schema/identity/binding errors exit 2. Exit 0 is not anatomy approval.
4. Preserve the full original profile, projection, source IDs, unit/status records and hashes privately,
   including every unmapped field. Verify them with `verify_profile` / `verify_projection` and externally
   retained expected hashes. Build the workflow's narrower cm/mm body subset only from supported projected
   inputs. Compare every supplied workflow value, unit and UID against the projection; declare any conversion
   and its provenance separately. Do not silently feed defaults through the bare block/garment CLI.
   Use one shared resolved body across an outfit and the same `profile_id` for all components of a proposal.
   Across separate garment proposals, retain the same body identity/hash and check overlapping projections
   agree. Finished dimensions and ease remain separate per garment.
5. Freeze finished lengths/girths, ease, material assumptions and construction/allowance targets before
   geometry. Use typed `design.constraints` to relate body and finished quantities. Author a dedicated
   parametric named-piece `recipe` with exact inventory, `depends_on`, cut quantities, paired ports and
   landmarks. Disclose unused workflow parameters/dimensions in `unused` with reasons; keep unsupported
   full-catalog fields in the original private profile rather than coercing them into body lengths.
   Family/style blueprints and knowledge sheets are inventory guidance, not whole-garment implementations.
6. Keep `profile.template.rule_state: external-unintegrated` and `custom_allowed: null` for external data.
   Declare only the projected parameter subset and its units in the workflow template; this is not a copy
   of unknown raw-unit metadata. An exact standard selection uses its model ID as `row_id` and freezes that
   projected row; custom selection is `custom-target` with no `row_id`. Retain the separate catalog target
   identity and base model in private evidence. Missing universal ranges, increments, precision or cross-field
   rules remain unavailable; observed extrema and captured sample rules cannot become global limits.
7. Run `workflow.validate(proposal)`, then `export_workflow(proposal, fresh_out)` and
   `verify_bundle(bundle_path)` (or the corresponding CLI commands). `proposal-ready` is not a saved export.
   Require actual saved SVG/mmDXF port, deduction, paired-seam and landmark readbacks at the original 1 mm
   tolerance, plus quantities, marks, CUT/SEAM geometry and units. For a new size, resolve/project its own
   body target and recheck all projected inputs. For declarative recipes, supply every frozen parameter
   and design dimension to `workflow.extend(proposal, target)`, then export and verify again. A supported
   procedural recipe may instead rebuild the complete proposal through its parameterized entry point;
   retain that generator's source hash, declared input coverage and joint receipt, rerun all saved-file
   checks, and compare cross-size allowances, marks, inventory and dependent components. Do not pretend
   `extend` can propagate a body change through already-resolved literal coordinates. Report fields the
   garment recipe cannot model explicitly; never silently ignore a required input. Neither changing a
   size label nor stretching the whole drawing is size extension. Reexport only through the verified
   workflow bundle.
8. Keep a private joint receipt binding the original lock, source evidence, catalog profile/projection,
   workflow profile/design/recipe and exported artifacts. Workflow bundles hash their complete proposal,
   geometry/export sources and schema; they do not natively replay catalog projections or store a dedicated
   catalog custom-target identity. Use existing `source`/analysis provenance strings to bind retained hashes
   and a caller-side replay/input comparison to check that boundary. Do not add unsupported schema fields
   or replace original catalog hashes with workflow hashes. Hashes establish consistency, not source
   authorship, anatomy, brand permission, sewability or physical fit. Report an unsupported mapping/contract
   as a gap instead of bypassing checks.

Keep real catalog data, locks, requests, full profiles, projections and orchestration evidence outside the
public repository. The exercised private composition is a small synthetic attachment coupon using a real
numeric-display-backed standard and an explicit non-grid custom target. It does not automatically provide
complete garment recipes; each garment still needs its own recipe and visual/toile review.

### Synthetic controls and drafting checks

Exercised synthetic controls (from the repository root, with an existing export-capable interpreter):

```sh
python skills/pattern-making/scripts/workflow.py validate tests/fixtures/workflow/top.json
python skills/pattern-making/scripts/workflow.py export tests/fixtures/workflow/top.json --out /tmp/workflow-top
python skills/pattern-making/scripts/workflow.py verify /tmp/workflow-top/workflow-bundle.json
python skills/pattern-making/scripts/workflow.py extend tests/fixtures/workflow/top.json --target tests/fixtures/workflow/custom-target.json --out /tmp/workflow-custom.json
python tests/run_workflow_controls.py --out /tmp/workflow-controls
```

Use fresh output paths. These fixtures are attachment coupons across construction families, not
complete garments. `proposal-ready` is distinct from `exported-2D-verified`; physical fit remains
unapproved. Catalog-to-workflow composition requires the caller checks above; user garment regeneration
requires separate work.

1. Print the body table with `measurements --body women --size 38`, then supply measured/selected
   overrides in a JSON file. Unsupported keys fail rather than silently disappearing.
2. Draft a block, supported outerwear spec, or explicit named-piece recipe. Coordinates in editable
   JSON are **cm**; glove `hand` fields are the documented **mm** exception.
3. Use `pivot` and `smooth` only when the affected construction marks and constraints are reviewed.
   Reexport edited JSON with `piece edited.json --out fresh-folder`; saved pass flags are not trusted.
4. Read every check. Ordinary sides and dart legs require zero ease within **1 mm**. Sleeve-cap,
   back-shoulder, elbow or other intentional ease must have an independent construction/material
   contract. Never calculate the permission to ease from the mismatch being tested.
   Boundary dart legs must use straight edges: `c` is rejected on the incoming mouth node and the
   dart apex, including collinear Bezier controls. Curved adjacent seams remain supported.
5. Validate SEAM and final CUT paths, including export precision and DXF readback. Allowance requests
   that self-intersect are rejected; the exporter does not silently repair a polygon or discard islands.
6. Reopen exports and check construction marks, quantities, grain, named seams and declared dimension/
   ratio constraints. Test ranges must come from the design contract, not the generated output.
7. Use a toile to assess fit and construction. A passed geometric check is not production or fit approval.

## Outputs and failure behavior

Use a fresh output directory. Validation stages files before publication. A rejected bundle has only
editable diagnostic JSON, seam tables and checks under `rejected/`; it has no final SVG/DXF/CLO3D bundle.
Source input files remain untouched by export. `pivot`/`smooth` edit their input unless `--output` is used.

- `pattern.svg`: every size's CUT/SEAM, holes, construction marks and quantities, with a size/color
  legend for grading. Physical mm and matching viewBox scale; print at 100% and measure the 10 cm square.
- `pattern_<size>.dxf`: modern R2010, `$INSUNITS=4`, numeric mm. Layers: CUT, SEAM, DART, INTERNAL,
  BUTTON, FOLD, NOTCHES, GRAIN, TEXT. Buttons are placement crosses, not holes or button diameters.
- `pieces_<size>.json`: cm geometry, construction marks, seams/holds, body provenance, and optional
  `proportion_contract`. Reexport recalculates validation.
- `seams_<size>.md`: named seam checks where declared. Absence of a seam declaration is not proof of assembly.
- `clo3d_<size>.json/.py`: only where supported; outline transfer with named seams. See
  [clo3d.md](references/clo3d.md). Fitted pieces with internal darts never receive an equivalent-shell claim.
- `python /path/to/skill/scripts/sheet.py folder/pieces_<size>.json`: PNG review sheets using the same
  construction marks as SVG/DXF. Print the SVG, not the PNG, for 1:1.

For allowances and finish choices read [finishes.md](references/finishes.md); for transformations read
[transformations.md](references/transformations.md). If execution is unavailable, label manual drafts
unverified and do not report automated checks as passed.
