"""Garments from reusable 2D constructions (validated export needs ezdxf and Shapely).

A garment is a JSON spec (references/garment-spec.md). `run(spec)` drafts it from the engine's bodice block:
body ease, shoulders (extension, pads), shaping (darts, boxy, armhole princess with flare), front edge (overlap,
buttons or a concealed fly), collar (notched lapel drafted in place, stand or funnel), a two-piece sleeve matched to
the armhole, facings, lining and pockets. It returns cut pieces, named seam contracts, construction checks and optional outline-transfer data.
Internal-dart sewing topology is unsupported; fitted shells are suppressed. Command: python pattern.py garment spec.json --out folder
"""
import copy
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pattern as P  # noqa: E402

# ------------------------------------------------------------------ geometry


def add(a, b, k=1.0):
    return (a[0] + b[0] * k, a[1] + b[1] * k)


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def unit(v):
    l = math.hypot(*v)
    return (v[0] / l, v[1] / l)


def rot(v, a):
    return (v[0] * math.cos(a) - v[1] * math.sin(a), v[0] * math.sin(a) + v[1] * math.cos(a))


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def dist(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


def bez(p0, c1, c2, p3, t):
    a, b, c = lerp(p0, c1, t), lerp(c1, c2, t), lerp(c2, p3, t)
    return lerp(lerp(a, b, t), lerp(b, c, t), t)


def split(p0, c1, c2, p3, t):
    a, b, c = lerp(p0, c1, t), lerp(c1, c2, t), lerp(c2, p3, t)
    d, e = lerp(a, b, t), lerp(b, c, t)
    f = lerp(d, e, t)
    return (p0, a, d, f), (f, e, c, p3)


def blen(cv):
    return P.length([cv[0]] + P.cubic(*cv, 64))


def t_at(cv, key, v):
    """Parameter where the curve reaches coordinate v (key 0: x, 1: y); the curve must be monotonic in it."""
    lo, hi = 0.0, 1.0
    up = bez(*cv, 1.0)[key] > bez(*cv, 0.0)[key]
    for _ in range(60):
        m = (lo + hi) / 2
        if (bez(*cv, m)[key] < v) == up:
            lo = m
        else:
            hi = m
    return (lo + hi) / 2


def t_len(cv, d):
    """Parameter at curve length d from the start."""
    lo, hi = 0.0, 1.0
    for _ in range(60):
        m = (lo + hi) / 2
        lo, hi = (m, hi) if blen(split(*cv, m)[0]) < d else (lo, m)
    return (lo + hi) / 2


def bent(p0, p3, off):
    """Controls of a seam bowed sideways by `off` (x, cm) at its middle."""
    o = (off * 1.33, 0.0)
    return add(lerp(p0, p3, 1 / 3), o), add(lerp(p0, p3, 2 / 3), o)


def hem_c(pa, da, pb, db):
    """Hem leaving pa in direction da and arriving at pb in direction db (square to the seams)."""
    k = dist(pa, pb) / 3
    return add(pa, da, k), add(pb, db, -k)


def perp_r(d):
    return (d[1], -d[0])


# ------------------------------------------------------------------ pieces


def mk(name, nodes, **kw):
    out = []
    for nm, p, c in nodes:
        n = {"name": nm, "p": [round(p[0], 4), round(p[1], 4)]}
        if c:
            n["c"] = [[round(c[0][0], 4), round(c[0][1], 4)], [round(c[1][0], 4), round(c[1][1], 4)]]
        out.append(n)
    return dict({"name": name, "outline": out, "allowances": {}, "notches": []}, **kw)


def idx(pc, nm):
    for i, n in enumerate(pc["outline"]):
        if n.get("name") == nm:
            return i
    raise KeyError(f"{pc['name']}: no node {nm}")


def nodep(pc, nm):
    return tuple(pc["outline"][idx(pc, nm)]["p"])


def edge_index(pc, a, b):
    """Outline index of the edge joining nodes a and b, and True when it runs from a to b."""
    n = len(pc["outline"])
    i, j = idx(pc, a), idx(pc, b)
    if (i + 1) % n == j:
        return i, True
    if (j + 1) % n == i:
        return j, False
    raise KeyError(f"{pc['name']}: {a} and {b} are not neighbours")


def elen(pc, a, b):
    """Length along the outline from node a forward to node b."""
    n = len(pc["outline"])
    i, j, tot = idx(pc, a), idx(pc, b), 0.0
    while i != j:
        tot += P.length(P.edge(pc, i, 48))
        i = (i + 1) % n
    return tot


def edge_len(pc, a, b):
    i, _ = edge_index(pc, a, b)
    return P.length(P.edge(pc, i, 64))


def split_on(pc, a, b, d, new):
    """Insert node `new` on the edge a-b at length d from a."""
    i, fwd = edge_index(pc, a, b)
    L = P.length(P.edge(pc, i, 64))
    dd = d if fwd else L - d
    P._attach(pc)
    nd, nx = pc["outline"][i], pc["outline"][(i + 1) % len(pc["outline"])]
    attrs = {k: copy.deepcopy(v) for k,v in nd.items() if k.startswith("_")}
    left_notches=[v for v in attrs["_notches"] if v <= dd]
    right_notches=[v-dd for v in attrs["_notches"] if v > dd]
    nd["_notches"]=left_notches
    attrs["_notches"]=right_notches
    p0, p3 = tuple(nd["p"]), tuple(nx["p"])
    if "c" not in nd:
        q = lerp(p0, p3, dd / L)
        pc["outline"].insert(i + 1, {"name": new, "p": list(q), **attrs})
        P._detach(pc)
        return
    cv = (p0, tuple(nd["c"][0]), tuple(nd["c"][1]), p3)
    left, right = split(*cv, t_len(cv, dd))
    nd["c"] = [list(left[1]), list(left[2])]
    pc["outline"].insert(i + 1, {"name": new, "p": list(left[3]), "c": [list(right[1]), list(right[2])], **attrs})
    P._detach(pc)


def allow(pc, names, v):
    for i, n in enumerate(pc["outline"]):
        if n.get("name") in names:
            pc["allowances"][str(i)] = v


def notch(pc, nm, d=0.0):
    pc.setdefault("notches", []).append({"edge": idx(pc, nm), "d": d})


def notch_on(pc, a, b, d):
    i, fwd = edge_index(pc, a, b)
    L = P.length(P.edge(pc, i, 64))
    pc.setdefault("notches", []).append({"edge": i, "d": round(d if fwd else L - d, 3)})


# ------------------------------------------------------------------ spec

DEFAULTS = {
    "title": "Garment", "body": "women", "size": None, "measurements": None,
    "fit": {"side_ease": 1.0, "dart_reduce": 0.0, "neck_widen": 0.0, "neck_drop": 0.0, "arm_drop": 1.5,
            "across_out": 0.0},
    "shoulder": {"extend": 0.0, "pad": 0.0},
    "shaping": "darts",
    "length": {"below_waist": 23.0, "hip_ease": 6.0, "hem": None},
    "boxy": {"dart_keep": 1.5},
    "front": {"extension": 2.0, "buttons": [], "hold_to": None},
    "collar": {"type": "none"},
    "sleeve": {"type": "two-piece", "length": None, "hem": 28.0, "ease": 2.5, "cap_height": None, "drop": 0.0,
               "front_in": 3.0, "back_out": 1.5, "bend": 1.0, "elbow": 0.7, "vent": 0.0},
    "facing": {"type": "auto", "width": 10.0, "back_neck": None},
    "lining": None,
    "pockets": None,
    "allowance": 1.0, "hem_allowance": 4.0,
}
NOTCHED = {"break": 22.0, "stand": 2.5, "lapel": 7.5, "belly": 1.0, "gorge_y": 7.0, "gorge_angle": 90.0,
           "notch_lapel": 3.5, "notch_collar": 3.2, "notch_angle": 75.0, "collar_stand": 3.0, "collar_fall": 4.0,
           "spring": 3.0, "turn_of_cloth": 0.3, "facing_turn": 0.4}
STAND = {"h_cb": 6.0, "h_cf": 5.5, "funnel": 0.0}


def merged(spec):
    out = copy.deepcopy(DEFAULTS)
    for k, v in spec.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k].update(v)
        else:
            out[k] = v
    if out["collar"]["type"] == "notched":
        out["collar"] = {**NOTCHED, **out["collar"]}
    elif out["collar"]["type"] in ("stand", "funnel"):
        out["collar"] = {**STAND, **out["collar"]}
    return out


# ------------------------------------------------------------------ body


