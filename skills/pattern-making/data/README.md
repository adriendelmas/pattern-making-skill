# Data library

Everything in this folder is data a pattern maker can add or correct without writing code. The engine reads its
numbers from here. One thing per file, in JSON, with where it comes from.

| Folder | One file is | The engine uses it for |
|---|---|---|
| `measurements/` | a size table and its ease: a method, a country, a brand, hands for gloves | `block`, `garment`, grading (`--table <id>`) |
| `constructions/` | the values of a construction: a collar, a hood, the defaults of a garment | `garment` (`"preset": "<id>"` in a spec section) |
| `shapes/` | a real piece digitised from a pattern: outline, named points, how it scales | `shape <id>`, and blocks that name it (`block glove`) |
| `avatars/` | which arrangement point of an avatar each piece goes to | the 3D shell sent to CLO3D (`--avatar <id>`) |

```
python scripts/pattern.py data list                       # every file, with its confidence
python scripts/pattern.py data show shapes bolton-thumb   # one file
python scripts/pattern.py check                           # validate everything; run it before a pull request
```

## Every file

```json
{
  "id": "my-table",
  "kind": "measurements",
  "title": "What it is, in one line",
  "provenance": {
    "source": "The book, standard, pattern or garment it comes from",
    "confidence": "measured",
    "rights": "Why it can be shared: your own work, public domain, values cited from a book...",
    "contributors": ["your name or handle"],
    "added": "2026-11-19",
    "notes": "optional: anything a reader should know"
  }
}
```

- `id` is the file name without `.json`: lowercase words joined by dashes.
- `kind` is `measurements`, `construction`, `shape` or `avatar`, matching the folder.
- `provenance` is required: `source`, `confidence`, `rights`, and `extraction` (`{"method": ...}`: how the data was
  taken, one of the methods of [EXTRACTION.md](EXTRACTION.md)). A file with a `TODO` left in it is refused.
- The folder holds data only. No photo, scan or PDF is ever added; the `.svg` previews and `.md` analysis sheets
  next to the files are drawn by the skill when a contribution is merged.

`confidence` is one of four words, the same everywhere in the skill:

| Level | Meaning |
|---|---|
| `measured` | taken from a real pattern or garment by the contributor |
| `published` | from a cited book, standard or published pattern |
| `practice` | common trade values, consistent with the technique sheets, not traced to one source |
| `unverified` | a description or a guess nobody has checked against a real pattern or a toile |

## Measurements

Two ways to give the sizes of a body (`women`, `men`, `children`, or `hand` for gloves). Units: `cm` (`mm` for hands).

A size chart, one row per size, when you have the table:

```json
"bodies": {"women": {"reference_size": "38",
  "sizes": {"36": {"bust": 84, "waist": 64, "hip": 90, "back_length": 40.5, "hip_depth": 20, "skirt_length": 60,
                   "arm_length": 58.5, "wrist": 15.5, "body_rise": 26.5, "trouser_length": 102, "knee_width": 41, "hem_width": 37},
            "38": {"...": "..."}}}}
```

Or one reference size and the step between sizes, when the table is regular:

```json
"bodies": {"women": {"reference_size": 38, "size_step": 2, "sizes_range": [34, 48],
  "base": {"bust": 88, "waist": 68, "...": "..."}, "grade": {"bust": 4, "waist": 4, "hip": 4, "back_length": 0.5}}}
```

The twelve measurements are described in `references/measurements.md`. An optional `"ease"` block gives the ease per
body (`references/ease.md`); without it the default ease is used. `check` drafts every block in every size of the
table: a value that cannot make a pattern is reported with its size.

## Constructions

```json
{"id": "notched-collar-wide", "kind": "construction", "applies_to": "collar.notched",
 "title": "Notched lapel, wide 1970s lapel",
 "values": {"lapel": 10.5, "break": 26, "gorge_y": 9},
 "doc": {"lapel": "lapel width, square to the roll line"}}
```

`applies_to` names what the values belong to: `collar.notched`, `collar.stand`, `collar.shirt`,
`collar.convertible`, `collar.hood`, or a section of a garment spec (`fit`, `shoulder`, `length`, `front`, `sleeve`,
`facing`). Give only the values that differ from the default file of the same `applies_to` (the one with
`"default": true`, where every value is described). A spec uses it with `"collar": {"preset": "notched-collar-wide"}`.
To correct a default value, edit the default file and say why in the pull request.

## Shapes

A shape is a real pattern at the size it was drafted for: one piece, or every piece of a garment with its seams.

```json
{"id": "patch-pocket-workwear", "kind": "shape", "title": "Patch pocket of a 1950s work jacket, size 50",
 "unit": "cm",
 "reference": {"bust": 100},
 "scale": {"measure": "bust"},
 "outlines": {"pocket": {"type": "other", "closed": true,
   "points": [
     {"name": "top_left", "p": [0, 0], "corner": true}, {"name": "top_right", "p": [14, 0], "corner": true},
     {"name": "side_right", "p": [14, 12]}, {"name": "bottom", "p": [7, 16]}, {"name": "side_left", "p": [0, 12]}],
   "edges": {"hem": [["top_left", "top_right"]],
             "applied": [["top_right", "side_right"], ["side_right", "bottom"], ["bottom", "side_left"], ["side_left", "top_left"]]}}},
 "seams": [],
 "parameters": [{"name": "pocket_width", "measure": ["dist", "pocket", "top_left", "top_right"], "what": "pocket mouth"}],
 "provenance": {"source": "...", "confidence": "measured", "rights": "...",
                "extraction": {"method": "ruler", "line": "seam", "deviation_mm": 1.0}}}
```

- `type`: what the piece is (`bodice_back`, `bodice_front`, `sleeve`, `skirt_front`, `skirt_back`,
  `trousers_front`, `trousers_back`, `collar`, `other`). A standard type has standard point names, and the skill
  measures its standard dimensions from them.
- `seams`: pairs of edges sewn together, between named points, as in a recipe (`references/piece-format.md`).
  `edges`: every edge that is not a seam (`fold`, `hem`, `applied`, `free`, `slit`). Every edge is one or the other.
- `parameters`: dimensions to adjust that the standard types do not measure.
- `python scripts/pattern.py analyze <id>` measures all of it and lists what is missing; the full method is in
  [EXTRACTION.md](EXTRACTION.md).

- `points`: the outline passes through them in order and is smoothed; a point marked `corner` breaks the curve; two
  corners in a row give a straight edge. Or `nodes` with Bezier controls, in the skill's piece format
  (`references/piece-format.md`), which is what a traced drawing gives.
- Name the points that matter: notches, corners, where a seam starts. Seams are written between named points.
- `reference`: the measurements of the pattern the shape came from. `scale`: the one it grows with (optional).
- x to the right, y downwards, any origin.

You do not write the points by hand: `python scripts/pattern.py digitize` makes the file from a photo, a tracing
or a list of points, and `python scripts/pattern.py shape <id> --out preview` draws it so you can lay the paper on
it. A point marked `"dart": true` is a dart tip; `"grain": [[x, y], [x, y]]` on an outline is its grain line.

## Avatars

```json
{"id": "my-avatar", "kind": "avatar", "software": "CLO3D", "title": "Arrangement points of ...",
 "arrangement": {"Front": "Body_Front_2_{side}", "Collar": {"name": "Neck_Collar", "x": 50, "y": 50, "offset": 120}}}
```

Piece name of the 3D shell, then the arrangement point (`{side}` becomes L or R, the wearer's side). A piece is
looked up by its full name, then by its first word. Read the point names of your avatar with the `get_scene_summary`
tool of clo3d-mcp.
