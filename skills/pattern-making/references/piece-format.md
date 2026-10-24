# Piece format

JSON format read by `python scripts/pattern.py piece file.json` and produced by the `block` command in
`pieces_<size>.json`. Units in cm. Axes: x towards the side, y downwards.

```json
{
  "title": "A-line skirt",
  "size": "38",
  "pieces": [
    {
      "name": "Skirt front",
      "cut": "1x on fold",
      "allowance": 1.0,
      "allowances": {"2": 3.0},
      "fold": [3],
      "outline": [
        {"name": "center_waist", "p": [0, 0]},
        {"name": "side_waist", "p": [20, -1], "c": [[22, 3], [25, 10]]},
        {"name": "side_hem", "p": [30, 60]},
        {"name": "center_hem", "p": [0, 60]}
      ],
      "notches": [{"edge": 1, "d": 20}],
      "grain": [[10, 10], [10, 50]]
    }
  ]
}
```

## Fields

- **`outline`**: the seam line, as nodes in order. The outline closes itself.
  - `p`: node coordinates.
  - `c`: makes the edge leaving this node curved. These are the two control points of a cubic Bezier
    curve towards the next node.
  - `dart: true`: the node is a dart point. The nodes just before and after are the dart legs. The cut
    line bridges the dart opening. Both boundary dart legs must be straight: omit `c` on the preceding
    mouth node (mouth to apex) and the dart node (apex to next mouth). Any Bezier definition on either
    leg is rejected, including collinear, overshooting or looping controls. Curved adjacent seams
    remain supported; curved dart closure is not implemented.
  - `name`: optional, to find your way.
- **Edges**: edge `i` runs from node `i` to node `i + 1`. The last edge returns to the first node.
- **`allowance`**: default seam allowance in cm. **`allowances`**: allowance per edge, key = edge number
  as text.
- **`fold`**: list of edges cut on the fold, without allowance. The CLO3D export unfolds the piece on
  the first one.
- **`notches`**: `edge` and either `d`, distance in cm from the edge start (negative: from the end), or
  `t`, fraction of the edge length between 0 and 1.
- **`grain`**: two points of the grain line arrow.
- **`cut`**, **`size`**: texts printed on the pattern.
- **`holes`**: closed inner cut-outs (thumb hole, design cut-outs), each `{"name": ..., "outline": [...]}`
  with named nodes like the outline. SVG and DXF draw them; the CLO3D export opens each one to the nearest
  outline node through a slit 1.5 mm wide, to be sewn back (`node` / `node~` pairs), because the API
  cannot cut a hole.
- **`within`**: name of the piece this one is cut from (facing, interfacing, pocket facing; not a lining, larger by design). The export
  checks that it lies inside that piece, up to 0.6 cm (turn of cloth). For mirrored pieces, `L` matches `L`.
- **`mirror: true`**: the piece is cut as a left and right pair. The export writes `<name> L` and its mirror
  `<name> R` (same node names, same winding).

## Seams (any garment, as data)

A file read by `piece` may carry a top-level `"seams"` list. Each seam pairs two edges by node names, first
node to first node:

```json
"seams": [
  ["Back", "side_waist", "hip", "Front", "side_waist", "hip"],
  ["Sleeve {side}", "cap", "back_underarm", "Bodice back", "shoulder", "underarm",
   {"ease": 0.05, "why": "sleeve cap ease, set-in sleeve in wool"}],
  ["Collar", "c0", "c1", "Bodice back", "center_neck", "neck"]
]
```

- `{side}` in a piece name writes the seam once for `L` and once for `R` (mirrored pieces).
- **Law of reciprocal lengths**: two sewn edges are the same length within 1 mm. Any intended difference
  (cap ease, gathers, easing a back onto a front) is declared as `ease` (ratio, edge A = edge B x (1 + ease))
  with its reason in `why`. An undeclared difference is an error.
- For inserted pieces (gussets, thumbs, collars, godets), name matching anchor points on both pieces (A, B,
  C, D or descriptive names) and split edges at those anchors, so every seam is one edge to one edge.

On every export the engine checks, for every garment:

| Check | Rule | Output |
|---|---|---|
| Seam lengths | Within 1 mm, or the declared ease | `seams_<size>.md` table and a `!!` line per failure |
| Fold | The outline meets each fold edge at 90 degrees (2 degrees tolerance), so the unfolded piece has no point or dip | report line per fold corner |
| Outline | Never crosses itself | report line |
| Narrow passage | No chord under 4 cm splits the piece into two parts both over 40 cm² (a lining strip left between a facing and a seam). Narrow strips and protrusions such as fingers pass | report line |
| Within | A piece with `within` lies inside its piece, up to 0.6 cm | report line |

`python scripts/pattern.py clo3d clo3d_<size>.json --assemble` then sews every seam in CLO3D.

## Tips

- Start from a file produced by `block` rather than from a blank page.
- Keep node names: they make transformations readable.
- A regular curve has its control points at about one third and two thirds of the chord.
- For a curve to meet a fold edge at a right angle, place its last control point at the same height as
  the end node.
- The `piece` command prints the length of each edge: use it to check that seams match.


## Validated export contract

- Editable specs use cm and retain full coordinate precision, `seams`, `holds`, `construction`,
  `resolved_measurements`, provenance and `proportion_contract`. Reexport ignores stored checks/pass flags.
- `darts_in` is a three-point triangle (tip, mouth1, mouth2) or four-point fish dart
  (tip1, mouth1, tip2, mouth2). Each tip's two legs must match within 1 mm. Outline dart nodes retain
  `dart:true`; their legs and folded-seam tangent continuity are checked independently of seam declarations.
- `lines`, `buttons`, `fold`, `grain`, and `notches` share geometry across SVG/DXF/PNG. Buttons are placement
  crosses, not hole/diameter specifications. DXF uses DART/INTERNAL/BUTTON/FOLD/GRAIN/NOTCHES layers.
- Mirror transforms affect absolute internal marks and remap edge-indexed attributes. Fold expansion
  duplicates internal marks across the fold. Expanded JSON is not expanded a second time on reexport.
- `notches` accepts distance `d` (negative counts from edge end) or fraction `t` consistently in all formats.
- Final CUT and SEAM must be finite, nondegenerate simple closed paths, including exported precision.
  Offset failures are rejected without polygon repair. Use a smaller supported allowance or revise the
  design intentionally. Source input is preserved and failed bundles are stored under `rejected/`.
- DXF is R2010 with `$INSUNITS=4`; there is no implicit legacy R12 fallback. SVG's physical mm size and
  viewBox use the same scale. Verify the exported test square before printing/importing.
- Graded SVGs include every size's CUT/SEAM, holes, DART/INTERNAL/BUTTON/FOLD/GRAIN/NOTCHES paths
  and printed quantity text. Each size uses its legend color; CUT is solid and SEAM dashed. XML groups
  identify `data-size`, `data-piece` and `data-cut`; hole paths carry `data-hole`. User labels are XML-escaped.
- See `photo-to-pattern.md` for executable independent landmark dimension and ratio constraints.


Whole-seam contracts may use `seam_chains`: each entry has `a` and `b` lists of
`[piece, from_node, to_node]` adjacent edge references, `ease_cm` (default 0), and `why`. The summed
length difference must match independently chosen ease within 1 mm. These declarations are rechecked
on roundtrip and support `{side}` mirror expansion. `seam_reference_pieces` may hold explicitly named
construction references, such as the neutral collar before turn-of-cloth additions; they are not cut pieces.
