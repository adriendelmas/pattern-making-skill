# CLO3D

This skill is made to work with **clo3d-mcp**, which provides the plug-in to load in CLO3D and an MCP server:
https://github.com/Ubani-Studio/clo3d-mcp. It needs the extended tools (`build_garment`, `get_scene_summary`,
`sew_lines`...), version 0.2.0 or later; while they are in review there (pull request 9), they are on the `main`
branch of https://github.com/adriendelmas/clo3d-mcp.

The skill computes the pattern (measurements, blocks, transformations, grading) and writes a garment file,
`clo3d_<size>.json`, that says everything CLO3D needs: pieces with exact Bezier edges, named edges, seams by
node names, wrap holds, and for each piece its fabric role, mesh size, layer and arrangement point.
clo3d-mcp builds that file in CLO3D in one call (`build_garment`). The skill works on its own for
pattern making and the SVG and DXF exports. For CLO3D, it needs the clo3d-mcp plug-in.

## Setup

1. Install clo3d-mcp and register its MCP server in the agent (see its README).
2. In CLO3D: Script menu, Script Editor, open `plugin/clo3d_mcp_plugin.py` from clo3d-mcp, Run.
   Once per session. CLO3D stays usable while the plug-in listens. If the console prints "Timer listener
   disabled", set `CLO3D_MCP_TIMER=1` in the environment CLO3D starts from and run the plug-in again.

## The garment file

Every export writes `clo3d_<size>.json` (millimetres, y upwards, laid out around the 2D origin):

```json
{"pieces": [{"name": "Sleeve L", "points": [[x, y, type]...], "edges": [{"line": 0, "from": "cap", "length_mm": 97.0}...],
             "fabric": "shell", "particle_distance": 8, "layer": 0,
             "arrange": {"name": "Arm_Outside_1_L", "orientation": 0, "x": 50, "y": 50, "offset": 120}}],
 "seams": [["Sleeve L", "cap", "m2", "Bodice back R", "shoulder", "across", {"ease": 0.082, "why": "sleeve cap ease, back"}]],
 "holds": [{"top": "Front R", "under": "Front L", "edge": ["hold_end", "top_node"], "at": {...}, "layer": 1}]}
```

- Type 3 points are Bezier controls: a curved edge becomes one exact CLO3D line. Line `i` is edge `i`.
- `fabric` is a **role** (`shell`, `lining`, `patch`...), resolved at build time to a project fabric by index
  or name. `particle_distance` is the mesh size of that piece (fitted knit 8, gloves 4 to 6, loose garments the
  default 20). `arrange` names the avatar's arrangement point; `{side}` in a name is replaced by the wearer's
  side when a mirrored piece is split into L and R. Pieces drafted with their top towards the end of a limb
  (a glove, fingers up as on real patterns) carry `orientation: 0`, or they land upside down.
- The 3D shell of a garment is not the cut pattern: `block` and `garment` write the cut pieces (half pieces
  on the fold, pairs once) in the output folder and the shell (fold pieces unfolded, pairs mirrored into L
  and R, every seam one edge to one edge) in its `clo3d/` subfolder. Send the shell.
- Pieces with holes are opened by a slit sewn back together, because the API cannot cut a hole.

Default arrangement points (`data/avatars/clo-library.json`, written for CLO3D's library avatars and marked
`unverified`: only some names were read live):
front on the fold `Body_Front_Center_2`, half fronts `Body_Front_2_{side}`, backs `Body_Back_2_{side}`, side
panels `Body_Side_2_{side}`, sleeves `Arm_Outside_1_{side}` and `Arm_Inside_1_{side}`, skirts `Leg_Skirt_Front`
and `Leg_Skirt_Back`, trousers `Leg_Front_1_{side}` and `Leg_Back_1_{side}`, collars `Neck_Collar` held 120 mm
off the neck, waistbands `Body_*_Center_3` (the natural waist of the library avatars lies between `Center_3`
and `Waist`), gloves `Arm_Outside_3_{side}` and `Arm_Inside_3_{side}`. The build matches a name exactly, then
as a substring, and reports the pieces whose point was not found. Every avatar has its own list: read it with
`get_scene_summary` before building. For one build, override with `--arrange` (`{"piece": "Point_Name"}` or an
index). For an avatar you use often, write its list once as `data/avatars/<id>.json` and draft with `--avatar <id>`
(or `"avatar"` in a garment spec).

