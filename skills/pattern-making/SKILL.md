---
name: pattern-making
description: Pattern making, pattern design and sewing (garment drafting, flat pattern design, draping logic, sewing construction). Turns a request, a photo, a technical drawing or a fashion sketch, including sculptural or unconventional volumes, into real patterns drafted the way professional patterns are drafted, for every garment family and accessory (skirts, trousers, bodices, dresses, shirts, sleeves, collars, tailoring, outerwear, knits, lingerie, swimwear, gloves, hats, bags). Adds allowances, notches, grain lines, grades sizes, exports 1:1 SVG, DXF or CLO3D. Use whenever a garment pattern, a sketch to develop, body measurements, ease, grading, a toile, sewing techniques or a 3D garment comes up, whatever the software.
---

# Pattern making

Universal pattern-making skill. It drafts like a professional pattern maker: from the construction of
real garments and established methods, never from a silhouette alone. The knowledge is in `references/`,
the calculations are done by `scripts/pattern.py` (Python 3.9 or newer, standard library only), and the numbers
it drafts with (size tables, construction values, digitised shapes) are data files in `data/`.

## Rules

1. **Know the construction before drafting.** From a photo or a drawing, run the analysis protocol
   (`references/reference-analysis.md`): every seam, fold, piece, finish, with evidence and confidence,
   dimensions measured at scale on the photo, and its checklist answered line by line (front edge and
   overlap, closure, symmetry, collar, shoulders, volume, pockets...). A blank line is a misread garment.
   From a fashion sketch, follow `references/design-from-sketch.md`. Write the construction sheet first.
2. **Draft like real patterns.** For every garment type, follow the technique sheet of its family in
   `references/techniques/`. If the construction is not covered there, look up how published patterns
   and pattern-making books draft it (web search, pattern images the person gives), study their pieces,
   and draft the same way. Never invent a construction a pattern maker would not recognise.
3. **Always start from measurements.** Ask for the measurements needed (`references/measurements.md`). If
   they are missing, start from a standard size and say clearly which values are estimated.
4. **Never calculate in your head.** Coordinates go through the script. An error of a few millimetres is
   repeated on every seam.
5. **Read the checks.** Each draft prints a report. A line marked `!!` must be fixed before going on.
6. **Validate in 3D or on a toile, and correct the pattern, not the simulation.** When a piece is too
   complex to place automatically in CLO3D, hand it over to the person (`references/clo3d.md`).
7. **Stay neutral on the method.** The engine's blocks are proportional and tied to no author. If the
   person follows a given method (Aldrich, Armstrong, Müller, Esmod, Bunka, other), use its values.
8. **A real pattern is analysed by the skill, never by eye.** When the person gives a pattern (paper pieces, a
   photo or a scan of them, a tracing, measured points) to draft from or to add to the library, run the intake
   protocol (`references/pattern-intake.md`): digitise each piece, name the standard points, write the seams and
   what every other edge is, then `python scripts/pattern.py analyze`, which measures every dimension, seam and
   ease and lists what is missing. Answer both of its checklists line by line. Reference pictures are never copied
   into the skill or a repository: only the data taken from them.

## Construction laws (checked by the engine on every export)

1. **Reciprocal lengths**: edges sewn together have the same length within 1 mm. Every intended difference
   (cap ease, gathers, easing) is declared on the seam with its ratio and reason.
2. **Right angles at the fold**: a half piece meets its fold at 90 degrees (neckline, waist, hem), so the
   unfolded piece has no point or dip.
3. **Volume needs shaping**: the body is not developable. Curvature is taken by darts, seams, ease or
   stretch; joints with large movement get inserted pieces (gussets, set-in thumbs, crotch extensions).
4. **Shapes come from real patterns**: complex pieces (thumbs, gussets, collars, sleeve heads) follow the
   shapes of published patterns, scaled to the measurements, never an improvised outline.

Every piece cut from another one (facing, interfacing, pocket facing; not linings, which are larger by design) declares it with `"within"`, so the
engine checks it does not pass its piece; the engine also flags pieces pinched between two wide parts.

A pattern is finished when its report has no `!!` line and its seam table (`seams_<size>.md`) is all OK.

## Whole garments from a spec

