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
    line bridges the dart opening.
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
- **`wearer: "right"`**: on a mirrored piece whose original half is the wearer's right (backs, drawn with
  x towards the side): `{side}` in its arrangement name then follows the wearer, not the drawing.
- **CLO3D keys**, copied into `clo3d_<size>.json` and read by `build_garment` (`references/clo3d.md`):
  `fabric` (a role: `shell`, `lining`, `patch`), `particle_distance` (mesh size in mm), `layer`,
  `arrange` (`{"name": "Arm_Outside_1_{side}", "orientation": 0, "x", "y", "offset"}`).
- **`band`**: a straight band drafted from the edges it is sewn to, instead of an outline:

  ```json
  {"name": "Waistband", "band": {"height": 4, "extension": 3, "ease": 0,
   "along": [["Skirt back L", "center_waist", "dart0_1"], ["Skirt back L", "dart0_2", "side_waist"],
             ["Skirt front", "side_waist_sym", "dart0_2_sym"], ["Skirt front", "dart0_1_sym", "center_waist"]]},
   "arrange": {"name": "Body_Front_Center_3"}}
  ```

  Each entry of `along` is one edge (two neighbouring nodes) of another piece of the file, in sewing order;
  the band's lower edge is split at the same points (nodes `b0`, `b1`...) and one seam per edge is added, so
  a waistband, a stand collar, a cuff or a straight facing is written in four lines. `height` is the finished
  height as sewn in 3D (a folded band is cut at twice that height); `extension` adds an underlap past the
  last edge; `ease` (ratio, with `why`) when the band is eased onto the edges. The band is sewn edge to
  edge: list the segments between darts separately, as above.

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
