# Pattern intake

When the person gives a real pattern (paper pieces, a photo or a scan of them, a tracing, measured points) to
draft from, to adapt, or to add to the library, analyse it with this protocol. The analysis of a pattern is never
done by eye: the skill digitises it, names it, and measures it with `analyze`. Your part is to identify (what each
piece is, which point is which, which edge is sewn to which); the numbers come from the script.

Run it whole every time. A pattern taken in half-analysed gives a draft that cannot be adjusted: a sleeve whose
cap height nobody measured cannot be regraded.

## Protocol

1. **Ask what it is.** Garment, size, the body measurements it was made for, fabric (woven, knit, stretch),
   where it comes from and whether it may be shared. Answer the pattern checklist below.
2. **Digitise each piece** by the method of `data/EXTRACTION.md`: seam line, grain vertical, ruler in view, points
   placed by its rules. `python scripts/pattern.py digitize <photo.png|tracing.svg|points.csv> --id <id> --outline
   <piece> --type <type>`, once per piece, all in the same shape file. Work in a folder of the person's; write to
   `data/shapes/` only when the pattern is to join the library.
3. **Name the points** with the standard names of the piece type (`data/EXTRACTION.md`, section 3). Every
   corner, every notch, both ends of every seam, every dart.
4. **Write how it goes together**: `seams` between named points, with the ease and its reason when two edges differ;
   `edges` for every edge that is not a seam (fold, hem, applied, free, slit); `reference` for the body or size.
5. **Declare what the standard types do not measure** as `parameters`: every dimension of this pattern a pattern
   maker would adjust. Go down the adjustables checklist; a line with no standard parameter and no declared one
   is a hole in the analysis.
6. **Measure**: `python scripts/pattern.py analyze <id or file>`. It prints, for every piece, its standard
   dimensions, darts, declared parameters; every seam with both lengths and its ease; the garment's girths and
   their ease against the reference; and every `!!`: a standard point not named, a seam that does not match, an
   edge nobody accounts for. Fix the file until there is none. Never edit a number to make it pass: correct the
   points, or declare the ease the pattern really has.
7. **Check against the paper.** `python scripts/pattern.py shape <id> --out preview` and have the person lay the
   paper on the print (largest gap, 2 mm at most), and compare three analysed values with a tape on the paper.
8. **Answer both checklists** from the analysis sheet, line by line, and give them to the person. Each line: the
   value, where it was measured, what body measurement it follows, or "not on this pattern".
9. **Use it or file it.** To draft from it: the analysis gives the values for a garment spec, a preset
   (`data/constructions/`) or a measurements file. To add it to the library: fill `provenance` (source, rights,
   confidence, extraction with `deviation_mm`), run `python scripts/pattern.py check`, and offer to send it
   (`CONTRIBUTING.md`). The photo, scan or tracing is never copied into the skill or the repository.

## Pattern checklist (answer every line)

| Line | What to establish |
|---|---|
| Garment | what it is, which construction of the knowledge base it matches (`kb search`) |
| Size and body | the size, and the body measurements it was made for (`reference`) |
| Source and rights | where it comes from, whether it may be shared, how to credit it |
| Line | seam line or cutting line; the allowance if it had to be taken off |
| Scale | the ruler segment used, and the check that the picture is not distorted |
| Pieces | every piece, its type, how many to cut, pair or on the fold |
| Fabric | woven, knit or stretch; the stretch the pattern counts on |
| Grain | grain line of every piece; any piece on the bias |
| Seams | every pair of edges sewn together, both lengths, ease and its reason |
| Other edges | every edge that is not a seam: fold, hem, applied, free, slit |
| Darts, pleats, gathers | where, intake, length; what each one shapes |
| Notches | every notch, its distance from a named point, what it matches |
| Inner marks | pocket placement, roll line, buttons and buttonholes, fold lines |
| Missing pieces | what the pattern needs and was not given: facing, lining, interfacing, pocket bags |

## Adjustables checklist (answer every line that the garment has)

Every one of these must appear in the analysis, as a standard parameter or a declared one, with its value.

| Zone | Dimensions |
|---|---|
| Lengths | centre back and centre front length, side seam, total length, hem depth |
| Girths | bust or chest, waist, hip, hem, each with its ease against the body |
| Neckline | width, depth front and back, length |
| Shoulder | length, drop or slope, extension, pad allowance |
| Armhole | length front and back, depth, across back and across chest, where the notches sit |
| Sleeve | cap height, cap length front and back, cap ease and where it is spread, bicep width, elbow, hem width, length, vent |
| Darts and shaping | intake, length and position of every dart; seams that replace them |
| Collar | neck edge length against the neckline, stand and fall at the centre back, point, spring |
| Front and closure | extension or overlap, button positions and spacing, facing width |
| Waist and hip | waistband length and height, hip depth, yoke depth |
| Trousers | body rise, crotch extension front and back, crotch seam length, inseam, outseam, knee and hem widths |
| Pockets | position from named points, mouth, depth, flap or welt size |
| Hems and facings | hem allowance of every hem, facing and interfacing widths |
| Lining | where it differs from the shell: ease, pleat, hem |

## What the analysis is and is not

- It is exact for what the outlines say: lengths, widths, depths, angles, seam matching, ease against the
  reference.
- It does not know what was not digitised: a notch left out, a piece not given. That is what the pattern checklist
  is for.
- It measures one size. Grading rules come from two sizes of the same pattern analysed the same way: the
  difference of each parameter is its grade.
- A value read on the paper by eye never replaces an analysed one. If they disagree, the digitising is wrong:
  redo that piece.
