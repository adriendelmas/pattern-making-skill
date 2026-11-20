# Piece types

Generated from the analysis rules of `scripts/library.py`; do not edit. A piece of a shape file (`data/shapes/`) says what it is with `"type"`. A type has standard point names, the ones the engine itself gives to its pieces, and `python scripts/pattern.py analyze` measures the dimensions below from them. A dimension is measured when the piece has its points: name every point of the list that exists on your piece.

- **Points to name** are required. `a` or `b`: either name, whichever your piece has.
- `center_front` and `center_back` are marks, not points of the outline: when the centre line does not run along the piece (a lapel front, a wrap), give one point of it under `"marks"`: `{"center_front": {"outline": "front", "p": [x, y]}}`.
- A dart drawn inside a piece (a fish dart at the waist) is not on the outline: give it under `"inner_darts"` of the outline, `{"name": "waist_dart", "points": [top, one side, bottom, other side]}`. It is deducted from the waist.
- A piece of no listed type is `other`: its width and height are measured, and you declare its own dimensions under `"parameters"` (`data/EXTRACTION.md`).

## `bodice_back`, `bodice_front`

Points to name: `center_neck` or `center_front` or `center_back`, `neck` or `raglan_neck`, `shoulder` or `raglan_arm`, `underarm`, `side_waist` or `hem_side`.

| Dimension | Measured as | What it is |
|---|---|---|
| `neck_width` | horizontal distance, `center_neck` or `center_front` or `center_back` to `neck` | neck width from the centre line |
| `neck_depth` | vertical distance, `neck` to `center_neck` | neck depth below the neck point |
| `neckline` | length along the outline, `center_neck` to `neck` | neckline length, half |
| `neckline_to_raglan` | length along the outline, `center_neck` to `raglan_neck` | neckline on this piece, up to the raglan seam |
| `shoulder_length` | straight distance, `neck` to `shoulder` | shoulder seam |
| `shoulder_drop` | vertical distance, `neck` to `shoulder` | shoulder tip below the neck point |
| `shoulder_angle` | angle below the horizontal, degrees, `neck` to `shoulder` | shoulder slope |
| `armhole` | length along the outline, `shoulder` to `underarm` | armhole length on this piece |
| `armhole_depth` | vertical distance, `shoulder` to `underarm` | underarm below the shoulder tip |
| `across_width` | horizontal distance, `center_neck` or `center_front` or `center_back` to `across` | across back or across chest, half |
| `width_at_underarm` | horizontal distance, `center_neck` or `center_front` or `center_back` to `underarm` | bust or chest line, quarter of the girth |
| `side_seam` | length along the outline, dart legs left out, `underarm` to `side_waist` | side seam to the waist, bust dart closed |
| `waist_width` | length along the outline, dart legs left out, `side_waist` to `center_waist` | waist line, darts closed |
| `centre_length` | vertical distance, `center_neck` to `center_waist` | centre line, neck to waist |
| `width_at_waist` | horizontal distance, `cb_waist` or `center_neck` or `center_front` or `center_back` to `side_waist` | outline width at the waist |
| `waist_less_darts` | horizontal distance, less the darts drawn inside the piece, `cb_waist` or `center_neck` or `center_front` or `center_back` to `side_waist` | waist on this piece: outline width less its inner darts |
| `width_at_hip` | horizontal distance, `center_neck` or `center_front` or `center_back` to `side_hip` | outline width at the hip line |
| `width_at_hem` | horizontal distance, `center_neck` or `center_front` or `center_back` to `hem_side` | outline width at the hem |
| `side_seam_to_hem` | length along the outline, dart legs left out, `underarm` to `hem_side` | side seam to the hem, bust dart closed |
| `hem` | length along the outline, `hem_side` to `hem_front` or `hem_cb` | hem edge on this piece |
| `length_centre` | vertical distance, `center_neck` to `hem_front` or `hem_cb` | centre line, neck to hem |
| `length_from_neck_point` | vertical distance, `neck` or `raglan_neck` to `hem_front` or `hem_cb` | neck point to hem level |
| `cb_waist_shaping` | horizontal distance, `center_neck` to `cb_waist` | centre back seam taken in at the waist |
| `raglan_line` | length along the outline, `raglan_neck` to `raglan_arm` | raglan seam, neck to armhole |
| `raglan_underarm` | length along the outline, `raglan_arm` to `underarm` | lower armhole below the raglan seam |
| `overarm` | straight distance, `shoulder` to `wrist_top` | cut-on sleeve: shoulder tip to wrist |
| `wrist_width` | straight distance, `wrist_top` to `wrist_under` | cut-on sleeve: wrist, on this piece |
| `underarm_to_wrist` | length along the outline, `wrist_under` to `underarm` | cut-on sleeve: underarm seam |
| `extension` | horizontal distance, `center_neck` or `center_front` or `center_back` to `front_neck` or `break` | front edge past the centre line: button stand or wrap |
| `held_to` | vertical distance, `neck` or `raglan_neck` to `hold_end` | level down to which the two fronts are held together, below the neck point |
| `break_height` | vertical distance, `neck` to `break` | break point (where the lapel starts to roll) below the neck point |
| `lapel_width` | distance square to the line through two points, `lapel_point` to the line `break` - `gorge_roll` | lapel width, square to the roll line |
| `lapel_edge` | length along the outline, `break` to `lapel_point` | lapel edge, break point to lapel point |
| `lapel_step` | straight distance, `lapel_point` to `notch` | lapel point to the notch |
| `gorge` | length along the outline, `notch` to `gorge_neck` | gorge seam, sewn to the collar |

