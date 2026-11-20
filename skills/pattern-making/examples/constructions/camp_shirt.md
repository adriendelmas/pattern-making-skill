# Analysis: Camp shirt, size 38

Measured by the skill from the outlines of the garment the engine drafts from this spec (`python scripts/pattern.py analyze camp_shirt.json`), in cm at the reference size. Generated; do not edit.

Reference: bust 88.0, waist 68.0, hip 94.0, back_length 41.0, hip_depth 20.0, skirt_length 60.0, arm_length 59.0, wrist 16.0, body_rise 27.0, trouser_length 102.0, knee_width 42.0, hem_width 38.0, neck 37.0, shoulder 12.2, armhole_depth 21.0, half_back_width 17.0, half_chest_width 16.0, bust_depth 25.5, bust_span 18.5, bust_dart 4.0.

## Front (bodice_front)

Width 28.50, height 75.00, perimeter 217.83, area 1754 cm2. Named points: neck, shoulder, across, underarm, side_dart_1, side_dart, side_dart_2, hem_side, hem_mid, hem_front, hold_end, front_neck, center_neck.

| Parameter | Value | Measured as | What it is |
|---|---|---|---|
| `neck_width` | 7.00 | horizontal distance, center_neck to neck | neck width from the centre line |
| `neck_depth` | 14.00 | vertical distance, neck to center_neck | neck depth below the neck point |
| `neckline` | 16.36 | length along the outline, center_neck to neck | neckline length, half |
| `shoulder_length` | 12.20 | straight distance, neck to shoulder | shoulder seam |
| `shoulder_drop` | 5.00 | vertical distance, neck to shoulder | shoulder tip below the neck point |
| `shoulder_angle` | 24.19 | angle below the horizontal, degrees, neck to shoulder | shoulder slope |
| `armhole` | 26.64 | length along the outline, shoulder to underarm | armhole length on this piece |
| `armhole_depth` | 19.50 | vertical distance, shoulder to underarm | underarm below the shoulder tip |
| `across_width` | 16.00 | horizontal distance, center_neck to across | across back or across chest, half |
| `width_at_underarm` | 27.00 | horizontal distance, center_neck to underarm | bust or chest line, quarter of the girth |
| `width_at_hem` | 27.00 | horizontal distance, center_neck to hem_side | outline width at the hem |
| `side_seam_to_hem` | 46.50 | length along the outline, dart legs left out, underarm to hem_side | side seam to the hem, bust dart closed |
| `hem` | 28.67 | length along the outline, hem_side to hem_front | hem edge on this piece |
| `length_centre` | 61.00 | vertical distance, center_neck to hem_front | centre line, neck to hem |
| `length_from_neck_point` | 75.00 | vertical distance, neck to hem_front | neck point to hem level |
| `extension` | 1.50 | horizontal distance, center_neck to front_neck | front edge past the centre line: button stand or wrap |
| `held_to` | 42.00 | vertical distance, neck to hold_end | level down to which the two fronts are held together, below the neck point |

Dart `side_dart`: intake 1.50, length 12.45, legs 12.34 and 12.61.

Not sewn: hem_side..front_neck.

## Back (bodice_back)

Width 27.00, height 71.00, perimeter 189.82, area 1678 cm2. Named points: center_neck, neck, shoulder, across, underarm, m1, hem_side, hem_cb.

| Parameter | Value | Measured as | What it is |
|---|---|---|---|
| `neck_width` | 7.20 | horizontal distance, center_neck to neck | neck width from the centre line |
| `neck_depth` | 2.00 | vertical distance, neck to center_neck | neck depth below the neck point |
| `neckline` | 7.79 | length along the outline, center_neck to neck | neckline length, half |
| `shoulder_length` | 13.00 | straight distance, neck to shoulder | shoulder seam |
| `shoulder_drop` | 4.00 | vertical distance, neck to shoulder | shoulder tip below the neck point |
| `shoulder_angle` | 17.92 | angle below the horizontal, degrees, neck to shoulder | shoulder slope |
| `armhole` | 26.52 | length along the outline, shoulder to underarm | armhole length on this piece |
| `armhole_depth` | 20.50 | vertical distance, shoulder to underarm | underarm below the shoulder tip |
| `across_width` | 17.00 | horizontal distance, center_neck to across | across back or across chest, half |
| `width_at_underarm` | 27.00 | horizontal distance, center_neck to underarm | bust or chest line, quarter of the girth |
| `width_at_hem` | 27.00 | horizontal distance, center_neck to hem_side | outline width at the hem |
| `side_seam_to_hem` | 46.50 | length along the outline, dart legs left out, underarm to hem_side | side seam to the hem, bust dart closed |
| `hem` | 27.00 | length along the outline, hem_side to hem_cb | hem edge on this piece |
| `length_centre` | 69.00 | vertical distance, center_neck to hem_cb | centre line, neck to hem |
| `length_from_neck_point` | 71.00 | vertical distance, neck to hem_cb | neck point to hem level |

