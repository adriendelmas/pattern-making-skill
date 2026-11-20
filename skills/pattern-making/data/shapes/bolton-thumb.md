# Analysis: Bolton thumb and its hole in the trank (leather glove)

Measured by the skill from the outlines of the shape file (`python scripts/pattern.py analyze bolton-thumb`), in cm at the reference size. Generated; do not edit.

Reference: G 180.

## hole (glove_thumb_hole)

Width 3.07, height 6.40, perimeter 18.04, area 12 cm2. Named points: h_TL, h_B, h_RM, h_TR, h_D, h_TR2, h_V.

| Parameter | Value | Measured as | What it is |
|---|---|---|---|
| `height` | 5.40 | vertical distance, h_TL to h_B | hole, top to bottom |
| `width` | 3.06 | horizontal distance, h_TL to h_RM | hole at its widest |
| `flap_depth` | 1.39 | vertical distance, h_D to h_TR | flap that enters the slit of the thumb |

Not sewn: slit h_TR..h_D, slit h_D..h_TR2.

## thumb (glove_thumb)

Width 6.84, height 9.33, perimeter 27.66, area 50 cm2. Named points: C, LL, a, N1, N2, b, B, c, RM, Ps, d, RL.

| Parameter | Value | Measured as | What it is |
|---|---|---|---|
| `length` | 9.33 | vertical distance, LL to B | top of the lobes (the tip, once sewn) to the bottom of the base |
| `width` | 6.72 | horizontal distance, N2 to RM | thumb at its widest |
| `tip_lobe` | 2.04 | length along the outline, C to LL | one lobe of the tip |
| `side_left` | 4.13 | length along the outline, LL to N1 | side seam of the thumb, from the tip lobe to the hole notch |
| `base_left` | 7.75 | length along the outline, N1 to B | edge sewn round the hole, from the notch to the bottom of the base |
| `base_right` | 7.38 | length along the outline, B to Ps | edge sewn round the hole, from the bottom of the base up the other side |

## Seams

| Edge A | cm | Edge B | cm | Ease | Why | |
|---|---|---|---|---|---|---|
| thumb N1..Ps | 15.13 | hole h_TR2..h_TR | 14.69 | +3.0 % | the thumb is eased into the hole, round its base from notch to notch | OK |
| thumb C..LL | 2.04 | thumb RL..C | 2.02 | +0.8 % | the two lobes sewn together make the tip; their edges differ a little on the diagram | OK |
| thumb LL..N1 | 4.13 | thumb Ps..RL | 4.34 | -4.9 % | side of the thumb: the slit that takes the flap opens in the Ps..RL edge, at a point block glove computes | OK |

## Completeness

Every typed piece has its standard points, every seam matches, every edge is accounted for.
