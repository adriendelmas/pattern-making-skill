# Garment spec

`python scripts/pattern.py garment spec.json --out folder` drafts a whole garment from the engine's bodice block
with reusable constructions, so a jacket or a coat is a short JSON file, not a script. Every key is optional;
values are in cm. It writes the cut pieces (SVG, DXF, `pieces_<size>.json`), the 3D shell for CLO3D in
`folder/clo3d/` (mirror halves, every seam split one edge to one edge with its ease declared, wrap holds), and
the report. `python scripts/sheet.py folder/pieces_<size>.json` draws PNG sheets (needs Pillow).

Worked specs: `examples/notched-lapel-jacket/` (fitted and oversize), `examples/velvet-coat/`.

| Key | Content | Default |
|---|---|---|
| `title`, `body`, `size`, `measurements` | Body (women, men, children), standard size, or measurements: a file as for `block`, or the values themselves (`{"bust": 92, "ease": {"bust": 10}}`) | women, reference size |
| `table`, `avatar` | Size table of `data/measurements/` and avatar of `data/avatars/` | standard-eu, clo-library |
| `"preset"` in a section | `"collar": {"preset": "<id>"}` (also `fit`, `shoulder`, `length`, `front`, `sleeve`, `facing`) takes the values of `data/constructions/<id>.json`; keys written next to it win | none |
| `fit` | `side_ease` per quarter at the side seam, `dart_reduce` (narrower waist darts), `neck_widen`, `neck_drop` (front), `arm_drop` (armhole lowered), `across_out`, `cb_waist` (centre back seam taken in at the waist), `bust_dart` (intake of the side bust dart of a fitted front; null: the block's; what is left out shortens the front side seam and the hem drops at the centre front), `dart_below` (the waist darts end this far below the waist), `dart_shift` (front waist dart, or front princess seam, moved towards the side) | 1, 0, 0, 0, 1.5, 0, 1, null, 14, 0 |
| `shoulder` | `extend` (shoulder wider), `pad` (tip raised by the pad thickness); the back keeps its shoulder ease | 0, 0 |
| `shaping` | `darts`: side bust dart, fish darts, side seam out to the hip. `boxy`: unfitted, straight side seams, bust dart reduced to `boxy.dart_keep`, the rest as hem shaping. `princess`: armhole princess front and back, side dart turned into the seam, front edge bowed over the bust to match | darts |
| `length` | `below_waist` (along each seam), `hip_ease` (darts), `hem`: full hem circumference for a flared princess (flare solved on every vertical seam, hems trued square) | 23, 6, none |
| `front` | `extension` past the centre front (8 for a 16 cm wrap), `buttons` (heights below the neck point), `hold_to` (end of the fastened part; default last button + 2) | 2 |
| `collar` | `type`: `none`, `stand`, `funnel` (`h_cb`, `h_cf`, `funnel`: top edge longer than the neck edge, whole collar), `notched` (`break`, `stand`, `lapel`, `belly`, `gorge_y`, `gorge_angle`, `notch_lapel`, `notch_collar`, `notch_angle`, `collar_stand`, `collar_fall`, `spring`, `turn_of_cloth`, `facing_turn`), `shirt` (stand `h_cb`, `h_cf`, `rise` at the front, fall `fall_cb`, `spring`, `point`, `lean`, `fall_short`: fall neck edge shorter than the stand top), `convertible` (one-piece camp collar: `h_cb`, `spring`, `point`, `lean`; lower the front neckline with `fit.neck_drop`), `hood` (two-piece: `height`, `depth`, `radius`; lining when the garment is lined) | none |
| `sleeve` | `type`: `two-piece` (`length`, `hem` width, cap `ease`, `cap_height`, `drop`, `front_in`, `back_out`, `bend`, `elbow` ease, `vent` length and `vent_width`; `ease` and `hem` may be null: the size table's cap ease, and wrist + its wrist ease), `one-piece` (set-in, `length`, `hem`, `ease`), `raglan` (one-piece raglan with the sleeve-top dart: raglan line from `neck` cm past the neck point to `arm` cm above the underarm, bowed `bow`; base cap lowered by `cap_lower`; `dart` open at the neck; `raglan_ease`), `kimono` (cut in one with the body: `length` from the neck, `hem`, `slope` below horizontal, `underarm_drop`, diamond `gusset` side or 0 with a `radius` corner; a dolman is slope 40, underarm_drop 15 to 25, gusset 0), `none` | two-piece, arm length, 28, 2.5 |
| `facing` | `type`: `width` (inner edge `width` from the front edge) or `panel` (whole front panel, the default for princess; `width` is then not used); `back_neck`: depth of a back neck facing | auto, 10, none |
| `lining` | `hem`: `jump` (sewn to the hem, `up` 1.5) or `free` (hangs `up` 3 above the hem); `cb_pleat` | none |
| `pockets` | One pocket or a list; the values of each type are in `data/constructions/<type>-pocket.json`, and a spec gives only those it changes: `patch` (`w`, `h`, `x`, `y` below the waist, `facing`), `in-seam` (`top` below the waist, `length`; in the front princess seam or the side seam), `welt` (`where`: `chest` or `hip`, `x`, `y`, `length`, `depth`, `tilt`, `bag`: opening line on the front, welt cut folded, shell facing and pocketing bags; in 3D the welt is sewn on the opening line), `jetted` (`x`, `y`, `length`, `jet`, `bag`: opening and jet lines, jet strips, bags) | none |
| `allowance`, `hem_allowance` | Seam and hem allowances | 1, 4 |

The 3D shell carries, per piece, `fabric: "shell"` and its arrangement point (fronts `Body_Front_2_{side}`, backs
`Body_Back_2_{side}` or `Body_Back_Center_2` with side panels, side panels `Body_Side_2_{side}`, sleeves
`Arm_Outside_1_{side}` and `Arm_Inside_1_{side}`, collar `Neck_Collar` held 120 mm off the neck), so
`python scripts/pattern.py clo3d folder/clo3d/clo3d_38.json --fabrics shell=2` builds and places it in one call.

Every default of this table is a value of `data/constructions/` (`garment.json` and one file per collar, where
each value is described): correct it there, or add a preset file, rather than in the code (`data/README.md`).

Rules built in: a princess garment takes the panel facing (a narrower facing leaves a lining strip, caught by the
narrow-passage check); facings declare `within`; linings get 1 cm higher underarm and 0.5 cm side ease; a wrap is
never sewn closed in 3D: the top front's edge is held on an internal line of the under front along the fastened
part, top front on layer 1 (`references/clo3d.md`).

Raglan and kimono sleeves need the `darts` or `boxy` shaping and no lining (their lining is not drafted yet).
Not covered: trousers and skirts (use `block` and `piece`), shawl collars, puff and bishop sleeves (templates and
the technique sheets).
