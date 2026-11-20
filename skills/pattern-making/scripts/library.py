"""The skill's data library: everything a pattern maker can add or correct without writing code.

  data/measurements/<id>.json    size tables and ease (a method, a country, a brand, hands for gloves)
  data/constructions/<id>.json   the values of a construction (a collar, a hood, the garment defaults) and presets
  data/shapes/<id>.json          a real piece digitised from a pattern: outline, named points, how it scales
  data/avatars/<id>.json         which arrangement point of an avatar each piece goes to

Every file carries a `provenance` block (source, rights, confidence). The engine (pattern.py, garment.py) reads its
numbers from here. `python scripts/pattern.py check` validates every file and drafts with it, so a contribution is
known to work before it is sent; `check --write` also regenerates the index, COVERAGE.md and CREDITS.md.
Standard library only.
"""
import copy
import json
import math
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
REPO = os.path.dirname(os.path.dirname(ROOT))            # the published repository, when the skill sits in it
FOLDERS = {"measurements": "measurements", "construction": "constructions", "shape": "shapes", "avatar": "avatars"}
CONFIDENCE = {
    "measured": "taken from a real pattern or garment by the contributor",
    "published": "from a cited book, standard or published pattern",
    "practice": "common trade values, consistent with the technique sheets, not traced to one source",
    "unverified": "a description or a guess nobody has checked against a real pattern or a toile",
}
EXTRACTION = {
    "photo": "clicked on a photo or a scan of the paper piece (digitize, click tool)",
    "tracing": "traced in a drawing program over a photo or a scan (digitize, SVG)",
    "ruler": "measured with a ruler or a tape on the paper or on the garment",
    "diagram": "proportions read from a published diagram that is not full size",
    "transcribed": "numbers typed from a published table or text",
    "compiled": "assembled by the contributor from several sources or from practice",
    "software": "read from software through its interface",
}
METHODS = {"shape": ("photo", "tracing", "ruler", "diagram"), "measurements": ("ruler", "transcribed", "compiled"),
           "construction": ("ruler", "diagram", "transcribed", "compiled"), "avatar": ("software", "compiled")}
MAX_DEVIATION_MM = 2.0                                   # a digitised outline laid on its paper may be this far off
REFERENCE_FILES = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".webp", ".heic", ".pdf", ".svg", ".psd",
                   ".ai", ".eps")                         # what a reference image or a scan would be
BODY_KEYS = ("bust", "waist", "hip", "back_length", "hip_depth", "skirt_length", "arm_length", "wrist", "body_rise",
             "trouser_length", "knee_width", "hem_width")
EASE_KEYS = ("bust", "bodice_waist", "skirt_waist", "skirt_hip", "trouser_waist", "trouser_hip", "sleeve_cap", "wrist",
             "shoulder")
HAND_KEYS = ("G", "HL", "h_I", "h_M", "h_R", "h_L", "F_I", "F_M", "F_R", "F_L", "Cf_I", "Cf_M", "Cf_R", "Cf_L", "T_o",
             "T_p", "T_g", "Web_T", "end_below_wrist", "end_girth")
BODIES = {"women": BODY_KEYS, "men": BODY_KEYS, "children": BODY_KEYS, "hand": HAND_KEYS}
COLLARS = ("notched", "stand", "shirt", "convertible", "hood")
POCKETS = ("patch", "in-seam", "welt", "jetted")
ID = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_cache = {}


# ------------------------------------------------------------------ files


def files(kind=None):
    """(kind, id, path) of every data file, sorted."""
    out = []
    for k, folder in FOLDERS.items():
        d = os.path.join(DATA, folder)
        if (kind is None or kind == k) and os.path.isdir(d):
            out += [(k, f[:-5], os.path.join(d, f)) for f in sorted(os.listdir(d)) if f.endswith(".json")]
    return out


def load(kind, id_):
    key = (kind, id_)
    if key not in _cache:
        path = os.path.join(DATA, FOLDERS[kind], f"{id_}.json")
        if not os.path.isfile(path):
            have = ", ".join(i for _, i, _ in files(kind)) or "none"
            raise SystemExit(f"No {kind} '{id_}' in data/{FOLDERS[kind]}/ (available: {have})")
        with open(path, encoding="utf-8") as f:
            _cache[key] = json.load(f)
    return _cache[key]


def dump(data, width=110):
    """JSON a person can read and diff: two-space indent, and any value that fits on one line stays on one line."""
    def fmt(v, ind):
        flat = json.dumps(v, ensure_ascii=False)
        if not isinstance(v, (dict, list)) or len(flat) + ind <= width or not v:
            return flat
        pad, end = " " * (ind + 2), " " * ind
        if isinstance(v, dict):
            return "{\n" + ",\n".join(f"{pad}{json.dumps(k, ensure_ascii=False)}: {fmt(x, ind + 2)}" for k, x in v.items()) + f"\n{end}}}"
        return "[\n" + ",\n".join(pad + fmt(x, ind + 2) for x in v) + f"\n{end}]"
    return fmt(data, 0) + "\n"


