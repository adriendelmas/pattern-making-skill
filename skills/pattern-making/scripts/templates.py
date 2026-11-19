"""Template bank: typical pieces drafted from the technique sheets as parametric shapes (standard library only).

Each template returns pieces in the skill's format (references/piece-format.md) with named nodes, and seams
where the template sews to itself. The agent drafts one, then adds it to a garment recipe and writes the seams
to the pieces it joins (a `band` is simpler for straight bands). Command line:

  python scripts/pattern.py template list
  python scripts/pattern.py template show peter-pan-collar
  python scripts/pattern.py template draft peter-pan-collar --param width=7 --param overlap=1.5 --out folder

Every shape states its source. "method sheet" means drafted from the numbered steps of
references/techniques/*.md (trade practice): check it against a published pattern before relying on the outline.
Digitised shapes from real patterns go in the same registry as point lists (see bolton-thumb in pattern.py).
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import library  # noqa: E402
import pattern as P  # noqa: E402
import garment as G  # noqa: E402

TEMPLATES = {}


def template(id_, params, doc, source):
    def deco(fn):
        TEMPLATES[id_] = {"fn": fn, "params": params, "doc": doc, "source": source}
        return fn
    return deco


# ------------------------------------------------------------------ geometry helpers


def rect(name, w, h, **kw):
    return G.mk(name, [("a", (0.0, 0.0), None), ("b", (w, 0.0), None), ("c", (w, h), None), ("d", (0.0, h), None)],
                grain=kw.pop("grain", [[1.0, 1.0], [1.0, h - 1.0]]), **kw)


def arc_c(p0, p3, center, sign=1):
    """Controls of a circular arc from p0 to p3 about `center` (up to 90 degrees)."""
    r = G.dist(center, p0)
    a0, a1 = math.atan2(p0[1] - center[1], p0[0] - center[0]), math.atan2(p3[1] - center[1], p3[0] - center[0])
    d = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
    k = 4.0 / 3.0 * math.tan(abs(d) / 4) * r
    t0, t1 = (-math.sin(a0), math.cos(a0)), (-math.sin(a1), math.cos(a1))
    s = 1 if d > 0 else -1
    return (G.add(p0, t0, s * k), G.add(p3, t1, -s * k))


def dense(nodes, n=48):
    """Dense polyline of an open chain of nodes (first to last, Beziers sampled)."""
    pts = []
    for a, b in zip(nodes, nodes[1:]):
        if "c" in a:
            pts += [tuple(a["p"])] + P.cubic(tuple(a["p"]), tuple(a["c"][0]), tuple(a["c"][1]), tuple(b["p"]), n)[:-1]
        else:
            pts.append(tuple(a["p"]))
    pts.append(tuple(nodes[-1]["p"]))
    return pts


def offset(pts, d):
    """Polyline offset by d along its left normal (y down: left of travel is (dy, -dx))."""
    out = []
    for i, p in enumerate(pts):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, len(pts) - 1)]
        t = G.unit(G.sub(b, a))
        out.append((p[0] + t[1] * d, p[1] - t[0] * d))
    return out


def fit_chain(pts, prefix, segments=4, names=None):
    """Nodes of an open Bezier chain fitted through a dense polyline (Catmull-Rom tangents), without the last node."""
    L = [0.0]
    for a, b in zip(pts, pts[1:]):
        L.append(L[-1] + G.dist(a, b))
    marks = [L[-1] * k / segments for k in range(segments + 1)]
    idx = [min(range(len(L)), key=lambda i: abs(L[i] - m)) for m in marks]
    nodes = []
    for s_, (i0, i1) in enumerate(zip(idx, idx[1:])):
        p0, p3 = pts[i0], pts[i1]
        t0 = G.unit(G.sub(pts[min(i0 + 1, len(pts) - 1)], pts[max(i0 - 1, 0)]))
        t1 = G.unit(G.sub(pts[min(i1 + 1, len(pts) - 1)], pts[max(i1 - 1, 0)]))
        k = G.dist(p0, p3) / 3
        nm = names[s_] if names and s_ < len(names) else f"{prefix}{s_}"
        nodes.append({"name": nm, "p": [round(p0[0], 4), round(p0[1], 4)],
                      "c": [[round(v, 4) for v in G.add(p0, t0, k)], [round(v, 4) for v in G.add(p3, t1, -k)]]})
    return nodes


def necklines(p):
    """Back and front necklines of the engine's bodice block (CB/CF to the neck point) and the shoulder lines."""
    body = p.get("body", "women")
    size = str(p.get("size") or library.reference_size(body))
    m = P.complete(P.standard_measurements(body, size), body)
    blk = {q["name"]: q for q in P.block_bodice(m, P.standard_ease(body), body)["pieces"]}
    bf, bb = blk["Bodice front"], blk["Bodice back"]
    nb = [dict(bb["outline"][G.idx(bb, "center_neck")]), dict(bb["outline"][G.idx(bb, "neck")])]
    nf = [dict(bf["outline"][G.idx(bf, "center_neck")]), dict(bf["outline"][G.idx(bf, "neck")])]
    return {"back": nb, "front": nf, "SHb": G.nodep(bb, "shoulder"), "SHf": G.nodep(bf, "shoulder"),
            "Nb": G.nodep(bb, "neck"), "Nf": G.nodep(bf, "neck")}


