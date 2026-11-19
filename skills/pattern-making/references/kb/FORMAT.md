# Knowledge base format

One entry per garment, piece or technique, one file per entry: `references/kb/<family>/<id>.md`. The engine indexes
them (`python scripts/pattern.py kb search <words>`, `kb show <id>`) and `python scripts/pattern.py check` refuses an
entry with a field missing.

To add an entry, copy this into `<family>/<id>.md` and fill every field:

```
# <Name in English> {#<id>}

- **Aliases**: other English names; French names (fr: ...); other languages if usual
- **Family**: garment family or technique family
- **Recognize**: how to tell it on a photo or a drawing (seams, folds, shapes, closures)
- **Pieces**: piece name (cut count), piece name (cut count) ...
- **Shape**: for each non-trivial piece, its outline in words AND numbers: overall proportions (width /
  height), named anchor points (A, B, C... or descriptive), notches, slits, holes, curves and where they
  are, which edge is sewn to which edge of which piece. State the source of the shape: "drawn pattern:
  <source>" when taken from a real pattern drawing, otherwise "unverified". When the engine drafts the piece,
  say so: "shape: <id>" (`data/shapes/`), "template: <id>" (`references/templates.md`) or
  "garment: <construction>" (`references/garment-spec.md`).
- **Drafting**: numbered steps with measurements and formulas in cm or mm (typical values marked)
- **Sewing order**: numbered
- **Finishes and notions**: seam types, hems, facings, interfacing, closures
- **Fabrics**: suitable fabrics and how they change the pattern (ease, stretch, nap, grain)
- **Fit faults**: fault -> pattern fix
- **Variants**: related constructions and how they differ (link ids with #id)
- **CLO3D**: how to build it there (pieces, seams, mesh size, layers, what the user must place by hand)
- **Confidence**: what each part rests on, in words: the source for the shape, for the numbers, for the sewing order
- **Status**: measured | published | practice | unverified
```

`Status` is one word, the weakest link of the entry:

| Status | Meaning |
|---|---|
| `measured` | the shape and the numbers were taken from a real pattern or garment by the contributor |
| `published` | they come from a cited book, standard or published pattern |
| `practice` | common trade values, consistent with the technique sheets, not traced to one source |
| `unverified` | a description or a guess nobody has checked against a real pattern or a toile |

The statuses of the first 570 entries were set mechanically on 2026-11-19 from the wording of their `Shape` and
`Confidence` fields ("unverified", "from memory", "drawn pattern:"). Correct one whenever you know better.

Rules:

- Ids are lowercase with dashes, unique across the whole base (`bolton-thumb`, `circle-skirt`); the file is named
  after the id.
- Metric units. Plain technical English. No emojis.
- Never invent a shape or a number to fill a field: write "unverified" or "not known" instead.
- Written in your own words from what you know or from a named source. No sentence copied, no figure, no image.
- Sources (books, published patterns, URLs) go in `SOURCES.md` of the family folder; cite them by name in
  `Confidence`. `README.md` of a family folder holds its reading conventions.
- `INDEX.md` is generated when a contribution is merged; do not edit it.
