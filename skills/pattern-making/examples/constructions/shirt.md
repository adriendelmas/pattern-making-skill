# Analysis: Shirt, size 38

Measured by the skill from the outlines of the garment the engine drafts from this spec (`python scripts/pattern.py analyze shirt.json`), in cm at the reference size. Generated; do not edit.

Reference: bust 88.0, waist 68.0, hip 94.0, back_length 41.0, hip_depth 20.0, skirt_length 60.0, arm_length 59.0, wrist 16.0, body_rise 27.0, trouser_length 102.0, knee_width 42.0, hem_width 38.0, neck 37.0, shoulder 12.2, armhole_depth 21.0, half_back_width 17.0, half_chest_width 16.0, bust_depth 25.5, bust_span 18.5, bust_dart 4.0.

## Front (bodice_front)

Width 28.25, height 77.00, perimeter 221.51, area 1832 cm2. Named points: neck, shoulder, across, underarm, side_dart_1, side_dart, side_dart_2, hem_side, hem_mid, hem_front, hold_end, front_neck, center_neck.

| Parameter | Value | Measured as | What it is |
|---|---|---|---|
| `neck_width` | 7.00 | horizontal distance, center_neck to neck | neck width from the centre line |
| `neck_depth` | 8.00 | vertical distance, neck to center_neck | neck depth below the neck point |
| `neckline` | 11.34 | length along the outline, center_neck to neck | neckline length, half |
| `shoulder_length` | 12.20 | straight distance, neck to shoulder | shoulder seam |
| `shoulder_drop` | 5.00 | vertical distance, neck to shoulder | shoulder tip below the neck point |
| `shoulder_angle` | 24.19 | angle below the horizontal, degrees, neck to shoulder | shoulder slope |
| `armhole` | 26.63 | length along the outline, shoulder to underarm | armhole length on this piece |
| `armhole_depth` | 20.00 | vertical distance, shoulder to underarm | underarm below the shoulder tip |
| `across_width` | 16.00 | horizontal distance, center_neck to across | across back or across chest, half |
| `width_at_underarm` | 26.50 | horizontal distance, center_neck to underarm | bust or chest line, quarter of the girth |
| `width_at_hem` | 26.50 | horizontal distance, center_neck to hem_side | outline width at the hem |
| `side_seam_to_hem` | 48.00 | length along the outline, dart legs left out, underarm to hem_side | side seam to the hem, bust dart closed |
| `hem` | 28.41 | length along the outline, hem_side to hem_front | hem edge on this piece |
| `length_centre` | 69.00 | vertical distance, center_neck to hem_front | centre line, neck to hem |
| `length_from_neck_point` | 77.00 | vertical distance, neck to hem_front | neck point to hem level |
| `extension` | 1.75 | horizontal distance, center_neck to front_neck | front edge past the centre line: button stand or wrap |
| `held_to` | 44.00 | vertical distance, neck to hold_end | level down to which the two fronts are held together, below the neck point |

Dart `side_dart`: intake 1.50, length 12.07, legs 11.92 and 12.26.

Not sewn: hem_side..front_neck.

## Back (bodice_back)

Width 26.50, height 73.00, perimeter 192.86, area 1703 cm2. Named points: center_neck, neck, shoulder, across, underarm, m1, hem_side, hem_cb.

| Parameter | Value | Measured as | What it is |
|---|---|---|---|
| `neck_width` | 7.20 | horizontal distance, center_neck to neck | neck width from the centre line |
| `neck_depth` | 2.00 | vertical distance, neck to center_neck | neck depth below the neck point |
| `neckline` | 7.79 | length along the outline, center_neck to neck | neckline length, half |
| `shoulder_length` | 13.00 | straight distance, neck to shoulder | shoulder seam |
| `shoulder_drop` | 4.00 | vertical distance, neck to shoulder | shoulder tip below the neck point |
| `shoulder_angle` | 17.92 | angle below the horizontal, degrees, neck to shoulder | shoulder slope |
| `armhole` | 26.56 | length along the outline, shoulder to underarm | armhole length on this piece |
| `armhole_depth` | 21.00 | vertical distance, shoulder to underarm | underarm below the shoulder tip |
| `across_width` | 17.00 | horizontal distance, center_neck to across | across back or across chest, half |
| `width_at_underarm` | 26.50 | horizontal distance, center_neck to underarm | bust or chest line, quarter of the girth |
| `width_at_hem` | 26.50 | horizontal distance, center_neck to hem_side | outline width at the hem |
| `side_seam_to_hem` | 48.00 | length along the outline, dart legs left out, underarm to hem_side | side seam to the hem, bust dart closed |
| `hem` | 26.50 | length along the outline, hem_side to hem_cb | hem edge on this piece |
| `length_centre` | 71.00 | vertical distance, center_neck to hem_cb | centre line, neck to hem |
| `length_from_neck_point` | 73.00 | vertical distance, neck to hem_cb | neck point to hem level |

Not sewn: hem_side..hem_cb.

## Collar (collar)

Width 23.13, height 7.73, perimeter 54.15, area 97 cm2. Named points: cb_neck, front_neck, point, cb_top.

