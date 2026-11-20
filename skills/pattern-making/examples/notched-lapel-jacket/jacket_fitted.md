# Analysis: Notched-lapel jacket, fitted, size 38

Measured by the skill from the outlines of the garment the engine drafts from this spec (`python scripts/pattern.py analyze jacket_fitted.json`), in cm at the reference size. Generated; do not edit.

Reference: bust 88.0, waist 68.0, hip 94.0, back_length 41.0, hip_depth 20.0, skirt_length 60.0, arm_length 59.0, wrist 16.0, body_rise 27.0, trouser_length 102.0, knee_width 42.0, hem_width 38.0, neck 37.0, shoulder 12.2, armhole_depth 21.0, half_back_width 17.0, half_chest_width 16.0, bust_depth 25.5, bust_span 18.5, bust_dart 4.0.

## Front (bodice_front)

Width 29.71, height 70.00, perimeter 216.35, area 1582 cm2. Named points: neck, shoulder, across, m3, underarm, side_dart_1, side_dart, side_dart_2, side_waist, side_hip, hem_side, hem_front, hold_end, break, lapel_point, notch, gorge_roll, gorge_neck.

| Parameter | Value | Measured as | What it is |
|---|---|---|---|
| `neck_width` | 7.00 | horizontal distance, center_front to neck | neck width from the centre line |
| `shoulder_length` | 12.20 | straight distance, neck to shoulder | shoulder seam |
| `shoulder_drop` | 5.00 | vertical distance, neck to shoulder | shoulder tip below the neck point |
| `shoulder_angle` | 24.19 | angle below the horizontal, degrees, neck to shoulder | shoulder slope |
| `armhole` | 25.04 | length along the outline, shoulder to underarm | armhole length on this piece |
| `armhole_depth` | 19.50 | vertical distance, shoulder to underarm | underarm below the shoulder tip |
| `across_width` | 16.00 | horizontal distance, center_front to across | across back or across chest, half |
| `width_at_underarm` | 25.00 | horizontal distance, center_front to underarm | bust or chest line, quarter of the girth |
| `side_seam` | 18.63 | length along the outline, dart legs left out, underarm to side_waist | side seam to the waist, bust dart closed |
| `width_at_waist` | 22.60 | horizontal distance, center_front to side_waist | outline width at the waist |
| `waist_less_darts` | 19.00 | horizontal distance, less the darts drawn inside the piece, center_front to side_waist | waist on this piece: outline width less its inner darts |
| `width_at_hip` | 25.00 | horizontal distance, center_front to side_hip | outline width at the hip line |
| `width_at_hem` | 25.00 | horizontal distance, center_front to hem_side | outline width at the hem |
| `side_seam_to_hem` | 41.80 | length along the outline, dart legs left out, underarm to hem_side | side seam to the hem, bust dart closed |
| `hem` | 27.00 | length along the outline, hem_side to hem_front | hem edge on this piece |
| `length_from_neck_point` | 70.00 | vertical distance, neck to hem_front | neck point to hem level |
| `extension` | 2.00 | horizontal distance, center_front to break | front edge past the centre line: button stand or wrap |
| `held_to` | 38.00 | vertical distance, neck to hold_end | level down to which the two fronts are held together, below the neck point |
| `break_height` | 22.00 | vertical distance, neck to break | break point (where the lapel starts to roll) below the neck point |
| `lapel_width` | 7.50 | distance square to the line through two points, lapel_point to break > gorge_roll | lapel width, square to the roll line |
| `lapel_edge` | 18.11 | length along the outline, break to lapel_point | lapel edge, break point to lapel point |
| `lapel_step` | 3.50 | straight distance, lapel_point to notch | lapel point to the notch |
| `gorge` | 6.48 | length along the outline, notch to gorge_neck | gorge seam, sewn to the collar |

Dart `side_dart`: intake 4.00, length 13.32, legs 12.99 and 13.94.
Inner dart `waist_dart`: intake 3.60, length 33.50.

Not sewn: hem_side..notch.

## Back (bodice_back)

Width 25.00, height 66.00, perimeter 175.89, area 1375 cm2. Named points: center_neck, neck, shoulder, across, m5, underarm, m1, side_waist, side_hip, hem_side, hem_cb, cb_waist, cb_blade.