def torso(m, ease, body, f):
    """Points of the front and back from the engine's bodice block, with the garment ease."""
    blk = {p["name"]: p for p in P.build("bodice", m, ease, body)["pieces"]}
    bf, bb = blk["Bodice front"], blk["Bodice back"]
    required = {"waist_dart", "waist_dart_1", "waist_dart_2", "side_dart", "side_dart_1", "side_dart_2"}
    if not required.issubset({n["name"] for n in bf["outline"]}) or "dart" not in {n["name"] for n in bb["outline"]}:
        raise ValueError("This garment recipe requires bust and waist dart landmarks; use the no-dart block and a dedicated piece recipe")
    T = {}
    N0, SH0 = nodep(bf, "neck"), nodep(bf, "shoulder")
    u = unit(sub(SH0, N0))
    T["N"] = add(N0, u, f["neck_widen"])
    T["CFN"] = (0.0, nodep(bf, "center_neck")[1] + f["neck_drop"])
    T["SH"], T["AC"] = SH0, add(nodep(bf, "across"), (f["across_out"], 0.0))
    se = f["side_ease"]
    T["UA"] = add(nodep(bf, "underarm"), (se, f["arm_drop"]))
    T["BP"] = (m["bust_span"] / 2, m["bust_depth"])
    T["WA"] = nodep(bf, "waist_dart")
    T["YW"] = nodep(bf, "center_waist")[1]
    wd = (nodep(bf, "waist_dart_1")[0] - nodep(bf, "waist_dart_2")[0] - f["dart_reduce"]) / 2
    T["WLi"], T["WLo"] = (T["BP"][0] - wd, T["YW"]), (T["BP"][0] + wd, T["YW"])
    T["SW"] = add(nodep(bf, "side_waist"), (se, 0.0))
    T["L1"], T["L2"] = add(nodep(bf, "side_dart_1"), (se, 0.0)), add(nodep(bf, "side_dart_2"), (se, 0.0))
    T["AS"] = nodep(bf, "side_dart")
    N0b, SH0b = nodep(bb, "neck"), nodep(bb, "shoulder")
    ub = unit(sub(SH0b, N0b))
    T["Nb"], T["CBN"], T["SHb"] = add(N0b, ub, f["neck_widen"]), nodep(bb, "center_neck"), SH0b
    T["ACb"] = add(nodep(bb, "across"), (f["across_out"], 0.0))
    T["UAb"] = add(nodep(bb, "underarm"), (se, f["arm_drop"]))
    T["Ab"], T["YWb"] = nodep(bb, "dart"), nodep(bb, "center_waist")[1]
    wdb = (nodep(bb, "dart_1")[0] - nodep(bb, "dart_2")[0] - f["dart_reduce"]) / 2
    T["WLbi"], T["WLbo"] = (T["Ab"][0] - wdb, T["YWb"]), (T["Ab"][0] + wdb, T["YWb"])
    T["SWb"] = add(nodep(bb, "side_waist"), (se, 0.0))
    T["CBW"] = (1.0, T["YWb"])
    T["sh_ease"] = dist(N0b, SH0b) - dist(N0, SH0)
    return T


def shoulders(T, extend, pad):
    """Extended and padded shoulder: tip moved out along the shoulder line and raised by the pad thickness; the
    back keeps the block's shoulder ease."""
    u = unit(sub(T["SH"], T["N"]))
    T["SH"] = add(add(T["SH"], u, extend), (0.0, -pad))
    ub = unit(sub(T["SHb"], T["Nb"]))
    shb = add(add(T["SHb"], ub, extend), (0.0, -pad))
    T["SHb"] = add(T["Nb"], unit(sub(shb, T["Nb"])), dist(T["N"], T["SH"]) + T["sh_ease"])


def curves(T):
    """Necklines and armholes from the final points."""
    us, ub = unit(sub(T["SH"], T["N"])), unit(sub(T["SHb"], T["Nb"]))
    T["us"], T["ub"] = us, ub
    T["neck_f"] = ((0.6 * T["N"][0], T["CFN"][1]), add(T["N"], (-us[1], us[0]), 3.5))
    T["neck_b"] = ((0.5 * T["Nb"][0], T["CBN"][1]), add(T["Nb"], (-ub[1], ub[0]), 1.5))
    for s, sh, ac, ua, uu in (("", "SH", "AC", "UA", us), ("b", "SHb", "ACb", "UAb", ub)):
        T["arm_up" + s] = (add(T[sh], (-uu[1], uu[0]), 4.0), add(T[ac], (0.0, -4.0)))
        T["arm_lo" + s] = ((T[ac][0], T[ac][1] + 0.55 * (T[ua][1] - T[ac][1])),
                           (T[ac][0] + 0.35 * (T[ua][0] - T[ac][0]), T[ua][1]))


# ------------------------------------------------------------------ front edge and collars


def notched_collar(T, c, ext):
    """Notched lapel and collar drafted in place on the front (kb notched-lapel): roll line from the break point to
    the stand point on the extended shoulder line, new neckline parallel to it, gorge, notch, collar rotated by the
    spring and squared at the centre back."""
    N, SH = T["N"], T["SH"]
    u = unit(sub(N, SH))
    R = add(N, u, c["stand"])
    B = (-ext, c["break"])
    d = unit(sub(B, R))
    G0 = add(N, d, (c["gorge_y"] - N[1]) / d[1])
    g = rot(d, math.radians(c["gorge_angle"]))
    if g[0] > 0:
        g = rot(d, -math.radians(c["gorge_angle"]))
    Gx = P.intersection(G0, add(G0, g), R, B)
    nrm = rot(d, math.pi / 2) if rot(d, math.pi / 2)[0] < 0 else rot(d, -math.pi / 2)
    L = add(Gx, g, c["lapel"] / abs(g[0] * nrm[0] + g[1] * nrm[1]))
    Pn = add(L, g, -c["notch_lapel"])
    up = rot(g, math.radians(c["notch_angle"]))
    if up[1] > 0:
        up = rot(g, -math.radians(c["notch_angle"]))
    C = add(Pn, up, c["notch_collar"])
    BNL = blen((T["CBN"], *T["neck_b"], T["Nb"]))

    def neck_edge(k):
        a = math.atan2(-d[1], -d[0])
        th = c["spring"] / k
        th = th if math.cos(a + th) > math.cos(a) else -th
        Q = (N[0] + k * math.cos(a + th), N[1] + k * math.sin(a + th))
        w = unit(sub(N, Q))
        return Q, w, (add(Q, w, k * 0.35), add(N, d, -k * 0.35))

    k = BNL
    for _ in range(30):
        Q, w, qc = neck_edge(k)
        k += BNL - blen((Q, *qc, N))
    cb = (w[1], -w[0])
    if (R[0] - Q[0]) * cb[0] + (R[1] - Q[1]) * cb[1] < 0:
        cb = (-cb[0], -cb[1])
    belly = (nrm[0] * 1.33 * c["belly"], nrm[1] * 1.33 * c["belly"])

    def lapel_c(Lp):
        return add(add(B, sub(Lp, B), 1 / 3), belly), add(add(B, sub(Lp, B), 2 / 3), belly)

    def collar(name, toc):
        qt = add(Q, cb, c["collar_stand"] + c["collar_fall"] + toc)
        t = unit(sub(qt, C))
        n_out = (t[1], -t[0]) if (N[0] - C[0]) * t[1] - (N[1] - C[1]) * t[0] < 0 else (-t[1], t[0])
        n_end = (up[1], -up[0]) if (N[0] - C[0]) * up[1] - (N[1] - C[1]) * up[0] < 0 else (-up[1], up[0])
        cc = add(add(C, n_end, toc), n_out, toc)
        D = dist(cc, qt)
        oc = (add(add(cc, unit(sub(qt, cc)), D * 0.3), nrm, 0.8), add(qt, w, D * 0.45))
        mid = add(Q, add(cb, w, 1.5), 1.0)
        return mk(name, [("cb_neck", Q, qc), ("neck", N, None), ("gorge_neck", G0, None), ("notch", Pn, None),
                         ("collar_point", cc, oc), ("cb_top", qt, None)],
                  grain=[list(add(mid, cb, -1.5)), list(add(mid, cb, 1.5))],
                  lines=[[list(add(Q, cb, c["collar_stand"])), list(R)]])

    def cf_nodes(toc=0.0):
        Lp = add(L, nrm, toc)
        return [("break", B, lapel_c(Lp)), ("lapel_point", Lp, None)] + (
            [("notch", Pn, None), ("gorge_roll", Gx, None)] if toc == 0.0 else []) + [("gorge_neck", G0, None)]

    return {"B": B, "R": R, "cf_nodes": cf_nodes, "collar": collar, "top_y": c["break"], "top_node": "break",
            "roll": [list(B), list(R)], "BNL": BNL}