| Parameter | Value | Measured as | What it is |
|---|---|---|---|
| `neck_edge` | 19.24 | length along the outline, cb_neck to front_neck | edge sewn to the neckline, half |
| `height_cb` | 4.50 | straight distance, cb_neck to cb_top | height at the centre back |
| `outer_edge` | 23.74 | length along the outline, front_neck to cb_top | front end and outer edge, half |
| `point_length` | 7.00 | straight distance, front_neck to point | front end of the collar, neck edge to its point |

Not sewn: front_neck..cb_top.

## Collar stand (collar_stand)

Width 21.54, height 3.98, perimeter 48.01, area 61 cm2. Named points: cb_neck, m4, m5, front_neck, front_top, fall_end, cb_top.

| Parameter | Value | Measured as | What it is |
|---|---|---|---|
| `neck_edge` | 20.89 | length along the outline, cb_neck to front_neck | edge sewn to the neckline, half |
| `top_edge` | 19.24 | length along the outline, fall_end to cb_top | edge sewn to the fall, half |
| `height_cb` | 3.20 | straight distance, cb_neck to cb_top | stand height at the centre back |
| `height_front` | 2.50 | straight distance, front_neck to front_top | stand height at the front end |

Not sewn: front_neck..fall_end.

## Sleeve (sleeve)

Width 39.45, height 59.00, perimeter 165.10, area 1739 cm2. Named points: crown, m3, back_underarm, back_wrist, front_wrist, front_underarm, m2.

| Parameter | Value | Measured as | What it is |
|---|---|---|---|
| `cap_height` | 17.08 | vertical distance, crown to back_underarm | cap height above the underarm line |
| `bicep_width` | 39.45 | horizontal distance, front_underarm to back_underarm | width at the underarm line |
| `cap_back` | 27.10 | length along the outline, crown to back_underarm | back half of the cap |
| `cap_front` | 27.09 | length along the outline, front_underarm to crown | front half of the cap |
| `underarm_seam` | 42.45 | length along the outline, back_underarm to back_wrist | underarm seam |
| `hem_width` | 26.00 | straight distance, back_wrist to front_wrist | hem, full width |
| `length` | 59.00 | vertical distance, crown to back_wrist | cap top to hem |

Not sewn: back_wrist..front_wrist.

## Welt (other)

Width 10.50, height 1.80, perimeter 24.60, area 19 cm2. Named points: w_top0, w_top1, w1, w0.

Not sewn: the whole outline.

## Seams

| Edge A | cm | Edge B | cm | Ease | Why | |
|---|---|---|---|---|---|---|
| Front underarm..side_dart_1 | 2.50 | Back underarm..m1 | 2.50 |  |  | OK |
| Front side_dart_2..hem_side | 45.50 | Back m1..hem_side | 45.50 |  |  | OK |
| Front side_dart_1..side_dart | 11.92 | Front side_dart_2..side_dart | 12.26 | -2.8 % | dart legs, trued | OK |
| Back neck..shoulder | 13.00 | Front neck..shoulder | 12.20 | +6.6 % | back shoulder ease | OK |
| Sleeve back_underarm..back_wrist | 42.45 | Sleeve front_underarm..front_wrist | 42.45 |  |  | OK |
| Sleeve front_underarm..m2 | 16.69 | Front underarm..across | 16.40 | +1.7 % | sleeve cap ease, front | OK |
| Sleeve m2..crown | 10.40 | Front across..shoulder | 10.22 | +1.7 % | sleeve cap ease, front | OK |
| Sleeve back_underarm..m3 | 17.91 | Back underarm..across | 17.55 | +2.0 % | sleeve cap ease, back | OK |
| Sleeve m3..crown | 9.20 | Back across..shoulder | 9.01 | +2.0 % | sleeve cap ease, back | OK |
| Back hem_cb..center_neck | 71.00 | Back hem_cb..center_neck | 71.00 |  |  | OK |
| Collar stand cb_neck..m4 | 7.79 | Back center_neck..neck | 7.79 |  |  | OK |
| Collar stand m4..m5 | 11.34 | Front neck..center_neck | 11.34 |  |  | OK |
| Collar stand m5..front_neck | 1.75 | Front center_neck..front_neck | 1.75 |  |  | OK |
| Collar stand cb_top..cb_neck | 3.20 | Collar stand cb_top..cb_neck | 3.20 |  |  | OK |
| Collar cb_neck..front_neck | 19.24 | Collar stand cb_top..fall_end | 19.24 |  |  | OK |
| Collar cb_top..cb_neck | 4.50 | Collar cb_top..cb_neck | 4.50 |  |  | OK |

## Garment

| Measure | Value | Body | Ease | What it is |
|---|---|---|---|---|
| `finished_bust` | 106.00 | bust 88.00 | +18.00 | girth at the underarm line |
| `finished_hem` | 106.00 |  |  | girth at the hem |
| `armhole_total` | 53.19 |  |  | whole armhole |
| `neckline_total` | 38.27 | neck 37.00 | +1.27 | whole neckline |
| `cap_total` | 54.19 |  |  | whole sleeve cap |
| `cap_ease` | 1.00 |  |  | sleeve cap longer than the armhole |

## Completeness

Every typed piece has its standard points, every seam matches, every edge is accounted for.
