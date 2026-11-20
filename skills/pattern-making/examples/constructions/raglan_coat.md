# Analysis: Raglan coat, size 38

Measured by the skill from the outlines of the garment the engine drafts from this spec (`python scripts/pattern.py analyze raglan_coat.json`), in cm at the reference size. Generated; do not edit.

Reference: bust 88.0, waist 68.0, hip 94.0, back_length 41.0, hip_depth 20.0, skirt_length 60.0, arm_length 59.0, wrist 16.0, body_rise 27.0, trouser_length 102.0, knee_width 42.0, hem_width 38.0, neck 37.0, shoulder 12.2, armhole_depth 21.0, half_back_width 17.0, half_chest_width 16.0, bust_depth 25.5, bust_span 18.5, bust_dart 4.0.

## Front (bodice_front)

Width 29.50, height 88.34, perimeter 243.25, area 2244 cm2. Named points: raglan_arm, underarm, side_dart_1, side_dart, side_dart_2, hem_side, hem_mid, hem_front, hold_end, front_neck, center_neck, raglan_neck.

| Parameter | Value | Measured as | What it is |
|---|---|---|---|
| `neckline_to_raglan` | 7.34 | length along the outline, center_neck to raglan_neck | neckline on this piece, up to the raglan seam |
| `width_at_underarm` | 27.00 | horizontal distance, center_neck to underarm | bust or chest line, quarter of the girth |
| `width_at_hem` | 27.00 | horizontal distance, center_neck to hem_side | outline width at the hem |
| `side_seam_to_hem` | 62.00 | length along the outline, dart legs left out, underarm to hem_side | side seam to the hem, bust dart closed |
| `hem` | 29.68 | length along the outline, hem_side to hem_front | hem edge on this piece |
| `length_centre` | 84.00 | vertical distance, center_neck to hem_front | centre line, neck to hem |
| `length_from_neck_point` | 88.34 | vertical distance, raglan_neck to hem_front | neck point to hem level |
| `raglan_line` | 28.57 | length along the outline, raglan_neck to raglan_arm | raglan seam, neck to armhole |
| `raglan_underarm` | 3.50 | length along the outline, raglan_arm to underarm | lower armhole below the raglan seam |
| `extension` | 2.50 | horizontal distance, center_neck to front_neck | front edge past the centre line: button stand or wrap |
| `held_to` | 34.34 | vertical distance, raglan_neck to hold_end | level down to which the two fronts are held together, below the neck point |

Dart `side_dart`: intake 1.50, length 12.81, legs 12.61 and 13.05.

Not sewn: hem_side..front_neck.

## Back (bodice_back)

Width 27.00, height 86.26, perimeter 213.24, area 1988 cm2. Named points: center_neck, raglan_neck, raglan_arm, underarm, m1, hem_side, hem_cb.

| Parameter | Value | Measured as | What it is |
|---|---|---|---|
| `neckline_to_raglan` | 3.79 | length along the outline, center_neck to raglan_neck | neckline on this piece, up to the raglan seam |
| `width_at_underarm` | 27.00 | horizontal distance, center_neck to underarm | bust or chest line, quarter of the girth |
| `width_at_hem` | 27.00 | horizontal distance, center_neck to hem_side | outline width at the hem |
| `side_seam_to_hem` | 62.00 | length along the outline, dart legs left out, underarm to hem_side | side seam to the hem, bust dart closed |
| `hem` | 27.00 | length along the outline, hem_side to hem_cb | hem edge on this piece |
| `length_centre` | 86.00 | vertical distance, center_neck to hem_cb | centre line, neck to hem |
| `length_from_neck_point` | 86.26 | vertical distance, raglan_neck to hem_cb | neck point to hem level |
| `raglan_line` | 30.95 | length along the outline, raglan_neck to raglan_arm | raglan seam, neck to armhole |
| `raglan_underarm` | 3.50 | length along the outline, raglan_arm to underarm | lower armhole below the raglan seam |

Not sewn: hem_side..hem_cb.

## Collar (collar)

Width 21.64, height 5.50, perimeter 53.78, area 114 cm2. Named points: cb_neck, m2, m3, m4, m5, front_neck, front_top, cb_top.

| Parameter | Value | Measured as | What it is |
|---|---|---|---|
| `neck_edge` | 21.64 | length along the outline, cb_neck to front_neck | edge sewn to the neckline, half |
| `height_cb` | 5.00 | straight distance, cb_neck to cb_top | height at the centre back |
| `outer_edge` | 26.64 | length along the outline, front_neck to cb_top | front end and outer edge, half |
| `point_length` | 5.50 | straight distance, front_neck to front_top | front end of the collar, neck edge to its point |