Jackets, coats, shirts and tops are drafted by `python scripts/pattern.py garment spec.json --out folder`
(`references/garment-spec.md`): reusable constructions on the bodice block (body ease, extended and padded
shoulders, darts, boxy or armhole princess with flare, overlap or wrap, notched lapel drafted in place, stand,
funnel, shirt, convertible collars and hoods, two-piece, one-piece, raglan and kimono sleeves matched to the
armhole, facings, lining, patch, in-seam, welt and jetted pockets). It writes the cut pieces and
the 3D shell for CLO3D with every seam and wrap hold; `python scripts/sheet.py folder/pieces_<size>.json` draws PNG
sheets (Pillow). Add a construction to `scripts/garment.py` rather than writing a one-off script.

## Any garment as data

Garments the engine has no block for are written as a recipe: pieces with named nodes, Bezier curves, holes
and mirror pairs, plus a seam list pairing edges by node names, with declared ease
(`references/piece-format.md`). `python scripts/pattern.py piece recipe.json --out folder` validates it with
the same laws, exports it, and `clo3d ... --assemble` sews it in CLO3D. No new code per garment.

## Data library

The engine's numbers are data anyone can add to (`data/README.md`): size tables and ease in `data/measurements/`,
construction values and presets in `data/constructions/`, real pieces digitised from patterns in `data/shapes/`,
avatar arrangement points in `data/avatars/`. Each file states its source and a confidence: `measured`, `published`,
`practice` or `unverified`. Say which one a draft rests on when it matters.

```
python scripts/pattern.py data list                              # what is available, with its confidence
python scripts/pattern.py block all --table <id> --size 40       # draft from another size table
python scripts/pattern.py shape <id> --measure G=190 --out dir   # draw a digitised shape, scaled
python scripts/pattern.py digitize photo.png --id <id> --outline back --type bodice_back   # also .svg, .csv
python scripts/pattern.py analyze <id>                           # measure a digitised pattern, list what is missing
python scripts/pattern.py check                                  # validate every data file and entry
```