def stand_collar(T, c, ext):
    """Stand or funnel collar: a band whose neck edge is the neckline plus the extension; a funnel's top edge is
    `funnel` cm longer than its neck edge (whole collar), so it stands away from the neck."""
    BN = blen((T["CBN"], *T["neck_b"], T["Nb"]))
    FN = blen((T["CFN"], *T["neck_f"], T["N"]))
    LN = BN + FN + ext
    half_f = max(c["funnel"] / 2, 1e-3)
    R = c["h_cb"] * LN / half_f
    phi = LN / R
    C = (0.0, c["h_cb"] + R)

    def on(r, a):
        return (C[0] + r * math.sin(a), C[1] - r * math.cos(a))

    def collar(name, toc):
        n0, n1 = on(R, 0), on(R, phi)
        t0, t1 = on(R + c["h_cb"] + toc, 0), on(R + c["h_cf"] + toc, phi)
        kn, kt = R * phi / 3, (R + c["h_cb"]) * phi / 3
        nc = (add(n0, (1, 0), kn), add(n1, (-math.cos(phi), -math.sin(phi)), kn))
        tc = (add(t1, (-math.cos(phi), -math.sin(phi)), kt), add(t0, (1, 0), kt))
        return mk(name, [("cb_neck", n0, nc), ("front_neck", n1, None), ("front_top", t1, tc), ("cb_top", t0, None)],
                  grain=[[2.0, c["h_cb"] * 0.3], [2.0, c["h_cb"] * 0.8]])

    def overlap_line():
        """Where the other half's front end lies on this half (both ends overlap by 2 x ext)."""
        pk = (LN - 2 * ext) / R
        hk = c["h_cb"] + (c["h_cf"] - c["h_cb"]) * pk / phi - 0.3
        return {"front_neck": on(R, pk), "front_top": on(R + hk, pk)}

    def cf_nodes(toc=0.0):
        return [("front_neck", (-ext, T["CFN"][1]), None), ("center_neck", T["CFN"], T["neck_f"])]

    return {"cf_nodes": cf_nodes, "collar": collar, "top_y": T["CFN"][1], "top_node": "front_neck",
            "overlap_line": overlap_line, "BN": BN, "FN": FN, "LN": LN}


def no_collar(T, ext):
    def cf_nodes(toc=0.0):
        return [("front_neck", (-ext, T["CFN"][1]), None), ("center_neck", T["CFN"], T["neck_f"])]
    return {"cf_nodes": cf_nodes, "collar": None, "top_y": T["CFN"][1], "top_node": "front_neck"}


def front_edge(K, ext, yhem, hold_to, toc=0.0):
    """Nodes of the front from the hem at the front edge up to the neck (closing onto the neck point)."""
    out = [("hem_front", (-ext, yhem), None)]
    if hold_to and hold_to > K["top_y"] + 1:
        out.append(("hold_end", (-ext, hold_to), None))
    return out + K["cf_nodes"](toc)


# ------------------------------------------------------------------ flare


def lower(W0, s, D, length):
    """Seam from the waist point W0 to the hem: leaves vertical, flares sideways by D (s = +1 towards +x),
    curve length = length. Returns hem point, controls, end direction."""
    lo, hi = length * 0.5, length
    for _ in range(60):
        h = (lo + hi) / 2
        beta = 1.25 * math.atan2(D, h)
        hp = add(W0, (s * D, h))
        c1, c2 = add(W0, (0, 0.25 * h)), add(hp, (s * math.sin(beta), math.cos(beta)), -0.33 * h)
        if blen((W0, c1, c2, hp)) > length:
            hi = h
        else:
            lo = h
    return hp, (c1, c2), (s * math.sin(beta), math.cos(beta))


# ------------------------------------------------------------------ shaping


def body_darts(T, S, m, K):
    """Fitted: side bust dart in the side seam, fish darts at the waist, side seam out to the hip, straight below."""
    hq = (m["hip"] + S["length"]["hip_ease"]) / 4
    hd, bw = m["hip_depth"], S["length"]["below_waist"]
    ext, yf, yb = S["front"]["extension"], T["YW"] + bw, T["YWb"] + bw

    def hip_c(sw):
        return (sw[0], sw[1] + 0.35 * hd), (hq, sw[1] + 0.65 * hd)

    front = mk("Front", [("neck", T["N"], None), ("shoulder", T["SH"], T["arm_up"]), ("across", T["AC"], T["arm_lo"]),
                         ("underarm", T["UA"], None), ("side_dart_1", T["L1"], None), ("side_dart", T["AS"], None),
                         ("side_dart_2", T["L2"], None), ("side_waist", T["SW"], hip_c(T["SW"])),
                         ("side_hip", (hq, T["YW"] + hd), None), ("hem_side", (hq, yf), None)]
               + front_edge(K, ext, yf, S["front"]["hold_to"]),
               darts_in=[[list(T["WA"]), list(T["WLo"]), [T["WA"][0], T["YW"] + 14], list(T["WLi"])]])
    front["outline"][idx(front, "side_dart")]["dart"] = True
    back = mk("Back", [("center_neck", T["CBN"], T["neck_b"]), ("neck", T["Nb"], None),
                       ("shoulder", T["SHb"], T["arm_upb"]), ("across", T["ACb"], T["arm_lob"]),
                       ("underarm", T["UAb"], None), ("side_waist", T["SWb"], hip_c(T["SWb"])),
                       ("side_hip", (hq, T["YWb"] + hd), None), ("hem_side", (hq, yb), None), ("hem_cb", (0.8, yb), None),
                       ("cb_waist", T["CBW"], ((1.0, 32.0), (0.0, 26.0))), ("cb_blade", (0.0, 20.0), None)],
              darts_in=[[list(T["Ab"]), list(T["WLbo"]), [T["Ab"][0], T["YWb"] + 14], list(T["WLbi"])]])
    P.true_boundary_darts(front)
    for pc in (front, back):
        notch(pc, "side_waist")
    side_f = [("Front", "underarm", "side_dart_1"), ("Front", "side_dart_2", "side_waist"),
              ("Front", "side_waist", "side_hip"), ("Front", "side_hip", "hem_side")]
    side_b = [("Back", "underarm", "side_waist"), ("Back", "side_waist", "side_hip"), ("Back", "side_hip", "hem_side")]
    return {"pieces": [front, back], "side": (side_f, side_b), "arm_f": [("Front", "underarm", "across"),
            ("Front", "across", "shoulder")], "arm_b": [("Back", "underarm", "across"), ("Back", "across", "shoulder")],
            "darts": [("Front", "side_dart_1", "side_dart", "side_dart_2")], "hem_names": {"Front": ["hem_side"],
            "Back": ["hem_side"]}, "front_panel": "Front", "back_panel": "Back"}


def body_boxy(T, S, m, K):
    """Unfitted: no waist shaping, straight side seams, bust dart reduced to `dart_keep`; the removed part of the dart
    becomes hem shaping so the side seams still match."""
    keep, bw, ext = S["boxy"]["dart_keep"], S["length"]["below_waist"], S["front"]["extension"]
    UA = T["UA"]
    apex = (T["AS"][0] + 3.0, T["AS"][1])
    l1, l2 = (UA[0], UA[1] + 2.5), (UA[0], UA[1] + 2.5 + keep)
    yb, yf = T["YWb"] + bw, T["YW"] + bw
    yf_side = l2[1] + (yb - T["UAb"][1]) - 2.5
    xm = -ext + S["facing"]["width"]
    front = mk("Front", [("neck", T["N"], None), ("shoulder", T["SH"], T["arm_up"]), ("across", T["AC"], T["arm_lo"]),
                         ("underarm", UA, None), ("side_dart_1", l1, None), ("side_dart", apex, None),
                         ("side_dart_2", l2, None),
                         ("hem_side", (UA[0], yf_side), ((UA[0] - 8, yf_side), (UA[0] - 15, yf))),
                         ("hem_mid", (xm, yf), None)] + front_edge(K, ext, yf, S["front"]["hold_to"]))
    front["outline"][idx(front, "side_dart")]["dart"] = True
    back = mk("Back", [("center_neck", T["CBN"], T["neck_b"]), ("neck", T["Nb"], None),
                       ("shoulder", T["SHb"], T["arm_upb"]), ("across", T["ACb"], T["arm_lob"]),
                       ("underarm", T["UAb"], None), ("hem_side", (T["UAb"][0], yb), None), ("hem_cb", (0.0, yb), None)])
    P.true_boundary_darts(front)
    return {"pieces": [front, back],
            "side": ([("Front", "underarm", "side_dart_1"), ("Front", "side_dart_2", "hem_side")],
                     [("Back", "underarm", "hem_side")]),
            "arm_f": [("Front", "underarm", "across"), ("Front", "across", "shoulder")],
            "arm_b": [("Back", "underarm", "across"), ("Back", "across", "shoulder")],
            "darts": [("Front", "side_dart_1", "side_dart", "side_dart_2")],
            "hem_names": {"Front": ["hem_side", "hem_mid"], "Back": ["hem_side"]}, "front_panel": "Front",
            "back_panel": "Back"}