def flat_collar_neck_edge(p, overlap):
    """Collar neck edge as a dense polyline from CB to CF: back neckline, then the front neckline laid shoulder to
    shoulder (mirrored across the shoulder seam) and turned about the shoulder tip by `overlap` cm at the neck
    point (sheet 2.1: the overlap gives the roll). Returns (points, index of the neck point)."""
    nk = necklines(p)
    back = dense(nk["back"])
    SHb, Nb, SHf, Nf = nk["SHb"], nk["Nb"], nk["SHf"], nk["Nf"]
    # front frame -> back frame: shoulder tip on shoulder tip, front shoulder line along the back shoulder line,
    # the front on the other side of the seam (reflection)
    ub, uf = G.unit(G.sub(Nb, SHb)), G.unit(G.sub(Nf, SHf))
    ang = math.atan2(ub[1], ub[0]) - math.atan2(uf[1], uf[0])

    def to_back(q):
        v = G.rot(G.sub(q, SHf), ang)
        # reflect across the shoulder line (direction ub) so the front lies beyond the seam
        d = (v[0] * ub[0] + v[1] * ub[1])
        n = (v[0] - d * ub[0], v[1] - d * ub[1])
        return G.add(G.add(SHb, ub, d), n, -1.0)
    front = [to_back(q) for q in dense(nk["front"])]          # from CF to the neck point
    # overlap: turn the front about the shoulder tip so its neck point moves `overlap` into the back
    Nf2 = front[-1]
    r = G.dist(SHb, Nf2)
    theta = overlap / r
    # sign: towards the back neckline side of the shoulder line
    test = G.add(SHb, G.rot(G.sub(Nf2, SHb), theta))
    side = lambda q: (q[0] - SHb[0]) * ub[1] - (q[1] - SHb[1]) * ub[0]
    if (side(test) > 0) != (side(back[0]) > 0):
        theta = -theta
    front = [G.add(SHb, G.rot(G.sub(q, SHb), theta)) for q in front]
    pts = back + list(reversed(front))[1:]
    return pts, len(back) - 1


# ------------------------------------------------------------------ collars


def parallel_outer(neck, end_pt, w):
    """Outer edge parallel to a fitted neck chain (nodes + end point), `w` away on the right of travel (the body
    side), returned as nodes from the end back to the start, with the tangents kept: how a collar's outer edge is
    drawn by hand, parallel to the neck edge."""
    segs = [(tuple(n["p"]), tuple(n["c"][0]), tuple(n["c"][1]), tuple(neck[i + 1]["p"]) if i + 1 < len(neck) else end_pt)
            for i, n in enumerate(neck)]
    pts = [sg[0] for sg in segs] + [end_pt]
    tangents = []
    for i in range(len(pts)):
        t_in = G.unit(G.sub(segs[i - 1][3], segs[i - 1][2])) if i > 0 else None
        t_out = G.unit(G.sub(segs[i][1], segs[i][0])) if i < len(segs) else None
        t = t_out if t_in is None else t_in if t_out is None else G.unit(G.add(t_in, t_out))
        tangents.append(t)
    normal = lambda t: (-t[1], t[0])                                  # right of travel, y down
    off = [G.add(pts[i], normal(tangents[i]), w) for i in range(len(pts))]
    nodes = []
    for i in range(len(segs) - 1, -1, -1):                            # reversed segments: end -> start
        p0, c1, c2, p3 = segs[i]
        nodes.append({"p": off[i + 1], "c": [G.add(c2, normal(tangents[i + 1]), w), G.add(c1, normal(tangents[i]), w)]})
    return nodes, off


@template("peter-pan-collar", {"body": "women", "size": None, "width": 7.0, "overlap": 1.5, "tip_radius": 3.5, "gap": 0.0},
          "Flat collar on the block's neckline: shoulders overlapped at the neck point for the roll, outer edge at "
          "`width`, front tip rounded; half collar, centre back on the fold. Under collar: same, 0.25 narrower.",
          "method sheet sleeves-collars 2.1 (outline unverified against a published pattern)")