## `princess_front`

Points to name: `center_neck` or `center_front` or `center_back`, `neck`, `shoulder`, `across`, `bust`, `waist`, `hem_princess`, `hem_front`.

| Dimension | Measured as | What it is |
|---|---|---|
| `neck_width` | horizontal distance, `center_neck` or `center_front` or `center_back` to `neck` | neck width from the centre line |
| `neck_depth` | vertical distance, `neck` to `center_neck` | neck depth below the neck point |
| `neckline` | length along the outline, `center_neck` to `neck` | neckline length, half |
| `neckline_to_raglan` | length along the outline, `center_neck` to `raglan_neck` | neckline on this piece, up to the raglan seam |
| `shoulder_length` | straight distance, `neck` to `shoulder` | shoulder seam |
| `shoulder_drop` | vertical distance, `neck` to `shoulder` | shoulder tip below the neck point |
| `shoulder_angle` | angle below the horizontal, degrees, `neck` to `shoulder` | shoulder slope |
| `armhole_upper` | length along the outline, `shoulder` to `across` | armhole on this panel, shoulder to the princess seam |
| `width_at_underarm` | horizontal distance, `center_neck` or `center_front` or `center_back` to `bust` or `dart_point` | panel width at the bust or blade line |
| `width_at_waist` | horizontal distance, `cb_waist` or `center_neck` or `center_front` or `center_back` to `waist` | panel width at the waist |
| `width_at_hem` | straight distance, `hem_front` or `hem_cb` to `hem_princess` | panel width at the hem |
| `princess_seam` | length along the outline, `across` to `hem_princess` | princess seam on this panel |
| `length_centre` | vertical distance, `center_neck` to `hem_front` or `hem_cb` | centre line, neck to hem |
| `cb_waist_shaping` | horizontal distance, `center_neck` to `cb_waist` | centre back seam taken in at the waist |
| `extension` | horizontal distance, `center_neck` or `center_front` or `center_back` to `front_neck` or `break` | front edge past the centre line: button stand or wrap |
| `held_to` | vertical distance, `neck` or `raglan_neck` to `hold_end` | level down to which the two fronts are held together, below the neck point |
| `break_height` | vertical distance, `neck` to `break` | break point (where the lapel starts to roll) below the neck point |
| `lapel_width` | distance square to the line through two points, `lapel_point` to the line `break` - `gorge_roll` | lapel width, square to the roll line |
| `lapel_edge` | length along the outline, `break` to `lapel_point` | lapel edge, break point to lapel point |
| `lapel_step` | straight distance, `lapel_point` to `notch` | lapel point to the notch |
| `gorge` | length along the outline, `notch` to `gorge_neck` | gorge seam, sewn to the collar |

## `princess_back`

Points to name: `center_neck` or `center_front` or `center_back`, `neck`, `shoulder`, `across`, `dart_point`, `waist`, `hem_princess`, `hem_cb`.