def write(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(dump(data))


# ------------------------------------------------------------------ measurements

STATE = {"table": "standard-eu", "avatar": None}         # shared by pattern.py and garment.py


def use_table(id_):
    if id_:
        load("measurements", id_)
        STATE["table"] = id_


def use_avatar(id_):
    if id_:
        load("avatar", id_)
        STATE["avatar"] = id_


def body_table(body, table=None):
    t = load("measurements", table or STATE["table"])
    if body not in t["bodies"]:
        raise SystemExit(f"Measurement table '{t['id']}' has no body '{body}' (it has: {', '.join(t['bodies'])})")
    return t, t["bodies"][body]


def _size_key(size):
    try:
        v = float(size)
        return str(int(v)) if v == int(v) else str(v)
    except (TypeError, ValueError):
        return str(size)


def reference_size(body, table=None):
    return body_table(body, table)[1]["reference_size"]


def sizes(body, table=None):
    b = body_table(body, table)[1]
    if "sizes" in b:
        return list(b["sizes"])
    lo, hi = b["sizes_range"]
    n = int(round((hi - lo) / b["size_step"]))
    return [_size_key(lo + i * b["size_step"]) for i in range(n + 1)]


def standard(body, size=None, table=None):
    """Measurements of a standard size: read from the table's size chart, or graded from its reference size."""
    t, b = body_table(body, table)
    rnd = (lambda v: round(v, 1)) if t.get("unit", "cm") == "cm" else (lambda v: v)
    if "sizes" in b:
        key = _size_key(size if size is not None else b["reference_size"])
        if key not in b["sizes"]:
            raise SystemExit(f"Available sizes for {body} in '{t['id']}': {', '.join(b['sizes'])}")
        out = dict(b["sizes"][key])
        L = b.get("lengths")                             # lengths given at one stature, scaled by this size's
        if L:
            k = out.pop(L["by"]) / L["at"]
            out.update({c: rnd(v * k) for c, v in L["values"].items()})
        return out
    ref = b["reference_size"]
    k = (float(size if size is not None else ref) - ref) / b["size_step"]
    return {c: rnd(v + b.get("grade", {}).get(c, 0) * k) for c, v in b["base"].items()}


def ease(body, table=None):
    """Ease of a table; a table that brings none uses the ease of the default table."""
    t = load("measurements", table or STATE["table"])
    e = t.get("ease", {}).get(body)
    return dict(e if e is not None else load("measurements", "standard-eu")["ease"][body])


# ------------------------------------------------------------------ constructions and avatars


def default_file(kind, applies_to=None):
    for k, i, _ in files(kind):
        d = load(k, i)
        if d.get("default") and (applies_to is None or d.get("applies_to") == applies_to):
            return d
    raise SystemExit(f"No default {kind} file" + (f" for {applies_to}" if applies_to else ""))


def values(applies_to):
    """The engine's values for a construction (a copy)."""
    return copy.deepcopy(default_file("construction", applies_to)["values"])


def preset(id_, section):
    """Values of a construction file used as a preset of a spec section: returns (type or None, values)."""
    d = load("construction", id_)
    sec, _, typ = d["applies_to"].partition(".")
    if sec != section:
        raise SystemExit(f"Preset '{id_}' applies to {d['applies_to']}, not to the '{section}' section")
    return (typ or None), copy.deepcopy(d["values"])


def arrangement(avatar=None):
    d = load("avatar", avatar) if avatar else default_file("avatar")
    return dict(d["arrangement"])


# ------------------------------------------------------------------ shapes


def smooth_nodes(points, closed=True):
    """Points through which the outline passes -> nodes with Bezier controls (Catmull-Rom). A point marked
    `corner` breaks the curve; two corners in a row give a straight edge."""
    n = len(points)
    P_ = [tuple(q["p"]) for q in points]
    corner = [bool(q.get("corner") or q.get("dart")) for q in points]
    for i, q in enumerate(points):                        # a dart: straight legs, so its three points are corners
        if q.get("dart"):
            corner[i - 1] = corner[(i + 1) % n] = True
    if not closed:
        corner[0] = corner[-1] = True
    out = []
    for i in range(n):
        p0, p1, p2, p3 = P_[i - 1], P_[i], P_[(i + 1) % n], P_[(i + 2) % n]
        node = {"name": points[i].get("name") or f"n{i}", "p": [p1[0], p1[1]]}
        if points[i].get("dart"):
            node["dart"] = True
        j = (i + 1) % n
        if not (corner[i] and corner[j]):
            c1 = (p1[0] + (p2[0] - p1[0]) / 3, p1[1] + (p2[1] - p1[1]) / 3) if corner[i] else \
                 (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
            c2 = (p2[0] - (p2[0] - p1[0]) / 3, p2[1] - (p2[1] - p1[1]) / 3) if corner[j] else \
                 (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
            node["c"] = [list(c1), list(c2)]
        out.append(node)
    return out


def shape_factor(shape, measures=None):
    sc = shape.get("scale")
    if not sc:
        return 1.0
    ref = float(shape["reference"][sc["measure"]])
    return float((measures or {}).get(sc["measure"], ref)) / ref


def shape_pieces(shape, measures=None):
    """Pieces (skill format, cm) of a shape file, scaled to the given measures."""
    f = shape_factor(shape, measures) * (0.1 if shape.get("unit", "cm") == "mm" else 1.0)
    pieces = []
    for name, o in shape["outlines"].items():
        k = f * o.get("unit_scale", 1.0)
        nodes = o["nodes"] if "nodes" in o else smooth_nodes(o["points"], o.get("closed", True))
        outline = []
        for nd in nodes:
            q = {"name": nd.get("name", ""), "p": [round(nd["p"][0] * k, 4), round(nd["p"][1] * k, 4)]}
            if nd.get("dart"):
                q["dart"] = True
            if "c" in nd:
                q["c"] = [[round(c[0] * k, 4), round(c[1] * k, 4)] for c in nd["c"]]
            outline.append(q)
        piece = {"name": f"{shape['id']} {name}", "cut": "shape, net outline", "allowance": 0.0, "outline": outline}
        if o.get("grain"):
            piece["grain"] = [[g[0] * k, g[1] * k] for g in o["grain"]]
        marks = [m for m in shape.get("marks", {}).values() if m.get("outline") == name]
        if marks:
            piece["lines"] = []
            for m in marks:
                x, y = m["p"][0] * k, m["p"][1] * k
                piece["lines"] += [[[x - 0.3, y], [x + 0.3, y]], [[x, y - 0.3], [x, y + 0.3]]]
        pieces.append(piece)
    return pieces


# ------------------------------------------------------------------ analysis of a pattern
# A digitised pattern is analysed by the skill, never by eye: every dimension that makes the construction and
# that a pattern maker adjusts (lengths, widths, armhole, cap, darts, seam lengths and their ease) is computed
# here from the outlines and their named points. Standard piece types use the engine's own point names, so the
# same words mean the same thing in a block, in a recipe and in a contributed pattern.

M = {  # what each kind of measure is
    "dx": "horizontal distance", "dy": "vertical distance", "dist": "straight distance",
    "path": "length along the outline", "seamline": "length along the outline, dart legs left out",
    "angle": "angle below the horizontal, degrees", "perp": "distance square to the line through two points",
    "dx_less_darts": "horizontal distance, less the darts drawn inside the piece",
}
# A parameter is (name, kind, point, point, what it is[, point that rules it out]). A point is a standard name, or
# several joined by "|" (the first one the piece has); for "perp" the second is the line "p>q". A parameter is
# measured when the piece has its points: a block bodice has no hem, a notched front has no centre neck point.
_C = "center_neck|center_front|center_back"                # a point of the centre line: on the outline, or a mark
_NECK = [
    ("neck_width", "dx", _C, "neck", "neck width from the centre line"),
    ("neck_depth", "dy", "neck", "center_neck", "neck depth below the neck point"),
    ("neckline", "path", "center_neck", "neck", "neckline length, half"),
    ("neckline_to_raglan", "path", "center_neck", "raglan_neck", "neckline on this piece, up to the raglan seam"),
    ("shoulder_length", "dist", "neck", "shoulder", "shoulder seam"),
    ("shoulder_drop", "dy", "neck", "shoulder", "shoulder tip below the neck point"),
    ("shoulder_angle", "angle", "neck", "shoulder", "shoulder slope"),
]
_FRONT_EDGE = [
    ("extension", "dx", _C, "front_neck|break", "front edge past the centre line: button stand or wrap"),
    ("held_to", "dy", "neck|raglan_neck", "hold_end", "level down to which the two fronts are held together, below the neck point"),
    ("break_height", "dy", "neck", "break", "break point (where the lapel starts to roll) below the neck point"),
    ("lapel_width", "perp", "lapel_point", "break>gorge_roll", "lapel width, square to the roll line"),
    ("lapel_edge", "path", "break", "lapel_point", "lapel edge, break point to lapel point"),
    ("lapel_step", "dist", "lapel_point", "notch", "lapel point to the notch"),
    ("gorge", "path", "notch", "gorge_neck", "gorge seam, sewn to the collar"),
]
_HEM = "hem_front|hem_cb"
_BODICE = _NECK + [
    ("armhole", "path", "shoulder", "underarm", "armhole length on this piece", "wrist_top"),
    ("armhole_depth", "dy", "shoulder", "underarm", "underarm below the shoulder tip", "wrist_top"),
    ("across_width", "dx", _C, "across", "across back or across chest, half"),
    ("width_at_underarm", "dx", _C, "underarm", "bust or chest line, quarter of the girth"),
    ("side_seam", "seamline", "underarm", "side_waist", "side seam to the waist, bust dart closed"),
    ("waist_width", "seamline", "side_waist", "center_waist", "waist line, darts closed"),
    ("centre_length", "dy", "center_neck", "center_waist", "centre line, neck to waist"),
    ("width_at_waist", "dx", "cb_waist|" + _C, "side_waist", "outline width at the waist", "center_waist"),
    ("waist_less_darts", "dx_less_darts", "cb_waist|" + _C, "side_waist", "waist on this piece: outline width less its inner darts", "center_waist"),
    ("width_at_hip", "dx", _C, "side_hip", "outline width at the hip line"),
    ("width_at_hem", "dx", _C, "hem_side", "outline width at the hem"),
    ("side_seam_to_hem", "seamline", "underarm", "hem_side", "side seam to the hem, bust dart closed"),
    ("hem", "path", "hem_side", _HEM, "hem edge on this piece"),
    ("length_centre", "dy", "center_neck", _HEM, "centre line, neck to hem"),
    ("length_from_neck_point", "dy", "neck|raglan_neck", _HEM, "neck point to hem level"),
    ("cb_waist_shaping", "dx", "center_neck", "cb_waist", "centre back seam taken in at the waist"),
    ("raglan_line", "path", "raglan_neck", "raglan_arm", "raglan seam, neck to armhole"),
    ("raglan_underarm", "path", "raglan_arm", "underarm", "lower armhole below the raglan seam"),
    ("overarm", "dist", "shoulder", "wrist_top", "cut-on sleeve: shoulder tip to wrist"),
    ("wrist_width", "dist", "wrist_top", "wrist_under", "cut-on sleeve: wrist, on this piece"),
    ("underarm_to_wrist", "path", "wrist_under", "underarm", "cut-on sleeve: underarm seam"),
] + _FRONT_EDGE
_SLEEVE_HEM = "back_seam_hem|vent_hem"
_PRINCESS_CENTRE = _NECK + [                               # centre panel of an armhole princess line
    ("armhole_upper", "path", "shoulder", "across", "armhole on this panel, shoulder to the princess seam"),
    ("width_at_underarm", "dx", _C, "bust|dart_point", "panel width at the bust or blade line"),
    ("width_at_waist", "dx", "cb_waist|" + _C, "waist", "panel width at the waist"),
    ("width_at_hem", "dist", _HEM, "hem_princess", "panel width at the hem"),
    ("princess_seam", "path", "across", "hem_princess", "princess seam on this panel"),
    ("length_centre", "dy", "center_neck", _HEM, "centre line, neck to hem"),
    ("cb_waist_shaping", "dx", "center_neck", "cb_waist", "centre back seam taken in at the waist"),
] + _FRONT_EDGE
_PRINCESS_SIDE = [                                         # side panel of an armhole princess line
    ("armhole_lower", "path", "across", "underarm", "armhole on this panel, princess seam to underarm"),
    ("width_at_underarm", "dx", "bust|dart_point", "underarm", "panel width at the bust or blade line"),
    ("width_at_waist", "dx", "waist", "side_waist", "panel width at the waist"),
    ("width_at_hem", "dist", "hem_princess", "hem_side", "panel width at the hem"),
    ("princess_seam", "path", "across", "hem_princess", "princess seam on this panel"),
    ("side_seam_to_hem", "seamline", "underarm", "hem_side", "side seam to the hem"),
]
_FINGERS = (("I", "index"), ("M", "middle"), ("R", "ring"), ("L", "little"))
_CROTCH = {"I": "IM", "M": "IM", "R": "RL", "L": "RL"}     # the fork each finger length is taken from
_TRANK = [
    ("width_back", "dx", "side_b", "C0", "back of the hand, side to the thumb-side fold"),
    ("width_palm", "dx", "C0", "side_p", "palm, thumb-side fold to the side"),
    ("cuff_length", "dy", "cuff_b", "side_b", "glove end to the base of the little finger"),
    ("cuff_width", "dist", "cuff_b", "cuff_p", "glove end, full width"),
    ("web_height", "dy", "cuff_b", "C0", "glove end to the thumb web, on the fold"),
]
for _f, _w in _FINGERS:
    _TRANK += [(f"{_w}_width_back", "dist", f"b_{_f}_t0", f"b_{_f}_t1", f"{_w} finger, back, at the start of the tip curve"),
               (f"{_w}_width_palm", "dist", f"p_{_f}_t0", f"p_{_f}_t1", f"{_w} finger, palm, at the start of the tip curve"),
               (f"{_w}_length_back", "dy", f"b_{_f}_t0", f"b_{_CROTCH[_f]}", f"{_w} finger, back: fork to the start of the tip curve"),
               (f"{_w}_length_palm", "dy", f"p_{_f}_t0", f"p_{_CROTCH[_f]}", f"{_w} finger, palm: fork to the start of the tip curve")]
PIECE_TYPES = {
    "bodice_back": {"anchors": (_C, "neck|raglan_neck", "shoulder|raglan_arm", "underarm", "side_waist|hem_side"), "params": _BODICE},
    "bodice_front": {"anchors": (_C, "neck|raglan_neck", "shoulder|raglan_arm", "underarm", "side_waist|hem_side"), "params": _BODICE},
    "princess_front": {"anchors": (_C, "neck", "shoulder", "across", "bust", "waist", "hem_princess", "hem_front"), "params": _PRINCESS_CENTRE},
    "princess_back": {"anchors": (_C, "neck", "shoulder", "across", "dart_point", "waist", "hem_princess", "hem_cb"), "params": _PRINCESS_CENTRE},
    "princess_side_front": {"anchors": ("across", "underarm", "side_waist", "hem_side", "hem_princess", "waist", "bust"), "params": _PRINCESS_SIDE},
    "princess_side_back": {"anchors": ("across", "underarm", "side_waist", "hem_side", "hem_princess", "waist", "dart_point"), "params": _PRINCESS_SIDE},
    "sleeve": {"anchors": ("cap|crown", "back_underarm", "back_wrist", "front_wrist", "front_underarm"), "params": [
        ("cap_height", "dy", "cap|crown", "back_underarm", "cap height above the underarm line"),
        ("bicep_width", "dx", "front_underarm", "back_underarm", "width at the underarm line"),
        ("cap_back", "path", "cap|crown", "back_underarm", "back half of the cap"),
        ("cap_front", "path", "front_underarm", "cap|crown", "front half of the cap"),
        ("underarm_seam", "path", "back_underarm", "back_wrist", "underarm seam"),
        ("hem_width", "dist", "back_wrist", "front_wrist", "hem, full width"),
        ("length", "dy", "cap|crown", "back_wrist", "cap top to hem"),
    ]},
    "sleeve_top": {"anchors": ("front_seam_cap", "crown", "back_seam_cap", "front_seam_hem", _SLEEVE_HEM), "params": [
        ("cap", "path", "front_seam_cap", "back_seam_cap", "cap on the top sleeve, seam to seam over the crown"),
        ("crown_height", "dy", "crown", "back_seam_cap", "crown above the top of the back seam"),
        ("width_at_cap", "dist", "front_seam_cap", "back_seam_cap", "top sleeve width, seam to seam at the cap"),
        ("front_seam", "path", "front_seam_hem", "front_seam_cap", "front seam"),
        ("back_seam", "path", "back_seam_cap", "back_seam_hem|vent_top", "back seam, down to the vent if there is one"),
        ("vent_length", "dy", "vent_top", "vent_hem", "vent length"),
        ("vent_width", "dist", "vent_top", "vent_corner", "vent extension"),
        ("hem_width", "dist", "front_seam_hem", _SLEEVE_HEM, "hem on the top sleeve"),
        ("length", "dy", "crown", "front_seam_hem", "crown to hem"),
    ]},
    "sleeve_under": {"anchors": ("back_seam_cap", "underarm", "front_seam_cap", "front_seam_hem", _SLEEVE_HEM), "params": [
        ("undercap", "path", "back_seam_cap", "front_seam_cap", "cap on the under sleeve, seam to seam through the underarm"),
        ("width_at_cap", "dist", "front_seam_cap", "back_seam_cap", "under sleeve width, seam to seam at the cap"),
        ("front_seam", "path", "front_seam_cap", "front_seam_hem", "front seam"),
        ("back_seam", "path", "back_seam_hem|vent_top", "back_seam_cap", "back seam, down to the vent if there is one"),
        ("hem_width", "dist", "front_seam_hem", _SLEEVE_HEM, "hem on the under sleeve"),
    ]},
    "sleeve_raglan": {"anchors": ("shoulder", "neck_front", "neck_back", "raglan_front_neck", "raglan_back_neck", "front_underarm",
                                  "back_underarm", "front_wrist", "back_wrist"), "params": [
        ("raglan_front", "path", "raglan_front_neck", "front_underarm", "front raglan seam and lower cap"),
        ("raglan_back", "path", "raglan_back_neck", "back_underarm", "back raglan seam and lower cap"),
        ("neck_front", "path", "neck_front", "raglan_front_neck", "neckline carried by the sleeve, front"),
        ("neck_back", "path", "neck_back", "raglan_back_neck", "neckline carried by the sleeve, back"),
        ("shoulder_dart_intake", "dist", "neck_front", "neck_back", "shoulder dart, open at the neck"),
        ("shoulder_dart_length", "dy", "neck_front", "shoulder", "shoulder dart, neck to shoulder tip"),
        ("bicep_width", "dx", "front_underarm", "back_underarm", "width at the underarm line"),
        ("underarm_seam", "path", "back_underarm", "back_wrist", "underarm seam"),
        ("hem_width", "dist", "back_wrist", "front_wrist", "hem, full width"),
        ("length", "dy", "shoulder", "back_wrist", "shoulder tip to hem"),
    ]},
    "skirt": {"anchors": ("center_waist", "side_waist", "hip", "side_hem", "center_hem"), "params": [
        ("waist_width", "seamline", "center_waist", "side_waist", "waist line, darts closed"),
        ("hip_width", "dx", "center_waist", "hip", "hip line, quarter of the girth"),
        ("hip_depth", "dy", "side_waist", "hip", "hip line below the waist"),
        ("side_seam", "path", "side_waist", "side_hem", "side seam"),
        ("length", "dy", "center_waist", "center_hem", "centre line, waist to hem"),
        ("hem_width", "dist", "side_hem", "center_hem", "hem, on this piece"),
    ]},
    "circle_skirt": {"anchors": ("waist_start", "waist_end", "hem_end", "hem_start"), "params": [
        ("waist", "path", "waist_start", "waist_end", "waist edge of this panel"),
        ("hem", "path", "hem_end", "hem_start", "hem edge of this panel"),
        ("length", "dist", "waist_end", "hem_end", "waist to hem along the seam"),
    ]},
    "trousers": {"anchors": ("center_waist", "side_waist", "hip", "outer_hem", "inner_hem", "crotch", "center_hip"), "params": [
        ("waist_width", "seamline", "center_waist", "side_waist", "waist line, darts closed"),
        ("hip_width", "dx", "center_hip", "hip", "hip line, quarter of the girth"),
        ("rise", "dy", "side_waist", "crotch", "body rise: waist to crotch line"),
        ("crotch_extension", "dx", "center_hip", "crotch", "crotch point past the centre line"),
        ("crotch_curve", "path", "crotch", "center_waist", "crotch seam on this piece"),
        ("inseam", "path", "inner_hem", "crotch", "inside leg seam"),
        ("outseam", "path", "side_waist", "outer_hem", "side seam"),
        ("knee_width", "dist", "outer_knee", "inner_knee", "knee, on this piece"),
        ("hem_width", "dist", "outer_hem", "inner_hem", "hem, on this piece"),
    ]},
    "collar": {"anchors": ("cb_neck", "front_neck|gorge_neck|cf_neck", "cb_top|cb_outer"), "params": [
        ("neck_edge", "path", "cb_neck", "front_neck|gorge_neck|cf_neck", "edge sewn to the neckline, half"),
        ("height_cb", "dist", "cb_neck", "cb_top|cb_outer", "height at the centre back"),
        ("outer_edge", "path", "front_neck|notch|cf_neck", "cb_top|cb_outer", "front end and outer edge, half"),
        ("point_length", "dist", "front_neck|notch|cf_neck", "point|collar_point|front_top|outer_tip", "front end of the collar, neck edge to its point"),
        ("gorge", "path", "gorge_neck", "notch", "gorge seam, sewn to the lapel"),
    ]},
    "collar_stand": {"anchors": ("cb_neck", "front_neck", "front_top", "cb_top"), "params": [
        ("neck_edge", "path", "cb_neck", "front_neck", "edge sewn to the neckline, half"),
        ("top_edge", "path", "fall_end|front_top", "cb_top", "edge sewn to the fall, half"),
        ("height_cb", "dist", "cb_neck", "cb_top", "stand height at the centre back"),
        ("height_front", "dist", "front_neck", "front_top", "stand height at the front end"),
    ]},
    "hood": {"anchors": ("cb_neck", "face_neck", "face_top", "top_back", "cb_round"), "params": [
        ("neck_edge", "path", "cb_neck", "face_neck", "edge sewn to the neckline, half"),
        ("face_edge", "path", "face_neck", "face_top", "edge round the face"),
        ("face_height", "dy", "face_neck", "face_top", "height of the face opening"),
        ("depth", "dx", "face_top", "cb_round", "front to back at the top of the head"),
        ("top_seam", "path", "face_top", "top_back", "seam over the head: face to the back of the crown"),
        ("back_curve", "path", "top_back", "cb_round", "seam over the head: round the back of the crown"),
        ("back_seam", "path", "cb_round", "cb_neck", "seam over the head: down to the nape"),
    ]},
    "glove_trank": {"anchors": ("cuff_b", "side_b", "C0", "side_p", "cuff_p") + tuple(
        f"{s}_{f}_t{i}" for s in "bp" for f, _ in _FINGERS for i in (0, 1)) + tuple(f"{s}_{k}" for s in "bp" for k in ("IM", "MR", "RL")),
        "params": _TRANK},
    "glove_thumb": {"anchors": ("C|t_C", "LL|t_LL", "RL|t_RL", "N1|t_N1", "N2|t_N2", "B|t_B", "RM|t_RM", "Ps|t_Ps"), "params": [
        ("length", "dy", "LL|t_LL", "B|t_B", "top of the lobes (the tip, once sewn) to the bottom of the base"),
        ("width", "dx", "N2|t_N2", "RM|t_RM", "thumb at its widest"),
        ("tip_lobe", "path", "C|t_C", "LL|t_LL", "one lobe of the tip"),
        ("side_left", "path", "LL|t_LL", "N1|t_N1", "side seam of the thumb, from the tip lobe to the hole notch"),
        ("base_left", "path", "N1|t_N1", "B|t_B", "edge sewn round the hole, from the notch to the bottom of the base"),
        ("base_right", "path", "B|t_B", "Ps|t_Ps", "edge sewn round the hole, from the bottom of the base up the other side"),
    ]},
    "glove_thumb_hole": {"anchors": ("h_TL", "h_B", "h_RM", "h_TR"), "params": [
        ("height", "dy", "h_TL", "h_B", "hole, top to bottom"),
        ("width", "dx", "h_TL", "h_RM", "hole at its widest"),
        ("flap_depth", "dy", "h_D", "h_TR", "flap that enters the slit of the thumb"),
    ]},
    "glove_fourchette": {"anchors": ("base_p", "tip_p", "tip_b", "base_b"), "params": [
        ("length_palm", "path", "base_p", "tip_p", "edge sewn to the palm side of a finger"),
        ("length_back", "path", "tip_b", "base_b", "edge sewn to the back of a finger"),
        ("width_base", "dist", "base_p", "base_b", "width at the fork"),
        ("width_tip", "dist", "tip_p", "tip_b", "width at the tip"),
    ]},
    "other": {"anchors": (), "params": []},
}
PIECE_TYPES["skirt_front"] = PIECE_TYPES["skirt_back"] = PIECE_TYPES["skirt"]
PIECE_TYPES["trousers_front"] = PIECE_TYPES["trousers_back"] = PIECE_TYPES["trousers"]
EDGE_KINDS = {"fold": "cut on the fold", "hem": "hem or finished edge with its own allowance",
              "applied": "laid on another piece and stitched down", "free": "left free (opening, vent, raw edge)",
              "slit": "a slash whose lips are sewn to a piece set into it"}
_QUARTERS = ("bodice_back", "bodice_front")
_PANELS = ("princess_front", "princess_side_front", "princess_side_back", "princess_back")
GARMENT = [  # (name, [(type, parameter)...], factor, body measurement it is compared with, what it is)
    ("finished_bust", [(t, "width_at_underarm") for t in _QUARTERS], 2, "bust", "girth at the underarm line"),
    ("finished_bust", [(t, "width_at_underarm") for t in _PANELS], 2, "bust", "girth at the bust line, panel widths added"),
    ("finished_waist", [(t, "waist_width") for t in _QUARTERS], 2, "waist", "waist girth, darts closed"),
    ("finished_waist", [(t, "waist_less_darts") for t in _QUARTERS], 2, "waist", "waist girth, inner darts and centre back shaping deducted"),
    ("finished_waist", [(t, "width_at_waist") for t in _PANELS], 2, "waist", "waist girth, panel widths added"),
    ("finished_hip", [(t, "width_at_hip") for t in _QUARTERS], 2, "hip", "girth at the hip line"),
    ("finished_hem", [(t, "width_at_hem") for t in _QUARTERS], 2, None, "girth at the hem"),
    ("finished_hem", [(t, "width_at_hem") for t in _PANELS], 2, None, "girth at the hem, panel widths added"),
    ("armhole_total", [(t, "armhole") for t in _QUARTERS], 1, None, "whole armhole"),
    ("armhole_total", [("princess_front", "armhole_upper"), ("princess_side_front", "armhole_lower"), ("princess_side_back", "armhole_lower"),
                       ("princess_back", "armhole_upper")], 1, None, "whole armhole"),
    ("neckline_total", [(t, "neckline") for t in _QUARTERS], 2, "neck", "whole neckline"),
    ("neckline_total", [(t, "neckline_to_raglan") for t in _QUARTERS] + [("sleeve_raglan", "neck_front"), ("sleeve_raglan", "neck_back")],
     2, "neck", "whole neckline, the part the raglan sleeves carry included"),
    ("cap_total", [("sleeve", "cap_back"), ("sleeve", "cap_front")], 1, None, "whole sleeve cap"),
    ("cap_total", [("sleeve_top", "cap"), ("sleeve_under", "undercap")], 1, None, "whole sleeve cap, top and under sleeve"),
    ("sleeve_width", [("sleeve_top", "width_at_cap"), ("sleeve_under", "width_at_cap")], 1, None, "sleeve girth at the cap line, top and under sleeve"),
    ("sleeve_hem", [("sleeve_top", "hem_width"), ("sleeve_under", "hem_width")], 1, "wrist", "sleeve hem girth, top and under sleeve"),
    ("skirt_waist", [("skirt_front", "waist_width"), ("skirt_back", "waist_width")], 2, "waist", "skirt waist girth"),
    ("skirt_hip", [("skirt_front", "hip_width"), ("skirt_back", "hip_width")], 2, "hip", "skirt hip girth"),
    ("trouser_waist", [("trousers_front", "waist_width"), ("trousers_back", "waist_width")], 2, "waist", "trouser waist girth"),
    ("trouser_hip", [("trousers_front", "hip_width"), ("trousers_back", "hip_width")], 2, "hip", "trouser hip girth"),
    ("crotch_total", [("trousers_front", "crotch_curve"), ("trousers_back", "crotch_curve")], 1, None, "whole crotch seam"),
]
SEAM_TOL_CM = 0.1
_AUTO = re.compile(r"n\d+$")


class Outline:
    """One outline of a shape, in cm: named points, lengths along it, spans between named points."""

    def __init__(self, piece, marks=None, inner=0.0):
        import pattern as P
        self.piece = piece
        self.inner = inner                                # total intake of the darts drawn inside the piece
        self.marks = marks or {}                          # named points that are not on the outline (a centre line)
        self.nodes = piece["outline"]
        n = len(self.nodes)
        self.L = [P.length(P.edge(piece, i, 64)) for i in range(n)]
        self.at = {nd["name"]: i for i, nd in enumerate(self.nodes) if nd.get("name") and not _AUTO.match(nd["name"])}
        self.dart = [bool(nd.get("dart")) for nd in self.nodes]
        self.named = sorted(self.at.values())

    def p(self, name):
        return self.nodes[self.at[name]]["p"] if name in self.at else self.marks[name]

    def pick(self, names):
        """The first of the names "a|b|c" this piece has, on its outline or as a mark; None when it has none."""
        return next((x for x in names.split("|") if x in self.at or x in self.marks), None)

    def resolve(self, kind, a, b):
        """The points of a measure on this piece, alternatives settled, or None when the piece does not have them."""
        a_ = self.pick(a)
        b_ = tuple(self.pick(x) for x in b.split(">")) if kind == "perp" else self.pick(b)
        if a_ is None or b_ is None or (kind == "perp" and (len(b_) != 2 or None in b_)):
            return None
        if kind in ("path", "seamline") and not (a_ in self.at and b_ in self.at):
            return None
        return a_, b_

    def forward(self, a, b, seamline=False):
        """Length going forward in point order from a to b; with seamline, dart legs are left out."""
        n, i, tot = len(self.nodes), self.at[a], 0.0
        while i != self.at[b]:
            j = (i + 1) % n
            if not (seamline and (self.dart[i] or self.dart[j])):
                tot += self.L[i]
            i = j
        return tot

    def span(self, a, b, seamline=False):
        """The shorter way round between two named points: (length, start, end) with start -> end forward."""
        f, r = self.forward(a, b, seamline), self.forward(b, a, seamline)
        return (f, a, b) if f <= r else (r, b, a)

    def measure(self, kind, a, b):
        if kind == "perp":                                # b is the line: two point names
            (xa, ya), (x1, y1), (x2, y2) = self.p(a), self.p(b[0]), self.p(b[1])
            return abs((x2 - x1) * (y1 - ya) - (x1 - xa) * (y2 - y1)) / math.hypot(x2 - x1, y2 - y1)
        (xa, ya), (xb, yb) = self.p(a), self.p(b)
        if kind == "dx_less_darts":
            return abs(xb - xa) - self.inner
        if kind == "dx":
            return abs(xb - xa)
        if kind == "dy":
            return abs(yb - ya)
        if kind == "dist":
            return math.hypot(xb - xa, yb - ya)
        if kind == "angle":
            return math.degrees(math.atan2(abs(yb - ya), abs(xb - xa)))
        if kind in ("path", "seamline"):
            return self.span(a, b, kind == "seamline")[0]
        raise ValueError(f"unknown measure '{kind}' (known: {', '.join(M)})")

    def cover(self, start, end, done):
        """Mark the stretches between consecutive named points from start forward to end."""
        k = self.named.index(self.at[start])
        while self.named[k] != self.at[end]:
            done.add(self.named[k])
            k = (k + 1) % len(self.named)


def analyze(shape, measures=None):
    """Everything measurable on a shape, in cm: per outline its facts, standard parameters and darts; every seam with
    both lengths; garment totals and ease against the reference body; and what is missing for the construction to be
    complete (anchors of a typed piece, a seam that does not match, an edge nobody accounts for)."""
    import pattern as P
    problems, out = [], {"pieces": {}, "seams": [], "garment": [], "custom": []}
    pieces = dict(zip(shape["outlines"], shape_pieces(shape, measures)))
    k_ref = shape_factor(shape, measures)
    k_unit = k_ref * (0.1 if shape.get("unit", "cm") == "mm" else 1.0)
    marks = {name: {} for name in pieces}
    for mname, mk in (shape.get("marks") or {}).items():
        if mk.get("outline") in marks:
            k = k_unit * shape["outlines"][mk["outline"]].get("unit_scale", 1.0)
            marks[mk["outline"]][mname] = [mk["p"][0] * k, mk["p"][1] * k]
    inner = {}                                            # darts drawn inside a piece: [top, one side, bottom, other side]
    for name in pieces:
        k = k_unit * shape["outlines"][name].get("unit_scale", 1.0)
        inner[name] = [{"name": d.get("name", ""), "intake": k * math.hypot(d["points"][1][0] - d["points"][3][0], d["points"][1][1] - d["points"][3][1]),
                        "length": k * math.hypot(d["points"][0][0] - d["points"][2][0], d["points"][0][1] - d["points"][2][1])}
                       for d in shape["outlines"][name].get("inner_darts", [])]
    O = {name: Outline(pc, marks[name], sum(d["intake"] for d in inner[name])) for name, pc in pieces.items()}
    lenient = shape.get("unlisted_edges") == "free"       # a draft of the engine: what no seam covers is simply listed
    for name, o in O.items():
        spec = shape["outlines"][name]
        typ = spec.get("type")
        pts = P.outline(o.piece, 16)
        xs, ys = [q[0] for q in pts], [q[1] for q in pts]
        rec = {"type": typ, "width": max(xs) - min(xs), "height": max(ys) - min(ys), "perimeter": sum(o.L),
               "area": abs(P.area(pts)), "named": [nd["name"] for nd in o.nodes if nd.get("name") in o.at],
               "parameters": [], "darts": [], "inner_darts": inner[name], "open": []}
        if typ not in PIECE_TYPES:
            problems.append(f'outline "{name}": "type" must be one of: {", ".join(sorted(PIECE_TYPES))}')
            typ = "other"
        missing = [a.replace("|", " or ") for a in PIECE_TYPES[typ]["anchors"] if o.pick(a) is None]
        if missing:
            problems.append(f'outline "{name}" ({typ}): points to name: {", ".join(missing)} (data/EXTRACTION.md, standard names)')
        for prm in PIECE_TYPES[typ]["params"]:
            pname, kind, a, b, what = prm[:5]
            found = None if len(prm) > 5 and o.pick(prm[5]) else o.resolve(kind, a, b)
            if found:
                rec["parameters"].append({"name": pname, "value": o.measure(kind, *found), "kind": kind, "from": found[0],
                                          "to": " > ".join(found[1]) if kind == "perp" else found[1], "what": what})
        n = len(o.nodes)
        for i, nd in enumerate(o.nodes):
            if o.dart[i]:
                a, b = o.nodes[i - 1]["p"], o.nodes[(i + 1) % n]["p"]
                mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
                rec["darts"].append({"name": nd.get("name", ""), "intake": math.hypot(b[0] - a[0], b[1] - a[1]),
                                     "length": math.hypot(nd["p"][0] - mid[0], nd["p"][1] - mid[1]),
                                     "legs": [o.L[i - 1], o.L[i]]})
        out["pieces"][name] = rec
    for c in shape.get("parameters", []):                 # dimensions the standard types do not know: declared, then measured here
        try:
            kind, oname, a, b = c["measure"]
            found = O[oname].resolve(kind, a, b)
            if kind not in M or not found:
                raise ValueError(f"{kind} {a} {b}: unknown measure, or points this outline does not have")
            out["custom"].append({"name": c["name"], "outline": oname, "value": O[oname].measure(kind, *found), "kind": kind,
                                  "from": found[0], "to": " > ".join(found[1]) if kind == "perp" else found[1], "what": c.get("what", "")})
        except (KeyError, ValueError, TypeError) as e:
            problems.append(f'parameter "{c.get("name", "?")}": {e} (expected "measure": [kind, outline, point, point])')
    # seams: both sides measured; of the two ways round between two points, the pair whose lengths agree is the seam
    covered = {name: set() for name in O}
    for s_ in shape.get("seams", []):
        try:
            A, a1, a2, B, b1, b2 = s_[:6]
            opt = s_[6] if len(s_) > 6 and isinstance(s_[6], dict) else {}
            ease = float(opt.get("ease", 0.0))
            best = None
            for fa in ((a1, a2), (a2, a1)):
                for fb in ((b1, b2), (b2, b1)):
                    la, lb = O[A].forward(*fa), O[B].forward(*fb)
                    if A == B and {fa[0], fa[1]} == {fb[0], fb[1]} and fa != fb:
                        continue
                    gap = abs(la - lb * (1 + ease))
                    if best is None or gap < best[0] - 1e-9 or (abs(gap - best[0]) <= 1e-9 and la + lb < best[1] + best[2]):
                        best = (gap, la, lb, fa, fb)     # equal gaps (an edge sewn to its own mirror): the shorter way round
            gap, la, lb, fa, fb = best
            ok = gap <= SEAM_TOL_CM
            out["seams"].append({"a": [A, a1, a2], "la": la, "b": [B, b1, b2], "lb": lb, "ease": ease, "why": opt.get("why", ""), "ok": ok})
            if not ok:
                problems.append(f"seam {A} {a1}..{a2} ({la:.2f} cm) / {B} {b1}..{b2} ({lb:.2f} cm): the lengths differ by "
                                f"{la - lb:+.2f} cm; correct the outline, or declare the ease with its reason "
                                f'({{"ease": {la / lb - 1:.3f}, "why": "..."}})')
            if ease and not opt.get("why"):
                problems.append(f"seam {A} {a1}..{a2} / {B} {b1}..{b2}: an ease is declared without its reason (\"why\")")
            O[A].cover(fa[0], fa[1], covered[A])
            O[B].cover(fb[0], fb[1], covered[B])
        except (KeyError, ValueError, TypeError, IndexError) as e:
            problems.append(f"seam {s_[:6]}: cannot be read ({type(e).__name__}: {e}); points must be named points of the outlines")
    for name, o in O.items():
        spec = shape["outlines"][name]
        for kind, spans in (spec.get("edges") or {}).items():
            if kind not in EDGE_KINDS:
                problems.append(f'outline "{name}": edge kind "{kind}" (known: {", ".join(EDGE_KINDS)})')
                continue
            for a, b in spans:
                if a not in o.at or b not in o.at:
                    problems.append(f'outline "{name}", {kind} edge {a}..{b}: not named points of this outline')
                    continue
                _, s0, s1 = o.span(a, b)
                o.cover(s0, s1, covered[name])
                out["pieces"][name]["open"].append(f"{kind} {a}..{b}")
        if len(o.named) < 2:
            problems.append(f'outline "{name}": name its corners and notches; nothing can be measured or sewn between unnamed points')
            continue
        n = len(o.nodes)
        for k, i in enumerate(o.named):
            j = o.named[(k + 1) % len(o.named)]
            is_dart_leg = (o.dart[i] and (i + 1) % n == j) or (o.dart[j] and (i + 1) % n == j)
            if i not in covered[name] and not is_dart_leg and lenient:
                run = out["pieces"][name]["open"]
                a_, b_ = o.nodes[i]["name"], o.nodes[j]["name"]
                if run and run[-1].endswith(".." + a_):   # consecutive stretches read as one edge
                    run[-1] = run[-1][:run[-1].rindex("..") + 2] + b_
                else:
                    run.append(f"{a_}..{b_}")
            elif i not in covered[name] and not is_dart_leg:
                problems.append(f'outline "{name}": the edge {o.nodes[i]["name"]}..{o.nodes[j]["name"]} is not accounted for: sew it '
                                f'("seams") or list it under "edges" as {", ".join(EDGE_KINDS)}')
    # garment totals, and ease against the body the pattern was made for
    by_type = {}
    for name, rec in out["pieces"].items():
        by_type.setdefault(rec["type"], {p["name"]: p["value"] for p in rec["parameters"]})
    ref = shape.get("reference", {})
    for gname, parts, factor, body_key, what in GARMENT:
        if all(t in by_type and prm in by_type[t] for t, prm in parts):
            v = factor * sum(by_type[t][prm] for t, prm in parts)
            row = {"name": gname, "value": v, "what": what}
            if body_key and _num(ref.get(body_key)):
                row.update(body=body_key, body_value=ref[body_key] * k_ref, ease=v - ref[body_key] * k_ref)
            out["garment"].append(row)
    tot = {g["name"]: g["value"] for g in out["garment"]}
    if "cap_total" in tot and "armhole_total" in tot:
        out["garment"].append({"name": "cap_ease", "value": tot["cap_total"] - tot["armhole_total"], "what": "sleeve cap longer than the armhole"})
    out["problems"] = problems
    return out


def render_analysis(shape, A):
    f = lambda v: f"{v:.2f}"
    lines = [f"# Analysis: {shape.get('title', shape['id'])}", "",
             "Measured by the skill from the outlines of " + (shape.get("drafted") or "the shape file")
             + f" (`python scripts/pattern.py analyze {shape.get('command', shape['id'])}`), in cm at the reference size. "
             "Generated; do not edit.", "",
             "Reference: " + (", ".join(f"{k} {v}" for k, v in shape.get("reference", {}).items()) or "none given") + ".", ""]
    for name, r in A["pieces"].items():
        lines += [f"## {name} ({r['type'] or 'no type'})", "",
                  f"Width {f(r['width'])}, height {f(r['height'])}, perimeter {f(r['perimeter'])}, area {r['area']:.0f} cm2. "
                  f"Named points: {', '.join(r['named']) or 'none'}.", ""]
        if r["parameters"]:
            lines += ["| Parameter | Value | Measured as | What it is |", "|---|---|---|---|"]
            lines += [f"| `{p['name']}` | {f(p['value'])} | {M[p['kind']]}, {p['from']} to {p['to']} | {p['what']} |" for p in r["parameters"]]
            lines.append("")
        for d in r["darts"]:
            lines.append(f"Dart `{d['name']}`: intake {f(d['intake'])}, length {f(d['length'])}, legs {f(d['legs'][0])} and {f(d['legs'][1])}.")
        for d in r.get("inner_darts", []):
            lines.append(f"Inner dart `{d['name']}`: intake {f(d['intake'])}, length {f(d['length'])}.")
        if r["darts"] or r.get("inner_darts"):
            lines.append("")
        if r.get("open"):
            whole = lambda e: e.split("..")[0].split()[-1] == e.split("..")[1]
            lines += ["Not sewn: " + ", ".join("the whole outline" if whole(e) else e for e in r["open"]) + ".", ""]
    if A["custom"]:
        lines += ["## Declared parameters", "", "| Parameter | Value | Measured as | What it is |", "|---|---|---|---|"]
        lines += [f"| `{p['name']}` | {f(p['value'])} | {M[p['kind']]} on {p['outline']}, {p['from']} to {p['to']} | {p['what']} |" for p in A["custom"]]
        lines.append("")
    if A["seams"]:
        lines += ["## Seams", "", "| Edge A | cm | Edge B | cm | Ease | Why | |", "|---|---|---|---|---|---|---|"]
        for s_ in A["seams"]:
            lines.append(f"| {s_['a'][0]} {s_['a'][1]}..{s_['a'][2]} | {f(s_['la'])} | {s_['b'][0]} {s_['b'][1]}..{s_['b'][2]} | {f(s_['lb'])} | "
                         + (f"{s_['ease'] * 100:+.1f} %" if s_["ease"] else "") + f" | {s_['why']} | {'OK' if s_['ok'] else '!!'} |")
        lines.append("")
    if A["garment"]:
        lines += ["## Garment", "", "| Measure | Value | Body | Ease | What it is |", "|---|---|---|---|---|"]
        for g in A["garment"]:
            body = f"{g['body']} {f(g['body_value'])}" if "body" in g else ""
            lines.append(f"| `{g['name']}` | {f(g['value'])} | {body} | " + (f"{g['ease']:+.2f}" if "ease" in g else "") + f" | {g['what']} |")
        lines.append("")
    lines += ["## Completeness", ""]
    lines += [f"- !! {p}" for p in A["problems"]] or ["Every typed piece has its standard points, every seam matches, every edge is accounted for."]
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------ the engine's own drafts, analysed the same way
ENGINE_TYPES = [  # start of a piece name of the engine (lower case) -> the types it can be; the first whose points are all there
    ("trousers front", ["trousers_front"]), ("trousers back", ["trousers_back"]), ("skirt front", ["skirt_front"]),
    ("skirt back", ["skirt_back"]), ("circle skirt", ["circle_skirt"]), ("side front", ["princess_side_front"]),
    ("side back", ["princess_side_back"]), ("top sleeve", ["sleeve_top"]), ("under sleeve", ["sleeve_under"]),
    ("collar stand", ["collar_stand"]), ("hood", ["hood"]), ("collar", ["collar"]), ("sleeve", ["sleeve", "sleeve_raglan"]),
    ("bodice front", ["bodice_front"]), ("bodice back", ["bodice_back"]), ("front", ["bodice_front", "princess_front"]),
    ("back", ["bodice_back", "princess_back"]), ("trank", ["glove_trank"]), ("thumb", ["glove_thumb"]),
    ("fourchette", ["glove_fourchette"]),
]


def engine_shape(pieces, seams=(), reference=None, id_="draft", title="", drafted="the pieces the engine drafted", command=None):
    """A shape (the format of data/shapes/) from pieces the engine drafted, so that `analyze` measures the engine's
    own drafts by the rules it applies to a contributed pattern. The two sides of a pair are one piece, a hole is an
    outline of its own, and the engine's centre line (x = 0) is given as a mark where no point of the outline is on it."""
    side = lambda n: re.sub(r"\s+[LR]$", "", n.strip())
    outlines, marks, home = {}, {}, {}

    def typed(name, nodes, candidates):
        probe = Outline({"outline": nodes}, marks_of.get(name))
        return next((t for t in candidates if all(probe.pick(a) for a in PIECE_TYPES[t]["anchors"])), "other")

    marks_of = {}
    for pc in pieces:
        name = side(pc["name"])
        if name in outlines:
            continue
        nodes = [dict(n) for n in pc["outline"]]
        cands = next((c for key, c in ENGINE_TYPES if name.lower().startswith(key)), [])
        if any(c.startswith(("bodice", "princess")) for c in cands) and not any(n.get("name") == "center_neck" for n in nodes):
            mname = "center_back" if "back" in name.lower() else "center_front"
            marks[mname] = {"outline": name, "p": [0.0, min(n["p"][1] for n in nodes)]}
            marks_of[name] = {mname: marks[mname]["p"]}
        outlines[name] = {"type": typed(name, nodes, cands), "nodes": nodes}
        if pc.get("darts_in"):
            outlines[name]["inner_darts"] = [{"name": "waist_dart" if len(pc["darts_in"]) == 1 else f"waist_dart{i}", "points": d}
                                             for i, d in enumerate(pc["darts_in"], 1)]
        for h in pc.get("holes", []):
            hname = f"{name} {h.get('name', 'hole')}"
            outlines[hname] = {"type": typed(hname, h["outline"], ["glove_thumb_hole"]), "nodes": [dict(n) for n in h["outline"]]}
            home.update({(name, n.get("name")): hname for n in h["outline"]})
    out, seen = [], set()
    for s_ in seams:
        A, a1, a2, B, b1, b2 = s_[:6]
        A, B = side(A), side(B)
        A, B = home.get((A, a1), A), home.get((B, b1), B)
        key = (A, a1, a2, B, b1, b2)
        have = lambda o, x: o in outlines and any(n.get("name") == x for n in outlines[o]["nodes"])
        if key in seen or not (have(A, a1) and have(A, a2) and have(B, b1) and have(B, b2)):
            continue                                      # the other side of a pair, or the two lips of a slit
        seen.add(key)
        opt = [o for o in s_[6:] if isinstance(o, dict) and o.get("ease")]
        out.append([A, a1, a2, B, b1, b2] + [{"ease": o["ease"], "why": o.get("why", "")} for o in opt[:1]])
    return {"id": id_, "kind": "shape", "title": title or id_, "unit": "cm", "reference": dict(reference or {}),
            "outlines": outlines, "marks": marks, "seams": out, "unlisted_edges": "free", "drafted": drafted, "command": command or id_}


def _draft(spec, base_dir="."):
    """What garment.run gives for a spec, silently, leaving the chosen table and avatar as they were."""
    import garment, contextlib, io
    state = dict(STATE)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            return garment.run(spec, base_dir)
    finally:
        STATE.update(state)


def garment_shape(spec, base_dir=".", name="garment", res=None):
    """The 3D shell of a garment spec (net pieces and their seams), as a shape to analyse."""
    res = res or _draft(spec, base_dir)
    ref = {k: v for k, v in res["measurements"].items() if _num(v)}
    cut_darts = {c["name"]: c["darts_in"] for c in res["cut"] if c.get("darts_in")}   # the 3D shell does not carry them
    return engine_shape([dict(pc, darts_in=cut_darts.get(pc["name"])) for pc in res["shell3d"]], res["seams"], ref, name, f'{res["spec"]["title"]}, size {res["size"]}',
                        "the garment the engine drafts from this spec", command=name + ".json")


def _flat(A):
    """Every dimension of an analysis by name: piece.parameter, the darts, the totals; width and height for untyped pieces."""
    out = {}
    for name, r in A["pieces"].items():
        if not r["parameters"]:
            out[f"{name}.width"], out[f"{name}.height"] = r["width"], r["height"]
        for q in r["parameters"]:
            out[f"{name}.{q['name']}"] = q["value"]
        for i, d in enumerate(r["darts"] + r.get("inner_darts", [])):
            out[f"{name}.{d['name'] or 'dart' + str(i)}.intake"], out[f"{name}.{d['name'] or 'dart' + str(i)}.length"] = d["intake"], d["length"]
    out.update({q["name"]: q["value"] for q in A["custom"]})
    out.update({g["name"]: g["value"] for g in A["garment"]})
    return out


def _numbers(d, path=()):
    """(path, value) of every number in nested dicts and lists."""
    items = d.items() if isinstance(d, dict) else enumerate(d) if isinstance(d, list) else ()
    for k, v in items:
        if _num(v):
            yield path + (k,), v
        else:
            yield from _numbers(v, path + (k,))


def _print(x):
    """A value as text with its numbers rounded to 0.1 mm, to tell whether two drafts are the same."""
    return json.dumps(x, sort_keys=True, default=str) if not isinstance(x, (dict, list, tuple, float)) else (
        f"{x:.2f}" if isinstance(x, float) else "{" + ",".join(f"{k}:{_print(v)}" for k, v in sorted(x.items())) + "}"
        if isinstance(x, dict) else "[" + ",".join(_print(v) for v in x) + "]")


def adjustables(spec, base_dir=".", step=1.0, moved=0.05):
    """Which number moves which dimension of a garment: every number of the spec (defaults included), every ease and
    every body measurement is raised by `step` in turn, and the garment is drafted and analysed again. Returns
    (dimensions, keys): dimensions = {name: (value, [(key, change, raise)...])}; keys = {key: what raising it did}:
    "dims" (it moves measured dimensions), "shell" (it reshapes the sewn pieces without moving a measured dimension),
    "cut" (it changes only the cut pieces: allowances, facings, linings, marks), "nothing", or "fails" (the garment
    cannot be drafted with it). A dimension that only `body.*` keys move follows the body and has no control of its
    own; one that nothing moves is fixed in the engine."""
    import copy

    def measured(S_):
        res = _draft(S_, base_dir)
        net = [[pc["name"], pc["outline"], pc.get("lines"), pc.get("internals")] for pc in res["shell3d"]]
        return _flat(analyze(garment_shape(S_, base_dir, res=res))), _print([net, res["seams"], res["holds"]]), _print([res["cut"], res["lining"]])

    res = _draft(spec, base_dir)
    S = res["spec"]
    body = {k: v for k, v in res["measurements"].items() if _num(v)}
    S["measurements"] = {**body, "body": S["body"], "ease": dict(res["ease"])}
    base, shell0, cut0 = measured(S)
    keys = [(("body", k), ("measurements", k)) for k in body] + [(("ease", k), ("measurements", "ease", k)) for k in res["ease"]]
    keys += [(path, path) for path, _ in _numbers({k: v for k, v in S.items() if k not in ("measurements", "size")})]
    keys += [(path, path) for path in res["resolved"]]    # nulls of the spec: varied from what they came to
    dims, used = {k: (v, []) for k, v in base.items()}, {}
    for label, path in keys:
        label = ".".join(str(x) for x in label)
        used[label] = "fails"
        for inc in (step, None):                          # a ratio or an angle may not take +1: then +10 %
            T = copy.deepcopy(S)
            node = T
            for k in path[:-1]:
                node = node[k]
            if node[path[-1]] is None:
                node[path[-1]] = res["resolved"][path]
            inc = inc if inc is not None else (abs(node[path[-1]]) * 0.1 or 0.1)
            node[path[-1]] += inc
            try:
                got, shell, cut = measured(T)
            except (Exception, SystemExit):
                continue
            hit = [(k, got[k] - v) for k, v in base.items() if k in got and abs(got[k] - v) > moved]
            for k, d in hit:
                dims[k][1].append((label, d, inc))
            used[label] = "dims" if hit else "shell" if shell != shell0 else "cut" if cut != cut0 else "nothing"
            break
    return dims, used


def render_adjustables(dims, used):
    f = lambda v: f"{v:.2f}"
    how = lambda key, d, inc: f"`{key}` ({d:+.2f}" + ("" if inc == 1 else f" for {inc:+.2g}") + ")"
    own = {k: [m for m in v[1] if not m[0].startswith("body.")] for k, v in dims.items()}
    keys = lambda what: ", ".join(f"`{k}`" for k, n in used.items() if n == what and not k.startswith("body.")) or "none"
    lines = ["## What moves each dimension", "",
             "Every number of the spec, every ease and every body measurement was raised by 1 in turn (by 10 % where the "
             "garment cannot be drafted with +1), and the garment drafted and measured again. In brackets: the change of "
             "the dimension, in cm.", "", "| Dimension | Value | Moved by |", "|---|---|---|"]
    lines += [f"| `{k}` | {f(dims[k][0])} | {', '.join(how(*m) for m in sorted(own[k], key=lambda m: -abs(m[1])))} |" for k in dims if own[k]]
    follow = [k for k in dims if not own[k] and dims[k][1]]
    fixed = [k for k in dims if not dims[k][1]]
    lines += ["", "**Follow the body only** (no value of the spec moves them): " + (", ".join(f"`{k}`" for k in follow) or "none") + ".", "",
              "**Fixed** (nothing moves them: set in the engine): " + (", ".join(f"`{k}`" for k in fixed) or "none") + ".", "",
              "**Values that reshape the sewn pieces without moving a measured dimension** (an angle, a curve, a mark): " + keys("shell") + ".", "",
              "**Values that change only the cut pieces** (allowances, facings, linings, pockets): " + keys("cut") + ".", "",
              "**Values that change nothing in this garment** (they belong to an option it does not use): " + keys("nothing") + ".", "",
              "**Values the garment cannot be drafted with when raised**: " + keys("fails") + "."]
    return "\n".join(lines) + "\n"


def cmd_analyze(args):
    """Analyse a shape of data/shapes/ (by id) or a shape file anywhere (by path): prints the analysis sheet."""
    spec = None
    if os.path.isfile(args.shape):
        with open(args.shape, encoding="utf-8") as f:
            shape = json.load(f)
        if "outlines" not in shape:                       # a garment spec: the engine drafts it, then it is analysed
            spec, where = shape, os.path.dirname(os.path.abspath(args.shape))
            shape = garment_shape(spec, where, os.path.splitext(os.path.basename(args.shape))[0])
    else:
        shape = load("shape", args.shape)
    measures = {}
    for it in args.measure or []:
        k, _, v = it.partition("=")
        measures[k] = float(v)
    A = analyze(shape, measures)
    print(render_analysis(shape, A), end="")
    if getattr(args, "keys", False):
        if spec is None:
            print("\n--keys needs a garment spec: a shape has no value to vary.")
        else:
            print("\n" + render_adjustables(*adjustables(spec, where)), end="")
    return 0 if not A["problems"] else 2


# ------------------------------------------------------------------ digitising a real pattern


def _normalise(outlines):
    """Shift every outline so the whole drawing starts at (0, 0), and round."""
    pts = [n["p"] for o in outlines.values() for n in o.get("nodes", o.get("points"))]
    x0, y0 = min(p[0] for p in pts), min(p[1] for p in pts)
    for o in outlines.values():
        for n in o.get("nodes", o.get("points")):
            n["p"] = [round(n["p"][0] - x0, 3), round(n["p"][1] - y0, 3)]
            if "c" in n:
                n["c"] = [[round(c[0] - x0, 3), round(c[1] - y0, 3)] for c in n["c"]]
    return outlines


def digitize_csv(path, unit="cm"):
    """Points measured on the pattern with a ruler: one `x, y[, name][, corner]` per line, y downwards."""
    k = {"cm": 1.0, "mm": 0.1, "in": 2.54}[unit]
    pts = []
    with open(path, encoding="utf-8-sig") as f:
        for ln, line in enumerate(f, 1):
            cells = [c.strip() for c in re.split(r"[,;\t]", line.strip())]
            if not cells or not cells[0] or cells[0].startswith("#"):
                continue
            try:
                x, y = float(cells[0]), float(cells[1])
            except (ValueError, IndexError):
                if ln == 1:
                    continue                              # header line
                raise SystemExit(f"{path}, line {ln}: expected x, y[, name][, corner]")
            q = {"p": [x * k, y * k]}
            rest = [c for c in cells[2:] if c]
            if any(c.lower() == "corner" for c in rest):
                q["corner"] = True
            names = [c for c in rest if c.lower() != "corner"]
            if names:
                q["name"] = names[0]
            pts.append(q)
    if len(pts) < 3:
        raise SystemExit(f"{path}: at least 3 points")
    return {"outline": {"closed": True, "points": pts}}


def _matrix(text):
    """SVG transform attribute -> (a, b, c, d, e, f)."""
    m = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    for name, args in re.findall(r"(\w+)\s*\(([^)]*)\)", text or ""):
        v = [float(x) for x in re.split(r"[\s,]+", args.strip()) if x]
        if name == "matrix":
            t = tuple(v)
        elif name == "translate":
            t = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0)
        elif name == "scale":
            t = (v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0)
        elif name == "rotate":
            a = math.radians(v[0])
            t = (math.cos(a), math.sin(a), -math.sin(a), math.cos(a), 0, 0)
            if len(v) == 3:
                cx, cy = v[1], v[2]
                t = _mul(_mul((1, 0, 0, 1, cx, cy), t), (1, 0, 0, 1, -cx, -cy))
        else:
            raise SystemExit(f"SVG transform '{name}' is not supported: apply the transform in your drawing program")
        m = _mul(m, t)
    return m


def _mul(m, t):
    return (m[0] * t[0] + m[2] * t[1], m[1] * t[0] + m[3] * t[1], m[0] * t[2] + m[2] * t[3], m[1] * t[2] + m[3] * t[3],
            m[0] * t[4] + m[2] * t[5] + m[4], m[1] * t[4] + m[3] * t[5] + m[5])


def _apply(m, p):
    return (m[0] * p[0] + m[2] * p[1] + m[4], m[1] * p[0] + m[3] * p[1] + m[5])


def _path_nodes(d):
    """First subpath of an SVG path as nodes (straight and cubic segments; quadratics converted)."""
    tok = re.findall(r"[MmLlHhVvCcSsQqZz]|[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?", d)
    if re.search(r"[AaTt]", d):
        raise SystemExit("SVG arcs (A) and smooth quadratics (T) are not supported: convert the object to a path with curves")
    nodes, i, cmd, cur, start, last_c2 = [], 0, None, (0.0, 0.0), None, None
    def num():
        nonlocal i
        i += 1
        return float(tok[i - 1])
    while i < len(tok):
        if re.match(r"[A-Za-z]", tok[i]):
            cmd = tok[i]
            i += 1
            if cmd in "Zz":
                break
            if cmd in "Mm" and nodes:
                break                                     # a second subpath: only the first is the outline
        rel = cmd.islower()
        base = cur if rel else (0.0, 0.0)
        if cmd in "Mm":
            cur = (base[0] + num(), base[1] + num())
            start = cur
            nodes.append({"p": list(cur)})
            cmd = "l" if rel else "L"
            continue
        if cmd in "LlHhVv":
            if cmd in "Ll":
                nxt = (base[0] + num(), base[1] + num())
            elif cmd in "Hh":
                nxt = ((cur[0] if rel else 0.0) + num(), cur[1])
            else:
                nxt = (cur[0], (cur[1] if rel else 0.0) + num())
            last_c2 = None
        elif cmd in "CcSsQq":
            if cmd in "Cc":
                c1, c2 = (base[0] + num(), base[1] + num()), (base[0] + num(), base[1] + num())
            elif cmd in "Ss":
                c1 = (2 * cur[0] - last_c2[0], 2 * cur[1] - last_c2[1]) if last_c2 else cur
                c2 = (base[0] + num(), base[1] + num())
            else:
                q = (base[0] + num(), base[1] + num())
            nxt = (base[0] + num(), base[1] + num())
            if cmd in "Qq":
                c1 = (cur[0] + 2 / 3 * (q[0] - cur[0]), cur[1] + 2 / 3 * (q[1] - cur[1]))
                c2 = (nxt[0] + 2 / 3 * (q[0] - nxt[0]), nxt[1] + 2 / 3 * (q[1] - nxt[1]))
            nodes[-1]["c"] = [list(c1), list(c2)]
            last_c2 = c2
        cur = nxt
        nodes.append({"p": list(cur)})
    if len(nodes) > 1 and start and math.hypot(nodes[-1]["p"][0] - start[0], nodes[-1]["p"][1] - start[1]) < 1e-6:
        nodes.pop()                                       # the path came back to its start: that edge is the closing one
    return nodes


def digitize_svg(path, scale_length=None, px_per_cm=None):
    """A pattern traced in a drawing program. Every path is an outline (named by its id or label); a line or
    two-point path named `scale` drawn over a ruler gives the size (`--scale-length` cm); a circle with a name
    names the outline node it sits on."""
    import xml.etree.ElementTree as ET
    tree = ET.parse(path)
    found, circles, scale = [], [], None

    def label(el):
        for k, v in el.attrib.items():
            if k.endswith("}label") and v:
                return v
        return el.get("id") or ""

    def walk(el, m):
        m = _mul(m, _matrix(el.get("transform")))
        tag = el.tag.split("}")[-1]
        name = label(el)
        nodes = None
        if tag == "path":
            nodes = _path_nodes(el.get("d", ""))
        elif tag in ("polygon", "polyline"):
            v = [float(x) for x in re.split(r"[\s,]+", el.get("points", "").strip()) if x]
            nodes = [{"p": [v[k], v[k + 1]]} for k in range(0, len(v) - 1, 2)]
        elif tag == "line":
            nodes = [{"p": [float(el.get("x1", 0)), float(el.get("y1", 0))]}, {"p": [float(el.get("x2", 0)), float(el.get("y2", 0))]}]
        elif tag in ("circle", "ellipse"):
            circles.append((name, _apply(m, (float(el.get("cx", 0)), float(el.get("cy", 0))))))
        if nodes:
            for n in nodes:
                n["p"] = list(_apply(m, n["p"]))
                if "c" in n:
                    n["c"] = [list(_apply(m, c)) for c in n["c"]]
            found.append((name, nodes))
        for child in el:
            walk(child, m)
    walk(tree.getroot(), (1.0, 0.0, 0.0, 1.0, 0.0, 0.0))
    nonlocal_scale = [f for f in found if re.search(r"scale|ruler", f[0], re.I)]
    if nonlocal_scale:
        nd = nonlocal_scale[0][1]
        if scale_length is None:
            raise SystemExit("The drawing has a `scale` line: give its real length with --scale-length <cm>")
        scale = math.hypot(nd[-1]["p"][0] - nd[0]["p"][0], nd[-1]["p"][1] - nd[0]["p"][1]) / scale_length
    elif px_per_cm:
        scale = px_per_cm
    else:
        raise SystemExit("No size reference: draw a straight line over a ruler, name it `scale`, and pass "
                         "--scale-length <cm>; or pass --px-per-cm")
    shapes = [f for f in found if f not in nonlocal_scale and len(f[1]) >= 3]
    if not shapes:
        raise SystemExit(f"{path}: no closed path with at least 3 nodes")
    outlines = {}
    for k, (name, nodes) in enumerate(shapes):
        key = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_") if name and not re.match(r"(path|rect|polygon)\d*$", name) else ""
        key = key or ("outline" if len(shapes) == 1 else f"outline_{k + 1}")
        for j, n in enumerate(nodes):
            n["name"] = f"n{j}"
            n["p"] = [n["p"][0] / scale, n["p"][1] / scale]
            if "c" in n:
                n["c"] = [[c[0] / scale, c[1] / scale] for c in n["c"]]
        outlines[key] = {"nodes": nodes}
    for name, c in circles:                               # a named circle names the node it sits on
        if not name or re.match(r"(circle|ellipse|path)\d*$", name):
            continue
        c = (c[0] / scale, c[1] / scale)
        best = min(((math.hypot(n["p"][0] - c[0], n["p"][1] - c[1]), n) for o in outlines.values() for n in o["nodes"]),
                   key=lambda t: t[0])
        best[1]["name"] = name
    return outlines


def digitize_image(path, scale_length=None):
    """Click the outline on a photo or a scan (PNG or GIF) taken flat with a ruler in view."""
    import tkinter as tk
    from tkinter import simpledialog
    root = tk.Tk()
    root.title("Digitise a pattern piece")
    try:
        full = tk.PhotoImage(file=path)
    except tk.TclError:
        root.destroy()
        raise SystemExit(f"{path}: the click tool reads PNG and GIF. Convert the image, or trace it and use the SVG route.")
    k = max(1, int(math.ceil(max(full.width() / 1500.0, full.height() / 850.0))))
    img = full.subsample(k)
    st = {"ruler": [], "pts": [], "px_per_cm": None, "done": False}
    info = tk.StringVar()
    tk.Label(root, textvariable=info, anchor="w", justify="left").pack(fill="x")
    cv = tk.Canvas(root, width=img.width(), height=img.height(), cursor="crosshair")
    cv.pack()
    cv.create_image(0, 0, image=img, anchor="nw")

    def redraw():
        cv.delete("mark")
        for a, b in zip(st["ruler"], st["ruler"][1:]):
            cv.create_line(a[0], a[1], b[0], b[1], fill="#00a0ff", width=2, tags="mark")
        pts = st["pts"]
        for a, b in zip(pts, pts[1:] + (pts[:1] if len(pts) > 2 else [])):
            cv.create_line(a["x"], a["y"], b["x"], b["y"], fill="#e02020", width=1, tags="mark")
        for q in pts:
            r = 4 if q.get("corner") else 3
            cv.create_rectangle(q["x"] - r, q["y"] - r, q["x"] + r, q["y"] + r, outline="#e02020",
                                fill="#e02020" if q.get("corner") else "", tags="mark")
            if q.get("name"):
                cv.create_text(q["x"] + 8, q["y"] - 8, text=q["name"], fill="#e02020", anchor="w", tags="mark")
        if len(st["ruler"]) < 2:
            info.set("1. Click the two ends of a known length on the ruler.")
        else:
            info.set(f"2. Click along the outline, in order ({len(pts)} points). Left click: a point on a curve. Right click "
                     "or Shift+click: a corner.\n   N: name the last point (notch, anchor).  U: undo.  Enter: finish.  Esc: cancel.")

    def click(ev, corner=False):
        if len(st["ruler"]) < 2:
            st["ruler"].append((ev.x, ev.y))
            if len(st["ruler"]) == 2:
                L = scale_length or simpledialog.askfloat("Scale", "Real length between the two points, in cm:", parent=root, minvalue=0.1)
                if not L:
                    st["ruler"] = []
                else:
                    a, b = st["ruler"]
                    st["px_per_cm"] = math.hypot(b[0] - a[0], b[1] - a[1]) * k / L
        else:
            st["pts"].append({"x": ev.x, "y": ev.y, "corner": corner})
        redraw()

    def name_last(_ev=None):
        if st["pts"]:
            nm = simpledialog.askstring("Name", "Name of this point (letters, digits, _):", parent=root)
            if nm:
                st["pts"][-1]["name"] = re.sub(r"[^A-Za-z0-9_]+", "_", nm.strip())
            redraw()

    def undo(_ev=None):
        if st["pts"]:
            st["pts"].pop()
        elif st["ruler"]:
            st["ruler"].pop()
        redraw()

    def finish(_ev=None):
        st["done"] = len(st["pts"]) >= 3
        root.destroy()

    cv.bind("<Button-1>", click)
    cv.bind("<Shift-Button-1>", lambda ev: click(ev, True))
    cv.bind("<Button-3>", lambda ev: click(ev, True))
    root.bind("n", name_last)
    root.bind("u", undo)
    root.bind("<BackSpace>", undo)
    root.bind("<Return>", finish)
    root.bind("<Escape>", lambda _ev: root.destroy())
    redraw()
    if os.environ.get("PATTERN_DIGITIZE_SELFTEST"):       # drive the handlers without a person (development only)
        import types
        for x, y in ((10, 10), (110, 10)):
            click(types.SimpleNamespace(x=x, y=y))
        for x, y, c in ((20, 30, True), (120, 30, False), (120, 90, True), (20, 90, True)):
            click(types.SimpleNamespace(x=x, y=y), c)
        finish()
    else:
        root.mainloop()
    if not st["done"] or not st["px_per_cm"]:
        raise SystemExit("Cancelled: nothing written")
    pts = []
    for q in st["pts"]:
        p = {"p": [q["x"] * k / st["px_per_cm"], q["y"] * k / st["px_per_cm"]]}
        if q.get("corner"):
            p["corner"] = True
        if q.get("name"):
            p["name"] = q["name"]
        pts.append(p)
    return {"outline": {"closed": True, "points": pts}}


def cmd_digitize(args):
    if not ID.match(args.id or ""):
        raise SystemExit("--id: lowercase words joined by dashes, for example patch-pocket-1950s")
    ext = os.path.splitext(args.file)[1].lower()
    if ext == ".svg":
        outlines = digitize_svg(args.file, args.scale_length, args.px_per_cm)
    elif ext in (".csv", ".txt", ".tsv"):
        outlines = digitize_csv(args.file, args.unit)
    else:
        outlines = digitize_image(args.file, args.scale_length)
    method = "tracing" if ext == ".svg" else "ruler" if ext in (".csv", ".txt", ".tsv") else "photo"
    if len(outlines) == 1 and args.outline:
        outlines = {args.outline: next(iter(outlines.values()))}
    for o in outlines.values():
        o["type"] = args.type or "TODO: " + ", ".join(sorted(PIECE_TYPES))
    path = args.out or os.path.join(DATA, "shapes", f"{args.id}.json")
    if os.path.isfile(path):                              # another piece of the same pattern: add it to the file
        with open(path, encoding="utf-8") as f:
            shape = json.load(f)
        shape["outlines"].update(_normalise(outlines))
        write(path, shape)
        print(f"Added to {path}: {', '.join(outlines)} (now {len(shape['outlines'])} outlines)")
        print(f"Next: python scripts/pattern.py analyze {path}")
        return 0
    shape = {"id": args.id, "kind": "shape", "title": args.title or "TODO: what this piece is, which garment, which size",
             "description": "TODO: where it comes from on the garment, which edge is sewn to what",
             "unit": "cm",
             "reference": {"TODO_measure": 0},
             "outlines": _normalise(outlines),
             "seams": [],
             "provenance": {"source": "TODO: the pattern, book or garment this was taken from",
                            "confidence": "measured",
                            "rights": "TODO: why you may share it (your own pattern, public domain, permission...)",
                            "extraction": {"method": method, "line": "TODO: seam (digitise the seam line; if the paper shows "
                                           "the cutting line, take the allowance off first)",
                                           "deviation_mm": "TODO: largest gap in mm when the print is laid on the paper"},
                            "contributors": ["TODO: your name or handle"],
                            "added": __import__("datetime").date.today().isoformat()}}
    write(path, shape)
    n = sum(len(o.get("nodes", o.get("points"))) for o in shape["outlines"].values())
    print(f"Written: {path} ({len(shape['outlines'])} outline(s), {n} points, cm)")
    for problem in shape_geometry(shape):
        print(" !! " + problem)
    print("Next (the method is in references/pattern-intake.md and data/EXTRACTION.md):\n"
          f"  1. python scripts/pattern.py shape {args.id} --out preview      # print pattern.svg at 100 %, lay the paper on it\n"
          "  2. Open the file and replace every TODO: title, description, type of each outline, reference,\n"
          "     provenance, and the largest gap between the print and the paper (deviation_mm, 2 mm at most).\n"
          "     Name the standard points, write the seams, and say what every other edge is (\"edges\").\n"
          f"  3. python scripts/pattern.py analyze {args.id}                    # the skill measures the pattern: no !! line\n"
          "  4. python scripts/pattern.py check\n"
          "The photo, scan or tracing stays with you: only the shape file goes in the repository.")
    return 0


# ------------------------------------------------------------------ validation


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _todo(v):
    if isinstance(v, str):
        return "TODO" in v
    if isinstance(v, dict):
        return any(_todo(k) or _todo(x) for k, x in v.items())
    if isinstance(v, list):
        return any(_todo(x) for x in v)
    return False


def shape_geometry(shape):
    """The engine's laws on a shape: every outline closed, with unique names, and never crossing itself."""
    import pattern as P
    out = []
    for piece in shape_pieces(shape):
        names = [n["name"] for n in piece["outline"] if n.get("name")]
        dup = sorted({x for x in names if names.count(x) > 1})
        if dup:
            out.append(f"{piece['name']}: point names used twice: {', '.join(dup)}")
        if len(piece["outline"]) < 3:
            out.append(f"{piece['name']}: fewer than 3 points")
            continue
        c = P.crossing_check(piece)
        if c and c["value"] != c["expected"]:
            out.append(f"{piece['name']}: the outline crosses itself (points clicked out of order, or a curve handle too long)")
    return out


def validate(kind, id_, data):
    """Problems of one data file, as sentences a contributor can act on."""
    out = []
    if data.get("id") != id_:
        out.append(f'"id" must be the file name without .json ("{id_}")')
    if not ID.match(id_):
        out.append("file name: lowercase words joined by dashes")
    if data.get("kind") != kind:
        out.append(f'"kind" must be "{kind}" in data/{FOLDERS[kind]}/')
    if not str(data.get("title", "")).strip():
        out.append('"title" is missing')
    if _todo(data):
        out.append("a TODO is left: fill every field")
    pv = data.get("provenance")
    if not isinstance(pv, dict):
        out.append('"provenance" is missing (source, confidence, rights)')
    else:
        for k in ("source", "rights"):
            if not str(pv.get(k, "")).strip():
                out.append(f'provenance.{k} is missing')
        if pv.get("confidence") not in CONFIDENCE:
            out.append(f'provenance.confidence must be one of: {", ".join(CONFIDENCE)}')
        ex = pv.get("extraction")
        allowed = METHODS.get(kind, ())
        if not isinstance(ex, dict) or ex.get("method") not in allowed:
            out.append(f'provenance.extraction.method must be one of: {", ".join(allowed)} (data/EXTRACTION.md)')
        else:
            if pv.get("confidence") == "measured" and ex["method"] not in ("photo", "tracing", "ruler"):
                out.append('confidence "measured" needs an extraction from the real thing: photo, tracing or ruler')
            if kind == "shape":
                if ex.get("line") != "seam":
                    out.append('provenance.extraction.line must be "seam": shapes are seam lines, without allowance')
                dev = ex.get("deviation_mm")
                if ex["method"] == "diagram":
                    if dev is not None:
                        out.append("provenance.extraction.deviation_mm: null for a diagram (there is no full-size paper to lay on)")
                elif not _num(dev):
                    out.append("provenance.extraction.deviation_mm: the largest gap in mm between the print and the paper")
                elif dev > MAX_DEVIATION_MM:
                    out.append(f"provenance.extraction.deviation_mm is {dev}: digitise again, {MAX_DEVIATION_MM:g} mm at most")
    try:
        out += {"measurements": _v_measurements, "construction": _v_construction, "shape": _v_shape,
                "avatar": _v_avatar}[kind](data)
    except (KeyError, TypeError, ValueError, IndexError, AttributeError, ZeroDivisionError) as e:
        out.append(f"cannot be read ({type(e).__name__}: {e}): compare with a file of the same folder")
    return out


def _v_measurements(d):
    import pattern as P
    out = []
    if d.get("unit") not in ("cm", "mm"):
        out.append('"unit" must be "cm" or "mm"')
    if not d.get("bodies"):
        return out + ['"bodies" is missing']
    for body, b in d["bodies"].items():
        if body not in BODIES:
            out.append(f'body "{body}": the engine knows {", ".join(BODIES)}')
            continue
        rows = list(b["sizes"].values()) if "sizes" in b else [b["base"]]
        have = set(rows[0]) | set(b.get("lengths", {}).get("values", {}))
        missing = [k for k in BODIES[body] if k not in have]
        if missing:
            out.append(f"{body}: measurements missing: {', '.join(missing)}")
            continue
        if "sizes" not in b and not all(k in b for k in ("size_step", "sizes_range", "reference_size")):
            out.append(f"{body}: a graded table needs reference_size, size_step and sizes_range")
            continue
        for size in sizes(body, d["id"]):                # the law: every size of the table must draft cleanly
            try:
                m = standard(body, size, d["id"])
                if body == "hand":
                    checks = P.block_glove(m)["checks"]
                else:
                    checks = P.build("all", P.complete(m, body), ease(body, d["id"]), body)["checks"]
            except SystemExit as e:
                out.append(f"{body} size {size}: {e}")
                continue
            except Exception as e:                        # a value that breaks the draft (zero, negative, absurd)
                out.append(f"{body} size {size}: the blocks cannot be drafted ({type(e).__name__}: {e})")
                continue
            bad = [c["label"] for c in checks if c["expected"] is not None and abs(c["value"] - c["expected"]) > c["tol"]]
            if bad:
                out.append(f"{body} size {size}: the blocks drafted from these values fail: {'; '.join(bad[:3])}")
    for body, e in d.get("ease", {}).items():
        unknown = [k for k in e if k not in EASE_KEYS]
        if unknown:
            out.append(f"ease.{body}: unknown keys {', '.join(unknown)} (known: {', '.join(EASE_KEYS)})")
    return out


def _v_construction(d):
    out = []
    target = d.get("applies_to", "")
    sec, _, typ = target.partition(".")
    garment = default_file("construction", "garment")["values"]
    if target == "garment":
        known = None
    elif (sec == "collar" and typ in COLLARS) or (sec == "pocket" and typ in POCKETS):
        known = set(default_file("construction", target)["values"]) | {"type"}
    elif sec in garment and isinstance(garment[sec], dict):
        known = set(garment[sec])
    else:
        return [f'"applies_to": "garment", "collar.<{"|".join(COLLARS)}>", "pocket.<{"|".join(POCKETS)}>" or a spec section '
                f'({", ".join(k for k, v in garment.items() if isinstance(v, dict))})']
    if not isinstance(d.get("values"), dict) or not d["values"]:
        return ['"values" is missing']
    if known is not None:
        unknown = [k for k in d["values"] if k not in known]
        if unknown:
            out.append(f"values: unknown keys {', '.join(unknown)} (known: {', '.join(sorted(known))})")
        bad = [k for k, v in d["values"].items() if k not in ("type", "where") and v is not None and not _num(v)
               and not isinstance(v, list) and not (isinstance(v, dict) and all(_num(x) for x in v.values()))]
        if bad:
            out.append(f"values must be numbers: {', '.join(bad)}")
    inner = {k2 for v in d["values"].values() if isinstance(v, dict) for k2 in v}
    unknown = [k for k in d.get("doc", {}) if k not in d["values"] and k not in inner]
    if unknown:
        out.append(f"doc: describes values that do not exist: {', '.join(unknown)}")
    if d.get("default"):
        twins = [i for _, i, _ in files("construction") if i != d["id"] and load("construction", i).get("default")
                 and load("construction", i).get("applies_to") == target]
        if twins:
            out.append(f"two default files for {target}: {d['id']} and {', '.join(twins)}")
    return out


def _v_avatar(d):
    a = d.get("arrangement")
    ok = lambda v: (isinstance(v, str) and v) or (isinstance(v, dict) and isinstance(v.get("name"), str) and v["name"])
    if not isinstance(a, dict) or not a or not all(ok(v) for v in a.values()):
        return ['"arrangement" must map piece names to an arrangement point name, or to {"name": point, ...}']
    return []


def _v_shape(d):
    out = []
    if d.get("unit") not in ("cm", "mm"):
        out.append('"unit" must be "cm" or "mm"')
    if not d.get("outlines"):
        return out + ['"outlines" is missing']
    for name, o in d["outlines"].items():
        pts = o.get("nodes", o.get("points"))
        if not isinstance(pts, list) or len(pts) < 3:
            out.append(f'outline "{name}": at least 3 nodes or points')
        elif not all(isinstance(q.get("p"), list) and len(q["p"]) == 2 and all(_num(v) for v in q["p"]) for q in pts):
            out.append(f'outline "{name}": every point needs "p": [x, y]')
    if out:
        return out
    sc = d.get("scale")
    if sc and sc.get("measure") not in d.get("reference", {}):
        out.append(f'scale.measure "{sc.get("measure")}" must be one of the "reference" measurements')
    if not d.get("reference"):
        out.append('"reference": the measurements of the pattern the shape was taken from (size, girth, length...)')
    for k, m in d.get("marks", {}).items():
        if m.get("outline") not in d["outlines"]:
            out.append(f'mark "{k}": outline "{m.get("outline")}" does not exist')
    out += shape_geometry(d)
    return out if out else analyze(d)["problems"]


# ------------------------------------------------------------------ generated documents


def kb_status(e):
    return e.get("status") or "unverified"


def render_index(entries):
    by = {}
    for e in entries:
        by.setdefault(e["file"].split("/")[1], []).append(e)
    lines = ["# Knowledge base index", "",
             f"{len(entries)} entries, one file each. Search: `python scripts/pattern.py kb search <words>`; full entry: "
             "`python scripts/pattern.py kb show <id>`. Format: `FORMAT.md`. Generated by `pattern.py check --write`.", ""]
    for fam in sorted(by):
        lines += [f"## {fam}", ""]
        lines += [f"- [`{e['id']}`]({fam}/{e['id']}.md): {e['name']} ({kb_status(e)})" for e in sorted(by[fam], key=lambda x: x["id"])]
        lines.append("")
    return "\n".join(lines)


def render_coverage(entries):
    order = list(CONFIDENCE)
    lines = ["# Coverage", "",
             "What the skill knows and how sure it is. Generated by `python scripts/pattern.py check --write`; do not edit.", "",
             "| Level | Meaning |", "|---|---|"]
    lines += [f"| `{k}` | {v} |" for k, v in CONFIDENCE.items()]
    lines += ["", "## Data files", "", "| File | Title | Confidence | Source |", "|---|---|---|---|"]
    for kind, i, path in files():
        d = load(kind, i)
        pv = d.get("provenance", {})
        lines.append(f"| `data/{FOLDERS[kind]}/{i}.json` | {d.get('title', '')} | `{pv.get('confidence', '?')}` | {pv.get('source', '')} |")
    by = {}
    for e in entries:
        by.setdefault(e["file"].split("/")[1], []).append(e)
    lines += ["", "## Knowledge base", "", "| Family | Entries | " + " | ".join(order) + " |", "|---|---|" + "---|" * len(order)]
    tot = {k: 0 for k in order}
    for fam in sorted(by):
        cnt = {k: sum(1 for e in by[fam] if kb_status(e) == k) for k in order}
        for k in order:
            tot[k] += cnt[k]
        lines.append(f"| [{fam}](skills/pattern-making/references/kb/{fam}/) | {len(by[fam])} | " + " | ".join(str(cnt[k]) for k in order) + " |")
    lines.append(f"| **Total** | **{len(entries)}** | " + " | ".join(f"**{tot[k]}**" for k in order) + " |")
    lines += ["", "## Wanted", "",
              "Every entry below describes a shape or gives numbers that nobody has checked against a real pattern. "
              "Checking one, correcting it and changing its `Status` is a complete contribution (see CONTRIBUTING.md).", ""]
    for fam in sorted(by):
        todo = sorted((e for e in by[fam] if kb_status(e) == "unverified"), key=lambda x: x["id"])
        if todo:
            lines += [f"<details><summary>{fam}: {len(todo)} to verify</summary>", ""]
            lines += [f"- [`{e['id']}`](skills/pattern-making/references/kb/{fam}/{e['id']}.md): {e['name']}" for e in todo]
            lines += ["", "</details>", ""]
    return "\n".join(lines)


def render_credits():
    refs = os.path.join(ROOT, "references")
    lines = ["# Credits", "",
             "Sources of the data and of the knowledge in this skill. Generated by `python scripts/pattern.py check --write` "
             "from the `provenance` block of every data file and from the source lists of the knowledge base; do not edit.", "",
             "## Data files", ""]
    for kind, i, _ in files():
        d = load(kind, i)
        pv = d.get("provenance", {})
        who = ", ".join(pv.get("contributors", [])) or "unknown"
        lines += [f"### `data/{FOLDERS[kind]}/{i}.json`", "",
                  f"- **What it is used for**: {d.get('title', '')}",
                  f"- **Source**: {pv.get('source', '')}",
                  f"- **Rights and conditions**: {pv.get('rights', '')}",
                  f"- **Credit**: {pv.get('source', '')} (contributed by {who})", ""]
    lines += ["## Knowledge base and technique sheets", "",
              "Books, published patterns and pages consulted for facts and methods. They are cited references: no text or "
              "drawing of theirs is reproduced.", ""]
    found = []
    for base, _dirs, names in os.walk(refs):
        for n in sorted(names):
            p = os.path.join(base, n)
            rel = os.path.relpath(p, ROOT).replace("\\", "/")
            if n == "SOURCES.md":
                with open(p, encoding="utf-8") as f:
                    found.append((rel, f.read().split("\n", 1)[-1].strip()))
            elif n.endswith(".md") and os.path.basename(base) == "techniques" or (base == refs and n.endswith(".md")):
                with open(p, encoding="utf-8") as f:
                    text = f.read()
                m = re.search(r"^#{1,3} (?:\d+\.\s*)?Sources[^\n]*\n(.*?)(?=^#{1,3} |\Z)", text, re.S | re.M)
                if m and m.group(1).strip():
                    found.append((rel, m.group(1).strip()))
    for rel, body in sorted(found):
        lines += [f"### `{rel}`", "", body, ""]
    return "\n".join(lines)


def preview_svg(pieces, title):
    """A picture of pieces drawn by the engine from the data: the only kind of image the repository holds.
    Seam line black, cut line grey, fold blue, internal lines green; the square is 10 cm."""
    import pattern as P
    offs, W, H = P.layout([pieces])
    W, head = max(W, 700.0), 150
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 {-head} {W:.0f} {H + head:.0f}" font-family="sans-serif">',
         f'<rect x="0" y="{-head}" width="{W:.0f}" height="{H + head:.0f}" fill="#fff"/>',
         f'<text x="12" y="-104" font-size="30">{P.esc(title)}</text>',
         '<text x="12" y="-72" font-size="15" fill="#666">Drawn by the skill from its data. Seam line black, cut line grey, '
         'fold blue, internal lines green. The square is 10 cm.</text>',
         f'<rect x="{W - 112:.0f}" y="-140" width="100" height="100" fill="none" stroke="#111" stroke-width="2"/>']
    txt = lambda pts, off: " ".join(f"{x:.1f},{y:.1f}" for x, y in (P.mm(q, off) for q in pts))
    for p, off in zip(pieces, offs):
        cut = P.cut_line(p)
        o.append(f'<polygon points="{txt(cut, off)}" fill="#e4e4fa" stroke="#9a9ab8" stroke-width="1.2"/>')
        o.append(f'<polygon points="{txt(P.outline(p, 8), off)}" fill="none" stroke="#111" stroke-width="2.2"/>')
        for hl in p.get("holes", []):
            o.append(f'<polygon points="{txt(P.outline(hl, 8), off)}" fill="#fff" stroke="#111" stroke-width="2.2"/>')
        for ln in p.get("lines", []):
            o.append(f'<polyline points="{txt(ln, off)}" fill="none" stroke="#1a8f4a" stroke-width="1.6" stroke-dasharray="9 6"/>')
        for e in p.get("fold", []):
            o.append(f'<polyline points="{txt(P.edge(p, e, 8), off)}" fill="none" stroke="#2040d0" stroke-width="3.5"/>')
        for a, b in P.notches(p):
            o.append(f'<polyline points="{txt([a, b], off)}" fill="none" stroke="#111" stroke-width="2.2"/>')
        if p.get("grain"):
            o.append(f'<polyline points="{txt(p["grain"], off)}" fill="none" stroke="#111" stroke-width="1.6"/>')
        x0, y0 = min(P.mm(q, off)[0] for q in cut), min(P.mm(q, off)[1] for q in cut)
        o.append(f'<text x="{x0:.1f}" y="{y0 - 9:.1f}" font-size="15">{P.esc(p["name"])}</text>')
    o.append("</svg>")
    return "\n".join(o) + "\n"


def render_types():
    """data/TYPES.md: every piece type, the points to name on it and what the analysis measures from them."""
    alt = lambda x: " or ".join(f"`{y}`" for y in x.split("|"))
    pts = lambda kind, a, b: f"{alt(a)} to the line {' - '.join(alt(y) for y in b.split('>'))}" if kind == "perp" else f"{alt(a)} to {alt(b)}"
    lines = ["# Piece types", "",
             "Generated from the analysis rules of `scripts/library.py`; do not edit. A piece of a shape file "
             "(`data/shapes/`) says what it is with `\"type\"`. A type has standard point names, the ones the engine "
             "itself gives to its pieces, and `python scripts/pattern.py analyze` measures the dimensions below from "
             "them. A dimension is measured when the piece has its points: name every point of the list that exists "
             "on your piece.", "",
             "- **Points to name** are required. `a` or `b`: either name, whichever your piece has.",
             "- `center_front` and `center_back` are marks, not points of the outline: when the centre line does not "
             "run along the piece (a lapel front, a wrap), give one point of it under `\"marks\"`: "
             "`{\"center_front\": {\"outline\": \"front\", \"p\": [x, y]}}`.",
             "- A dart drawn inside a piece (a fish dart at the waist) is not on the outline: give it under "
             "`\"inner_darts\"` of the outline, `{\"name\": \"waist_dart\", \"points\": [top, one side, bottom, other side]}`. "
             "It is deducted from the waist.",
             "- A piece of no listed type is `other`: its width and height are measured, and you declare its own "
             "dimensions under `\"parameters\"` (`data/EXTRACTION.md`).", ""]
    groups = {}
    for t, spec in PIECE_TYPES.items():
        groups.setdefault((spec["anchors"], tuple(q[:4] for q in spec["params"])), []).append(t)
    for (anchors, _), names in groups.items():
        spec = PIECE_TYPES[names[0]]
        if not anchors:
            continue
        lines += ["## " + ", ".join(f"`{n}`" for n in names), "", "Points to name: " + ", ".join(alt(a) for a in anchors) + ".", "",
                  "| Dimension | Measured as | What it is |", "|---|---|---|"]
        lines += [f"| `{q[0]}` | {M[q[1]]}, {pts(q[1], q[2], q[3])} | {q[4]} |" for q in spec["params"]]
        lines.append("")
    lines += ["## Totals of a garment", "", "Added up over the pieces, and compared with the body the pattern was made for (`reference`).", "",
              "| Total | Sum of | Compared with |", "|---|---|---|"]
    lines += [f"| `{g[0]}` | {'2 x (' if g[2] == 2 else ''}{' + '.join(f'{t}.{q}' for t, q in g[1])}{')' if g[2] == 2 else ''} | {g[3] or ''} |" for g in GARMENT]
    lines += ["| `cap_ease` | cap_total - armhole_total | |", ""]
    return "\n".join(lines)


def example_specs():
    """Garment specs of examples/: every .json directly inside an example folder."""
    ex = os.path.join(ROOT, "examples")
    out = []
    for d in sorted(os.listdir(ex)) if os.path.isdir(ex) else []:
        folder = os.path.join(ex, d)
        if os.path.isdir(folder):
            out += [os.path.join(folder, f) for f in sorted(os.listdir(folder)) if f.endswith(".json")]
    return out


def generated(problems=None):
    """(path, content) of every generated document: index, coverage, credits, and one preview per shape and per
    example spec. They are built from the data by the skill, at merge time; nobody writes them by hand."""
    import pattern as P
    entries = [e for e in P.kb_entries() if e["kb"]]
    out = [(os.path.join(ROOT, "references", "kb", "INDEX.md"), render_index(entries)), (os.path.join(DATA, "TYPES.md"), render_types())]
    for _, i, path in files("shape"):
        try:
            out.append((path[:-5] + ".svg", preview_svg(shape_pieces(load("shape", i)), load("shape", i).get("title", i))))
            out.append((path[:-5] + ".md", render_analysis(load("shape", i), analyze(load("shape", i)))))
        except Exception as e:                            # an invalid shape is reported by validate; no preview
            if problems is not None:
                problems.append(f"data/shapes/{i}.json: no preview can be drawn ({type(e).__name__}: {e})")
    import garment
    state = dict(STATE)
    for spec_path in example_specs():
        rel = os.path.relpath(spec_path, ROOT).replace("\\", "/")
        try:
            with open(spec_path, encoding="utf-8") as f:
                spec = json.load(f)
            res = garment.run(spec, os.path.dirname(spec_path))
            out.append((spec_path[:-5] + ".svg", preview_svg(res["cut"] + res["lining"], res["spec"]["title"] + ", size " + str(res["size"]))))
            sh = garment_shape(spec, os.path.dirname(spec_path), os.path.basename(spec_path)[:-5], res=res)
            out.append((spec_path[:-5] + ".md", render_analysis(sh, analyze(sh))))
        except (Exception, SystemExit) as e:
            if problems is not None:
                problems.append(f"{rel}: the garment cannot be drafted ({type(e).__name__}: {e})")
        STATE.update(state)
    if os.path.isdir(os.path.join(REPO, ".claude-plugin")):          # only inside the published repository
        out += [(os.path.join(REPO, "COVERAGE.md"), render_coverage(entries)), (os.path.join(REPO, "CREDITS.md"), render_credits())]
    return out


def _same(a, b, tol=0.06):
    """Same document, numbers compared with a tolerance (a float may round differently on another machine)."""
    num = re.compile(r"-?\d+\.\d+")
    if num.sub("#", a.strip()) != num.sub("#", b.strip()):
        return False
    return all(abs(float(x) - float(y)) <= tol for x, y in zip(num.findall(a), num.findall(b)))


def _git(*args):
    import subprocess
    try:
        r = subprocess.run(["git", "-C", REPO] + list(args), capture_output=True, text=True, encoding="utf-8", errors="replace")
    except OSError:
        return None
    return r.stdout.split("\n") if r.returncode == 0 else None


def check_files(gen_paths, base=None):
    """The repository holds data, never the images the data was taken from: the only image files allowed are the
    previews the skill draws itself. In a pull request (`base`), generated files must not be touched at all."""
    out = []
    listed = _git("ls-files", "--cached", "--others", "--exclude-standard")
    if listed is None:
        return out                                        # not a git checkout: nothing to guard
    allowed = {os.path.relpath(p, REPO).replace("\\", "/") for p in gen_paths}
    for f in sorted(x for x in listed if x):
        if os.path.splitext(f)[1].lower() in REFERENCE_FILES and f not in allowed and os.path.exists(os.path.join(REPO, f)):
            out.append(f"{f}: images, scans and PDFs are never committed (reference material stays with you; the "
                       "repository holds the data taken from it, and the skill draws its own previews)")
    if base:
        changed = _git("diff", "--name-only", f"{base}...HEAD")
        if changed is None:
            out.append(f"cannot compare with {base}: fetch it first")
        for f in sorted(x for x in (changed or []) if x in allowed):
            out.append(f"{f}: this file is generated when the pull request is merged; leave it out of your changes")
    return out


KB_FIELDS = ("Aliases", "Family", "Recognize", "Pieces", "Shape", "Drafting", "Sewing order", "Finishes and notions", "Fabrics",
             "Fit faults", "Variants", "CLO3D", "Confidence", "Status")


def check_kb():
    import pattern as P
    out, seen = [], {}
    for e in P.kb_entries():
        if not e["kb"]:
            continue
        where = f"references/{e['file']}"
        if e["id"] in seen:
            out.append(f"{where}: id {e['id']} is already used by references/{seen[e['id']]}")
        seen[e["id"]] = e["file"]
        if os.path.basename(e["file"]) != e["id"] + ".md":
            out.append(f"{where}: the file must be named {e['id']}.md, like its id")
        have = set(re.findall(r"^- \*\*([^*]+)\*\*", "\n".join(e["text"]), re.M))
        missing = [f for f in KB_FIELDS if f not in have]
        if missing:
            out.append(f"{where}: fields missing: {', '.join(missing)} (see references/kb/FORMAT.md)")
        elif e.get("status") not in CONFIDENCE:
            out.append(f"{where}: Status must be one of: {', '.join(CONFIDENCE)}")
    return out


def cmd_check(args):
    """Validate every data file and knowledge-base entry; with --write, regenerate the generated documents."""
    problems, n = [], 0
    for kind, i, path in files():
        n += 1
        rel = os.path.relpath(path, ROOT).replace("\\", "/")
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except ValueError as e:
            problems.append(f"{rel}: not valid JSON ({e})")
            continue
        _cache[(kind, i)] = data
        problems += [f"{rel}: {p}" for p in validate(kind, i, data)]
    kb = check_kb()
    problems += kb
    gen = generated(problems)
    in_repo = os.path.isdir(os.path.join(REPO, ".claude-plugin"))
    stale = 0
    for path, content in gen:
        rel = os.path.relpath(path, REPO if in_repo else ROOT).replace("\\", "/")
        old = ""
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                old = f.read()
        if not _same(old, content):
            if getattr(args, "write", False):
                with open(path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(content.rstrip("\n") + "\n")
                print(f"    written: {rel}")
            else:
                stale += 1
    if in_repo:
        problems += check_files([g[0] for g in gen], getattr(args, "base", None))
    if stale:
        print(f"    {stale} generated file(s) (index, coverage, credits, previews) will be rebuilt when this is merged;"
              " nothing to do.")
    for p in problems:
        print(" !! " + p)
    import pattern as P
    print(f"{' OK' if not problems else ' !!'} {n} data files, {sum(1 for e in P.kb_entries() if e['kb'])} knowledge-base "
          f"entries checked: {len(problems)} problem(s)")
    return 0 if not problems else 2


def cmd_data(args):
    if args.action == "list":
        for kind, i, _ in files():
            d = load(kind, i)
            print(f"{FOLDERS[kind] + '/' + i:<38} {d.get('provenance', {}).get('confidence', '?'):<11} {d.get('title', '')}")
        return 0
    kind = {v: k for k, v in FOLDERS.items()}.get(args.kind, args.kind)
    if kind not in FOLDERS or not args.id:
        raise SystemExit("data show <measurements|constructions|shapes|avatars> <id>")
    print(dump(load(kind, args.id)), end="")
    return 0


def cmd_shape(args):
    """Draw a shape file scaled to the given measures, with the engine's checks."""
    import pattern as P
    shape = load("shape", args.id)
    measures = {}
    for it in args.measure or []:
        k, _, v = it.partition("=")
        measures[k] = float(v)
    pieces = shape_pieces(shape, measures)
    sets = [("one", {"pieces": pieces, "checks": [], "seams": []})]
    P.export(sets, args.out, shape["id"])
    ok = P.report(sets)
    for pc in pieces:
        print(f"{pc['name']}: " + ", ".join(f"{n.get('name') or i}-> {P.length(P.edge(pc, i)):.2f} cm" for i, n in enumerate(pc["outline"])))
    pv = shape.get("provenance", {})
    print(f"Scale factor {shape_factor(shape, measures):.3f} (reference {shape.get('reference')}). "
          f"Source: {pv.get('source')} [{pv.get('confidence')}]")
    print(f"Files written to {os.path.abspath(args.out)}")
    return 0 if ok else 2
