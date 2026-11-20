# Analysis: Hooded jacket, size 38

Measured by the skill from the outlines of the garment the engine drafts from this spec (`python scripts/pattern.py analyze hooded_jacket.json`), in cm at the reference size. Generated; do not edit.

Reference: bust 88.0, waist 68.0, hip 94.0, back_length 41.0, hip_depth 20.0, skirt_length 60.0, arm_length 59.0, wrist 16.0, body_rise 27.0, trouser_length 102.0, knee_width 42.0, hem_width 38.0, neck 37.0, shoulder 12.2, armhole_depth 21.0, half_back_width 17.0, half_chest_width 16.0, bust_depth 25.5, bust_span 18.5, bust_dart 4.0.

## Front (bodice_front)

Width 28.00, height 72.00, perimeter 214.77, area 1624 cm2. Named points: neck, shoulder, across, m4, underarm, side_dart_1, side_dart, side_dart_2, side_waist, side_hip, hem_side, hem_front, hold_end, front_neck, center_neck.

| Parameter | Value | Measured as | What it is |
|---|---|---|---|
| `neck_width` | 7.00 | horizontal distance, center_neck to neck | neck width from the centre line |
| `neck_depth` | 8.00 | vertical distance, neck to center_neck | neck depth below the neck point |
| `neckline` | 11.34 | length along the outline, center_neck to neck | neckline length, half |
| `shoulder_length` | 12.20 | straight distance, neck to shoulder | shoulder seam |
| `shoulder_drop` | 5.00 | vertical distance, neck to shoulder | shoulder tip below the neck point |
| `shoulder_angle` | 24.19 | angle below the horizontal, degrees, neck to shoulder | shoulder slope |
| `armhole` | 26.23 | length along the outline, shoulder to underarm | armhole length on this piece |
| `armhole_depth` | 20.00 | vertical distance, shoulder to underarm | underarm below the shoulder tip |
| `across_width` | 16.00 | horizontal distance, center_neck to across | across back or across chest, half |
| `width_at_underarm` | 26.00 | horizontal distance, center_neck to underarm | bust or chest line, quarter of the girth |
| `side_seam` | 18.14 | length along the outline, dart legs left out, underarm to side_waist | side seam to the waist, bust dart closed |
| `width_at_waist` | 23.60 | horizontal distance, center_neck to side_waist | outline width at the waist |
| `waist_less_darts` | 20.00 | horizontal distance, less the darts drawn inside the piece, center_neck to side_waist | waist on this piece: outline width less its inner darts |
| `width_at_hip` | 25.00 | horizontal distance, center_neck to side_hip | outline width at the hip line |
| `width_at_hem` | 25.00 | horizontal distance, center_neck to hem_side | outline width at the hem |
| `side_seam_to_hem` | 43.20 | length along the outline, dart legs left out, underarm to hem_side | side seam to the hem, bust dart closed |
| `hem` | 27.00 | length along the outline, hem_side to hem_front | hem edge on this piece |
| `length_centre` | 64.00 | vertical distance, center_neck to hem_front | centre line, neck to hem |
| `length_from_neck_point` | 72.00 | vertical distance, neck to hem_front | neck point to hem level |
| `extension` | 2.00 | horizontal distance, center_neck to front_neck | front edge past the centre line: button stand or wrap |
| `held_to` | 30.00 | vertical distance, neck to hold_end | level down to which the two fronts are held together, below the neck point |

Dart `side_dart`: intake 4.00, length 14.27, legs 13.97 and 14.83.
Inner dart `waist_dart`: intake 3.60, length 33.50.

Not sewn: hem_side..front_neck.

## Back (bodice_back)

Width 26.00, height 68.00, perimeter 180.44, area 1451 cm2. Named points: center_neck, neck, shoulder, across, m6, underarm, m1, side_waist, side_hip, hem_side, hem_cb, cb_waist, cb_blade.