def peter_pan(p):
    pts, i_sh = flat_collar_neck_edge(p, p["overlap"])
    w, r = p["width"], p["tip_radius"]
    neck = fit_chain(pts, "neck_", 4, ["cb_neck", "neck_b1", "shoulder_neck", "neck_f1"])
    cf_neck = pts[-1]
    outer, off = parallel_outer(neck, cf_neck, w)
    C = off[-1]                                                # front corner of the collar end
    n = G.unit(G.sub(C, cf_neck))                              # along the collar end, neck to outer edge
    t = G.unit(G.sub(outer[0]["c"][0], C))                     # outer edge direction leaving the corner
    A, Bp = G.add(C, n, -r), G.add(C, t, r)                    # corner rounded with radius r
    c_tip = arc_c(A, Bp, G.add(G.add(C, n, -r), t, r))
    outer[0]["p"] = Bp
    outer[0]["c"][0] = G.add(outer[0]["c"][0], G.sub(Bp, C))
    names = ["outer_tip", "outer_f1", "outer_shoulder", "outer_b1"]
    rd = lambda q: [round(q[0], 4), round(q[1], 4)]
    outer_nodes = [{"name": names[i], "p": rd(o["p"]), "c": [rd(o["c"][0]), rd(o["c"][1])]} for i, o in enumerate(outer)]
    piece = {"name": "Collar", "cut": "1 on fold (upper); under collar 0.25 narrower", "allowance": 0.6,
             "outline": neck + [{"name": "cf_neck", "p": rd(cf_neck)},
                                {"name": "cf_end", "p": rd(A), "c": [rd(c_tip[0]), rd(c_tip[1])]}] + outer_nodes
             + [{"name": "cb_outer", "p": rd(off[0])}],
             "allowances": {"0": 1.0, "1": 1.0, "2": 1.0, "3": 1.0}, "notches": [{"edge": 2, "d": 0}]}
    piece["fold"] = [len(piece["outline"]) - 1]
    return {"pieces": [piece], "seams": [], "notes": "Sew edges cb_neck..cf_neck to the neckline (CB to CF) with the facing."}


@template("sailor-collar", {"body": "women", "size": None, "v_depth": 20.0, "width": 6.0, "back_depth": 20.0, "overlap": 0.5},
          "Sailor collar: the front neckline is a V `v_depth` below the neck point, the band along the V is `width` "
          "wide, the back is a square flap `back_depth` deep as wide as the shoulders; half collar on the fold.",
          "method sheet sleeves-collars 2.1 (outline unverified)")
def sailor(p):
    nk = necklines(p)
    back = dense(nk["back"])
    SHb, Nb = nk["SHb"], nk["Nb"]
    ub = G.unit(G.sub(Nb, SHb))
    # V front: straight from the neck point towards CF, laid beyond the shoulder seam (mirrored), length v_depth
    # along the actual CF direction is approximated by the front neckline chord
    Nf, SHf = nk["Nf"], nk["SHf"]
    CFv = (0.0, Nf[1] + p["v_depth"])
    uf = G.unit(G.sub(Nf, SHf))
    ang = math.atan2(ub[1], ub[0]) - math.atan2(uf[1], uf[0])

    def to_back(q):
        v = G.rot(G.sub(q, SHf), ang)
        d = v[0] * ub[0] + v[1] * ub[1]
        n = (v[0] - d * ub[0], v[1] - d * ub[1])
        return G.add(G.add(SHb, ub, d), n, -1.0)
    V = to_back(CFv)
    Nf2 = to_back(Nf)
    theta = p["overlap"] / G.dist(SHb, Nf2)
    side = lambda q: (q[0] - SHb[0]) * ub[1] - (q[1] - SHb[1]) * ub[0]
    test = G.add(SHb, G.rot(G.sub(Nf2, SHb), theta))
    if (side(test) > 0) != (side(back[0]) > 0):
        theta = -theta
    V, Nf2 = (G.add(SHb, G.rot(G.sub(q, SHb), theta)) for q in (V, Nf2))
    w, bd = p["width"], p["back_depth"]
    vdir = G.unit(G.sub(V, Nf2))
    nrm = (vdir[1], -vdir[0])
    to_sh = G.sub(SHb, Nf2)                                  # the body lies on the shoulder side of the V line
    if nrm[0] * to_sh[0] + nrm[1] * to_sh[1] < 0:
        nrm = (-nrm[0], -nrm[1])
    V_out = G.add(V, nrm, w)
    # the band's outer edge runs back parallel to the V; the flap's side starts where it passes the shoulder tip
    back_dir = (-vdir[0], -vdir[1])
    s_ = max((SHb[0] - V_out[0]) * back_dir[0] + (SHb[1] - V_out[1]) * back_dir[1], 0.0)
    flap_front = G.add(V_out, back_dir, s_)
    flap_x = flap_front[0]
    neck = fit_chain(back, "neck_", 3, ["cb_neck", "neck_b1", "neck_b2"])
    outline = neck + [{"name": "shoulder_neck", "p": list(Nb)}, {"name": "cf_point", "p": list(V)},
                      {"name": "cf_outer", "p": list(V_out)}, {"name": "flap_front", "p": list(flap_front)},
                      {"name": "flap_corner", "p": [flap_x, bd]}, {"name": "cb_flap", "p": [0.0, bd]}]
    outline = [{"name": n["name"], "p": [round(n["p"][0], 4), round(n["p"][1], 4)], **({"c": n["c"]} if "c" in n else {})} for n in outline]
    piece = {"name": "Sailor collar", "cut": "1 on fold (upper and under)", "allowance": 1.0, "outline": outline,
             "fold": [len(outline) - 1], "notches": [{"edge": 3, "d": 0}]}
    return {"pieces": [piece], "seams": [],
            "notes": "Neck edge: cb_neck..shoulder_neck..cf_point onto the back neckline and the V front. The flap corner is "
                     "square; round it in the recipe if wanted."}