| Dimension | Measured as | What it is |
|---|---|---|
| `neck_width` | horizontal distance, `center_neck` or `center_front` or `center_back` to `neck` | neck width from the centre line |
| `neck_depth` | vertical distance, `neck` to `center_neck` | neck depth below the neck point |
| `neckline` | length along the outline, `center_neck` to `neck` | neckline length, half |
| `neckline_to_raglan` | length along the outline, `center_neck` to `raglan_neck` | neckline on this piece, up to the raglan seam |
| `shoulder_length` | straight distance, `neck` to `shoulder` | shoulder seam |
| `shoulder_drop` | vertical distance, `neck` to `shoulder` | shoulder tip below the neck point |
| `shoulder_angle` | angle below the horizontal, degrees, `neck` to `shoulder` | shoulder slope |
| `armhole_upper` | length along the outline, `shoulder` to `across` | armhole on this panel, shoulder to the princess seam |
| `width_at_underarm` | horizontal distance, `center_neck` or `center_front` or `center_back` to `bust` or `dart_point` | panel width at the bust or blade line |
| `width_at_waist` | horizontal distance, `cb_waist` or `center_neck` or `center_front` or `center_back` to `waist` | panel width at the waist |
| `width_at_hem` | straight distance, `hem_front` or `hem_cb` to `hem_princess` | panel width at the hem |
| `princess_seam` | length along the outline, `across` to `hem_princess` | princess seam on this panel |
| `length_centre` | vertical distance, `center_neck` to `hem_front` or `hem_cb` | centre line, neck to hem |
| `cb_waist_shaping` | horizontal distance, `center_neck` to `cb_waist` | centre back seam taken in at the waist |
| `extension` | horizontal distance, `center_neck` or `center_front` or `center_back` to `front_neck` or `break` | front edge past the centre line: button stand or wrap |
| `held_to` | vertical distance, `neck` or `raglan_neck` to `hold_end` | level down to which the two fronts are held together, below the neck point |
| `break_height` | vertical distance, `neck` to `break` | break point (where the lapel starts to roll) below the neck point |
| `lapel_width` | distance square to the line through two points, `lapel_point` to the line `break` - `gorge_roll` | lapel width, square to the roll line |
| `lapel_edge` | length along the outline, `break` to `lapel_point` | lapel edge, break point to lapel point |
| `lapel_step` | straight distance, `lapel_point` to `notch` | lapel point to the notch |
| `gorge` | length along the outline, `notch` to `gorge_neck` | gorge seam, sewn to the collar |

## `princess_side_front`

Points to name: `across`, `underarm`, `side_waist`, `hem_side`, `hem_princess`, `waist`, `bust`.

| Dimension | Measured as | What it is |
|---|---|---|
| `armhole_lower` | length along the outline, `across` to `underarm` | armhole on this panel, princess seam to underarm |
| `width_at_underarm` | horizontal distance, `bust` or `dart_point` to `underarm` | panel width at the bust or blade line |
| `width_at_waist` | horizontal distance, `waist` to `side_waist` | panel width at the waist |
| `width_at_hem` | straight distance, `hem_princess` to `hem_side` | panel width at the hem |
| `princess_seam` | length along the outline, `across` to `hem_princess` | princess seam on this panel |
| `side_seam_to_hem` | length along the outline, dart legs left out, `underarm` to `hem_side` | side seam to the hem |

## `princess_side_back`

Points to name: `across`, `underarm`, `side_waist`, `hem_side`, `hem_princess`, `waist`, `dart_point`.

| Dimension | Measured as | What it is |
|---|---|---|
| `armhole_lower` | length along the outline, `across` to `underarm` | armhole on this panel, princess seam to underarm |
| `width_at_underarm` | horizontal distance, `bust` or `dart_point` to `underarm` | panel width at the bust or blade line |
| `width_at_waist` | horizontal distance, `waist` to `side_waist` | panel width at the waist |
| `width_at_hem` | straight distance, `hem_princess` to `hem_side` | panel width at the hem |
| `princess_seam` | length along the outline, `across` to `hem_princess` | princess seam on this panel |
| `side_seam_to_hem` | length along the outline, dart legs left out, `underarm` to `hem_side` | side seam to the hem |

## `sleeve`

Points to name: `cap` or `crown`, `back_underarm`, `back_wrist`, `front_wrist`, `front_underarm`.