def princess_geometry(T):
    """Armhole princess: the side bust dart is closed by turning the side panel above it about the dart point
    (leg 1 set on leg 2), which opens it into the armhole; the front panel's edge is bowed over the bust until it
    matches the side front's. Back princess through the back dart point."""
    AS, L1, L2 = T["AS"], T["L1"], T["L2"]
    th = math.atan2(*reversed(sub(L2, AS))) - math.atan2(*reversed(sub(L1, AS)))

    def M(p):
        return add(add(AS, rot(sub(p, AS), th)), sub(L2, add(AS, rot(sub(L1, AS), th))))

    G = {"th": th, "ACs": M(T["AC"]), "UAs": M(T["UA"]), "arm_lo_s": (M(T["arm_lo"][0]), M(T["arm_lo"][1]))}
    BP, AC = T["BP"], T["AC"]
    G["ps_up"] = (lerp(G["ACs"], BP, 0.35), add(BP, (0, -4.0)))
    target = blen((G["ACs"], *G["ps_up"], BP))
    d0 = unit(sub(BP, AC))
    nrm = (-d0[1], d0[0]) if -d0[1] > 0 else (d0[1], -d0[0])
    lo, hi = 0.0, 8.0
    for _ in range(60):
        k = (lo + hi) / 2
        G["pf_up"] = (add(lerp(AC, BP, 0.35), nrm, k), add(BP, (0, -4.0)))
        lo, hi = (k, hi) if blen((AC, *G["pf_up"], BP)) < target else (lo, k)
    G["bow"] = k
    G["pr_lo_i"] = (add(BP, (0, 4.0)), add(T["WLi"], (0, -8.0)))
    G["pr_lo_o"] = (add(BP, (0, 4.0)), add(T["WLo"], (0, -8.0)))
    Ab, ACb = T["Ab"], T["ACb"]
    G["pb_up"] = (add(ACb, (-3.0, 3.0)), add(Ab, (0, -4.0)))
    G["pb_lo_i"] = (add(Ab, (0, 4.0)), add(T["WLbi"], (0, -8.0)))
    G["pb_lo_o"] = (add(Ab, (0, 4.0)), add(T["WLbo"], (0, -8.0)))
    return G


def princess_panels(T, G, S, K, D, length, lining=None):
    """Front, side front, side back and back panels, flared by D on every vertical seam below the waist.
    lining: None for the shell, or {"facing_shoulder": ..., "pleat": cm, "bnf": (Fsb, depth, controls)}."""
    ext, hold = S["front"]["extension"], S["front"]["hold_to"]
    ua_f = add(G["UAs"], (0.5, -1.0)) if lining else G["UAs"]
    ua_b = add(T["UAb"], (0.5, -1.0)) if lining else T["UAb"]
    sw_f, sw_b = (add(T["SW"], (0.5, 0)), add(T["SWb"], (0.5, 0))) if lining else (T["SW"], T["SWb"])
    l2 = add(T["L2"], (0.5, 0)) if lining else T["L2"]
    hf, cf_, df = lower(T["WLi"], +1, D, length)
    hs1, cs1, ds1 = lower(T["WLo"], -1, D, length)
    hs2, cs2, ds2 = lower(sw_f, +1, D, length)
    hb1, cb1, db1 = lower(sw_b, +1, D, length)
    hb2, cb2, db2 = lower(T["WLbo"], -1, D, length)
    hk1, ck1, dk1 = lower(T["WLbi"], +1, D, length)
    hk2, ck2, dk2 = lower(T["CBW"], -1, D, length)
    yhem = T["YW"] + length
    out = []
    if not lining:
        out.append(mk("Front", [("neck", T["N"], None), ("shoulder", T["SH"], T["arm_up"]), ("across", T["AC"], G["pf_up"]),
                                ("bust", T["BP"], G["pr_lo_i"]), ("waist", T["WLi"], cf_),
                                ("hem_princess", hf, hem_c(hf, (-df[1], df[0]), (-ext, yhem), (-1, 0)))]
                      + front_edge(K, ext, yhem, hold)))
    out.append(mk("Side front lining" if lining else "Side front", [
        ("across", G["ACs"], G["arm_lo_s"]), ("underarm", ua_f, None), ("side_dart", l2, None), ("side_waist", sw_f, cs2),
        ("hem_side", hs2, hem_c(hs2, (-ds2[1], ds2[0]), hs1, (-perp_r(ds1)[0], -perp_r(ds1)[1]))),
        ("hem_princess", hs1, (cs1[1], cs1[0])), ("waist", T["WLo"], (G["pr_lo_o"][1], G["pr_lo_o"][0])),
        ("bust", T["BP"], (G["ps_up"][1], G["ps_up"][0]))]))
    out.append(mk("Side back lining" if lining else "Side back", [
        ("across", T["ACb"], T["arm_lob"]), ("underarm", ua_b, None), ("side_waist", sw_b, cb1),
        ("hem_side", hb1, hem_c(hb1, (-db1[1], db1[0]), hb2, (-perp_r(db2)[0], -perp_r(db2)[1]))),
        ("hem_princess", hb2, (cb2[1], cb2[0])), ("waist", T["WLbo"], (G["pb_lo_o"][1], G["pb_lo_o"][0])),
        ("dart_point", T["Ab"], (G["pb_up"][1], G["pb_up"][0]))]))
    neg = (-perp_r(dk2)[0], -perp_r(dk2)[1])
    if lining:
        pl = lining["pleat"]
        top = [("facing_shoulder", lining["Fsb"], None)] if lining.get("bnf") else [
            ("pleat_neck", (-pl, T["CBN"][1]), None), ("center_neck", T["CBN"], T["neck_b"]), ("neck", T["Nb"], None)]
        cbtop = [("cb_top", (-pl, lining["bnf"][1]), None), ("bnf_cb", (0.0, lining["bnf"][1]),
                 (lining["bnf"][2][1], lining["bnf"][2][0]))] if lining.get("bnf") else [("cb_top", (-pl, 20.0), None)]
        out.append(mk("Back lining", top + [
            ("shoulder", T["SHb"], T["arm_upb"]), ("across", T["ACb"], G["pb_up"]), ("dart_point", T["Ab"], G["pb_lo_i"]),
            ("waist", T["WLbi"], ck1), ("hem_princess", hk1, hem_c(hk1, (-dk1[1], dk1[0]), add(hk2, (-pl, 0)), neg)),
            ("hem_cb", add(hk2, (-pl, 0)), (add(ck2[1], (-pl, 0)), add(ck2[0], (-pl, 0)))),
            ("cb_waist", add(T["CBW"], (-pl, 0)), ((1.0 - pl, 32.0), (-pl, 26.0)))] + cbtop,
            lines=[[[0.0, lining["bnf"][1] if lining.get("bnf") else T["CBN"][1]], [1.0, T["YWb"]]]]))
    else:
        out.append(mk("Back", [
            ("center_neck", T["CBN"], T["neck_b"]), ("neck", T["Nb"], None), ("shoulder", T["SHb"], T["arm_upb"]),
            ("across", T["ACb"], G["pb_up"]), ("dart_point", T["Ab"], G["pb_lo_i"]), ("waist", T["WLbi"], ck1),
            ("hem_princess", hk1, hem_c(hk1, (-dk1[1], dk1[0]), hk2, neg)), ("hem_cb", hk2, (ck2[1], ck2[0])),
            ("cb_waist", T["CBW"], ((1.0, 32.0), (0.0, 26.0))), ("cb_blade", (0.0, 20.0), None)]))
    return out


def body_princess(T, S, m, K):
    G = princess_geometry(T)
    L = S["length"]["below_waist"]
    target = S["length"]["hem"]
    D = 0.0
    if target:
        for _ in range(40):
            pcs = {p["name"]: p for p in princess_panels(T, G, S, K, D, L)}
            half = (elen(pcs["Front"], "hem_princess", "hem_front") + elen(pcs["Side front"], "hem_side", "hem_princess")
                    + elen(pcs["Side back"], "hem_side", "hem_princess") + elen(pcs["Back"], "hem_princess", "hem_cb"))
            D += (target / 2 - half) / 7
    pcs = princess_panels(T, G, S, K, D, L)
    by = {p["name"]: p for p in pcs}
    for nm in ("Front", "Side front"):
        notch(by[nm], "bust")
        notch(by[nm], "waist")
    for nm in ("Side front", "Side back"):
        notch(by[nm], "side_waist")
    for nm in ("Side back", "Back"):
        notch(by[nm], "waist")
    return {"pieces": pcs, "G": G, "D": D,
            "side": ([("Side front", "underarm", "side_dart"), ("Side front", "side_dart", "side_waist"),
                      ("Side front", "side_waist", "hem_side")],
                     [("Side back", "underarm", "side_waist"), ("Side back", "side_waist", "hem_side")]),
            "princess": [
                ([("Front", "across", "bust"), ("Front", "bust", "waist"), ("Front", "waist", "hem_princess")],
                 [("Side front", "across", "bust"), ("Side front", "bust", "waist"), ("Side front", "waist", "hem_princess")]),
                ([("Side back", "across", "dart_point"), ("Side back", "dart_point", "waist"),
                  ("Side back", "waist", "hem_princess")],
                 [("Back", "across", "dart_point"), ("Back", "dart_point", "waist"), ("Back", "waist", "hem_princess")])],
            "arm_f": [("Side front", "underarm", "across"), ("Front", "across", "shoulder")],
            "arm_b": [("Side back", "underarm", "across"), ("Back", "across", "shoulder")], "darts": [],
            "hem_names": {"Front": ["hem_princess"], "Side front": ["hem_side"], "Side back": ["hem_side"],
                          "Back": ["hem_princess"]}, "front_panel": "Front", "back_panel": "Back"}