## Three ways to send a garment

1. **One command through the plug-in, no MCP server** (the normal way):
   ```
   python scripts/pattern.py clo3d out/clo3d/clo3d_38.json --fabrics shell=2 --snapshots out/views --save out/jacket.zprj --simulate 300
   ```
   One plug-in call creates and names every piece, sets its collision thickness to 0, its mesh, its fabric
   and its arrangement point, sews every seam and hold, and reads the line lengths back. The command then
   prints, per piece, the largest deviation between the pattern edges and the CLO3D lines (`!!` above 1 mm),
   the seams that failed, the pieces left unplaced and the arrangement names not found. Options:
   `--fabrics shell=2,lining=Cotton,*=0` (index or name of a project fabric, `*` for pieces without a role),
   `--mesh` for pieces without their own, `--arrange file.json` to override points, `--pieces-only` (no
   seams, no arrangement), `--snapshots folder` (2D capture, front and side views before simulation; front,
   side, back and stress map after), `--simulate N`, `--save file.zprj` (saved before the build as
   `<file>_before.zprj`, after it, and after the simulation). Exchange folder: `--dir` or `CLO3D_MCP_DIR`.
2. **MCP tool `build_garment`** with the file path: the same build, driven by the agent, who then goes on
   with the other tools (fabrics, fit maps, images). `get_scene_summary` reads the whole scene in one call.
3. **Standalone script, no plug-in**: `clo3d_<size>.py`, to open in the Script Editor and Run. Pieces only.

## Guards (CLO3D has crashed on each of these)

- **Stop the simulation before sending.** Pieces created while the simulation runs fall and tangle; no API
  reads the simulation state, so the command reminds you and the agent must ask.
- **Pieces near the origin.** The build refuses a point more than 2.5 m from the 2D origin, because CLO3D
  creates a new piece in 3D from its 2D position: pieces made 3 m away fell for metres and crashed CLO3D.
  The skill lays the shell out around the origin.
- **Fabric and placement right after creation**, in the same call: that is what `build_garment` does.
- **Save before and after** every large addition (`--save`). Unsaved work is lost at a crash.
- `set_fabric_material` on face 1 (`same_color_as_front`, `same_material_as_front`) right after `add_fabric`
  froze CLO3D twice. Do not use it; the back face was never the problem (see layers below).

## Check loop after the build

1. Read the report of the command: deviations under 1 mm, no failed seam, every piece placed or handed over.
2. Look at the views before simulation (`--snapshots`): no piece may start inside the avatar (a collar on
   `Neck_Collar` did, hence the 120 mm offset), none upside down, the waist pieces at the natural waist.
   The simulation does not lift a garment placed too low.
3. Simulate (`--simulate 300`, about 5 s), then read the front, side and back views and the stress map:
   skin showing through means a finer mesh, not an added collision thickness; a piece that slides means a
   missing seam or a wrong point; red zones on the stress map mean ease to add on the pattern.
4. Correct the pattern, not the simulation, and build again (delete the previous pieces first, or start from
   the `_before.zprj`).

## Measuring an avatar

No API reads an avatar's measurements, and `.avs` size files are binary. For any avatar:

1. Export a front view and a side view (`export_view_image`, views 2 and 4) with the avatar alone, same
   image size: both have the same scale. Take the avatar's height as the scale (library avatars state it;
   otherwise read it in Avatar Editor).
2. Measure on the images: lengths on the front view (shoulder to waist, waist to knee, arm), widths on the
   front view and depths on the side view; girths from width and depth as an ellipse,
   `girth ≈ π (w + d) / 2`, which is a few percent over the body: use the nearest standard size below.
3. Write the measurements file and draft; then correct from the simulation (the first fit shows what the
   images missed). Record what you measured in the construction sheet, with the avatar's name.

## Complete garment with the MCP tools, piece by piece

When the agent builds without the skill's file (a patch, a piece drawn from the MCP tools), the same rules
apply, by hand. Absolute rule: before placing anything, read the scene (`get_scene_summary`: positions,
bounds, fabrics, arrangement names), and capture the view (`export_snapshot_2d`, `export_view_image`)
before and after. The user may have moved pieces by hand.

