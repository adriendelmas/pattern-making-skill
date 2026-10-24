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
untrusted structured analysis and authored named-piece recipes; it does not call an image API or
integrate a real catalog. It distinguishes selected standard rows, custom targets and unverified
external template rules. Bare `pattern.py piece` does not enforce an absent workflow sidecar.

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
unapproved. Real catalog integration and user garment regeneration require separate work.

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