# ------------------------------------------------------------------ two-piece sleeve



def curve_to_length(cv, target):
    """Keep endpoints and tangents, solve independent seam length by handle scale."""
    a,c1,c2,b=cv
    if target < dist(a,b):
        raise ValueError("Sleeve seam contract shorter than endpoint distance")
    def scaled(v):
        return (a,add(a,sub(c1,a),v),add(b,sub(c2,b),v),b)
    lo,hi=0.0,1.0
    while blen(scaled(hi)) < target:
        hi*=2
        if hi>128:
            raise ValueError("Sleeve curve cannot meet contract")
    for _ in range(60):
        m=(lo+hi)/2
        if blen(scaled(m))>target:
            hi=m
        else:
            lo=m
    return scaled((lo+hi)/2)

def two_piece_sleeve(arm_f, arm_b, depth, c):
    """Two-piece sleeve matched to the armhole (kb two-piece-sleeve): one-piece base with parallel underarm sides,
    cap = armhole + ease, split with the forearm seam `front_in` cm under the arm and the hindarm seam on the back
    pitch; the taper to the hem is taken in the two seams (never in the underarm sides, or the under sleeve gets two
    grains); elbow ease by turning the lower top sleeve about the forearm elbow point."""
    CH = c["cap_height"] or 5 / 6 * depth - c["drop"] / 2
    Ls, WW, EASE = c["length"], c["hem"], c["ease"]

    def caps(W):
        Fu, Bu, Cr = (-W / 2, CH), (W / 2, CH), (0.0, 0.0)
        return (Fu, (-W / 2 + W * 0.18, CH), (-W * 0.22, 0.0), Cr), (Bu, (W / 2 - W * 0.14, CH), (W * 0.25, 0.0), Cr)

    W = 38.0
    for _ in range(60):
        fcap, bcap = caps(W)
        W += arm_f + arm_b + EASE - (blen(fcap) + blen(bcap))
    fcap, bcap = caps(W)
    fcap=curve_to_length(fcap,arm_f+EASE/2)
    bcap=curve_to_length(bcap,arm_b+EASE/2)
    Bu, Cr = bcap[0], fcap[3]
    f_lo, f_up = split(*fcap, t_at(fcap, 0, -W / 4 - c["front_in"]))
    b_lo, b_up = split(*bcap, t_at(bcap, 0, W / 4 + c["back_out"]))
    Pf, Pb = f_lo[3], b_lo[3]
    tf, tb = 0.4 * (W - WW) / 2, 0.6 * (W - WW) / 2
    xf, xb = -W / 4 - c["front_in"], W / 4
    FwT, FwU, BwT, BwU = (xf + tf, Ls), (xf - tf, Ls), (xb - tb, Ls), (xb + tb, Ls)
    vent = c["vent"]

    def on_line(a, b, y):
        return lerp(a, b, (y - a[1]) / (b[1] - a[1]))

    VtT, VtU = (on_line(Pb, BwT, Ls - vent), on_line(Pb, BwU, Ls - vent)) if vent else (BwT, BwU)
    fs_t = bent(Pf, FwT, c["bend"])
    bu = c["bend"]
    for _ in range(40):
        fs_u = bent(Pf, FwU, bu)
        bu += 2 * (blen((Pf, *fs_t, FwT)) - blen((Pf, *fs_u, FwU)))
    bs_u = bent(Pb, VtU, c["bend"])
    fs_hi, fs_lo = split(Pf, fs_t[0], fs_t[1], FwT, 0.5)
    Ef = fs_hi[3]
    Eb = bez(Pb, *bent(Pb, VtT, c["bend"]), VtT, 0.5)
    th = c["elbow"] / dist(Ef, Eb)

    def Rl(p):
        return add(Ef, rot(sub(p, Ef), th))

    bs_t = bent(Pb, Rl(VtT), c["bend"])
    target_back = blen((Pb,*bs_u,VtU))+c["elbow"]
    lo,hi=-0.3,0.3
    for _ in range(60):
        th=(lo+hi)/2
        candidate=(Pb,*bent(Pb,Rl(VtT),c["bend"]),Rl(VtT))
        if blen(candidate)>target_back:
            hi=th
        else:
            lo=th
    th=(lo+hi)/2
    bs_t=bent(Pb,Rl(VtT),c["bend"])
    if abs(blen((Pb,*bs_t,Rl(VtT)))-target_back)>.01:
        raise ValueError("Elbow construction cannot meet independently specified ease")

    def T(p):
        return (p[0] + W, p[1])

    def top(lining=False):
        if lining:
            hem = Ls - 1.5
            nodes = [("front_seam_cap", Pf, f_up[1:3]), ("crown", Cr, (b_up[2], b_up[1])),
                     ("back_seam_cap", Pb, bent(Pb, on_line(Pb, BwT, hem), c["bend"])),
                     ("back_seam_hem", on_line(Pb, BwT, hem), None), ("front_seam_hem", (FwT[0], hem), (fs_t[1], fs_t[0]))]
        else:
            nodes = [("front_seam_cap", Pf, f_up[1:3]), ("crown", Cr, (b_up[2], b_up[1])), ("back_seam_cap", Pb, bs_t)]
            if vent:
                nodes += [("vent_top", Rl(VtT), None), ("vent_corner", Rl((VtT[0] + 3.0, VtT[1] + 1.0)), None),
                          ("vent_hem", Rl((BwT[0] + 3.0, Ls)), None)]
            else:
                nodes += [("back_seam_hem", Rl(BwT), None)]
            nodes += [("front_seam_hem", Rl(FwT), (Rl(fs_lo[2]), Rl(fs_lo[1]))), ("front_seam_elbow", Ef, (fs_hi[2], fs_hi[1]))]
        pc = mk("Top sleeve lining" if lining else "Top sleeve", nodes, grain=[[0.0, CH + 4], [0.0, Ls - 14]],
                lines=[] if (lining or not vent) else [[list(Rl(VtT)), list(Rl(BwT))]])
        for nm in ("crown", "front_seam_cap", "back_seam_cap"):
            notch(pc, nm)
        return pc

    def under(lining=False):
        hem = Ls - 1.5 if lining else Ls
        upv = (0.0, -1.0) if lining else (0.0, 0.0)
        nodes = [("back_seam_cap", Pb, (b_lo[2], add(b_lo[1], upv))),
                 ("underarm", add(Bu, upv), (add(T(f_lo[1]), upv), T(f_lo[2]))),
                 ("front_seam_cap", T(Pf), (T(fs_u[0]), T(fs_u[1]))), ("front_seam_hem", T((FwU[0], hem)), None),
                 ("wrist_side", (W / 2, hem), None)]
        if vent and not lining:
            nodes += [("vent_hem", (BwU[0] - 3.0, hem), None), ("vent_corner", (VtU[0] - 3.0, VtU[1] + 1.0), None),
                      ("vent_top", VtU, (bs_u[1], bs_u[0]))]
        else:
            bh = on_line(Pb, BwU, hem)
            nodes += [("back_seam_hem", bh, (bs_u[1], bs_u[0]) if not lining else bent(bh, Pb, c["bend"]))]
        pc = mk("Under sleeve lining" if lining else "Under sleeve", nodes, grain=[[W / 2, CH + 4], [W / 2, Ls - 14]],
                lines=[] if (lining or not vent) else [[list(VtU), list(BwU)]])
        for nm in ("front_seam_cap", "back_seam_cap"):
            notch(pc, nm)
        return pc

    return {"top": top, "under": under, "W": W, "CH": CH, "f_lo": blen(f_lo), "b_lo": blen(b_lo),
            "back_end": "vent_top" if vent else "back_seam_hem"}


# ------------------------------------------------------------------ chains: seams one edge to one edge