| Parameter | Value | Measured as | What it is |
|---|---|---|---|
| `neck_width` | 7.20 | horizontal distance, center_neck to neck | neck width from the centre line |
| `neck_depth` | 2.00 | vertical distance, neck to center_neck | neck depth below the neck point |
| `neckline` | 7.79 | length along the outline, center_neck to neck | neckline length, half |
| `shoulder_length` | 13.00 | straight distance, neck to shoulder | shoulder seam |
| `shoulder_drop` | 4.00 | vertical distance, neck to shoulder | shoulder tip below the neck point |
| `shoulder_angle` | 17.92 | angle below the horizontal, degrees, neck to shoulder | shoulder slope |
| `armhole` | 26.20 | length along the outline, shoulder to underarm | armhole length on this piece |
| `armhole_depth` | 21.00 | vertical distance, shoulder to underarm | underarm below the shoulder tip |
| `across_width` | 17.00 | horizontal distance, center_neck to across | across back or across chest, half |
| `width_at_underarm` | 26.00 | horizontal distance, center_neck to underarm | bust or chest line, quarter of the girth |
| `side_seam` | 18.16 | length along the outline, dart legs left out, underarm to side_waist | side seam to the waist, bust dart closed |
| `width_at_waist` | 22.60 | horizontal distance, cb_waist to side_waist | outline width at the waist |
| `waist_less_darts` | 19.00 | horizontal distance, less the darts drawn inside the piece, cb_waist to side_waist | waist on this piece: outline width less its inner darts |
| `width_at_hip` | 25.00 | horizontal distance, center_neck to side_hip | outline width at the hip line |
| `width_at_hem` | 25.00 | horizontal distance, center_neck to hem_side | outline width at the hem |
| `side_seam_to_hem` | 43.22 | length along the outline, dart legs left out, underarm to hem_side | side seam to the hem, bust dart closed |
| `hem` | 24.20 | length along the outline, hem_side to hem_cb | hem edge on this piece |
| `length_centre` | 66.00 | vertical distance, center_neck to hem_cb | centre line, neck to hem |
| `length_from_neck_point` | 68.00 | vertical distance, neck to hem_cb | neck point to hem level |
| `cb_waist_shaping` | 1.00 | horizontal distance, center_neck to cb_waist | centre back seam taken in at the waist |

Inner dart `waist_dart`: intake 3.60, length 32.00.

Not sewn: hem_side..hem_cb.

## Hood (hood)

Width 30.00, height 34.00, perimeter 115.12, area 838 cm2. Named points: cb_neck, m2, m3, face_neck, face_top, top_back, cb_round.

| Parameter | Value | Measured as | What it is |
|---|---|---|---|
| `neck_edge` | 21.14 | length along the outline, cb_neck to face_neck | edge sewn to the neckline, half |
| `face_edge` | 35.14 | length along the outline, face_neck to face_top | edge round the face |
| `face_height` | 34.00 | vertical distance, face_neck to face_top | height of the face opening |
| `depth` | 30.00 | horizontal distance, face_top to cb_round | front to back at the top of the head |
| `top_seam` | 18.00 | length along the outline, face_top to top_back | seam over the head: face to the back of the crown |
| `back_curve` | 18.85 | length along the outline, top_back to cb_round | seam over the head: round the back of the crown |
| `back_seam` | 22.00 | length along the outline, cb_round to cb_neck | seam over the head: down to the nape |

Not sewn: face_neck..face_top.

## Top sleeve (sleeve_top)

Width 24.70, height 59.56, perimeter 149.08, area 1177 cm2. Named points: front_seam_cap, m5, crown, m7, back_seam_cap, back_seam_hem, front_seam_hem, front_seam_elbow.

| Parameter | Value | Measured as | What it is |
|---|---|---|---|
| `cap` | 33.17 | length along the outline, front_seam_cap to back_seam_cap | cap on the top sleeve, seam to seam over the crown |
| `crown_height` | 8.31 | vertical distance, crown to back_seam_cap | crown above the top of the back seam |
| `width_at_cap` | 24.96 | straight distance, front_seam_cap to back_seam_cap | top sleeve width, seam to seam at the cap |
| `front_seam` | 47.25 | length along the outline, front_seam_hem to front_seam_cap | front seam |
| `back_seam` | 51.66 | length along the outline, back_seam_cap to back_seam_hem | back seam, down to the vent if there is one |
| `hem_width` | 17.00 | straight distance, front_seam_hem to back_seam_hem | hem on the top sleeve |
| `length` | 58.99 | vertical distance, crown to front_seam_hem | crown to hem |

Not sewn: back_seam_hem..front_seam_hem.

## Under sleeve (sleeve_under)

Width 15.85, height 50.69, perimeter 130.80, area 583 cm2. Named points: back_seam_cap, underarm, front_seam_cap, m8, front_seam_hem, wrist_side, back_seam_hem.

| Parameter | Value | Measured as | What it is |
|---|---|---|---|
| `undercap` | 21.76 | length along the outline, back_seam_cap to front_seam_cap | cap on the under sleeve, seam to seam through the underarm |
| `width_at_cap` | 16.10 | straight distance, front_seam_cap to back_seam_cap | under sleeve width, seam to seam at the cap |
| `front_seam` | 47.25 | length along the outline, front_seam_cap to front_seam_hem | front seam |
| `back_seam` | 50.79 | length along the outline, back_seam_hem to back_seam_cap | back seam, down to the vent if there is one |
| `hem_width` | 11.00 | straight distance, front_seam_hem to back_seam_hem | hem on the under sleeve |

