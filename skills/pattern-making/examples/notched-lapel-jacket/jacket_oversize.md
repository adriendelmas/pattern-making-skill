# Analysis: Notched-lapel jacket, oversize with shoulder pads, size 38

Measured by the skill from the outlines of the garment the engine drafts from this spec (`python scripts/pattern.py analyze jacket_oversize.json`), in cm at the reference size. Generated; do not edit.

Reference: bust 88.0, waist 68.0, hip 94.0, back_length 41.0, hip_depth 20.0, skirt_length 60.0, arm_length 59.0, wrist 16.0, body_rise 27.0, trouser_length 102.0, knee_width 42.0, hem_width 38.0, neck 37.0, shoulder 12.2, armhole_depth 21.0, half_back_width 17.0, half_chest_width 16.0, bust_depth 25.5, bust_span 18.5, bust_dart 4.0.

## Front (bodice_front)

Width 31.29, height 75.00, perimeter 229.70, area 1902 cm2. Named points: neck, shoulder, across, m3, underarm, side_dart_1, side_dart, side_dart_2, hem_side, hem_mid, hem_front, hold_end, break, lapel_point, notch, gorge_roll, gorge_neck.

| Parameter | Value | Measured as | What it is |
|---|---|---|---|
| `neck_width` | 7.00 | horizontal distance, center_front to neck | neck width from the centre line |
| `shoulder_length` | 15.15 | straight distance, neck to shoulder | shoulder seam |
| `shoulder_drop` | 4.93 | vertical distance, neck to shoulder | shoulder tip below the neck point |
| `shoulder_angle` | 19.01 | angle below the horizontal, degrees, neck to shoulder | shoulder slope |
| `armhole` | 28.04 | length along the outline, shoulder to underarm | armhole length on this piece |
| `armhole_depth` | 22.07 | vertical distance, shoulder to underarm | underarm below the shoulder tip |
| `across_width` | 17.50 | horizontal distance, center_front to across | across back or across chest, half |
| `width_at_underarm` | 27.00 | horizontal distance, center_front to underarm | bust or chest line, quarter of the girth |
| `width_at_hem` | 27.00 | horizontal distance, center_front to hem_side | outline width at the hem |
| `side_seam_to_hem` | 44.00 | length along the outline, dart legs left out, underarm to hem_side | side seam to the hem, bust dart closed |
| `hem` | 29.20 | length along the outline, hem_side to hem_front | hem edge on this piece |
| `length_from_neck_point` | 75.00 | vertical distance, neck to hem_front | neck point to hem level |
| `extension` | 2.00 | horizontal distance, center_front to break | front edge past the centre line: button stand or wrap |
| `held_to` | 52.00 | vertical distance, neck to hold_end | level down to which the two fronts are held together, below the neck point |
| `break_height` | 36.00 | vertical distance, neck to break | break point (where the lapel starts to roll) below the neck point |
| `lapel_width` | 7.50 | distance square to the line through two points, lapel_point to break > gorge_roll | lapel width, square to the roll line |
| `lapel_edge` | 30.92 | length along the outline, break to lapel_point | lapel edge, break point to lapel point |
| `lapel_step` | 3.50 | straight distance, lapel_point to notch | lapel point to the notch |
| `gorge` | 6.47 | length along the outline, notch to gorge_neck | gorge seam, sewn to the collar |

Dart `side_dart`: intake 1.50, length 13.14, legs 12.89 and 13.43.

Not sewn: hem_side..notch.

## Back (bodice_back)

Width 27.00, height 71.00, perimeter 192.46, area 1705 cm2. Named points: center_neck, neck, shoulder, across, m5, underarm, m1, hem_side, hem_cb.