Not sewn: front_neck..cb_top.

## Sleeve (sleeve_raglan)

Width 40.40, height 74.01, perimeter 219.52, area 2223 cm2. Named points: front_wrist, front_underarm, cap_front_low, raglan_front_neck, neck_front, shoulder, neck_back, raglan_back_neck, cap_back_low, back_underarm, back_wrist.

| Parameter | Value | Measured as | What it is |
|---|---|---|---|
| `raglan_front` | 32.07 | length along the outline, raglan_front_neck to front_underarm | front raglan seam and lower cap |
| `raglan_back` | 34.45 | length along the outline, raglan_back_neck to back_underarm | back raglan seam and lower cap |
| `neck_front` | 4.00 | length along the outline, neck_front to raglan_front_neck | neckline carried by the sleeve, front |
| `neck_back` | 4.00 | length along the outline, neck_back to raglan_back_neck | neckline carried by the sleeve, back |
| `shoulder_dart_intake` | 2.50 | straight distance, neck_front to neck_back | shoulder dart, open at the neck |
| `shoulder_dart_length` | 12.55 | vertical distance, neck_front to shoulder | shoulder dart, neck to shoulder tip |
| `bicep_width` | 40.40 | horizontal distance, front_underarm to back_underarm | width at the underarm line |
| `underarm_seam` | 44.89 | length along the outline, back_underarm to back_wrist | underarm seam |
| `hem_width` | 30.00 | straight distance, back_wrist to front_wrist | hem, full width |
| `length` | 59.15 | vertical distance, shoulder to back_wrist | shoulder tip to hem |

Dart `shoulder`: intake 2.50, length 12.56, legs 12.57 and 12.67.

Not sewn: back_wrist..front_wrist.

## Seams

| Edge A | cm | Edge B | cm | Ease | Why | |
|---|---|---|---|---|---|---|
| Front underarm..side_dart_1 | 2.50 | Back underarm..m1 | 2.50 |  |  | OK |
| Front side_dart_2..hem_side | 59.50 | Back m1..hem_side | 59.50 |  |  | OK |
| Front side_dart_1..side_dart | 12.61 | Front side_dart_2..side_dart | 13.05 | -3.4 % | dart legs, trued | OK |
| Sleeve cap_front_low..raglan_front_neck | 28.57 | Front raglan_arm..raglan_neck | 28.57 |  |  | OK |
| Sleeve cap_front_low..front_underarm | 3.50 | Front raglan_arm..underarm | 3.50 |  |  | OK |
| Sleeve cap_back_low..raglan_back_neck | 30.95 | Back raglan_arm..raglan_neck | 30.95 |  |  | OK |
| Sleeve cap_back_low..back_underarm | 3.50 | Back raglan_arm..underarm | 3.50 |  |  | OK |
| Sleeve neck_front..shoulder | 12.57 | Sleeve neck_back..shoulder | 12.67 | -0.8 % | sleeve-top dart: shoulder lines, back ease | OK |
| Sleeve back_underarm..back_wrist | 44.89 | Sleeve front_underarm..front_wrist | 44.89 |  |  | OK |
| Back hem_cb..center_neck | 86.00 | Back hem_cb..center_neck | 86.00 |  |  | OK |
| Collar cb_neck..m2 | 3.79 | Back center_neck..raglan_neck | 3.79 |  |  | OK |
| Collar m2..m3 | 4.00 | Sleeve raglan_back_neck..neck_back | 4.00 |  |  | OK |
| Collar m3..m4 | 4.00 | Sleeve neck_front..raglan_front_neck | 4.00 |  |  | OK |
| Collar m4..m5 | 7.34 | Front raglan_neck..center_neck | 7.34 |  |  | OK |
| Collar m5..front_neck | 2.50 | Front center_neck..front_neck | 2.50 |  |  | OK |
| Collar cb_top..cb_neck | 5.00 | Collar cb_top..cb_neck | 5.00 |  |  | OK |

## Garment

| Measure | Value | Body | Ease | What it is |
|---|---|---|---|---|
| `finished_bust` | 108.00 | bust 88.00 | +20.00 | girth at the underarm line |
| `finished_hem` | 108.00 |  |  | girth at the hem |
| `neckline_total` | 38.27 | neck 37.00 | +1.27 | whole neckline, the part the raglan sleeves carry included |

## Completeness

Every typed piece has its standard points, every seam matches, every edge is accounted for.