1. **Pieces**: `create_pattern` with the points of the `clo3d_<size>.json` file. Right after creating each
   piece, set its **added collision thickness to 0** (`set_collision_thickness` with `thickness: 0`). CLO3D
   fabrics already carry their own thickness: an added collision thickness pushes the cloth away from the
   body and from other layers, which breaks close-fitting garments, gloves above all. Raise it only for a
   specific, stated reason, on the pieces concerned. Set the **mesh size** (`set_particle_distance`) to
   the fit: 8 mm for a fitted knit, 4 to 6 mm for gloves, fingers and small pieces, default for loose
   garments. A finer mesh is the fix for skin showing through, not an added collision thickness.
2. **Check the lines**: `get_line_lengths` must give back the lengths of the pattern edges.
3. **Seams**: `sew_lines` between edges that join. If a seam crosses itself, invert `direction_b`.
4. **Darts**: draw them as internal lines (`create_internal_shape`), or sew the two legs together.
5. **Placement**: `arrange_pattern` with an index from `get_scene_summary`. This needs an avatar that
   has arrangement points, such as those of CLO3D's library.
6. **Fabric and simulation**: `set_pattern_fabric`, `set_fabric_material`, `simulate`, then
   `set_fit_maps` and `export_view_image` to judge balance and tension.

## Overlapping fronts and collars (wraps, double breasted, concealed fly)

Never sew the two fronts together at the centre: that turns a coat into a closed dress. Keep each front's
extension. Create an internal line on the under front where the top front's edge lies (extension past the
centre, `create_internal_shape`), and sew the top front's edge onto it along the fastened part only
(`sew` with `child_b`); below the last fastening the fronts stay free. Same for overlapping collar ends. Put the
top front and its collar half on layer 1. Women: right over left; men: left over right.

## Hand over to the user when placement is too complex

Automatic placement only knows the avatar's arrangement points. Some pieces cannot be placed reliably
that way: glove fingers (avatars rarely have finger points), pieces that must thread through others,
layered or tucked parts, pieces that start inside the body. When a piece is too complex to place, or
a simulation leaves it badly placed after one corrected attempt:

1. Stop the automatic attempts. Do not loop on arrangement settings.
2. Save the project, tell the user which pieces need placing and where they must end up (for example
   "each glove finger over its finger, thumb over the thumb"), and let them drag the pieces in CLO3D
   (pause or step the simulation, move, then simulate).
3. Continue once they confirm: read the new positions back before any further action.

The user is there to correct placement and simulation; spending many runs on a placement they can fix
in seconds is wasted work.

## Logos: the sewn patch

Placing a logo directly is approximate and refused on pieces created by script. Reliable method:

1. `duplicate_fabric` from an existing fabric, then `set_fabric_maps` with the logo as `base_color`.
2. Create the patch piece in the intended shape, and give it this fabric (`set_pattern_fabric`).
3. Draw on the garment a closed internal shape of the same shape, at the exact intended position
   (`create_internal_shape`, same frame as the piece outline).
4. Sew each edge of the patch onto the matching line of the shape: `sew_lines` with `child_b`.

## Notches, buttons, buttonholes

The API does not create them directly. The pieces JSON export (`export_pattern_json`) holds them:

- button (`ButtonHeadList`) and buttonhole (`ButtonHoleList`): `{"fOffSetX", "fOffSetY", "fAngle"}`;
- notch (`NotchList`): `{"ShapeID": piece ID, "StartPosition": outline point, "EndPosition": piece
  center, "fAngle": 0, "IsCCW": true, "fWidth": 0, "fLength": 0, "uiNotchType": 4}`.

Coordinates are those of the 2D window, like the piece points. `import_pattern_json` **replaces the whole
scene**: build the complete garment in the JSON (pieces, seams, notches, buttons), import it once, then
place the patches. Have the project saved first.

## Known limits (CLO3D 2025.2)

- Seam allowances, pleats and zips placed on a seam: missing from the API, to be done in CLO3D.
- CLO3D's option objects are not exposed to Python: no opening a project without a dialog, no DXF import
  with options.
- A placed logo can be neither moved nor deleted through the API; deleting the piece deletes its logos.