@template("tie-collar", {"neck": 38.0, "ease": 1.0, "width": 4.0, "tie": 30.0, "end": "pointed"},
          "Tie (bow) collar: one band, neck part = neckline + ease, a tie of `tie` cm at each end, finished `width`; "
          "cut double (2 x width) and folded, ends pointed or straight.",
          "method sheet sleeves-collars 2.8")
def tie_collar(p):
    L, w, t = p["neck"] + p["ease"], p["width"], p["tie"]
    tot = L + 2 * t
    nodes = [("end_a", (0.0, 0.0)), ("neck_a", (t, 0.0)), ("neck_b", (t + L, 0.0)), ("end_b", (tot, 0.0)),
             ("end_b_low", (tot, w)), ("end_a_low", (0.0, w))]
    if p["end"] == "pointed":
        nodes = [("tip_a", (-w, w / 2))] + nodes[:4] + [("tip_b", (tot + w, w / 2))] + nodes[4:]
    pc = G.mk("Tie collar", [(n, q, None) for n, q in nodes], grain=[[t + 2, w / 2], [t + L - 2, w / 2]],
              cut="1, cut at 2 x width and folded lengthwise, or 2 (upper and under)")
    pc["notches"] = [{"edge": 1 if p["end"] != "pointed" else 2, "d": 0}, {"edge": 2 if p["end"] != "pointed" else 3, "d": 0}]
    return {"pieces": [pc], "seams": [], "notes": "Edge neck_a..neck_b onto the neckline; the ties hang free."}


# ------------------------------------------------------------------ cuffs, plackets, bands


@template("shirt-cuff", {"wrist": 16.0, "ease": 3.5, "overlap": 3.0, "height": 6.0, "radius": 1.5, "french": False},
          "Barrel cuff: length = wrist + ease + overlap, finished `height`, front corners rounded by `radius`; "
          "cut folded at 2 x height (4 x height for a French cuff). Buttons 1.5 cm from the end.",
          "method sheet sleeves-collars 1.19; kb mens-shirt-cuff")
def shirt_cuff(p):
    L, h, r = p["wrist"] + p["ease"] + p["overlap"], p["height"], p["radius"]
    k = 0.552 * r
    nodes = [("top_a", (0.0, 0.0), None), ("top_b", (L, 0.0), None), ("corner_b", (L, h - r), ((L, h - r + k), (L - r + k, h))),
             ("low_b", (L - r, h), None), ("low_a", (r, h), ((r - k, h), (0.0, h - r + k))), ("corner_a", (0.0, h - r), None)]
    pc = G.mk("Cuff", nodes, grain=[[2.0, h / 2], [L - 2, h / 2]],
              cut=("1 pair, cut at 4 x height, folded twice (French)" if p["french"] else "1 pair, cut at 2 x height and folded (or outer + lining)"))
    pc["buttons"] = [[1.5, h / 2], [3.0, h / 2]]
    pc["notches"] = [{"edge": 0, "d": p["overlap"]}, {"edge": 0, "d": -p["overlap"]}]
    return {"pieces": [pc], "seams": [], "notes": "Edge top_a..top_b onto the sleeve hem (pleats taken first); the overlap is at the placket."}


