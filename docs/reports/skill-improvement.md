# Bounded pattern-making skill improvements

Date: 2026-10-24. Upstream: `adriendelmas/pattern-making-skill`, commit
`6587004c4c0495592d0a3947553b52e72f1e354c`, branch `feat/photo-proportion-validation`.
Changes are local and uncommitted. The MIT licence and original attribution are unchanged.

## Review corrections

Independent review reproduced two gaps in the earlier 44-test acceptance suite:

- Boundary dart checks compared endpoint distances even when a leg used a Bezier curve. Export now
  requires straight boundary dart edges. A `c` field on the incoming mouth node or dart apex is rejected,
  including collinear, overshooting and looping controls. Curved adjacent seams remain supported.
  This is a representation guard; no body geometry or dart construction was rewritten. Existing 1 mm
  leg and 2 degree folded-seam tangent tolerances are unchanged.
- Graded SVGs previously included only the first size's cuts, holes and construction marks. Every size
  now includes CUT/SEAM, holes, DART/INTERNAL/BUTTON/FOLD/GRAIN/NOTCHES paths and quantity labels.
  Size colors agree with the legend; cuts are solid and seams dashed. XML groups identify the size,
  piece and quantity, with safely escaped labels. Single-size coordinates and physical mm scale remain.

The installation examples consistently use the created virtual environment. Python **3.13.13** was
used for this correction; older Python versions were not tested. No dependencies were installed during
verification. The previous report was archived byte-for-byte in local review evidence before replacing
its private host links with this portable maintainer report. Repository tests require no private files.

## Verification

The new [focused regressions](../../tests/test_review_fixes.py) cover both dart legs, cyclic outline
indexing, collinear/overshooting controls, a valid straight-dart control, complete two-size SVG/DXF
coordinates, holes, quantities, escaped labels, single-size scale, and real CLI grading at sizes 34/40.
The synthetic panels move their marks separately for each size. Expected mark coordinates are written
explicitly, rather than obtained from the shared marker enumerator.

Before the production edits, the new tests reported **13 failed, 1 passed**. Four curved-leg CLI cases
incorrectly exited 0, six syntax guards failed to reject, and SVG tests exposed missing paths/metadata.
An additional pre-fix real-CLI run isolated the missing size-40 grain coordinates (**1 failed,
13 deselected**). After the fixes the focused suite reported **14 passed**.

The full current-code suite reported **58 passed** (44 existing cases plus 14 new cases). A fresh
regression runner completed **26 CLI checks: 17 exited 0 and 9 exited 2 as expected**, with **12 saved
DXF readbacks**. Its built-in `pattern.py test` command exited 0. These counts include measurement,
preview and rejection checks; they do not mean 26 successful garment generations.

Fresh original-case replays completed seven CLI checks (four exit 0, three expected exit 2) and one
two-size API export. Seven DXFs reopened without audit errors or fixes. The curved-dart input now exits
2 with no final SVG/DXF, while its straight control passes. Sizes 34 and 40 both contain their saved
cut/seam/grain coordinates. Both synthetic sizes contain all six construction-mark layers. Compared
with the prior saved positive controls, all seven DXFs retain identical modelspace entities and the
saved JSON retains identical geometry, marks and constraints. The straight control's SVG coordinates
are unchanged. Original review inputs and outputs were not overwritten.

The optional skill frontmatter validator could not start because PyYAML is absent from the supplied
environment. The frontmatter remains byte-identical to the prior version, and all local documentation
links were checked separately. This is not recorded as a stock-validator pass.

## Portable verification commands

Run from the repository root after following [README](../../README.md). Use new evidence directories
on every run; the regression runner refuses to overwrite an existing output folder.

```sh
export PYTHONDONTWRITEBYTECODE=1
review_dir=$(mktemp -d)
mkdir "$review_dir/tmp"
export TMPDIR="$review_dir/tmp"
.venv/bin/python -m pytest -q -p no:cacheprovider tests/test_review_fixes.py --basetemp="$review_dir/focused"
.venv/bin/python -m pytest -q -p no:cacheprovider tests --basetemp="$review_dir/full"
.venv/bin/python tests/run_regressions.py --out "$review_dir/regressions"
```

The runner invokes `pattern.py test`, the three unchanged example specs, body blocks and positive and
negative export controls. It records command arguments, actual and expected exit codes, and saved-file
readbacks in `results.json`. Successful negative checks are expected rejections, not generated garments.
CLI subprocesses run from temporary directories and invoke scripts by absolute path.

## Existing capabilities and limits

The earlier changes provide measurement resolution/provenance, independent seam and proportion
contracts, staged CUT/SEAM validation, R2010 mm DXF, construction marks, and editable JSON that retains
constraints for revalidation. The review corrections above close the two reproduced D2/D4 gaps within
that bounded 2D scope. Independent reacceptance remains a separate review step.

- Personal measurements combined with standard multi-size grading are rejected. Missing personal fields
  use the chosen/default table, not an inferred nearest size. `height` is unsupported; use explicit lengths.
- Ordinary sides and darts require zero ease within 1 mm. Intended cap/shoulder/elbow ease requires an
  independent amount and reason. Saved seam contracts are recomputed after editing; stored pass flags
  cannot bypass validation.
- Final CUT and SEAM must be simple closed paths, including rounded output and actual DXF readback.
  Export rejects invalid allowances without repairing polygons. Rejected bundles retain diagnostics
  under `rejected/` and publish no final SVG/DXF/CLO3D bundle. Existing deliverables are not overwritten.
- Both notched-jacket examples have successful 2D export controls. The existing velvet-coat allowance
  remains rejected for invalid CUT paths. Default glove allowances remain rejected; successful primitive
  or measurement tests do not establish a valid glove cutting bundle.
- Male/child whole-garment outerwear and bodies without required dart landmarks are unsupported.
  Primitive blocks remain separate from complete garment recipes.
- Internal darts remain in 2D exports. Sewn internal-dart topology is unsupported, so fitted CLO3D shells
  are suppressed. No CLO3D runtime, simulation, physical printer, CAD import or toile validation ran.
- Fitted front-lining darts can approach/cross the facing boundary and need recipe review before cutting.
  The neutral collar reference does not establish complete top/under-collar turn-of-cloth or lining assembly.
  Passing 2D checks is not production approval.
- Photo landmark constraints measure specified piece-point dimensions and ratios; they do not infer
  assembled girths, exact wearer measurements, or photo similarity. No photo-derived garment collection
  or new garment/platform feature was created in this correction.

See [piece format](../../skills/pattern-making/references/piece-format.md) for the export contract and
[photo-to-pattern](../../skills/pattern-making/references/photo-to-pattern.md) for design assumptions.
Detailed command receipts, preserved failures, source hashes and original-input replays are maintained
outside the public repository. No private images, measurements or log contents are embedded here.