| Dimension | Measured as | What it is |
|---|---|---|
| `cap_height` | vertical distance, `cap` or `crown` to `back_underarm` | cap height above the underarm line |
| `bicep_width` | horizontal distance, `front_underarm` to `back_underarm` | width at the underarm line |
| `cap_back` | length along the outline, `cap` or `crown` to `back_underarm` | back half of the cap |
| `cap_front` | length along the outline, `front_underarm` to `cap` or `crown` | front half of the cap |
| `underarm_seam` | length along the outline, `back_underarm` to `back_wrist` | underarm seam |
| `hem_width` | straight distance, `back_wrist` to `front_wrist` | hem, full width |
| `length` | vertical distance, `cap` or `crown` to `back_wrist` | cap top to hem |

## `sleeve_top`

Points to name: `front_seam_cap`, `crown`, `back_seam_cap`, `front_seam_hem`, `back_seam_hem` or `vent_hem`.

| Dimension | Measured as | What it is |
|---|---|---|
| `cap` | length along the outline, `front_seam_cap` to `back_seam_cap` | cap on the top sleeve, seam to seam over the crown |
| `crown_height` | vertical distance, `crown` to `back_seam_cap` | crown above the top of the back seam |
| `width_at_cap` | straight distance, `front_seam_cap` to `back_seam_cap` | top sleeve width, seam to seam at the cap |
| `front_seam` | length along the outline, `front_seam_hem` to `front_seam_cap` | front seam |
| `back_seam` | length along the outline, `back_seam_cap` to `back_seam_hem` or `vent_top` | back seam, down to the vent if there is one |
| `vent_length` | vertical distance, `vent_top` to `vent_hem` | vent length |
| `vent_width` | straight distance, `vent_top` to `vent_corner` | vent extension |
| `hem_width` | straight distance, `front_seam_hem` to `back_seam_hem` or `vent_hem` | hem on the top sleeve |
| `length` | vertical distance, `crown` to `front_seam_hem` | crown to hem |

## `sleeve_under`

Points to name: `back_seam_cap`, `underarm`, `front_seam_cap`, `front_seam_hem`, `back_seam_hem` or `vent_hem`.

| Dimension | Measured as | What it is |
|---|---|---|
| `undercap` | length along the outline, `back_seam_cap` to `front_seam_cap` | cap on the under sleeve, seam to seam through the underarm |
| `width_at_cap` | straight distance, `front_seam_cap` to `back_seam_cap` | under sleeve width, seam to seam at the cap |
| `front_seam` | length along the outline, `front_seam_cap` to `front_seam_hem` | front seam |
| `back_seam` | length along the outline, `back_seam_hem` or `vent_top` to `back_seam_cap` | back seam, down to the vent if there is one |
| `hem_width` | straight distance, `front_seam_hem` to `back_seam_hem` or `vent_hem` | hem on the under sleeve |

## `sleeve_raglan`

Points to name: `shoulder`, `neck_front`, `neck_back`, `raglan_front_neck`, `raglan_back_neck`, `front_underarm`, `back_underarm`, `front_wrist`, `back_wrist`.

| Dimension | Measured as | What it is |
|---|---|---|
| `raglan_front` | length along the outline, `raglan_front_neck` to `front_underarm` | front raglan seam and lower cap |
| `raglan_back` | length along the outline, `raglan_back_neck` to `back_underarm` | back raglan seam and lower cap |
| `neck_front` | length along the outline, `neck_front` to `raglan_front_neck` | neckline carried by the sleeve, front |
| `neck_back` | length along the outline, `neck_back` to `raglan_back_neck` | neckline carried by the sleeve, back |
| `shoulder_dart_intake` | straight distance, `neck_front` to `neck_back` | shoulder dart, open at the neck |
| `shoulder_dart_length` | vertical distance, `neck_front` to `shoulder` | shoulder dart, neck to shoulder tip |
| `bicep_width` | horizontal distance, `front_underarm` to `back_underarm` | width at the underarm line |
| `underarm_seam` | length along the outline, `back_underarm` to `back_wrist` | underarm seam |
| `hem_width` | straight distance, `back_wrist` to `front_wrist` | hem, full width |
| `length` | vertical distance, `shoulder` to `back_wrist` | shoulder tip to hem |

