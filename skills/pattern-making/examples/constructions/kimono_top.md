# Analysis: Kimono top, size 38

Measured by the skill from the outlines of the garment the engine drafts from this spec (`python scripts/pattern.py analyze kimono_top.json`), in cm at the reference size. Generated; do not edit.

Reference: bust 88.0, waist 68.0, hip 94.0, back_length 41.0, hip_depth 20.0, skirt_length 60.0, arm_length 59.0, wrist 16.0, body_rise 27.0, trouser_length 102.0, knee_width 42.0, hem_width 38.0, neck 37.0, shoulder 12.2, armhole_depth 21.0, half_back_width 17.0, half_chest_width 16.0, bust_depth 25.5, bust_span 18.5, bust_dart 4.0.

## Front (bodice_front)

Width 47.45, height 65.00, perimeter 226.49, area 1835 cm2. Named points: neck, shoulder, wrist_top, wrist_under, slash_mouth, slash_in, slash_in_b, underarm, hem_side, hem_mid, hem_front, front_neck, center_neck.

| Parameter | Value | Measured as | What it is |
|---|---|---|---|
| `neck_width` | 7.00 | horizontal distance, center_neck to neck | neck width from the centre line |
| `neck_depth` | 8.00 | vertical distance, neck to center_neck | neck depth below the neck point |
| `neckline` | 11.34 | length along the outline, center_neck to neck | neckline length, half |
| `shoulder_length` | 12.64 | straight distance, neck to shoulder | shoulder seam |
| `shoulder_drop` | 6.00 | vertical distance, neck to shoulder | shoulder tip below the neck point |
| `shoulder_angle` | 28.33 | angle below the horizontal, degrees, neck to shoulder | shoulder slope |
| `width_at_underarm` | 26.00 | horizontal distance, center_neck to underarm | bust or chest line, quarter of the girth |
| `width_at_hem` | 26.00 | horizontal distance, center_neck to hem_side | outline width at the hem |
| `side_seam_to_hem` | 35.50 | length along the outline, dart legs left out, underarm to hem_side | side seam to the hem, bust dart closed |
| `hem` | 26.19 | length along the outline, hem_side to hem_front | hem edge on this piece |
| `length_centre` | 57.00 | vertical distance, center_neck to hem_front | centre line, neck to hem |
| `length_from_neck_point` | 65.00 | vertical distance, neck to hem_front | neck point to hem level |
| `overarm` | 32.36 | straight distance, shoulder to wrist_top | cut-on sleeve: shoulder tip to wrist |
| `wrist_width` | 15.00 | straight distance, wrist_top to wrist_under | cut-on sleeve: wrist, on this piece |
| `underarm_to_wrist` | 36.46 | length along the outline, wrist_under to underarm | cut-on sleeve: underarm seam |
| `extension` | 0.00 | horizontal distance, center_neck to front_neck | front edge past the centre line: button stand or wrap |

Not sewn: wrist_top..wrist_under, slash_in..slash_in_b, hem_side..neck.

## Back (bodice_back)

Width 48.26, height 61.00, perimeter 223.57, area 1836 cm2. Named points: center_neck, neck, shoulder, wrist_top, wrist_under, slash_mouth, slash_in, slash_in_b, underarm, hem_side, hem_cb.

| Parameter | Value | Measured as | What it is |
|---|---|---|---|
| `neck_width` | 7.20 | horizontal distance, center_neck to neck | neck width from the centre line |
| `neck_depth` | 2.00 | vertical distance, neck to center_neck | neck depth below the neck point |
| `neckline` | 7.79 | length along the outline, center_neck to neck | neckline length, half |
| `shoulder_length` | 13.44 | straight distance, neck to shoulder | shoulder seam |
| `shoulder_drop` | 5.04 | vertical distance, neck to shoulder | shoulder tip below the neck point |
| `shoulder_angle` | 22.01 | angle below the horizontal, degrees, neck to shoulder | shoulder slope |
| `width_at_underarm` | 26.00 | horizontal distance, center_neck to underarm | bust or chest line, quarter of the girth |
| `width_at_hem` | 26.00 | horizontal distance, center_neck to hem_side | outline width at the hem |
| `side_seam_to_hem` | 34.00 | length along the outline, dart legs left out, underarm to hem_side | side seam to the hem, bust dart closed |
| `hem` | 26.00 | length along the outline, hem_side to hem_cb | hem edge on this piece |
| `length_centre` | 59.00 | vertical distance, center_neck to hem_cb | centre line, neck to hem |
| `length_from_neck_point` | 61.00 | vertical distance, neck to hem_cb | neck point to hem level |
| `overarm` | 31.56 | straight distance, shoulder to wrist_top | cut-on sleeve: shoulder tip to wrist |
| `wrist_width` | 15.00 | straight distance, wrist_top to wrist_under | cut-on sleeve: wrist, on this piece |
| `underarm_to_wrist` | 36.78 | length along the outline, wrist_under to underarm | cut-on sleeve: underarm seam |

Not sewn: center_neck..neck, wrist_top..wrist_under, slash_in..slash_in_b, hem_side..hem_cb.

## Gusset (other)

Width 14.14, height 14.14, perimeter 40.00, area 100 cm2. Named points: tip_front, side_seam, tip_back, underarm_seam.

## Seams

| Edge A | cm | Edge B | cm | Ease | Why | |
|---|---|---|---|---|---|---|
| Front underarm..hem_side | 35.50 | Back underarm..hem_side | 34.00 | +4.4 % | side seam | OK |
| Back neck..shoulder | 13.44 | Front neck..shoulder | 12.64 | +6.3 % | back shoulder ease | OK |
| Back shoulder..wrist_top | 31.56 | Front shoulder..wrist_top | 32.36 | -2.5 % | kimono sleeve top seam | OK |
| Front wrist_under..slash_mouth | 16.36 | Back wrist_under..slash_mouth | 16.68 | -1.9 % | kimono underarm seam | OK |
| Front slash_in_b..underarm | 10.00 | Gusset tip_front..side_seam | 10.00 |  |  | OK |
| Back underarm..slash_in_b | 10.00 | Gusset side_seam..tip_back | 10.00 |  |  | OK |
| Back slash_in..slash_mouth | 10.00 | Gusset tip_back..underarm_seam | 10.00 |  |  | OK |
| Front slash_mouth..slash_in | 10.00 | Gusset underarm_seam..tip_front | 10.00 |  |  | OK |
| Back hem_cb..center_neck | 59.00 | Back hem_cb..center_neck | 59.00 |  |  | OK |

## Garment

| Measure | Value | Body | Ease | What it is |
|---|---|---|---|---|
| `finished_bust` | 104.00 | bust 88.00 | +16.00 | girth at the underarm line |
| `finished_hem` | 104.00 |  |  | girth at the hem |
| `neckline_total` | 38.27 | neck 37.00 | +1.27 | whole neckline |

## Completeness

Every typed piece has its standard points, every seam matches, every edge is accounted for.