Not sewn: hem_side..hem_cb.

## Collar (collar)

Width 30.04, height 9.55, perimeter 71.28, area 189 cm2. Named points: cb_neck, m4, m5, front_neck, point, cb_top.

| Parameter | Value | Measured as | What it is |
|---|---|---|---|
| `neck_edge` | 25.66 | length along the outline, cb_neck to front_neck | edge sewn to the neckline, half |
| `height_cb` | 7.50 | straight distance, cb_neck to cb_top | height at the centre back |
| `outer_edge` | 33.16 | length along the outline, front_neck to cb_top | front end and outer edge, half |
| `point_length` | 8.00 | straight distance, front_neck to point | front end of the collar, neck edge to its point |

Not sewn: front_neck..cb_top.

## Sleeve (sleeve)

Width 39.53, height 24.00, perimeter 103.34, area 629 cm2. Named points: crown, m3, back_underarm, back_wrist, front_wrist, front_underarm, m2.

| Parameter | Value | Measured as | What it is |
|---|---|---|---|
| `cap_height` | 16.67 | vertical distance, crown to back_underarm | cap height above the underarm line |
| `bicep_width` | 39.53 | horizontal distance, front_underarm to back_underarm | width at the underarm line |
| `cap_back` | 26.84 | length along the outline, crown to back_underarm | back half of the cap |
| `cap_front` | 26.83 | length along the outline, front_underarm to crown | front half of the cap |
| `underarm_seam` | 7.84 | length along the outline, back_underarm to back_wrist | underarm seam |
| `hem_width` | 34.00 | straight distance, back_wrist to front_wrist | hem, full width |
| `length` | 24.00 | vertical distance, crown to back_wrist | cap top to hem |

Not sewn: back_wrist..front_wrist.

## Seams

| Edge A | cm | Edge B | cm | Ease | Why | |
|---|---|---|---|---|---|---|
| Front underarm..side_dart_1 | 2.50 | Back underarm..m1 | 2.50 |  |  | OK |
| Front side_dart_2..hem_side | 44.00 | Back m1..hem_side | 44.00 |  |  | OK |
| Front side_dart_1..side_dart | 12.34 | Front side_dart_2..side_dart | 12.61 | -2.1 % | dart legs, trued | OK |
| Back neck..shoulder | 13.00 | Front neck..shoulder | 12.20 | +6.6 % | back shoulder ease | OK |
| Sleeve back_underarm..back_wrist | 7.84 | Sleeve front_underarm..front_wrist | 7.84 |  |  | OK |
| Sleeve front_underarm..m2 | 16.53 | Front underarm..across | 16.42 | +0.7 % | sleeve cap ease, front | OK |
| Sleeve m2..crown | 10.30 | Front across..shoulder | 10.22 | +0.7 % | sleeve cap ease, front | OK |
| Sleeve back_underarm..m3 | 17.72 | Back underarm..across | 17.51 | +1.2 % | sleeve cap ease, back | OK |
| Sleeve m3..crown | 9.12 | Back across..shoulder | 9.01 | +1.2 % | sleeve cap ease, back | OK |
| Back hem_cb..center_neck | 69.00 | Back hem_cb..center_neck | 69.00 |  |  | OK |
| Collar cb_neck..m4 | 7.79 | Back center_neck..neck | 7.79 |  |  | OK |
| Collar m4..m5 | 16.36 | Front neck..center_neck | 16.36 |  |  | OK |
| Collar m5..front_neck | 1.50 | Front center_neck..front_neck | 1.50 |  |  | OK |
| Collar cb_top..cb_neck | 7.50 | Collar cb_top..cb_neck | 7.50 |  |  | OK |

## Garment

| Measure | Value | Body | Ease | What it is |
|---|---|---|---|---|
| `finished_bust` | 108.00 | bust 88.00 | +20.00 | girth at the underarm line |
| `finished_hem` | 108.00 |  |  | girth at the hem |
| `armhole_total` | 53.17 |  |  | whole armhole |
| `neckline_total` | 48.31 | neck 37.00 | +11.31 | whole neckline |
| `cap_total` | 53.67 |  |  | whole sleeve cap |
| `cap_ease` | 0.50 |  |  | sleeve cap longer than the armhole |

## Completeness

Every typed piece has its standard points, every seam matches, every edge is accounted for.
