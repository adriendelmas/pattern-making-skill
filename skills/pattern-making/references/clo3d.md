# Current support boundary

This revision has not run CLO3D. JSON/script export, seam checks and a clean DXF audit do not constitute
simulation or fit validation. Original integration notes below are upstream reference material.

Internal fish/triangle dart topology is unsupported. `write_clo3d` refuses such pieces; fitted garment
exports provide correct 2D internal marks and `shell_status.supported=false`, without an equivalent
shell. Adding visible lines does not sew a dart or consume its waist intake. Ordinary supported outline
transfers retain fold expansion, named edges and mirror constraints; validate externally on a toile or
in a separately authorized CLO3D session. No external integration is invoked by the 2D drafting commands.

# CLO3D

This skill is made to work with **clo3d-mcp-extended**, which provides the plug-in to load in CLO3D and an
MCP server of 170 tools: https://github.com/adriendelmas/clo3d-mcp-extended

The skill computes the pattern (measurements, blocks, transformations, grading). clo3d-mcp-extended builds
it in CLO3D (pieces, seams, fabrics, placement on the avatar, simulation, images). The skill works on its
own for pattern making and the SVG and DXF exports. For CLO3D, it needs the clo3d-mcp-extended plug-in.

## Setup

1. Install clo3d-mcp-extended and register its MCP server in the agent (see its README).
2. In CLO3D: Script menu, Script Editor, open `plugin/clo3d_mcp_plugin.py` from clo3d-mcp-extended, Run.
   Once per session. CLO3D stays usable while the plug-in listens.

## Three ways to send a pattern

1. **Standalone script, no plug-in**: the `block` or `piece` command writes `clo3d_<size>.py`. In CLO3D,
   open it in the Script Editor and click Run. Works with any agent.
2. **Direct send to the plug-in, no MCP server**: `python scripts/pattern.py clo3d folder/clo3d_38.json`
   creates and names the pieces. The exchange folder is changed with `--dir` or `CLO3D_MCP_DIR`.
3. **MCP tools**: the agent drives CLO3D directly, which allows going as far as the assembled garment.
4. **Assembly through the plug-in**: `python scripts/pattern.py clo3d folder/clo3d_7.json --assemble
   --fabric 2 --mesh 5 --arrange arrange.json` creates the pieces, sets collision thickness 0 and the mesh,
   places the pieces listed in the arrangement file and sews every seam listed in the file's `seams`
   (written by blocks that know their construction, such as `block glove`). Arrangement file:
   `{"piece name": point index}` or `{"piece name": {"point": i, "orientation": 0}}`. Pieces drafted with
   their top towards the end of a limb (a glove, fingers up as on real patterns) need orientation 0 on the
   arm points, or they land upside down. Pieces with holes are opened by a slit sewn back together,
   because the API cannot cut a hole.

## Complete garment with the MCP tools

Absolute rule: before placing anything, read the real position and bounds of the piece
(`get_pattern_details`, `get_bounding_box`), and capture the view (`export_snapshot_2d`,
`export_view_image`) before and after. The user may have moved pieces by hand.

1. **Pieces**: `create_pattern` with the points of the `clo3d_<size>.json` file (millimetres, y upwards,
   `[x, y, type]`). Type 3 points are Bezier controls: a curved edge becomes one exact line in CLO3D.
   Lines are numbered in point order, from 0. The `edges` list of the file names each line.
   Right after creating each piece, set its **added collision thickness to 0**
   (`set_collision_thickness` with `thickness: 0`). CLO3D fabrics already carry their own thickness:
   an added collision thickness pushes the cloth away from the body and from other layers, which breaks
   close-fitting garments, gloves above all. Raise it only for a specific, stated reason (for example a
   thick lining layer that sinks into the garment), on the pieces concerned.
   Set the **mesh size** (`set_particle_distance`) to the fit: CLO3D's default of 20 mm is too coarse for
   close-fitting pieces, and the skin pokes through between particles. Use about 8 mm for a fitted knit,
   4 to 6 mm for gloves, fingers and small pieces, and keep the default for loose garments. A finer mesh
   is the fix for skin showing through, not an added collision thickness.
2. **Check the lines**: `get_line_lengths` must give back the lengths of the pattern edges.
3. **Seams**: `sew_lines` between edges that join. If a seam crosses itself, invert `direction_b`.
4. **Darts**: draw them as internal lines (`create_internal_shape`), or sew the two legs together.
5. **Placement**: `get_arrangement_list`, then `arrange_pattern` for each piece. This needs an avatar that
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