@template("tower-placket", {"slit": 11.0, "over_width": 2.5, "under_width": 1.5, "point": 1.5},
          "Shirt sleeve placket: over (tower) placket `over_width` finished wide, slit + 3.5 long with a pointed end, and "
          "the under placket strip; finished shapes, cut each at twice its width plus allowances and folded.",
          "method sheet sleeves-collars 1.20; kb mens-shirt-sleeve-placket")
def tower_placket(p):
    L, w, pt = p["slit"] + 3.5, p["over_width"], p["point"]
    over = G.mk("Over placket", [("hem_a", (0.0, L), None), ("hem_b", (w, L), None), ("top_b", (w, pt), None),
                                 ("point", (w / 2, 0.0), None), ("top_a", (0.0, pt), None)],
                grain=[[w / 2, 3.0], [w / 2, L - 2]], cut="1 pair, cut at 2 x width + allowances, folded")
    over["lines"] = [[[0.0, 3.5], [w, 3.5]]]                 # box stitch at the top of the slit
    under = rect("Under placket", p["under_width"], p["slit"] + 3.0, cut="1 pair, cut at 2 x width + allowances, folded")
    return {"pieces": [over, under], "seams": [],
            "notes": "Slit on the sleeve 4 cm from the back underarm seam. Over placket on the front edge of the slit, "
                     "under placket on the back edge; the point sits 3.5 cm above the slit end."}


@template("continuous-lap", {"slit": 10.0, "finished": 0.8},
          "Continuous-lap placket: one strip 2 x slit + 3 long, finished `finished` wide (cut 2.5 to 3).",
          "method sheet sleeves-collars 1.20")
def continuous_lap(p):
    pc = rect("Placket strip", 2 * p["slit"] + 3.0, p["finished"], cut="1 pair, cut 2.5 to 3 wide (straight or bias), folded",
              grain=[[2.0, p["finished"] / 2], [2 * p["slit"], p["finished"] / 2]])
    return {"pieces": [pc], "seams": [], "notes": "Stitched along both edges of the slit in one pass, pivoting at the end."}


@template("casing-band", {"waist": 70.0, "ease": 4.0, "elastic": 3.0, "height": None},
          "Elastic or drawstring casing: band length = waist + ease (cut in a loop or with a seam), height = 2 x elastic "
          "width + 1.5 unless `height` is given; sewn to the edge and folded over the elastic.",
          "method sheet sewing-techniques (elastic casings)")
def casing_band(p):
    h = p["height"] or 2 * p["elastic"] + 1.5
    pc = rect("Casing band", p["waist"] + p["ease"], h, cut="1, seamed in a loop", grain=[[2.0, h / 2], [p["waist"], h / 2]])
    pc["lines"] = [[[0.0, h / 2], [p["waist"] + p["ease"], h / 2]]]
    return {"pieces": [pc], "seams": [["Casing band", "d", "a", "Casing band", "c", "b"]],
            "notes": "Edge a..b onto the garment edge; the band folds on its middle line over the elastic."}


# ------------------------------------------------------------------ pockets and flaps


def rounded_bottom(name, w, h, r, pointed=False, facing=0.0, cut="1"):
    k = 0.552 * r
    if pointed:
        nodes = [("top_l", (0.0, -facing), None), ("top_r", (w, -facing), None), ("side_r", (w, h - w / 2 * 0.6), None),
                 ("point", (w / 2, h), None), ("side_l", (0.0, h - w / 2 * 0.6), None)]
    else:
        nodes = [("top_l", (0.0, -facing), None), ("top_r", (w, -facing), None),
                 ("corner_r", (w, h - r), ((w, h - r + k), (w - r + k, h))), ("bottom_r", (w - r, h), None),
                 ("bottom_l", (r, h), ((r - k, h), (0.0, h - r + k))), ("corner_l", (0.0, h - r), None)]
    pc = G.mk(name, nodes, grain=[[w / 2, 2.0], [w / 2, h - 3.0]], cut=cut)
    if facing:
        pc["lines"] = [[[0.0, 0.0], [w, 0.0]]]
    return pc


@template("patch-pocket", {"w": 14.0, "h": 15.0, "radius": 2.5, "pointed": False, "facing": 3.0},
          "Patch pocket with a self facing at the top (`facing`, fold line drawn) and rounded (`radius`) or pointed bottom.",
          "method sheet sewing-techniques (patch pockets); kb patch-pocket")