| Parameter | Value | Measured as | What it is |
|---|---|---|---|
| `neck_width` | 7.20 | horizontal distance, center_neck to neck | neck width from the centre line |
| `neck_depth` | 2.00 | vertical distance, neck to center_neck | neck depth below the neck point |
| `neckline` | 7.79 | length along the outline, center_neck to neck | neckline length, half |
| `shoulder_length` | 13.00 | straight distance, neck to shoulder | shoulder seam |
| `shoulder_drop` | 4.00 | vertical distance, neck to shoulder | shoulder tip below the neck point |
| `shoulder_angle` | 17.92 | angle below the horizontal, degrees, neck to shoulder | shoulder slope |
| `armhole` | 25.04 | length along the outline, shoulder to underarm | armhole length on this piece |
| `armhole_depth` | 20.50 | vertical distance, shoulder to underarm | underarm below the shoulder tip |
| `across_width` | 17.00 | horizontal distance, center_neck to across | across back or across chest, half |
| `width_at_underarm` | 25.00 | horizontal distance, center_neck to underarm | bust or chest line, quarter of the girth |
| `side_seam` | 18.66 | length along the outline, dart legs left out, underarm to side_waist | side seam to the waist, bust dart closed |
| `width_at_waist` | 21.60 | horizontal distance, cb_waist to side_waist | outline width at the waist |
| `waist_less_darts` | 18.00 | horizontal distance, less the darts drawn inside the piece, cb_waist to side_waist | waist on this piece: outline width less its inner darts |
| `width_at_hip` | 25.00 | horizontal distance, center_neck to side_hip | outline width at the hip line |
| `width_at_hem` | 25.00 | horizontal distance, center_neck to hem_side | outline width at the hem |
| `side_seam_to_hem` | 41.83 | length along the outline, dart legs left out, underarm to hem_side | side seam to the hem, bust dart closed |
| `hem` | 24.20 | length along the outline, hem_side to hem_cb | hem edge on this piece |
| `length_centre` | 64.00 | vertical distance, center_neck to hem_cb | centre line, neck to hem |
| `length_from_neck_point` | 66.00 | vertical distance, neck to hem_cb | neck point to hem level |
| `cb_waist_shaping` | 1.00 | horizontal distance, center_neck to cb_waist | centre back seam taken in at the waist |

Inner dart `waist_dart`: intake 3.60, length 32.00.

Not sewn: hem_side..hem_cb.

## Collar (collar)

Width 13.07, height 17.39, perimeter 46.31, area 111 cm2. Named points: cb_neck, neck, gorge_neck, m2, notch, collar_point, cb_top.

| Parameter | Value | Measured as | What it is |
|---|---|---|---|
| `neck_edge` | 15.08 | length along the outline, cb_neck to gorge_neck | edge sewn to the neckline, half |
| `height_cb` | 7.00 | straight distance, cb_neck to cb_top | height at the centre back |
| `outer_edge` | 17.75 | length along the outline, notch to cb_top | front end and outer edge, half |
| `point_length` | 3.20 | straight distance, notch to collar_point | front end of the collar, neck edge to its point |
| `gorge` | 6.48 | length along the outline, gorge_neck to notch | gorge seam, sewn to the lapel |

Not sewn: notch..cb_top.

## Top sleeve (sleeve_top)

Width 23.88, height 59.61, perimeter 152.66, area 1154 cm2. Named points: front_seam_cap, m4, crown, m6, back_seam_cap, vent_top, vent_corner, vent_hem, front_seam_hem, front_seam_elbow.

| Parameter | Value | Measured as | What it is |
|---|---|---|---|
| `cap` | 32.36 | length along the outline, front_seam_cap to back_seam_cap | cap on the top sleeve, seam to seam over the crown |
| `crown_height` | 8.19 | vertical distance, crown to back_seam_cap | crown above the top of the back seam |
| `width_at_cap` | 24.14 | straight distance, front_seam_cap to back_seam_cap | top sleeve width, seam to seam at the cap |
| `front_seam` | 47.38 | length along the outline, front_seam_hem to front_seam_cap | front seam |
| `back_seam` | 41.69 | length along the outline, back_seam_cap to vent_top | back seam, down to the vent if there is one |
| `vent_length` | 10.06 | vertical distance, vent_top to vent_hem | vent length |
| `vent_width` | 3.16 | straight distance, vent_top to vent_corner | vent extension |
| `hem_width` | 19.00 | straight distance, front_seam_hem to vent_hem | hem on the top sleeve |
| `length` | 59.00 | vertical distance, crown to front_seam_hem | crown to hem |

Not sewn: vent_top..front_seam_hem.

## Under sleeve (sleeve_under)

Width 16.14, height 50.81, perimeter 134.19, area 582 cm2. Named points: back_seam_cap, underarm, front_seam_cap, m7, front_seam_hem, wrist_side, vent_hem, vent_corner, vent_top.