## `skirt`, `skirt_front`, `skirt_back`

Points to name: `center_waist`, `side_waist`, `hip`, `side_hem`, `center_hem`.

| Dimension | Measured as | What it is |
|---|---|---|
| `waist_width` | length along the outline, dart legs left out, `center_waist` to `side_waist` | waist line, darts closed |
| `hip_width` | horizontal distance, `center_waist` to `hip` | hip line, quarter of the girth |
| `hip_depth` | vertical distance, `side_waist` to `hip` | hip line below the waist |
| `side_seam` | length along the outline, `side_waist` to `side_hem` | side seam |
| `length` | vertical distance, `center_waist` to `center_hem` | centre line, waist to hem |
| `hem_width` | straight distance, `side_hem` to `center_hem` | hem, on this piece |

## `circle_skirt`

Points to name: `waist_start`, `waist_end`, `hem_end`, `hem_start`.

| Dimension | Measured as | What it is |
|---|---|---|
| `waist` | length along the outline, `waist_start` to `waist_end` | waist edge of this panel |
| `hem` | length along the outline, `hem_end` to `hem_start` | hem edge of this panel |
| `length` | straight distance, `waist_end` to `hem_end` | waist to hem along the seam |

## `trousers`, `trousers_front`, `trousers_back`

Points to name: `center_waist`, `side_waist`, `hip`, `outer_hem`, `inner_hem`, `crotch`, `center_hip`.

| Dimension | Measured as | What it is |
|---|---|---|
| `waist_width` | length along the outline, dart legs left out, `center_waist` to `side_waist` | waist line, darts closed |
| `hip_width` | horizontal distance, `center_hip` to `hip` | hip line, quarter of the girth |
| `rise` | vertical distance, `side_waist` to `crotch` | body rise: waist to crotch line |
| `crotch_extension` | horizontal distance, `center_hip` to `crotch` | crotch point past the centre line |
| `crotch_curve` | length along the outline, `crotch` to `center_waist` | crotch seam on this piece |
| `inseam` | length along the outline, `inner_hem` to `crotch` | inside leg seam |
| `outseam` | length along the outline, `side_waist` to `outer_hem` | side seam |
| `knee_width` | straight distance, `outer_knee` to `inner_knee` | knee, on this piece |
| `hem_width` | straight distance, `outer_hem` to `inner_hem` | hem, on this piece |

## `collar`

Points to name: `cb_neck`, `front_neck` or `gorge_neck` or `cf_neck`, `cb_top` or `cb_outer`.

| Dimension | Measured as | What it is |
|---|---|---|
| `neck_edge` | length along the outline, `cb_neck` to `front_neck` or `gorge_neck` or `cf_neck` | edge sewn to the neckline, half |
| `height_cb` | straight distance, `cb_neck` to `cb_top` or `cb_outer` | height at the centre back |
| `outer_edge` | length along the outline, `front_neck` or `notch` or `cf_neck` to `cb_top` or `cb_outer` | front end and outer edge, half |
| `point_length` | straight distance, `front_neck` or `notch` or `cf_neck` to `point` or `collar_point` or `front_top` or `outer_tip` | front end of the collar, neck edge to its point |
| `gorge` | length along the outline, `gorge_neck` to `notch` | gorge seam, sewn to the lapel |

## `collar_stand`

Points to name: `cb_neck`, `front_neck`, `front_top`, `cb_top`.

| Dimension | Measured as | What it is |
|---|---|---|
| `neck_edge` | length along the outline, `cb_neck` to `front_neck` | edge sewn to the neckline, half |
| `top_edge` | length along the outline, `fall_end` or `front_top` to `cb_top` | edge sewn to the fall, half |
| `height_cb` | straight distance, `cb_neck` to `cb_top` | stand height at the centre back |
| `height_front` | straight distance, `front_neck` to `front_top` | stand height at the front end |

## `hood`

Points to name: `cb_neck`, `face_neck`, `face_top`, `top_back`, `cb_round`.