def patch_pocket(p):
    pc = rounded_bottom("Patch pocket", p["w"], p["h"], p["radius"], p["pointed"], p["facing"], cut="1 per pocket")
    return {"pieces": [pc], "seams": [], "notes": "Position drawn on the front as internal lines; topstitched on three sides."}


@template("flap", {"w": 15.0, "depth": 5.5, "radius": 2.0, "pointed": False},
          "Pocket flap, width = opening + 0.6, `depth`, lower corners rounded or pointed; upper and under flap.",
          "kb flap-pocket (dimensions trade practice, outline unverified)")
def flap(p):
    pc = rounded_bottom("Flap", p["w"] + 0.6, p["depth"], p["radius"], p["pointed"], 0.0, cut="2 per pocket (upper, under 0.2 smaller), interfaced")
    return {"pieces": [pc], "seams": [], "notes": "Edge top_l..top_r sewn into the upper jet seam of the pocket opening."}


@template("bellows-pocket", {"w": 18.0, "d": 20.0, "pleat": 2.5, "hem": 3.5, "flap": 5.0},
          "Bellows (pleated) patch pocket: cut width = w + 4 x pleat, height = d + hem + 1, pleat folds drawn; a flap "
          "w + 0.6 wide and `flap` deep.",
          "kb bellows-pocket (TO 14.3 sizes; outline unverified)")
def bellows(p):
    W, H = p["w"] + 4 * p["pleat"], p["d"] + p["hem"] + 1.0
    pc = rect("Bellows pocket", W, H, cut="1 per pocket", grain=[[W / 2, 2.0], [W / 2, H - 3.0]])
    pc["lines"] = [[[x, 0.0], [x, H]] for x in (p["pleat"], 2 * p["pleat"], W - 2 * p["pleat"], W - p["pleat"])]
    pc["lines"].append([[0.0, p["hem"]], [W, p["hem"]]])
    fl = rounded_bottom("Bellows flap", p["w"] + 0.6, p["flap"], 1.5, False, 0.0, cut="2 (upper, under)")
    return {"pieces": [pc, fl], "seams": [], "notes": "Pleat folds at the four lines, pressed, topstitched at the top; the flap above the pocket."}


@template("storm-flap", {"w": 24.0, "depth": 16.0, "radius": 3.0},
          "Storm flap (parka, trench): cut double on the fold, bottom corners rounded.",
          "kb storm-flap (TO 17.2 dimensions, outline unverified)")
def storm_flap(p):
    pc = rounded_bottom("Storm flap", p["w"], p["depth"], p["radius"], False, 0.0, cut="1 on fold (double), interfaced")
    pc["fold"] = [0]
    return {"pieces": [pc], "seams": [], "notes": "Fold at the top edge; sewn into the yoke or shoulder seam."}


# ------------------------------------------------------------------ gussets, godets, hoods, fly


@template("gusset-diamond", {"side": 10.0},
          "Diamond underarm gusset, four sides of `side` cm, cut on the bias.",
          "method sheet sleeves-collars 1.6")
def gusset_diamond(p):
    h = p["side"] / math.sqrt(2)
    pc = G.mk("Gusset", [("tip_front", (0.0, 0.0), None), ("side_seam", (h, h), None), ("tip_back", (0.0, 2 * h), None),
                         ("underarm_seam", (-h, h), None)], grain=[[0.0, 0.5 * h], [0.0, 1.5 * h]], cut="1 pair, bias")
    return {"pieces": [pc], "seams": [], "notes": "Each side onto one slash edge: front slash (two edges), back slash (two edges)."}


@template("godet", {"length": 30.0, "hem": 24.0, "top_width": 0.0},
          "Godet: a circle sector `length` long whose hem arc is `hem` wide (a `top_width` makes it a trapezoid top).",
          "method sheet skirts-trousers (godets)")
def godet(p):
    L, hem, tw = p["length"], p["hem"], p["top_width"]
    ang = hem / L
    a0, a1 = -ang / 2, ang / 2
    pt = lambda r, a: (r * math.sin(a), r * math.cos(a))
    hl, hr = pt(L, a0), pt(L, a1)
    c = arc_c(hr, hl, (0.0, 0.0))
    nodes = [("top", (0.0, 0.0), None)] if tw <= 0 else [("top_l", (-tw / 2, 0.0), None), ("top_r", (tw / 2, 0.0), None)]
    nodes += [("hem_r", hr, c), ("hem_l", hl, None)]
    pc = G.mk("Godet", nodes, grain=[[0.0, 3.0], [0.0, L - 4.0]], cut="1 per godet", allowance=1.0)
    return {"pieces": [pc], "seams": [], "notes": "Sides top..hem_r and top..hem_l into the slashed seam, point at the slash end."}


