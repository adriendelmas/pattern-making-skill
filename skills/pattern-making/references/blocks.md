# Block construction

What `scripts/pattern.py` does, to explain, check or adapt it. Notation: B bust, W waist, H hip, ease
noted a. All values in cm, on the half body.

## Straight skirt

- **Widths**: at the hip, (H + a) / 4, plus 0.5 at the front and minus 0.5 at the back, to bring the side
  seam forward. At the waist, (W + a) / 4 with the same shift.
- **Sharing the waist-hip difference**: half at the side seam, 3 cm at most, the rest in darts. One dart
  up to 3 cm, two beyond. Darts are 9 cm long at the front and 13 cm at the back.
- **Waist line**: raised by 1 cm at the side. Center back is lowered by 1 cm for the sway of the back.
- **Side seam**: hip curve from the waist to the hip line, then straight to the hem.
- **Checks**: front side seam equal to back side seam, finished waist equal to W + ease.

## Bodice

- **Width at the underarm**: (B + a) / 4 at the back as at the front.
- **Neckline**: width neck / 5 minus 0.2 at the back, with 2 cm depth. At the front, width minus 0.2 and
  depth equal to the width plus 1.
- **Shoulder**: slope of 4 cm at the back and 5 cm at the front for women. The back length also receives
  the shoulder ease.
- **Armhole**: curve perpendicular to the shoulder, passing through the across-back or across-front line
  about halfway down, then meeting the underarm flat.
- **Bust dart, women**: side dart pointing to the bust point, stopped 2.5 cm before it. The front is
  lengthened by the dart value at the waist, so the side seams match once the dart is closed.
- **Waist darts, women**: the difference between bust width and waist is shared 40 % at the side, 2.5 cm at
  most, and the rest in darts. Back dart up to 4 cm, front dart under the bust up to 5 cm.
- **Men and children**: no bust dart and no waist dart. The block is straight.
- **Checks**: side seams match, shoulder ease, half neckline compared with neck / 2, waist. The total
  armhole is printed, the sleeve depends on it.

## Set-in sleeve

- **Sleeve cap**: its length equals the bodice armhole plus the ease. Cap height is about a third of the
  armhole. The script searches the sleeve width that makes it exact.
- **Hem**: (wrist + wrist ease) / 2 on each side of the center line.
- **Notches**: one notch at the top for the shoulder, one at the front and two at the back, placed at the
  same distance from the underarm as the bodice's across notches, plus a share of the ease.
- **Check**: cap length minus armhole equal to the planned ease.

## Circle skirt

- `block circle_skirt --fullness 1 --panels 2 --length 70`: waist radius r = finished waist / (2 π fullness),
  hem radius r + length; each panel spans 2 π fullness / panels, drawn symmetric about its grain line with
  arcs as cubic Beziers of 90 degrees at most. Fullness 1 full circle, 0.5 half, 0.25 quarter. Two panels give
  a front and a back with side seams, one panel a single seam; the seams are written.
- **Check**: the waist arcs add up to waist + `skirt_waist` ease. Hem length printed.

## Knits (`--knit`)

- Bodice and sleeve for a medium-stretch knit (`ease.md`): no bust dart, no waist darts (the side seam
  takes the whole bust-to-waist difference), ease bust -4, waist -4, sleeve cap 0, wrist +2, no shoulder ease,
  unless the measurements file sets its own `ease`. The 3D shell gets an 8 mm mesh.
- `--sleeve-length 26` and `--sleeve-hem 30` (finished hem circumference) shape a short or a wide sleeve.

## Trousers

- **Widths at the hip**: (H + a) / 4 minus 1 at the front, plus 1 at the back.
- **Crotch**: extension of H / 20 at the front and H / 10 at the back. The back crotch is dropped by 1 cm.
- **Body rise**: seated measurement plus 1 cm of ease.
- **Center back**: tilted 3 cm towards the side and raised 2 cm at the waist, for sitting.
- **Crease**: the crease line, which is also the grain line, runs through the middle of the width at the
  crotch line.
- **Leg**: knee placed 5 cm above halfway between crotch and hem. The front is 1 cm narrower on each side
  at the knee and the hem.
- **Darts**: 2 cm at most at the front, 3 cm at the back, removed below 0.5 cm.
- **Checks**: front and back side seams equal, back inseam slightly shorter than the front, waist.

## 3D shell of the blocks

`block` also writes, in `out/clo3d/`, the shell sent to CLO3D: fold pieces unfolded, pairs mirrored into L
and R (backs with the wearer's side), every seam one edge to one edge with its ease declared (side seams
with the bust dart closed, shoulders with the back ease, sleeve cap matched to the armhole at the notches,
centre seams, dart legs, trouser side seams and inseams node to node), fabric role `shell` and default
arrangement points (`references/clo3d.md`).

## Where the numbers come from

Standard sizes, grading steps and ease are read from `data/measurements/standard-eu.json` (or the table named by
`--table`); the glove's hand from `glove-hand.json`, its thumb and thumb hole from the digitised shape
`data/shapes/bolton-thumb.json`. The proportions inside the drafts (dart shares, curve shapes) are in the code and
described above.

## Blocks the script does not draft

They are built on the same principles, starting from the existing blocks:

- **Dress**: bodice and skirt joined at the waist, darts aligned. For a dress without waist seam, extend
  the bodice darts into the skirt.
- **Men's shirt**: men's bodice block with 12 to 16 cm of ease, back yoke, low sleeve cap of 10 to 13 cm,
  cuff and stand collar.
- **Jacket**: 10 to 14 cm of ease, shoulder widened by 1 cm, armhole lowered by 1.5 to 2 cm, two-piece
  sleeve to follow the elbow.
- **T-shirt, leggings**: `--knit` bodice and sleeve; leggings from the trousers block with negative ease.
- **Children**: no darts, more ease, and a growth allowance in the hem.