| Dimension | Measured as | What it is |
|---|---|---|
| `neck_edge` | length along the outline, `cb_neck` to `face_neck` | edge sewn to the neckline, half |
| `face_edge` | length along the outline, `face_neck` to `face_top` | edge round the face |
| `face_height` | vertical distance, `face_neck` to `face_top` | height of the face opening |
| `depth` | horizontal distance, `face_top` to `cb_round` | front to back at the top of the head |
| `top_seam` | length along the outline, `face_top` to `top_back` | seam over the head: face to the back of the crown |
| `back_curve` | length along the outline, `top_back` to `cb_round` | seam over the head: round the back of the crown |
| `back_seam` | length along the outline, `cb_round` to `cb_neck` | seam over the head: down to the nape |

## `glove_trank`

Points to name: `cuff_b`, `side_b`, `C0`, `side_p`, `cuff_p`, `b_I_t0`, `b_I_t1`, `b_M_t0`, `b_M_t1`, `b_R_t0`, `b_R_t1`, `b_L_t0`, `b_L_t1`, `p_I_t0`, `p_I_t1`, `p_M_t0`, `p_M_t1`, `p_R_t0`, `p_R_t1`, `p_L_t0`, `p_L_t1`, `b_IM`, `b_MR`, `b_RL`, `p_IM`, `p_MR`, `p_RL`.

| Dimension | Measured as | What it is |
|---|---|---|
| `width_back` | horizontal distance, `side_b` to `C0` | back of the hand, side to the thumb-side fold |
| `width_palm` | horizontal distance, `C0` to `side_p` | palm, thumb-side fold to the side |
| `cuff_length` | vertical distance, `cuff_b` to `side_b` | glove end to the base of the little finger |
| `cuff_width` | straight distance, `cuff_b` to `cuff_p` | glove end, full width |
| `web_height` | vertical distance, `cuff_b` to `C0` | glove end to the thumb web, on the fold |
| `index_width_back` | straight distance, `b_I_t0` to `b_I_t1` | index finger, back, at the start of the tip curve |
| `index_width_palm` | straight distance, `p_I_t0` to `p_I_t1` | index finger, palm, at the start of the tip curve |
| `index_length_back` | vertical distance, `b_I_t0` to `b_IM` | index finger, back: fork to the start of the tip curve |
| `index_length_palm` | vertical distance, `p_I_t0` to `p_IM` | index finger, palm: fork to the start of the tip curve |
| `middle_width_back` | straight distance, `b_M_t0` to `b_M_t1` | middle finger, back, at the start of the tip curve |
| `middle_width_palm` | straight distance, `p_M_t0` to `p_M_t1` | middle finger, palm, at the start of the tip curve |
| `middle_length_back` | vertical distance, `b_M_t0` to `b_IM` | middle finger, back: fork to the start of the tip curve |
| `middle_length_palm` | vertical distance, `p_M_t0` to `p_IM` | middle finger, palm: fork to the start of the tip curve |
| `ring_width_back` | straight distance, `b_R_t0` to `b_R_t1` | ring finger, back, at the start of the tip curve |
| `ring_width_palm` | straight distance, `p_R_t0` to `p_R_t1` | ring finger, palm, at the start of the tip curve |
| `ring_length_back` | vertical distance, `b_R_t0` to `b_RL` | ring finger, back: fork to the start of the tip curve |
| `ring_length_palm` | vertical distance, `p_R_t0` to `p_RL` | ring finger, palm: fork to the start of the tip curve |
| `little_width_back` | straight distance, `b_L_t0` to `b_L_t1` | little finger, back, at the start of the tip curve |
| `little_width_palm` | straight distance, `p_L_t0` to `p_L_t1` | little finger, palm, at the start of the tip curve |
| `little_length_back` | vertical distance, `b_L_t0` to `b_RL` | little finger, back: fork to the start of the tip curve |
| `little_length_palm` | vertical distance, `p_L_t0` to `p_RL` | little finger, palm: fork to the start of the tip curve |

## `glove_thumb`

Points to name: `C` or `t_C`, `LL` or `t_LL`, `RL` or `t_RL`, `N1` or `t_N1`, `N2` or `t_N2`, `B` or `t_B`, `RM` or `t_RM`, `Ps` or `t_Ps`.