@template("three-piece-hood", {"height": 34.0, "depth": 30.0, "radius": 12.0, "neck": 26.0, "panel_top": 10.0, "panel_nape": 6.0},
          "Three-piece hood: two side pieces (the two-piece hood minus half the panel along the top and the back) and a "
          "centre panel `panel_top` wide at the forehead tapering to `panel_nape` at the neck, as long as the side curve.",
          "method sheet sleeves-collars 2.10; kb hood-three-piece (outline unverified)")
def hood3(p):
    H, Wd, rad, LN = p["height"], max(p["depth"], p["neck"] + 1.0), p["radius"], p["neck"]
    wt, wn = p["panel_top"] / 2, p["panel_nape"] / 2
    k = 0.552
    # side piece: top edge lowered by wt, back edge moved in by wt at the top tapering to wn at the neck
    side = G.mk("Hood side", [("cb_neck", (wn, 0.0), None), ("face_neck", (LN, 0.0), None), ("face_top", (Wd, -H + wt), None),
                              ("top_back", (rad + wt, -H + wt), ((rad + wt - (rad) * k, -H + wt), (wt, -H + wt + rad * (1 - k)))),
                              ("cb_round", (wt, -H + wt + rad), None)],
                grain=[[Wd / 2, -H + 8], [Wd / 2, -6.0]], cut="1 pair (+ lining)")
    l1, l2, l3 = (G.edge_len(side, "face_top", "top_back"), G.edge_len(side, "top_back", "cb_round"),
                  G.edge_len(side, "cb_round", "cb_neck"))
    L_curve = l1 + l2 + l3
    wx = lambda y: wt + (wn - wt) * y / L_curve              # half width tapering from the forehead to the nape
    panel = G.mk("Hood panel", [("forehead_l", (-wt, 0.0), None), ("forehead_r", (wt, 0.0), None),
                                ("p1_r", (wx(l1), l1), None), ("p2_r", (wx(l1 + l2), l1 + l2), None),
                                ("nape_r", (wn, L_curve), None), ("nape_l", (-wn, L_curve), None),
                                ("p2_l", (-wx(l1 + l2), l1 + l2), None), ("p1_l", (-wx(l1), l1), None)],
                 grain=[[0.0, 3.0], [0.0, L_curve - 3.0]], cut="1 (+ lining)")
    seams = [["Hood panel", "forehead_r", "p1_r", "Hood side", "face_top", "top_back"],
             ["Hood panel", "p1_r", "p2_r", "Hood side", "top_back", "cb_round"],
             ["Hood panel", "p2_r", "nape_r", "Hood side", "cb_round", "cb_neck"]]
    return {"pieces": [side, panel], "seams": seams,
            "notes": "Seams listed for the right side piece; the left side (mirror) takes the panel's _l nodes the same way. "
                     "The panel's side edges are split where the side piece's top turns (p1, p2), so every seam is one edge to one edge."}


@template("fly", {"zip": 16.0, "width": 4.0, "shield": 7.0},
          "Trouser fly: J-shaped fly facing (`width`, length zip + 1.5, rounded bottom) and the fly shield (folded strip).",
          "kb mens-trouser-fly-waistband; sheet skirts-trousers B3 (outline unverified)")
def fly(p):
    L, w, sw = p["zip"] + 1.5, p["width"], p["shield"]
    k = 0.552 * w
    facing = G.mk("Fly facing", [("top_cf", (0.0, 0.0), None), ("top_out", (w, 0.0), None),
                                 ("out_low", (w, L - w), ((w, L - w + k), (w - w + k, L))), ("bottom_cf", (0.0, L), None)],
                  grain=[[w / 2, 2.0], [w / 2, L - 5.0]], cut="1, left front (as worn), interfaced")
    shield = G.mk("Fly shield", [("top_fold", (0.0, 0.0), None), ("top_out", (sw, 0.0), None),
                                 ("out_low", (sw, L + 2 - 2.5), ((sw, L + 2 - 2.5 + 0.552 * 2.5), (sw - 2.5 + 0.552 * 2.5, L + 2))),
                                 ("bottom", (sw - 2.5, L + 2), None), ("bottom_fold", (0.0, L + 2), None)],
                  grain=[[sw / 2, 2.0], [sw / 2, L - 3.0]], cut="1 on fold (double), right front")
    shield["fold"] = [len(shield["outline"]) - 1]
    return {"pieces": [facing, shield], "seams": [], "notes": "Facing on the left front CF edge; shield behind the zip on the right front."}