| Parameter | Value | Measured as | What it is |
|---|---|---|---|
| `neck_width` | 7.20 | horizontal distance, center_neck to neck | neck width from the centre line |
| `neck_depth` | 2.00 | vertical distance, neck to center_neck | neck depth below the neck point |
| `neckline` | 7.83 | length along the outline, center_neck to neck | neckline length, half |
| `shoulder_length` | 15.95 | straight distance, neck to shoulder | shoulder seam |
| `shoulder_drop` | 3.54 | vertical distance, neck to shoulder | shoulder tip below the neck point |
| `shoulder_angle` | 12.84 | angle below the horizontal, degrees, neck to shoulder | shoulder slope |
| `armhole` | 28.69 | length along the outline, shoulder to underarm | armhole length on this piece |
| `armhole_depth` | 23.46 | vertical distance, shoulder to underarm | underarm below the shoulder tip |
| `across_width` | 18.50 | horizontal distance, center_neck to across | across back or across chest, half |
| `width_at_underarm` | 27.00 | horizontal distance, center_neck to underarm | bust or chest line, quarter of the girth |
| `width_at_hem` | 27.00 | horizontal distance, center_neck to hem_side | outline width at the hem |
| `side_seam_to_hem` | 44.00 | length along the outline, dart legs left out, underarm to hem_side | side seam to the hem, bust dart closed |
| `hem` | 27.00 | length along the outline, hem_side to hem_cb | hem edge on this piece |
| `length_centre` | 69.00 | vertical distance, center_neck to hem_cb | centre line, neck to hem |
| `length_from_neck_point` | 71.00 | vertical distance, neck to hem_cb | neck point to hem level |

Not sewn: hem_side..hem_cb.

## Collar (collar)

Width 12.05, height 17.29, perimeter 46.01, area 110 cm2. Named points: cb_neck, neck, gorge_neck, m2, notch, collar_point, cb_top.

| Parameter | Value | Measured as | What it is |
|---|---|---|---|
| `neck_edge` | 14.94 | length along the outline, cb_neck to gorge_neck | edge sewn to the neckline, half |
| `height_cb` | 7.00 | straight distance, cb_neck to cb_top | height at the centre back |
| `outer_edge` | 17.60 | length along the outline, notch to cb_top | front end and outer edge, half |
| `point_length` | 3.20 | straight distance, notch to collar_point | front end of the collar, neck edge to its point |
| `gorge` | 6.47 | length along the outline, gorge_neck to notch | gorge seam, sewn to the lapel |

Not sewn: notch..cb_top.

## Top sleeve (sleeve_top)

Width 27.13, height 57.60, perimeter 152.47, area 1238 cm2. Named points: front_seam_cap, m4, crown, m6, back_seam_cap, vent_top, vent_corner, vent_hem, front_seam_hem, front_seam_elbow.

| Parameter | Value | Measured as | What it is |
|---|---|---|---|
| `cap` | 34.95 | length along the outline, front_seam_cap to back_seam_cap | cap on the top sleeve, seam to seam over the crown |
| `crown_height` | 8.27 | vertical distance, crown to back_seam_cap | crown above the top of the back seam |
| `width_at_cap` | 27.35 | straight distance, front_seam_cap to back_seam_cap | top sleeve width, seam to seam at the cap |
| `front_seam` | 45.49 | length along the outline, front_seam_hem to front_seam_cap | front seam |
| `back_seam` | 39.76 | length along the outline, back_seam_cap to vent_top | back seam, down to the vent if there is one |
| `vent_length` | 10.04 | vertical distance, vent_top to vent_hem | vent length |
| `vent_width` | 3.16 | straight distance, vent_top to vent_corner | vent extension |
| `hem_width` | 20.00 | straight distance, front_seam_hem to vent_hem | hem on the top sleeve |
| `length` | 57.01 | vertical distance, crown to front_seam_hem | crown to hem |

Not sewn: vent_top..front_seam_hem.

## Under sleeve (sleeve_under)

Width 18.23, height 48.73, perimeter 134.87, area 634 cm2. Named points: back_seam_cap, underarm, front_seam_cap, m7, front_seam_hem, wrist_side, vent_hem, vent_corner, vent_top.

