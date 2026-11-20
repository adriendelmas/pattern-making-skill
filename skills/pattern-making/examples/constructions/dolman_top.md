# Analysis: Dolman top, size 38

Measured by the skill from the outlines of the garment the engine drafts from this spec (`python scripts/pattern.py analyze dolman_top.json`), in cm at the reference size. Generated; do not edit.

Reference: bust 88.0, waist 68.0, hip 94.0, back_length 41.0, hip_depth 20.0, skirt_length 60.0, arm_length 59.0, wrist 16.0, body_rise 27.0, trouser_length 102.0, knee_width 42.0, hem_width 38.0, neck 37.0, shoulder 12.2, armhole_depth 21.0, half_back_width 17.0, half_chest_width 16.0, bust_depth 25.5, bust_span 18.5, bust_dart 4.0.

## Front (bodice_front)

Width 46.75, height 65.00, perimeter 191.79, area 1855 cm2. Named points: neck, shoulder, wrist_top, wrist_under, arm_curve, m2, underarm, hem_side, hem_mid, hem_front, front_neck, center_neck.

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
| `side_seam_to_hem` | 19.00 | length along the outline, dart legs left out, underarm to hem_side | side seam to the hem, bust dart closed |
| `hem` | 26.19 | length along the outline, hem_side to hem_front | hem edge on this piece |
| `length_centre` | 57.00 | vertical distance, center_neck to hem_front | centre line, neck to hem |
| `length_from_neck_point` | 65.00 | vertical distance, neck to hem_front | neck point to hem level |
| `overarm` | 37.36 | straight distance, shoulder to wrist_top | cut-on sleeve: shoulder tip to wrist |
| `wrist_width` | 12.00 | straight distance, wrist_top to wrist_under | cut-on sleeve: wrist, on this piece |
| `underarm_to_wrist` | 16.26 | length along the outline, wrist_under to underarm | cut-on sleeve: underarm seam |
| `extension` | 0.00 | horizontal distance, center_neck to front_neck | front edge past the centre line: button stand or wrap |

Not sewn: wrist_top..wrist_under, hem_side..neck.

## Back (bodice_back)

Width 47.67, height 61.00, perimeter 189.68, area 1868 cm2. Named points: center_neck, neck, shoulder, wrist_top, wrist_under, m1, arm_curve, underarm, hem_side, hem_cb.

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
| `side_seam_to_hem` | 17.50 | length along the outline, dart legs left out, underarm to hem_side | side seam to the hem, bust dart closed |
| `hem` | 26.00 | length along the outline, hem_side to hem_cb | hem edge on this piece |
| `length_centre` | 59.00 | vertical distance, center_neck to hem_cb | centre line, neck to hem |
| `length_from_neck_point` | 61.00 | vertical distance, neck to hem_cb | neck point to hem level |
| `overarm` | 36.56 | straight distance, shoulder to wrist_top | cut-on sleeve: shoulder tip to wrist |
| `wrist_width` | 12.00 | straight distance, wrist_top to wrist_under | cut-on sleeve: wrist, on this piece |
| `underarm_to_wrist` | 17.39 | length along the outline, wrist_under to underarm | cut-on sleeve: underarm seam |

Not sewn: center_neck..neck, wrist_top..wrist_under, hem_side..hem_cb.

## Seams

| Edge A | cm | Edge B | cm | Ease | Why | |
|---|---|---|---|---|---|---|
| Front underarm..hem_side | 19.00 | Back underarm..hem_side | 17.50 | +8.6 % | side seam | OK |
| Back neck..shoulder | 13.44 | Front neck..shoulder | 12.64 | +6.3 % | back shoulder ease | OK |
| Back shoulder..wrist_top | 36.56 | Front shoulder..wrist_top | 37.36 | -2.1 % | kimono sleeve top seam | OK |
| Front wrist_under..arm_curve | 9.04 | Back wrist_under..m1 | 9.66 | -6.5 % | kimono underarm seam | OK |
| Front arm_curve..m2 | 0.38 | Back m1..arm_curve | 0.41 | -6.5 % | kimono underarm seam | OK |
| Front m2..underarm | 6.85 | Back arm_curve..underarm | 7.32 | -6.5 % | kimono underarm seam | OK |
| Back hem_cb..center_neck | 59.00 | Back hem_cb..center_neck | 59.00 |  |  | OK |

## Garment

| Measure | Value | Body | Ease | What it is |
|---|---|---|---|---|
| `finished_bust` | 104.00 | bust 88.00 | +16.00 | girth at the underarm line |
| `finished_hem` | 104.00 |  |  | girth at the hem |
| `neckline_total` | 38.27 | neck 37.00 | +1.27 | whole neckline |

## Completeness

Every typed piece has its standard points, every seam matches, every edge is accounted for.
