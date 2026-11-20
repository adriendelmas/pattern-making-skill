# Extraction method

How data gets into this library, the same way for everyone. The repository holds the data taken from a pattern,
a book or a garment, and never the material itself: no photo, no scan, no tracing, no PDF. The photo you digitise
from stays on your machine. The only pictures in the repository are drawn by the skill from the data, when a
contribution is merged.

Every file records how it was obtained, in `provenance.extraction.method`:

| Method | Meaning | Used for |
|---|---|---|
| `photo` | clicked on a photo or a scan of the paper piece (`digitize`, click tool) | shapes |
| `tracing` | traced in a drawing program over a photo or a scan (`digitize`, SVG) | shapes |
| `ruler` | measured with a ruler or a tape on the paper or on the garment | shapes, constructions, measurements |
| `diagram` | proportions read from a published diagram that is not full size | shapes, constructions |
| `transcribed` | numbers typed from a published table or text | measurements, constructions |
| `compiled` | assembled by the contributor from several sources or from practice | measurements, constructions, avatars |
| `software` | read from software through its interface | avatars |

A file marked `measured` must come from the real thing: `photo`, `tracing` or `ruler`.

## A pattern piece or a whole pattern (`data/shapes/`)

The agent runs this with you (`references/pattern-intake.md`); the steps are the same by hand.

### 1. Prepare the paper

- Flat, right side up, grain line vertical.
- Digitise the **seam line**. If the paper only shows the cutting line, measure the allowance and take it off
  before digitising, and say so in `provenance.notes`.
- A ruler lies next to the piece, in the same plane.
- Photograph from straight above, the piece in the middle of the frame, from far enough that it fills no more than
  two thirds of the picture; or scan it. Check the picture: the ruler must read the same at both ends of the piece,
  within 1 mm per 30 cm. If it does not, take it again.

### 2. Place the points

Go round the outline once, clockwise, starting at the top point nearest the centre line.

- Every corner, marked `corner`.
- Every notch, and both ends of every seam.
- A dart: its two legs and its tip, the tip marked `dart`.
- On a curve: a point at each end, one at its deepest place, and one every 3 to 5 cm; every 1 to 2 cm where the
  curve is tight (underarm, neckline, crotch).
- A piece cut on the fold: digitise the half, and list the fold edge under `edges`.
- One outline per piece. All the pieces of one pattern go in the same file (`digitize ... --outline back --type
  bodice_back`, then again for the next piece).

### 3. Name the points

Names are what seams and measurements hang on. A piece of a standard type uses the engine's names, so that
"armhole depth" means the same thing in every pattern:

| Type | The piece |
|---|---|
| `bodice_back`, `bodice_front` | back and front of anything worn on the torso, to the waist or to the hem: block, shirt, jacket, coat, with a set-in, raglan or cut-on sleeve, with or without a lapel |
| `princess_front`, `princess_side_front`, `princess_side_back`, `princess_back` | the four panels of an armhole princess line |
| `sleeve`, `sleeve_top`, `sleeve_under`, `sleeve_raglan` | one-piece sleeve; top and under sleeve of a tailored sleeve; raglan sleeve |
| `skirt_front`, `skirt_back`, `circle_skirt` | straight or shaped skirt; panel of a circle skirt |
| `trousers_front`, `trousers_back` | trouser legs |
| `collar`, `collar_stand`, `hood` | collar or fall, separate stand, half hood |
| `glove_trank`, `glove_thumb`, `glove_thumb_hole`, `glove_fourchette` | the pieces of a glove |
| `other` | everything else (pocket, cuff, placket, facing, gusset): name every corner and notch for what it meets (`top_left`, `side_notch`) |

[TYPES.md](TYPES.md) lists, for each type, the points to name and every dimension the skill measures from them.
Name every point of that list your piece has: a dimension whose points are missing is not measured. When the
centre line does not run along the piece (a lapel front, a wrap), give one point of it as a mark:
`"marks": {"center_front": {"outline": "front", "p": [x, y]}}`.