| Dimension | Measured as | What it is |
|---|---|---|
| `length` | vertical distance, `LL` or `t_LL` to `B` or `t_B` | top of the lobes (the tip, once sewn) to the bottom of the base |
| `width` | horizontal distance, `N2` or `t_N2` to `RM` or `t_RM` | thumb at its widest |
| `tip_lobe` | length along the outline, `C` or `t_C` to `LL` or `t_LL` | one lobe of the tip |
| `side_left` | length along the outline, `LL` or `t_LL` to `N1` or `t_N1` | side seam of the thumb, from the tip lobe to the hole notch |
| `base_left` | length along the outline, `N1` or `t_N1` to `B` or `t_B` | edge sewn round the hole, from the notch to the bottom of the base |
| `base_right` | length along the outline, `B` or `t_B` to `Ps` or `t_Ps` | edge sewn round the hole, from the bottom of the base up the other side |

## `glove_thumb_hole`

Points to name: `h_TL`, `h_B`, `h_RM`, `h_TR`.

| Dimension | Measured as | What it is |
|---|---|---|
| `height` | vertical distance, `h_TL` to `h_B` | hole, top to bottom |
| `width` | horizontal distance, `h_TL` to `h_RM` | hole at its widest |
| `flap_depth` | vertical distance, `h_D` to `h_TR` | flap that enters the slit of the thumb |

## `glove_fourchette`

Points to name: `base_p`, `tip_p`, `tip_b`, `base_b`.

| Dimension | Measured as | What it is |
|---|---|---|
| `length_palm` | length along the outline, `base_p` to `tip_p` | edge sewn to the palm side of a finger |
| `length_back` | length along the outline, `tip_b` to `base_b` | edge sewn to the back of a finger |
| `width_base` | straight distance, `base_p` to `base_b` | width at the fork |
| `width_tip` | straight distance, `tip_p` to `tip_b` | width at the tip |

## Totals of a garment

Added up over the pieces, and compared with the body the pattern was made for (`reference`).

| Total | Sum of | Compared with |
|---|---|---|
| `finished_bust` | 2 x (bodice_back.width_at_underarm + bodice_front.width_at_underarm) | bust |
| `finished_bust` | 2 x (princess_front.width_at_underarm + princess_side_front.width_at_underarm + princess_side_back.width_at_underarm + princess_back.width_at_underarm) | bust |
| `finished_waist` | 2 x (bodice_back.waist_width + bodice_front.waist_width) | waist |
| `finished_waist` | 2 x (bodice_back.waist_less_darts + bodice_front.waist_less_darts) | waist |
| `finished_waist` | 2 x (princess_front.width_at_waist + princess_side_front.width_at_waist + princess_side_back.width_at_waist + princess_back.width_at_waist) | waist |
| `finished_hip` | 2 x (bodice_back.width_at_hip + bodice_front.width_at_hip) | hip |
| `finished_hem` | 2 x (bodice_back.width_at_hem + bodice_front.width_at_hem) |  |
| `finished_hem` | 2 x (princess_front.width_at_hem + princess_side_front.width_at_hem + princess_side_back.width_at_hem + princess_back.width_at_hem) |  |
| `armhole_total` | bodice_back.armhole + bodice_front.armhole |  |
| `armhole_total` | princess_front.armhole_upper + princess_side_front.armhole_lower + princess_side_back.armhole_lower + princess_back.armhole_upper |  |
| `neckline_total` | 2 x (bodice_back.neckline + bodice_front.neckline) | neck |
| `neckline_total` | 2 x (bodice_back.neckline_to_raglan + bodice_front.neckline_to_raglan + sleeve_raglan.neck_front + sleeve_raglan.neck_back) | neck |
| `cap_total` | sleeve.cap_back + sleeve.cap_front |  |
| `cap_total` | sleeve_top.cap + sleeve_under.undercap |  |
| `sleeve_width` | sleeve_top.width_at_cap + sleeve_under.width_at_cap |  |
| `sleeve_hem` | sleeve_top.hem_width + sleeve_under.hem_width | wrist |
| `skirt_waist` | 2 x (skirt_front.waist_width + skirt_back.waist_width) | waist |
| `skirt_hip` | 2 x (skirt_front.hip_width + skirt_back.hip_width) | hip |
| `trouser_waist` | 2 x (trousers_front.waist_width + trousers_back.waist_width) | waist |
| `trouser_hip` | 2 x (trousers_front.hip_width + trousers_back.hip_width) | hip |
| `crotch_total` | trousers_front.crotch_curve + trousers_back.crotch_curve |  |
| `cap_ease` | cap_total - armhole_total | |