class Seams:
    """Validates independent whole-seam contracts before splitting edges for outline transfer."""

    def __init__(self, pieces):
        self.p = pieces
        self.rows = []
        self.contracts = []
        self.k = 0

    def _positions(self, chain):
        out, s = [], 0.0
        for nm, a, b in chain:
            L = edge_len(self.p[nm], a, b)
            out.append((s, s + L))
            s += L
        return out, s

    def _insert(self, chain, pos):
        """Insert a node at chain position pos (cm from the chain start) unless a node is already there."""
        spans, _ = self._positions(chain)
        for k, ((s0, s1), (nm, a, b)) in enumerate(zip(spans, chain)):
            if s0 - 0.05 <= pos <= s1 + 0.05:
                if pos - s0 < 0.05 or s1 - pos < 0.05:
                    return chain
                self.k += 1
                new = f"m{self.k}"
                split_on(self.p[nm], a, b, pos - s0, new)
                return chain[:k] + [(nm, a, new), (nm, new, b)] + chain[k + 1:]
        return chain

    def match(self, A, B, knots=(), why="", sides=None, ease_cm=0.0):
        """Sew chain A onto chain B. knots: (posA, posB) points that must meet (sleeve seams on armhole notches);
        whole-chain ease_cm is independently specified and validated before any segment distribution."""
        _, LA = self._positions(A)
        _, LB = self._positions(B)
        if ease_cm and ("dart" in why.lower() or why.lower() in ("side seam", "princess seam", "forearm seam")):
            raise ValueError("Ordinary side and dart seams require zero ease")
        if not math.isfinite(ease_cm) or (ease_cm and not why):
            raise ValueError("seam ease needs a finite independent amount and reason")
        if abs(LA - LB - ease_cm) > 0.1:
            raise ValueError(f"seam {why}: {LA*10:.3f}/{LB*10:.3f} mm; declared ease {ease_cm*10:.3f} mm")
        self.contracts.append({"a":copy.deepcopy(A),"b":copy.deepcopy(B),"ease_cm":ease_cm,"why":why})
        ks = [(0.0, 0.0)] + list(knots) + [(LA, LB)]
        if any(a1 <= a0 or b1 <= b0 for (a0,b0),(a1,b1) in zip(ks,ks[1:])):
            raise ValueError("seam knots must be strictly increasing within the chain")
        if any(abs(a-b) > .1 for a,b in knots):
            raise ValueError("seam knots below the eased region must have zero ease")

        def a2b(x):
            for (a0, b0), (a1, b1) in zip(ks, ks[1:]):
                if x <= a1 + 1e-9:
                    return b0 + (x - a0) * (b1 - b0) / max(a1 - a0, 1e-9)
            return LB

        def b2a(y):
            for (a0, b0), (a1, b1) in zip(ks, ks[1:]):
                if y <= b1 + 1e-9:
                    return a0 + (y - b0) * (a1 - a0) / max(b1 - b0, 1e-9)
            return LA

        for pa in [a for a, _ in ks[1:-1]] + [s1 for s0, s1 in self._positions(A)[0][:-1]]:
            B = self._insert(B, a2b(pa))
        for pb in [b for _, b in ks[1:-1]] + [s1 for s0, s1 in self._positions(B)[0][:-1]]:
            A = self._insert(A, b2a(pb))
        sa, _ = self._positions(A)
        sb, _ = self._positions(B)
        assert len(A) == len(B), (A, B)
        for (na, a1, a2), (nb, b1, b2), (x0, x1), (y0, y1) in zip(A, B, sa, sb):
            ease = (x1 - x0) / (y1 - y0) - 1
            # Only distribute ease after the independent total contract has passed.
            opt = [{"ease": ease if ease_cm and y1 > (knots[-1][1] if knots else 0) else 0,
                    "why": why, "contract_ease_cm": ease_cm, "contract_length_cm": LB}]
            self.rows.append(((na, a1, a2), (nb, b1, b2), opt, sides))


# ------------------------------------------------------------------ garment


