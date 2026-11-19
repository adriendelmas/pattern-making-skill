# Template bank

Typical pieces drafted as parametric shapes by `scripts/templates.py`, from the numbered steps of the technique
sheets. Each template states its source; "method sheet" means trade practice drafted from the sheet, and its outline
has not been checked against a published pattern: compare before relying on it, and replace it with a digitised
shape when a real pattern is available: `python scripts/pattern.py digitize` writes it to `data/shapes/` and
`python scripts/pattern.py shape <id>` draws it (as the Bolton thumb, `data/shapes/bolton-thumb.json`).

```
python scripts/pattern.py template list
python scripts/pattern.py template show shirt-cuff
python scripts/pattern.py template draft shirt-cuff --param wrist=17 --param french=true --out folder
```

A draft writes the usual files (SVG, DXF, `clo3d_one.json`, `pieces_one.json`) and prints the edge lengths. To use
a template in a garment, copy its pieces into the garment recipe (`references/piece-format.md`) and write the seams
to the pieces it joins; the template's notes say which edge goes where.

| Template | Pieces | Parameters | Source |
|---|---|---|---|
| `peter-pan-collar` | flat collar, half on the fold | body, size, width, overlap, tip_radius | sheet 2.1 |
| `sailor-collar` | V front band and square back flap | body, size, v_depth, width, back_depth, overlap | sheet 2.1 |
| `tie-collar` | one band with ties | neck, ease, width, tie, end | sheet 2.8 |
| `shirt-cuff` | barrel or French cuff | wrist, ease, overlap, height, radius, french | sheet 1.19, kb mens-shirt-cuff |
| `tower-placket` | over and under placket | slit, over_width, under_width, point | sheet 1.20 |
| `continuous-lap` | placket strip | slit, finished | sheet 1.20 |
| `casing-band` | elastic or drawstring casing | waist, ease, elastic, height | sewing sheet |
| `patch-pocket` | patch with self facing | w, h, radius, pointed, facing | sewing sheet |
| `flap` | pocket flap | w, depth, radius, pointed | kb flap-pocket |
| `bellows-pocket` | pleated patch and its flap | w, d, pleat, hem, flap | kb bellows-pocket |
| `storm-flap` | double flap on the fold | w, depth, radius | kb storm-flap |
| `gusset-diamond` | underarm gusset | side | sheet 1.6 |
| `godet` | circle sector | length, hem, top_width | skirts sheet |
| `three-piece-hood` | two sides and a centre panel, seams split edge to edge | height, depth, radius, neck, panel_top, panel_nape | sheet 2.10 |
| `fly` | J fly facing and fly shield | zip, width, shield | kb mens-trouser-fly-waistband |
| `shirt-yoke` | yoke and lower back cut from the block | body, size, cb_depth, arm_below | kb mens-shirt-yoke |

Constructions drafted in place by `garment` (not templates): notched lapel, stand and funnel collars, shirt collar
with stand, convertible collar, two-piece hood, two-piece, one-piece, raglan and kimono sleeves, patch, in-seam,
welt and jetted pockets, facings, linings (`references/garment-spec.md`). Blocks: `block` (skirt, bodice, sleeve,
trousers, circle skirt, glove). Straight bands (waistbands, stand collars, cuffs sewn to known edges): `band` in a
recipe.

Adding a template: a function in `scripts/templates.py` registered with `@template(id, params, doc, source)`,
returning `{"pieces": [...], "seams": [...], "notes": ...}` in the piece format; run `template draft` and read the
report (crossing, fold angles, seams) before publishing it.