Not sewn: front_seam_hem..back_seam_hem.

## Welt (other)

Width 10.50, height 1.80, perimeter 24.60, area 19 cm2. Named points: w_top0, w_top1, w1, w0.

Not sewn: the whole outline.

## Seams

| Edge A | cm | Edge B | cm | Ease | Why | |
|---|---|---|---|---|---|---|
| Front underarm..side_dart_1 | 3.02 | Back underarm..m1 | 3.02 |  |  | OK |
| Front side_dart_2..side_waist | 15.12 | Back m1..side_waist | 15.14 |  |  | OK |
| Front side_waist..side_hip | 20.06 | Back side_waist..side_hip | 20.06 |  |  | OK |
| Front side_hip..hem_side | 5.00 | Back side_hip..hem_side | 5.00 |  |  | OK |
| Front side_dart_1..side_dart | 13.97 | Front side_dart_2..side_dart | 14.83 | -5.8 % | dart legs, trued | OK |
| Back neck..shoulder | 13.00 | Front neck..shoulder | 12.20 | +6.6 % | back shoulder ease | OK |
| Back hem_cb..cb_waist | 25.00 | Back hem_cb..cb_waist | 25.00 |  |  | OK |
| Back cb_waist..cb_blade | 23.03 | Back cb_waist..cb_blade | 23.03 |  |  | OK |
| Back cb_blade..center_neck | 18.00 | Back cb_blade..center_neck | 18.00 |  |  | OK |
| Hood cb_neck..m2 | 7.79 | Back center_neck..neck | 7.79 |  |  | OK |
| Hood m2..m3 | 11.34 | Front neck..center_neck | 11.34 |  |  | OK |
| Hood m3..face_neck | 2.00 | Front center_neck..front_neck | 2.00 |  |  | OK |
| Hood cb_neck..cb_round | 22.00 | Hood cb_neck..cb_round | 22.00 |  |  | OK |
| Hood cb_round..top_back | 18.85 | Hood cb_round..top_back | 18.85 |  |  | OK |
| Hood top_back..face_top | 18.00 | Hood top_back..face_top | 18.00 |  |  | OK |
| Under sleeve underarm..front_seam_cap | 9.12 | Front underarm..m4 | 9.12 |  |  | OK |
| Top sleeve front_seam_cap..m5 | 7.38 | Front m4..across | 6.88 | +7.2 % | sleeve cap ease, front | OK |
| Top sleeve m5..crown | 10.96 | Front across..shoulder | 10.22 | +7.2 % | sleeve cap ease, front | OK |
| Under sleeve underarm..back_seam_cap | 12.63 | Back underarm..m6 | 12.63 |  |  | OK |
| Top sleeve back_seam_cap..m7 | 4.98 | Back m6..across | 4.55 | +9.4 % | sleeve cap ease, back | OK |
| Top sleeve m7..crown | 9.86 | Back across..shoulder | 9.01 | +9.4 % | sleeve cap ease, back | OK |
| Top sleeve front_seam_cap..front_seam_elbow | 23.68 | Under sleeve front_seam_cap..m8 | 23.68 |  |  | OK |
| Top sleeve front_seam_elbow..front_seam_hem | 23.57 | Under sleeve m8..front_seam_hem | 23.57 |  |  | OK |
| Top sleeve back_seam_cap..back_seam_hem | 51.66 | Under sleeve back_seam_cap..back_seam_hem | 50.79 | +1.7 % | elbow ease | OK |

## Garment

| Measure | Value | Body | Ease | What it is |
|---|---|---|---|---|
| `finished_bust` | 104.00 | bust 88.00 | +16.00 | girth at the underarm line |
| `finished_waist` | 78.00 | waist 68.00 | +10.00 | waist girth, inner darts and centre back shaping deducted |
| `finished_hip` | 100.00 | hip 94.00 | +6.00 | girth at the hip line |
| `finished_hem` | 100.00 |  |  | girth at the hem |
| `armhole_total` | 52.43 |  |  | whole armhole |
| `neckline_total` | 38.27 | neck 37.00 | +1.27 | whole neckline |
| `cap_total` | 54.93 |  |  | whole sleeve cap, top and under sleeve |
| `sleeve_width` | 41.06 |  |  | sleeve girth at the cap line, top and under sleeve |
| `sleeve_hem` | 28.00 | wrist 16.00 | +12.00 | sleeve hem girth, top and under sleeve |
| `cap_ease` | 2.50 |  |  | sleeve cap longer than the armhole |

## Completeness

Every typed piece has its standard points, every seam matches, every edge is accounted for.