def run(spec, base_dir="."):
    S = merged(spec)
    body = S["body"]
    if S["shaping"] not in ("darts", "boxy", "princess"):
        raise ValueError("Unsupported shaping: choose darts, boxy or princess; use a dedicated piece recipe otherwise")
    own = {}
    if S["measurements"]:
        with open(os.path.join(base_dir, S["measurements"]), encoding="utf-8") as f:
            own = json.load(f)
        body = own.get("body", body)
    if body != "women":
        raise ValueError("garment recipes support women with dart shaping landmarks; use a male/child no-dart block plus a dedicated piece recipe")
    size = str(S["size"] or P.BASE[body]["ref"])
    body, m, ease, provenance = P.resolve_measurements(body, size, own)
    T = torso(m, ease, body, S["fit"])
    shoulders(T, S["shoulder"]["extend"], S["shoulder"]["pad"])
    curves(T)
    ext = S["front"]["extension"]
    if S["front"]["hold_to"] is None and S["front"]["buttons"]:
        S["front"]["hold_to"] = max(S["front"]["buttons"]) + 2.0
    ctype = S["collar"]["type"]
    K = (notched_collar(T, S["collar"], ext) if ctype == "notched" else
         stand_collar(T, S["collar"], ext) if ctype in ("stand", "funnel") else no_collar(T, ext))
    B = {"darts": body_darts, "boxy": body_boxy, "princess": body_princess}[S["shaping"]](T, S, m, K)
    pcs = {p["name"]: p for p in B["pieces"]}
    for chain_a, chain_b in [B["side"]] + B.get("princess", []):
        la = sum(edge_len(pcs[n], a, b) for n,a,b in chain_a)
        lb = sum(edge_len(pcs[n], a, b) for n,a,b in chain_b)
        short = chain_a if la < lb else chain_b
        nm,a,b = max(short, key=lambda row: edge_len(pcs[row[0]], row[1], row[2]))
        ix,_ = edge_index(pcs[nm],a,b)
        P.lengthen_edge(pcs[nm],ix,edge_len(pcs[nm],a,b)+abs(la-lb),preserve_tangents=True)
    front, back = pcs[B["front_panel"]], pcs[B["back_panel"]]
    for p in B["pieces"]:
        pts = P.outline(p)
        x = (min(q[0] for q in pts)+max(q[0] for q in pts))/2
        y0,y1=min(q[1] for q in pts),max(q[1] for q in pts)
        p["grain"] = [[x,y0+(y1-y0)*.45],[x,y0+(y1-y0)*.75]]
    checks = []

    def ck(label, got, want, tol=0.1):
        checks.append(P.check(label, got, want, tol))

    def info(label, v):
        checks.append(P.check(label, v))

    # buttons, roll line, hems
    front["buttons"] = [[ext - 2.5 if ext > 4 else 0.0, y] for y in S["front"]["buttons"]]
    if ctype == "notched":
        front["lines"] = front.get("lines", []) + [K["roll"]]
        notch(front, "break")
        notch(front, "gorge_neck")
    for nm, hems in B["hem_names"].items():
        allow(pcs[nm], hems, S["hem_allowance"])     # edges starting at these nodes are hems
    for p in B["pieces"]:
        p["cut"] = "1 pair"
        p["allowance"] = S["allowance"]

    # collar
    cut = list(B["pieces"])
    if K["collar"]:
        toc = S["collar"].get("turn_of_cloth", 0.3)
        top_c = K["collar"]("Top collar", toc)
        top_c.update(cut="1 on fold", fold=[len(top_c["outline"]) - 1], allowance=S["allowance"])
        under_c = K["collar"]("Undercollar" if ctype == "notched" else "Inner collar", -toc)
        under_c.update(cut="1 pair, bias" if ctype == "notched" else "1 on fold", allowance=S["allowance"])
        if ctype != "notched":
            under_c["fold"] = [len(under_c["outline"]) - 1]
        cut += [top_c, under_c]

    # sleeve
    sv = None
    if S["sleeve"]["type"] == "two-piece":
        ARM_F = sum(edge_len(pcs[n], a, b) for n, a, b in B["arm_f"])
        ARM_B = sum(edge_len(pcs[n], a, b) for n, a, b in B["arm_b"])
        depth = ((T["UA"][1] - T["SH"][1]) + (T["UAb"][1] - T["SHb"][1])) / 2
        sc = dict(S["sleeve"])
        sc["length"] = sc["length"] or m["arm_length"] - S["shoulder"]["extend"] + S["shoulder"]["pad"] / 2
        sv = two_piece_sleeve(ARM_F, ARM_B, depth, sc)
        ts, us_ = sv["top"](), sv["under"]()
        for p in (ts, us_):
            p.update(cut="1 pair", allowance=S["allowance"])
        allow(ts, ["vent_hem", "back_seam_hem"], S["hem_allowance"])
        allow(us_, ["front_seam_hem", "wrist_side"], S["hem_allowance"])
        cut += [ts, us_]
        info("bicep width", sv["W"])
        info("sleeve cap height", sv["CH"])
        info("sleeve length", sc["length"])

    # facings
    ftype = S["facing"]["type"]
    if ftype == "auto":
        ftype = "panel" if S["shaping"] == "princess" else "width"
    Fs = add(T["N"], T["us"], 4.0)
    xf = -ext + S["facing"]["width"]
    yhem_f = nodep(front, "hem_front")[1]
    y_low = min(yhem_f - 10.0, 45.0 if S["shaping"] == "princess" else 55.0)
    fac_c = ((Fs[0] - 1.5, 10.0), (xf, 28.0)) if ftype == "panel" else ((Fs[0] - 0.5, 12.0), (xf, 35.0))
    if ftype == "panel":
        facing = copy.deepcopy(front)
        facing.update(name="Front facing", within="Front")
        facing.pop("buttons", None)
    else:
        toc = S["collar"].get("facing_turn", 0.0) if ctype == "notched" else 0.0
        facing = mk("Front facing", [("neck", T["N"], None), ("facing_shoulder", Fs, fac_c), ("facing_low", (xf, y_low), None),
                                     ("hem_in", (xf, yhem_f), None)] + front_edge(K, ext, yhem_f, None, toc),
                    within="Front")
        allow(facing, ["hem_in"], S["hem_allowance"])
        notch(facing, "facing_low")
    facing.update(cut="1 pair", allowance=S["allowance"], grain=[[xf-2,y_low-12],[xf-2,y_low+5]])
    cut.append(facing)
    bnf = None
    if S["facing"]["back_neck"]:
        dep = S["facing"]["back_neck"]
        Fsb = add(T["Nb"], T["ub"], 4.0)
        bnf_c = ((Fsb[0] - 1.0, 8.0), (4.0, dep))
        bf_ = mk("Back neck facing", [("center_neck", T["CBN"], T["neck_b"]), ("neck", T["Nb"], None),
                                      ("facing_shoulder", Fsb, bnf_c), ("bnf_cb", (0.0, dep), None)],
                 fold=[3], cut="1 on fold", allowance=S["allowance"], within="Back")
        bf_["grain"] = [[2,3],[2,dep-1]]
        cut.append(bf_)
        bnf = (Fsb, dep, bnf_c)
        ck("front facing shoulder = back neck facing shoulder", dist(T["N"], Fs), dist(T["Nb"], Fsb))

    # pockets
    pk = S["pockets"]
    if pk and pk["type"] == "patch":
        w, h, fy = pk.get("w", 17.0), pk.get("h", 19.0), pk.get("facing", 4.0)
        r, x0, y0 = 3.0, pk.get("x", 4.0), T["YW"] + pk.get("y", 3.0)
        kk = 0.55 * r
        cut.append(mk("Patch pocket", [("top_left", (0, -fy), None), ("top_right", (w, -fy), None),
                                       ("corner_r", (w, h - r), ((w, h - r + kk), (w - r + kk, h))),
                                       ("bottom_r", (w - r, h), None),
                                       ("bottom_l", (r, h), ((r - kk, h), (0, h - r + kk))), ("corner_l", (0, h - r), None)],
                      grain=[[w / 2, 2.0], [w / 2, h - 4]], lines=[[[0, 0], [w, 0]]], cut="1 pair", allowance=1.0))
        front["lines"] = front.get("lines", []) + [[[x0, y0], [x0 + w, y0]], [[x0 + w, y0], [x0 + w, y0 + h]],
                                                   [[x0 + w, y0 + h], [x0, y0 + h]], [[x0, y0 + h], [x0, y0]]]
    elif pk and pk["type"] == "in-seam":
        top_, ln = pk.get("top", 6.0), pk.get("length", 17.0)
        seam = (B["princess"][0] if S["shaping"] == "princess" else B["side"])
        for chain in seam:
            nm, a, b = next(e for e in chain if e[1] in ("waist", "side_waist", "side_dart_2"))
            notch_on(pcs[nm], a, b, top_)
            notch_on(pcs[nm], a, b, top_ + ln)
        cut.append(mk("Pocket bag", [("seam_top", (0.0, -3.0), None), ("top_out", (-14.0, -1.0), ((-17.0, 8.0), (-14.0, 26.0))),
                                     ("bottom", (-6.0, 30.0), ((-2.0, 30.0), (0.0, 26.0))), ("seam_bottom", (0.0, ln + 4.0), None)],
                      grain=[[-7.0, 4.0], [-7.0, 22.0]], cut="2 pairs, lining", allowance=1.0))

    # lining
    lin = S["lining"]
    lining_pieces = []
    if lin:
        up = lin.get("up", 1.5 if lin.get("hem", "jump") == "jump" else 3.0)
        pl = lin.get("cb_pleat", 2.0)
        if S["shaping"] == "princess":
            L = S["length"]["below_waist"]
            lp = princess_panels(T, B["G"], S, K, B["D"] * (L - up) / L, L - up,
                                 lining={"pleat": pl, "Fsb": bnf[0] if bnf else None, "bnf": bnf})
            lining_pieces += lp
            if ftype != "panel":
                raise SystemExit("princess shaping: use the panel facing (a narrower facing leaves a lining strip)")
        else:
            lining_pieces += derived_linings(front, back, T, Fs, fac_c, xf, y_low, up, pl, bnf, S["shaping"])
        if sv:
            lining_pieces += [sv["top"](True), sv["under"](True)]
        for p in lining_pieces:
            P.true_boundary_darts(p)
            if not p.get("grain"):
                pts = P.outline(p)
                x = (min(q[0] for q in pts)+max(q[0] for q in pts))/2
                y0,y1=min(q[1] for q in pts),max(q[1] for q in pts)
                p["grain"]=[[x,y0+(y1-y0)*.45],[x,y0+(y1-y0)*.75]]
            p.update(cut=p.get("cut", "1 pair"), allowance=1.5 if S["shaping"] == "princess" else 1.0)
        info("lining hem above the finished hem", up)

    # 3D shell: mirror halves, every seam, wrap holds
    shell3d = {p["name"]: copy.deepcopy(p) for p in B["pieces"]}
    if K["collar"]:
        shell3d["Collar"] = K["collar"]("Collar", 0.0)
    if sv:
        shell3d["Top sleeve"], shell3d["Under sleeve"] = sv["top"](), sv["under"]()
    for p in shell3d.values():
        for k in ("buttons", "lines"):
            p.pop(k, None)
        p["mirror"] = True
    reference_pieces = [copy.deepcopy(p) for nm,p in shell3d.items() if nm == "Collar"]
    wearer = {nm: "right" if nm in ("Back", "Side back", "Collar") else "left" for nm in shell3d}
    sm = Seams(shell3d)
    sf, sb = B["side"]
    sm.match(sf, sb, why="side seam")
    for A_, B_ in B.get("princess", []):
        sm.match(A_, B_, why="princess seam")
    for nm, l1, ap, l2 in B["darts"]:
        sm.match([(nm, l1, ap)], [(nm, l2, ap)], why="dart legs, trued")
    sm.match([(B["back_panel"], "neck", "shoulder")], [(B["front_panel"], "neck", "shoulder")], why="back shoulder ease", ease_cm=ease["shoulder"])
    cb_chain, nb = [], back["outline"]
    i = idx(shell3d["Back"], "hem_cb")
    names = [n["name"] for n in shell3d["Back"]["outline"]]
    j = i
    while names[j] != "center_neck":
        cb_chain.append(("Back", names[j], names[(j + 1) % len(names)]))
        j = (j + 1) % len(names)
    sm.match(cb_chain, cb_chain, why="centre back", sides="LR")
    if K["collar"]:
        if ctype == "notched":
            col_chain = [("Collar", "cb_neck", "neck"), ("Collar", "neck", "gorge_neck"), ("Collar", "gorge_neck", "notch")]
            neck_chain = [("Back", "center_neck", "neck"), ("Front", "neck", "gorge_neck"), ("Front", "gorge_neck", "gorge_roll"),
                          ("Front", "gorge_roll", "notch")]
        else:
            col_chain = [("Collar", "cb_neck", "front_neck")]
            neck_chain = [("Back", "center_neck", "neck"), ("Front", "neck", "center_neck"), ("Front", "center_neck", "front_neck")]
        sm.match(col_chain, neck_chain, why="collar on neckline")
        sm.match([("Collar", "cb_top", "cb_neck")], [("Collar", "cb_top", "cb_neck")], why="collar centre back", sides="LR")
    if sv:
        sm.match([("Under sleeve", "underarm", "front_seam_cap"), ("Top sleeve", "front_seam_cap", "crown")], B["arm_f"],
                 knots=[(sv["f_lo"], sv["f_lo"])], why="sleeve cap ease, front", ease_cm=sc["ease"]/2)
        sm.match([("Under sleeve", "underarm", "back_seam_cap"), ("Top sleeve", "back_seam_cap", "crown")], B["arm_b"],
                 knots=[(sv["b_lo"], sv["b_lo"])], why="sleeve cap ease, back", ease_cm=sc["ease"]/2)
        sm.match([("Top sleeve", "front_seam_cap", "front_seam_elbow"), ("Top sleeve", "front_seam_elbow", "front_seam_hem")],
                 [("Under sleeve", "front_seam_cap", "front_seam_hem")], why="forearm seam")
        sm.match([("Top sleeve", "back_seam_cap", sv["back_end"])], [("Under sleeve", "back_seam_cap", sv["back_end"])],
                 why="elbow ease", ease_cm=sc["elbow"])
    cut_seams = []
    cut_names={p["name"] for p in cut}
    for c in sm.contracts:
        if len(c["a"])==len(c["b"])==1 and c["a"][0][0] in cut_names and c["b"][0][0] in cut_names:
            a,b=c["a"][0],c["b"][0]
            # Ordinary one-to-one seams remain directly named; additive ease stays in seam_chains.
            if c["ease_cm"]==0:
                cut_seams.append([*a,*b])
    seams = []
    opp = {"L": "R", "R": "L"}
    for (a, b, opt, sides) in sm.rows:
        if sides == "LR":
            seams.append([f"{a[0]} L", a[1], a[2], f"{b[0]} R", b[1], b[2]] + opt)
            continue
        for s in ("L", "R"):
            na = f"{a[0]} {s if wearer[a[0]] == 'left' else opp[s]}"
            nb_ = f"{b[0]} {s if wearer[b[0]] == 'left' else opp[s]}"
            seams.append([na, a[1], a[2], nb_, b[1], b[2]] + opt)
    holds = []
    hold_to = S["front"]["hold_to"]
    if ext > 0 and hold_to:
        y_top = K["top_y"]
        fp = B["front_panel"]
        holds.append({"top": f"{fp} R", "edge": ["hold_end", K["top_node"]], "under": f"{fp} L", "layer": 1,
                      "at": {K["top_node"]: [ext, y_top], "hold_end": [ext, hold_to]}})
    if K["collar"] and ctype != "notched" and ext > 0:
        ol = K["overlap_line"]()
        holds.append({"top": "Collar L", "edge": ["front_neck", "front_top"], "under": "Collar R", "layer": 1,
                      "at": {k: [-v[0], v[1]] for k, v in ol.items()}})

    # checks specific to the construction
    if S["shaping"] == "princess":
        info("flare added per seam edge at the hem (D)", B["D"])
        info("front princess bow over the bust (cm)", B["G"]["bow"])
        hem_half = (elen(pcs["Front"], "hem_princess", "hem_front") + elen(pcs["Side front"], "hem_side", "hem_princess")
                    + elen(pcs["Side back"], "hem_side", "hem_princess") + elen(pcs["Back"], "hem_princess", "hem_cb"))
        if S["length"]["hem"]:
            ck("hem circumference (full)", 2 * hem_half, S["length"]["hem"], 1.0)
    ck("back shoulder - front shoulder (ease)", edge_len(back, "neck", "shoulder") - edge_len(front, "neck", "shoulder"),
       T["sh_ease"])
    return {"spec": S, "size": size, "cut": cut, "lining": lining_pieces, "shell3d": list(shell3d.values()),
            "seams": seams, "holds": holds, "checks": checks,
            "resolved_measurements": m, "measurement_provenance": provenance, "resolved_ease": ease, "cut_seams": cut_seams, "cut_chains":sm.contracts, "reference_pieces":reference_pieces}