| Parameter | Value | Measured as | What it is |
|---|---|---|---|
| `undercap` | 20.73 | length along the outline, back_seam_cap to front_seam_cap | cap on the under sleeve, seam to seam through the underarm |
| `width_at_cap` | 15.30 | straight distance, front_seam_cap to back_seam_cap | under sleeve width, seam to seam at the cap |
| `front_seam` | 47.38 | length along the outline, front_seam_cap to front_seam_hem | front seam |
| `back_seam` | 40.91 | length along the outline, vent_top to back_seam_cap | back seam, down to the vent if there is one |
| `hem_width` | 13.00 | straight distance, front_seam_hem to vent_hem | hem on the under sleeve |

Not sewn: front_seam_hem..vent_top.

## Seams

| Edge A | cm | Edge B | cm | Ease | Why | |
|---|---|---|---|---|---|---|
| Front underarm..side_dart_1 | 3.51 | Back underarm..m1 | 3.51 |  |  | OK |
| Front side_dart_2..side_waist | 15.12 | Back m1..side_waist | 15.14 |  |  | OK |
| Front side_waist..side_hip | 20.17 | Back side_waist..side_hip | 20.17 |  |  | OK |
| Front side_hip..hem_side | 3.00 | Back side_hip..hem_side | 3.00 |  |  | OK |
| Front side_dart_1..side_dart | 12.99 | Front side_dart_2..side_dart | 13.94 | -6.8 % | dart legs, trued | OK |
| Back neck..shoulder | 13.00 | Front neck..shoulder | 12.20 | +6.6 % | back shoulder ease | OK |
| Back hem_cb..cb_waist | 23.00 | Back hem_cb..cb_waist | 23.00 |  |  | OK |
| Back cb_waist..cb_blade | 23.03 | Back cb_waist..cb_blade | 23.03 |  |  | OK |
| Back cb_blade..center_neck | 18.00 | Back cb_blade..center_neck | 18.00 |  |  | OK |
| Collar cb_neck..neck | 7.79 | Back center_neck..neck | 7.79 |  |  | OK |
| Collar neck..gorge_neck | 7.29 | Front neck..gorge_neck | 7.29 |  |  | OK |
| Collar gorge_neck..m2 | 2.48 | Front gorge_neck..gorge_roll | 2.48 |  |  | OK |
| Collar m2..notch | 4.00 | Front gorge_roll..notch | 4.00 |  |  | OK |
| Collar cb_top..cb_neck | 7.00 | Collar cb_top..cb_neck | 7.00 |  |  | OK |
| Under sleeve underarm..front_seam_cap | 8.60 | Front underarm..m3 | 8.60 |  |  | OK |
| Top sleeve front_seam_cap..m4 | 6.78 | Front m3..across | 6.21 | +9.1 % | sleeve cap ease, front | OK |
| Top sleeve m4..crown | 11.15 | Front across..shoulder | 10.22 | +9.1 % | sleeve cap ease, front | OK |
| Under sleeve underarm..back_seam_cap | 12.12 | Back underarm..m5 | 12.12 |  |  | OK |
| Top sleeve back_seam_cap..m6 | 4.37 | Back m5..across | 3.91 | +11.7 % | sleeve cap ease, back | OK |
| Top sleeve m6..crown | 10.06 | Back across..shoulder | 9.01 | +11.7 % | sleeve cap ease, back | OK |
| Top sleeve front_seam_cap..front_seam_elbow | 23.74 | Under sleeve front_seam_cap..m7 | 23.74 |  |  | OK |
| Top sleeve front_seam_elbow..front_seam_hem | 23.64 | Under sleeve m7..front_seam_hem | 23.64 |  |  | OK |
| Top sleeve back_seam_cap..vent_top | 41.69 | Under sleeve back_seam_cap..vent_top | 40.91 | +1.9 % | elbow ease | OK |

## Garment

| Measure | Value | Body | Ease | What it is |
|---|---|---|---|---|
| `finished_bust` | 100.00 | bust 88.00 | +12.00 | girth at the underarm line |
| `finished_waist` | 74.00 | waist 68.00 | +6.00 | waist girth, inner darts and centre back shaping deducted |
| `finished_hip` | 100.00 | hip 94.00 | +6.00 | girth at the hip line |
| `finished_hem` | 100.00 |  |  | girth at the hem |
| `armhole_total` | 50.08 |  |  | whole armhole |
| `cap_total` | 53.08 |  |  | whole sleeve cap, top and under sleeve |
| `sleeve_width` | 39.44 |  |  | sleeve girth at the cap line, top and under sleeve |
| `sleeve_hem` | 32.00 | wrist 16.00 | +16.00 | sleeve hem girth, top and under sleeve |
| `cap_ease` | 3.00 |  |  | sleeve cap longer than the armhole |

## Completeness

Every typed piece has its standard points, every seam matches, every edge is accounted for.