@template("shirt-yoke", {"body": "men", "size": None, "cb_depth": 8.0, "arm_below": 5.0},
          "Shirt back yoke cut from the engine's back block: yoke line from `cb_depth` below the nape to `arm_below` "
          "below the shoulder point on the armhole, trued straight; returns the yoke and the lower back.",
          "kb mens-shirt-yoke (geometry typical, unverified)")
def shirt_yoke(p):
    body, size = p["body"], str(p.get("size") or library.reference_size(p["body"]))
    m = P.complete(P.standard_measurements(body, size), body)
    bb = {q["name"]: q for q in P.block_bodice(m, P.standard_ease(body), body)["pieces"]}["Bodice back"]
    G.split_on(bb, "shoulder", "across", p["arm_below"], "yoke_arm")
    names = [n["name"] for n in bb["outline"]]
    i_ya = names.index("yoke_arm")
    ya = tuple(bb["outline"][i_ya]["p"])
    cb = (0.0, p["cb_depth"])
    c1, c2 = (ya[0] * 0.35, cb[1]), (ya[0] * 0.7, cb[1] + (ya[1] - cb[1]) * 0.6)   # square at CB, trued to the armhole
    yoke_cb = {"name": "yoke_cb", "p": [0.0, p["cb_depth"]]}
    yoke = {"name": "Yoke", "cut": "2 on fold (outer and inner)", "allowance": 1.0,
            "outline": [dict(n) for n in bb["outline"][:i_ya + 1]] + [yoke_cb]}
    yoke["outline"][-2].pop("c", None)
    yoke["outline"][-2]["c"] = [list(c2), list(c1)]          # yoke line from the armhole to CB
    yoke["fold"] = [len(yoke["outline"]) - 1]
    yoke["grain"] = [[5.0, 2.0], [5.0, p["cb_depth"] - 2.0]]
    lower = {"name": "Lower back", "cut": "1 on fold (add a box pleat of 2.5 at CB)", "allowance": 1.0,
             "outline": [dict(n) for n in bb["outline"][i_ya:]] + [dict(yoke_cb)]}
    lower["outline"][-1]["c"] = [list(c1), list(c2)]         # the same line, CB to the armhole (closing edge)
    lower["fold"] = [len(lower["outline"]) - 2]
    lower["grain"] = [[8.0, p["cb_depth"] + 4], [8.0, m["back_length"] - 4]]
    return {"pieces": [yoke, lower], "seams": [["Yoke", "yoke_arm", "yoke_cb", "Lower back", "yoke_arm", "yoke_cb"]],
            "notes": "Back shoulder dart closed into the yoke line; the lower back gets the pleat intake by slash and spread."}


# ------------------------------------------------------------------ command line


def draft(id_, params):
    t = TEMPLATES[id_]
    p = dict(t["params"])
    for k, v in params.items():
        if k not in p:
            raise SystemExit(f"{id_}: unknown parameter {k} (known: {', '.join(p)})")
        p[k] = v
    return t["fn"](p)


def parse_params(items):
    out = {}
    for it in items or []:
        k, _, v = it.partition("=")
        if v.lower() in ("true", "false"):
            out[k] = v.lower() == "true"
        else:
            try:
                out[k] = float(v)
            except ValueError:
                out[k] = v
    return out


def main(args):
    if args.action == "list":
        for id_, t in TEMPLATES.items():
            print(f"{id_:22} {t['doc'].split('.')[0]}.")
        return 0
    if not args.id or args.id not in TEMPLATES:
        raise SystemExit("template id: " + ", ".join(TEMPLATES))
    t = TEMPLATES[args.id]
    if args.action == "show":
        print(args.id + "\n  " + t["doc"] + "\n  Source: " + t["source"] + "\n  Parameters: " +
              ", ".join(f"{k}={v}" for k, v in t["params"].items()))
        return 0
    res = draft(args.id, parse_params(args.param))
    sets = [("one", {"pieces": res["pieces"], "checks": [], "seams": res.get("seams", [])})]
    P.export(sets, args.out, args.id)
    ok = P.report(sets)
    for pc in sets[0][1]["pieces"]:
        print(f"{pc['name']}: " + ", ".join(f"edge {i} = {P.length(P.edge(pc, i)):.2f} cm" for i in range(len(pc["outline"]))))
    print("Notes: " + res.get("notes", ""))
    print("Source: " + t["source"])
    print(f"Files written to {os.path.abspath(args.out)}")
    return 0 if ok else 2
