# pattern-making-skill

A 2D garment drafting skill for agents: proportional body blocks, named-piece recipes, construction
references, seam allowances, and validated SVG/DXF exports. The original upstream is
[adriendelmas/pattern-making-skill](https://github.com/adriendelmas/pattern-making-skill), licensed under MIT.

The knowledge base covers many garment families. Executable whole-garment recipes are a bounded set of
women's outerwear constructions; men's shirts/T-shirts, knit vests, and complete jeans need dedicated
recipes built from blocks and the piece API. Geometric validation does not establish fit. The existing floor-length velvet-coat spec is rejected
by CUT validation at its back neckline/facing; both notched-jacket examples pass 2D export.
Default glove Trank/Thumb allowances are also rejected; glove resolution/primitive tests passing does
not imply a validated glove cutting bundle.

## Install and load

Tested with Python 3.13; older versions have not been tested. Core drafting math uses the standard library. For validated export and optional
PNG previews, install in your own project environment:

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r requirements-export.txt
```

Ask Codex to read the local `skills/pattern-making/SKILL.md` and use its scripts by absolute path. No
installation into a global skill directory is needed. Agents that support skill directories may also
load/copy the `skills/pattern-making` folder through their usual setup. The existing Claude plugin
manifests are retained; no plugin or global configuration is changed by running the scripts.

## Run

```sh
.venv/bin/python skills/pattern-making/scripts/pattern.py measurements --body women --size 38
.venv/bin/python skills/pattern-making/scripts/pattern.py block all --body women --size 38 --out out-blocks
.venv/bin/python skills/pattern-making/scripts/pattern.py block bodice --measurements me.json --out out-personal
.venv/bin/python skills/pattern-making/scripts/pattern.py block bodice --body men --sizes 44,48,52 --out out-grading
.venv/bin/python skills/pattern-making/scripts/pattern.py garment skills/pattern-making/examples/notched-lapel-jacket/jacket_fitted.json --out out-jacket
.venv/bin/python skills/pattern-making/scripts/pattern.py piece recipe.json --out out-recipe
.venv/bin/python skills/pattern-making/scripts/sheet.py out-jacket/pieces_38.json
```

Choose fresh output directories. Personal measurements and `--sizes` cannot be combined. Missing personal
fields use the chosen/default indicative table, never an inferred nearest size. `height` is unsupported;
set explicit longitudinal dimensions. Resolved measurements and their input/table/derived provenance are
saved with blocks and garments. Photo proportions need a separate body/design contract; see
[photo-to-pattern.md](skills/pattern-making/references/photo-to-pattern.md).

| File | Meaning |
|---|---|
| `pattern.svg` | Every size's CUT/SEAM, holes, construction marks and quantities; color legend for grading. Physical mm; print 100%, verify the 10 cm square |
| `pattern_<size>.dxf` | R2010 mm (`INSUNITS=4`), reopened and audited; separate construction-mark layers |
| `pieces_<size>.json` | Editable cm geometry, original coordinates, seams/holds and measurement/construction metadata |
| `seams_<size>.md` | Declared seam checks within 1 mm or independently specified ease |
| `clo3d_<size>.json/.py` | Supported outline transfer only, not simulation/fit evidence |
| `rejected/` | Failed-check diagnostics; no final bundle is published |

Internal dart lines are preserved in 2D. Sewn internal-dart topology is not implemented for CLO3D, so
fitted shell export is suppressed. The upstream integration references remain available, but this
revision has **not** been tested in a CLO3D runtime. Validate garment fit and construction on a toile.

## Developer checks

The reusable [component workflow](skills/pattern-making/references/workflow-and-components.md) adds
strict [proposal/target/bundle schemas](skills/pattern-making/references/workflow.schema.json), explicit
body/template provenance, conditional component inventory, geometry-derived paired seams and hash-bound
verification/reexport. Named recipes use typed dimension expressions for coordinated size changes.
External catalog rules remain unintegrated; custom-target geometry checks do not establish brand compatibility.

These commands exercise invented attachment coupons with an existing export-capable interpreter:

```sh
python skills/pattern-making/scripts/workflow.py blueprints
python skills/pattern-making/scripts/workflow.py validate tests/fixtures/workflow/top.json
python skills/pattern-making/scripts/workflow.py export tests/fixtures/workflow/top.json --out /tmp/workflow-top
python skills/pattern-making/scripts/workflow.py verify /tmp/workflow-top/workflow-bundle.json
python skills/pattern-making/scripts/workflow.py extend tests/fixtures/workflow/top.json --target tests/fixtures/workflow/custom-target.json --out /tmp/workflow-custom.json
python skills/pattern-making/scripts/workflow.py export /tmp/workflow-custom.json --out /tmp/workflow-custom
python skills/pattern-making/scripts/workflow.py reexport /tmp/workflow-top/workflow-bundle.json --out /tmp/workflow-roundtrip
python tests/run_workflow_controls.py --out /tmp/workflow-controls
```

Choose fresh paths. The runner retains raw CLI logs, exact exit codes and saved SVG/mmDXF readbacks in
`results.json`. The controls cover four construction families and six attachment purposes; they are not
whole-garment recipes. Real catalog data and the six user garment regenerations remain separate integration.
Legacy bare-piece commands cannot certify a missing workflow sidecar. All exports remain 2D only and need
visual/toile review.

Install pytest in the same project environment. Tests call current code in temporary
folders and reopen actual exports; they have no dependency on private audit evidence.

```sh
.venv/bin/python -m pip install pytest
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider tests
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python skills/pattern-making/scripts/pattern.py test
```

See [the improvement report](docs/reports/skill-improvement.md) for reproducible checks,
intentional support limits, and example-command results. Scripts and reference paths work from an
unrelated current directory when invoked using an absolute path.

## Licence

MIT, see [LICENSE](LICENSE). Original copyright and attribution are preserved. CLO3D is a trademark of
CLO Virtual Fashion Inc.; this project is not affiliated with or endorsed by it.