def derived_linings(front, back, T, Fs, fac_c, xf, y_low, up, pl, bnf, shaping):
    """Front and back linings of a darted or boxy body: front from the facing edge to the side, back with a centre
    back pleat (cut on the fold) or below the back neck facing; underarm raised 1 cm and out 0.5 cm, side +0.5 cm,
    hem `up` cm above the finished hem."""

    def adapt(nodes):
        out, side = [], False
        for n in nodes:
            n = copy.deepcopy(n)
            nm = n["name"]
            if nm == "underarm":
                n["p"] = [n["p"][0] + 0.5, n["p"][1] - 1.0]
                side = True
            elif side and not n.get("dart") and (not nm.startswith("hem") or nm == "hem_side"):
                n["p"][0] += 0.5
            if nm.startswith("hem"):
                n["p"][1] -= up
                if "c" in n:
                    n["c"] = [[c[0], c[1] - up] for c in n["c"]]
            if nm == "across" and "c" in n:
                n["c"][1] = [n["c"][1][0] + 0.5, n["c"][1][1] - 1.0]
            out.append(n)
        return out

    fn = front["outline"]
    body = adapt(fn[idx(front, "shoulder"):idx(front, "hem_front")])
    if body[-1]["p"][0] <= xf + 0.5:      # a hem node at the facing edge: the lining ends there instead
        body.pop()
    yl = fn[idx(front, "hem_front")]["p"][1] - up
    fl = {"name": "Front lining", "outline": [{"name": "facing_shoulder", "p": list(Fs)}] + body + [
        {"name": "hem_facing", "p": [xf, yl]}, {"name": "facing_low", "p": [xf, y_low], "c": [list(fac_c[1]), list(fac_c[0])]}],
        "allowances": {}, "notches": [], "darts_in": front.get("darts_in", [])}
    notch(fl, "facing_low")
    bn = back["outline"]
    bbody = adapt(bn[idx(back, "shoulder"):idx(back, "hem_cb")])
    yb = bn[idx(back, "hem_cb")]["p"][1] - up
    if bnf:
        Fsb, dep, bnf_c = bnf
        top = [{"name": "facing_shoulder", "p": list(Fsb)}]
        tail = [{"name": "pleat_hem", "p": [-pl, yb]}, {"name": "cb_top", "p": [-pl, dep]},
                {"name": "bnf_cb", "p": [0.0, dep], "c": [list(bnf_c[1]), list(bnf_c[0])]}]
        fold = None
    else:
        top = [{"name": "pleat_neck", "p": [-pl, T["CBN"][1]]},
               {"name": "center_neck", "p": list(T["CBN"]), "c": [list(T["neck_b"][0]), list(T["neck_b"][1])]},
               {"name": "neck", "p": list(T["Nb"])}]
        tail = [{"name": "pleat_hem", "p": [-pl, yb]}]
        fold = None
    bl = {"name": "Back lining", "outline": top + bbody + tail, "allowances": {}, "notches": [],
          "darts_in": back.get("darts_in", []), "lines": [[[0.0, T["CBN"][1]], [0.0, yb]]]}
    if not bnf:
        bl["fold"] = [len(bl["outline"]) - 1]
        bl["cut"] = "1 on fold"
    return [fl, bl]


# ------------------------------------------------------------------ command


def write(res, out):
    """Deliver validated 2D pieces; a fitted internal-dart shell is explicitly unsupported."""
    sz,S = res["size"],res["spec"]
    unsupported = any(p.get("darts_in") for p in res["cut"] + res["lining"])
    data = {"pieces":res["cut"]+res["lining"], "checks":list(res["checks"]),
            "seams":res["cut_seams"], "seam_chains":res["cut_chains"],
            "seam_reference_pieces":res["reference_pieces"], "holds":[], "construction":S,
            "resolved_measurements":res["resolved_measurements"], "resolved_ease":res["resolved_ease"],
            "measurement_provenance":res["measurement_provenance"], "measurement_unit":"cm",
            "shell_status":{"supported":False, "reason":"Use the separately validated outline shell if available; internal dart topology unsupported"}}
    sets=[(sz,data)]
    os.makedirs(out,exist_ok=True)
    if any(n.startswith(("pattern", "clo3d", "pieces_")) for n in os.listdir(out)):
        raise ValueError("Output contains a previous bundle; choose a fresh --out directory")
    with P.tempfile.TemporaryDirectory(prefix="garment-stage-",dir=out) as stage:
        ok=P.export(sets,stage,S["title"])
        P.report(sets)
        if ok and not unsupported:
            shell=[(sz,{"pieces":res["shell3d"],"seams":res["seams"],"holds":res["holds"],"checks":[]})]
            try:
                ok=P.export(shell,os.path.join(stage,"clo3d"),S["title"]+" (outline transfer; not simulation)",allowance=0)
                P.report(shell)
            except ValueError as err:
                print(f"Shell export rejected: {err}")
                ok=False
        if ok:
            for name in os.listdir(stage):
                P.shutil.move(os.path.join(stage,name),os.path.join(out,name))
        else:
            target=os.path.join(out,"rejected")
            os.makedirs(target,exist_ok=True)
            source=os.path.join(stage,"rejected") if os.path.isdir(os.path.join(stage,"rejected")) else stage
            for name in os.listdir(source):
                if name.startswith(("pieces_","seams_","checks")):
                    src=os.path.join(source,name)
                    if name.startswith("pieces_"):
                        with open(src,encoding="utf-8") as f:
                            j=json.load(f)
                        j["validation_status"]="rejected"
                        with open(src,"w",encoding="utf-8") as f:
                            json.dump(j,f,indent=1)
                    P.shutil.move(src,os.path.join(target,name))
    if ok:
        print(f"Validated 2D files: {os.path.abspath(out)}")
        if unsupported:
            print("3D shell unsupported: internal darts require sewn topology; no fit simulation performed.")
    else:
        print("Export rejected; inspect diagnostics under rejected/.")
    return ok


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Draft a garment from a spec (references/garment-spec.md).")
    ap.add_argument("spec")
    ap.add_argument("--out", default="out")
    a = ap.parse_args(argv)
    with open(a.spec, encoding="utf-8") as f:
        spec = json.load(f)
    res = run(spec, os.path.dirname(os.path.abspath(a.spec)))
    return 0 if write(res, a.out) else 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError) as err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(2)