In a garment spec, `"collar": {"preset": "<id>"}` takes its values from a construction file, `"table"` and
`"avatar"` choose the size table and the avatar. When the person gives a size chart, a real pattern or a
correction, take it in by the method of `data/EXTRACTION.md` (a pattern: `references/pattern-intake.md`), put it in
`data/` (or in the entry's file) rather than in a one-off script, run `check`, and offer to send it to the project
(`CONTRIBUTING.md` at the root of the repository). The repository holds data only: the previews and analysis sheets
next to the data are drawn by the skill itself.

## Knowledge map

Start with the knowledge base: one entry per garment, piece or technique (recognition, pieces, shape with
anchors and seam correspondence, drafting, sewing order, fabrics, fit faults, CLO3D, confidence):

```
python scripts/pattern.py kb search <words>     # English or French, accents ignored
python scripts/pattern.py kb show <id>
```

Entries are one file each, `references/kb/<family>/<id>.md`, and end with a `Status`: `measured`, `published`,
`practice` or `unverified`. An `unverified` shape must be checked against real drawn patterns before it goes into a
pattern; tell the person when a draft rests on one. Index: `references/kb/INDEX.md`. Format: `references/kb/FORMAT.md`.

Worked specs: `examples/notched-lapel-jacket/` (fitted and oversize, lined), `examples/velvet-coat/` (princess,
flare, 16 cm wrap, funnel collar, lined) and `examples/constructions/` (raglan, kimono, dolman, shirt, camp shirt,
hooded jacket).

| Need | Sheet |
|---|---|
| Analyse a photo, recognise constructions | `references/reference-analysis.md` |
| Analyse a real pattern the person gives, add it to the library | `references/pattern-intake.md`, `data/EXTRACTION.md` |
| Develop a sketch, sculptural volumes, unconventional cutting | `references/design-from-sketch.md` |
| Skirts, trousers, shorts, jumpsuits | `references/techniques/skirts-trousers.md` |
| Bodices, dart manipulation, dresses, tops, shirts | `references/techniques/bodices-dresses-tops.md` |
| Sleeves, cuffs, plackets, collars, hoods | `references/techniques/sleeves-collars.md` |
| Jackets, coats, tailoring, outerwear | `references/techniques/tailoring-outerwear.md` |
| Knits, lingerie, swimwear, activewear | `references/techniques/knits-lingerie-swimwear.md` |
| Gloves, hats, bags, belts, ties | `references/techniques/accessories.md` |
| Seams, hems, facings, closures, pockets, gathers, elastic | `references/techniques/sewing-techniques.md` |
| Engine blocks and how they are drafted | `references/blocks.md` |
| Typical pieces as parametric templates (collars, cuffs, plackets, pockets, flaps, hoods, gusset, godet, fly, yoke) | `references/templates.md` |
| Dart pivot, slash and spread, fullness | `references/transformations.md` |
| Measurements, ease, finishes, piece format | `references/measurements.md`, `ease.md`, `finishes.md`, `piece-format.md` |
| Size tables, construction presets, digitised shapes, avatars | `data/README.md` |
| Sending, sewing and simulating in CLO3D | `references/clo3d.md` |

## Workflow

1. **Understand the request**: garment, wearer, fabric (woven, knit, stretch, leather), intended fit.
   With an image, write the construction sheet (rule 1). Read the technique sheet of the family.
2. **Measurements**: `python scripts/pattern.py measurements --body women --size 38` prints every
   measurement used (`--table <id>` for another size table of `data/measurements/`). For personal measurements,
   write a JSON file and pass it with `--measurements`.
3. **Ease**: by garment and fabric (`references/ease.md`), overridden in the measurements file (`"ease"`).
4. **Base**: `python scripts/pattern.py block <skirt|bodice|sleeve|trousers|all> --body ... --out folder`
   gives the standard blocks, with their 3D shell and seams in `folder/clo3d/`. Options: `--knit` (no darts,
   negative ease, no cap ease), `--sleeve-length`, `--sleeve-hem`; `block circle_skirt --fullness 1 --panels 2
   --length 70`. `block glove --size 7 --length 40 --end-girth 26` drafts a leather glove like
   real glove patterns (trank, Bolton thumb in a tongued hole, fourchettes) with its seam list; personal
   hand measurements go under `"hand"` in the measurements file (`references/techniques/accessories.md`).
   Waistbands, stand collars, cuffs and straight facings are written as a `band` along the edges they join
   (`references/piece-format.md`). Garments that do not start from these blocks (hats, bags, sculptural
   pieces) are drafted directly from their technique sheet, as pieces in the skill's format.
5. **Transformation**: `pivot` closes or transfers a dart, or opens a slash for fullness; `smooth`
   redraws a hem or a neckline. Methods in `references/transformations.md` and the technique sheets.
   Finish with `python scripts/pattern.py piece file.json --out folder`, which prints every edge length
   to check that seams match.
6. **Finishes and construction**: allowances by seam type, notches, grain, facings, closures
   (`references/finishes.md`, `references/techniques/sewing-techniques.md`).
7. **Grading**: `--sizes 36,38,40,42` produces every size and an SVG where they nest.
8. **Output**:
   - `pattern.svg`: print at 100 %, check the 10 cm square.
   - `pattern_<size>.dxf`: for CAD software (layers CUT, SEAM, NOTCHES, GRAIN, TEXT).
   - `clo3d_<size>.json`: the garment for CLO3D, built in one call by the plugin and MCP server of
     [clo3d-mcp](https://github.com/Ubani-Studio/clo3d-mcp): exact curves, one CLO3D
     line per pattern edge, seams, holds, and per piece its fabric role, mesh size and arrangement point.
     `python scripts/pattern.py clo3d folder/clo3d/clo3d_38.json --fabrics shell=2 --snapshots views --save
     file.zprj --simulate 300` builds it, checks the line lengths, captures the views and saves. Guards,
     check loop, avatar measuring: `references/clo3d.md`. `clo3d_<size>.py`: standalone script, pieces only.
   - `pieces_<size>.json`: the skill's editable format, in cm.

## Conventions

- Inputs in centimetres, SVG, DXF and CLO3D outputs in millimetres.
- Piece axes: x towards the side, y downwards, origin at center front or center back.
- Symmetric pieces are drafted as half pieces, with an edge "on the fold". The CLO3D export unfolds them.
- Notches: one notch at the front, two notches at the back.

## Without Python

If the agent cannot run a script, apply the methods of `references/` by hand, writing out each
calculation, and say that the draft was not verified by the automatic checks.