| Parameter | Value | Measured as | What it is |
|---|---|---|---|
| `undercap` | 24.28 | length along the outline, back_seam_cap to front_seam_cap | cap on the under sleeve, seam to seam through the underarm |
| `width_at_cap` | 18.45 | straight distance, front_seam_cap to back_seam_cap | under sleeve width, seam to seam at the cap |
| `front_seam` | 45.49 | length along the outline, front_seam_cap to front_seam_hem | front seam |
| `back_seam` | 38.91 | length along the outline, vent_top to back_seam_cap | back seam, down to the vent if there is one |
| `hem_width` | 14.00 | straight distance, front_seam_hem to vent_hem | hem on the under sleeve |

Not sewn: front_seam_hem..vent_top.

## Seams

| Edge A | cm | Edge B | cm | Ease | Why | |
|---|---|---|---|---|---|---|
| Front underarm..side_dart_1 | 2.50 | Back underarm..m1 | 2.50 |  |  | OK |
| Front side_dart_2..hem_side | 41.50 | Back m1..hem_side | 41.50 |  |  | OK |
| Front side_dart_1..side_dart | 12.89 | Front side_dart_2..side_dart | 13.43 | -4.0 % | dart legs, trued | OK |
| Back neck..shoulder | 15.95 | Front neck..shoulder | 15.15 | +5.3 % | back shoulder ease | OK |
| Back hem_cb..center_neck | 69.00 | Back hem_cb..center_neck | 69.00 |  |  | OK |
| Collar cb_neck..neck | 7.83 | Back center_neck..neck | 7.83 |  |  | OK |
| Collar neck..gorge_neck | 7.11 | Front neck..gorge_neck | 7.11 |  |  | OK |
| Collar gorge_neck..m2 | 2.47 | Front gorge_neck..gorge_roll | 2.47 |  |  | OK |
| Collar m2..notch | 4.00 | Front gorge_roll..notch | 4.00 |  |  | OK |
| Collar cb_top..cb_neck | 7.00 | Collar cb_top..cb_neck | 7.00 |  |  | OK |
| Under sleeve underarm..front_seam_cap | 10.46 | Front underarm..m3 | 10.46 |  |  | OK |
| Top sleeve front_seam_cap..m4 | 7.40 | Front m3..across | 6.80 | +8.9 % | sleeve cap ease, front | OK |
| Top sleeve m4..crown | 11.74 | Front across..shoulder | 10.78 | +8.9 % | sleeve cap ease, front | OK |
| Under sleeve underarm..back_seam_cap | 13.81 | Back underarm..m5 | 13.81 |  |  | OK |
| Top sleeve back_seam_cap..m6 | 5.05 | Back m5..across | 4.75 | +6.3 % | sleeve cap ease, back | OK |
| Top sleeve m6..crown | 10.76 | Back across..shoulder | 10.13 | +6.3 % | sleeve cap ease, back | OK |
| Top sleeve front_seam_cap..front_seam_elbow | 22.82 | Under sleeve front_seam_cap..m7 | 22.82 |  |  | OK |
| Top sleeve front_seam_elbow..front_seam_hem | 22.67 | Under sleeve m7..front_seam_hem | 22.67 |  |  | OK |
| Top sleeve back_seam_cap..vent_top | 39.76 | Under sleeve back_seam_cap..vent_top | 38.91 | +2.2 % | elbow ease | OK |

## Garment

| Measure | Value | Body | Ease | What it is |
|---|---|---|---|---|
| `finished_bust` | 108.00 | bust 88.00 | +20.00 | girth at the underarm line |
| `finished_hem` | 108.00 |  |  | girth at the hem |
| `armhole_total` | 56.73 |  |  | whole armhole |
| `cap_total` | 59.23 |  |  | whole sleeve cap, top and under sleeve |
| `sleeve_width` | 45.80 |  |  | sleeve girth at the cap line, top and under sleeve |
| `sleeve_hem` | 34.00 | wrist 16.00 | +18.00 | sleeve hem girth, top and under sleeve |
| `cap_ease` | 2.50 |  |  | sleeve cap longer than the armhole |

## Completeness

Every typed piece has its standard points, every seam matches, every edge is accounted for.