Lowercase, words joined by underscores. Darts: `dart` for the tip (or `waist_dart`, `side_dart`), its legs
`<tip>_1` and `<tip>_2`. A dart drawn inside the piece (a fish dart at the waist) is not on the outline: give its
four points under `inner_darts` of the outline, `{"name": "waist_dart", "points": [top, one side, bottom, other side]}`.

### 4. Say how it goes together

- `seams`: every pair of edges sewn together, between named points:
  `["sleeve", "cap", "back_underarm", "back", "shoulder", "underarm", {"ease": 0.05, "why": "cap ease"}]`.
  Two sewn edges have the same length within 1 mm; a wanted difference is declared as `ease` with its reason.
- `edges`, on each outline, for everything that is not a seam: `fold`, `hem`, `applied` (laid on another piece and
  stitched down), `free` (opening, vent, raw edge), `slit` (a slash whose lips are sewn to a piece set into it).
- Every edge must be one or the other. An edge nobody accounts for is how a construction gets misread.
- `reference`: the measurements of the body or the size the pattern was made for, with the keys of
  `references/measurements.md` (`bust`, `waist`, `hip`, `neck`...). The analysis computes the ease from them.
- `parameters`: any dimension a pattern maker would adjust that the standard types do not measure:
  `{"name": "pocket_width", "measure": ["dist", "pocket", "top_left", "top_right"], "what": "pocket mouth"}`.
  Measures: `dx`, `dy`, `dist`, `path` (along the outline, the shorter way round between the two points),
  `seamline` (the same, dart legs left out), `angle`, `perp` (distance from a point square to a line:
  `["perp", "front", "lapel_point", "break>gorge_roll"]`).

### 5. Let the skill measure it, and check against the paper

```
python scripts/pattern.py shape <id> --out preview    # print preview/pattern.svg at 100 %
python scripts/pattern.py analyze <id>                # every dimension, seam and ease, measured by the skill
python scripts/pattern.py check
```

- Lay the paper on the print. The largest gap between the two outlines goes in `provenance.extraction.deviation_mm`;
  above 2 mm, digitise again.
- Read the analysis against the paper: measure three of its values on the paper with a tape (a seam, a width, a
  dart). They must agree within 2 mm.
- `analyze` must end with no `!!` line: every typed piece has its standard points, every seam matches, every edge
  is accounted for.

### 6. Send the data, keep the picture

Only `data/shapes/<id>.json` goes in the repository. Its preview (`<id>.svg`) and its analysis sheet (`<id>.md`)
are drawn by the skill when the contribution is merged. A pull request that adds an image, or edits a generated
file, is refused by the check.

## A measurement table (`data/measurements/`)

1. Type the numbers; never add the page. Name the book, the edition, the page and the table in
   `provenance.source`.
2. Map each column to the skill's keys using their definitions in `references/measurements.md`. Where the source
   measures differently (a back length taken to the hip, a rise taken seated), convert, and write the conversion in
   `provenance.notes`.
3. A value the source does not give is derived from the ones it gives, and listed as derived in the notes. Never
   filled in from another table.
4. Centimetres. One file per source.
5. Read every row back against the source once, then run `check`: it drafts every block in every size.

## The values of a construction (`data/constructions/`)

1. Give only numbers you can point to: measured on a pattern with a tape (`ruler`), read on a diagram (`diagram`),
   typed from a text (`transcribed`), or your own practice (`compiled`).
2. Measure each value the way the default file of that construction describes it (`doc`). A lapel width is square
   to the roll line, not along the edge.
3. Draft a garment with the preset and compare the drawing with the source before sending.

## An avatar (`data/avatars/`)

Read the arrangement points with the `get_scene_summary` tool of clo3d-mcp on the loaded avatar (`software`), and
say which avatar and which version in `provenance.source`. Do not copy names from another avatar.

## A knowledge-base entry (`references/kb/`)

Written in your own words from what you know or from a named source: its numbers, its proportions, its order of
work. No sentence copied, no figure reproduced. Where the entry describes a shape that exists in `data/shapes/`,
it names it instead (`shape: <id>`).
