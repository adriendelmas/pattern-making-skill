"""Garments from reusable constructions (standard library only).

A garment is a JSON spec (references/garment-spec.md). `run(spec)` drafts it from the engine's bodice block:
body ease, shoulders (extension, pads), shaping (darts, boxy, armhole princess with flare), front edge (overlap,
buttons or a concealed fly), collar (notched lapel drafted in place, stand or funnel), a two-piece sleeve matched to
the armhole, facings, lining and pockets. It returns the cut pieces, the 3D shell with every seam and the wrap holds
for CLO3D, and the construction checks. Command: python pattern.py garment spec.json --out folder
"""
import copy
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import library  # noqa: E402
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
    nd, nx = pc["outline"][i], pc["outline"][(i + 1) % len(pc["outline"])]
    p0, p3 = tuple(nd["p"]), tuple(nx["p"])
    if "c" not in nd:
        q = lerp(p0, p3, dd / L)
        pc["outline"].insert(i + 1, {"name": new, "p": list(q)})
        return
    cv = (p0, tuple(nd["c"][0]), tuple(nd["c"][1]), p3)
    left, right = split(*cv, t_len(cv, dd))
    nd["c"] = [list(left[1]), list(left[2])]
    pc["outline"].insert(i + 1, {"name": new, "p": list(left[3]), "c": [list(right[1]), list(right[2])]})


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

# The values of every construction live in data/constructions/ (garment.json holds the defaults of a spec, one
# file per collar); a spec section may name another file of that folder as its "preset".
DEFAULTS = library.values("garment")


def merged(spec):
    out = copy.deepcopy(DEFAULTS)
    for k, v in spec.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            v = dict(v)
            if v.get("preset"):                        # a construction file of data/constructions/
                typ, vals = library.preset(v.pop("preset"), k)
                out[k].update(vals)
                if typ and "type" not in vals:
                    out[k]["type"] = typ
            out[k].update(v)
        else:
            out[k] = v
    ctype = {"funnel": "stand"}.get(out["collar"]["type"], out["collar"]["type"])
    if ctype in library.COLLARS:
        out["collar"] = {**library.values("collar." + ctype), **out["collar"]}
    if out["pockets"] and not isinstance(out["pockets"], list):
        out["pockets"] = [out["pockets"]]
    out["pockets"] = [pocket_values(pk) for pk in out["pockets"] or []] or None
    return out


def pocket_values(pk):
    """A pocket of the spec over the values of its type (data/constructions/<type>-pocket.json); a welt has values
    of its own for the chest and for the hip."""
    if pk.get("type") not in library.POCKETS:
        return dict(pk)                                # refused in run, with the list of types
    v = library.values("pocket." + pk["type"])
    where = v.get(pk.get("where", v.get("where")), {})
    return {**{k: x for k, x in v.items() if not isinstance(x, dict)}, **where, **pk}


# ------------------------------------------------------------------ body


def torso(m, ease, body, f):
    """Points of the front and back from the engine's bodice block, with the garment ease."""
    blk = {p["name"]: p for p in P.build("bodice", m, ease, body)["pieces"]}
    bf, bb = blk["Bodice front"], blk["Bodice back"]
    T = {}
    N0, SH0 = nodep(bf, "neck"), nodep(bf, "shoulder")
    u = unit(sub(SH0, N0))
    T["N"] = add(N0, u, f["neck_widen"])
    T["CFN"] = (0.0, nodep(bf, "center_neck")[1] + f["neck_drop"])
    T["SH"], T["AC"] = SH0, add(nodep(bf, "across"), (f["across_out"], 0.0))
    se = f["side_ease"]
    T["UA"] = add(nodep(bf, "underarm"), (se, f["arm_drop"]))
    T["WA"] = add(nodep(bf, "waist_dart"), (f["dart_shift"], 0.0))   # front waist dart, or the princess seam, moved sideways
    T["BP"] = (T["WA"][0], nodep(bf, "side_dart")[1])
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
    T["CBW"] = (f["cb_waist"], T["YWb"])
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

    L2, SW, up = T["L2"], T["SW"], 0.0
    if S["fit"]["bust_dart"] is not None:              # a smaller (or larger) bust dart than the block's: the front side
        up = dist(T["L1"], L2) - S["fit"]["bust_dart"]   # seam below it moves up by the difference, so it still matches
        L2 = add(T["L1"], unit(sub(L2, T["L1"])), S["fit"]["bust_dart"])   # the back, and the front hem drops at the centre
        SW = add(SW, (0.0, -up))

    front = mk("Front", [("neck", T["N"], None), ("shoulder", T["SH"], T["arm_up"]), ("across", T["AC"], T["arm_lo"]),
                         ("underarm", T["UA"], None), ("side_dart_1", T["L1"], None), ("side_dart", T["AS"], None),
                         ("side_dart_2", L2, None), ("side_waist", SW, hip_c(SW)),
                         ("side_hip", (hq, T["YW"] + hd - up), None)]
               + ([("hem_side", (hq, yf), None)] if not up else             # the hem stays level under the facing, then rises
                  [("hem_side", (hq, yf - up), ((hq - 8, yf - up), (hq - 15, yf))), ("hem_mid", (-ext + S["facing"]["width"], yf), None)])
               + front_edge(K, ext, yf, S["front"]["hold_to"]),
               darts_in=[[list(T["WA"]), list(T["WLo"]), [T["WA"][0], T["YW"] + S["fit"]["dart_below"]], list(T["WLi"])]])
    front["outline"][idx(front, "side_dart")]["dart"] = True
    back = mk("Back", [("center_neck", T["CBN"], T["neck_b"]), ("neck", T["Nb"], None),
                       ("shoulder", T["SHb"], T["arm_upb"]), ("across", T["ACb"], T["arm_lob"]),
                       ("underarm", T["UAb"], None), ("side_waist", T["SWb"], hip_c(T["SWb"])),
                       ("side_hip", (hq, T["YWb"] + hd), None), ("hem_side", (hq, yb), None), ("hem_cb", (0.8 * T["CBW"][0], yb), None),
                       ("cb_waist", T["CBW"], ((T["CBW"][0], 32.0), (0.0, 26.0))), ("cb_blade", (0.0, 20.0), None)],
              darts_in=[[list(T["Ab"]), list(T["WLbo"]), [T["Ab"][0], T["YWb"] + S["fit"]["dart_below"]], list(T["WLbi"])]])
    for pc in (front, back):
        notch(pc, "side_waist")
    side_f = [("Front", "underarm", "side_dart_1"), ("Front", "side_dart_2", "side_waist"),
              ("Front", "side_waist", "side_hip"), ("Front", "side_hip", "hem_side")]
    side_b = [("Back", "underarm", "side_waist"), ("Back", "side_waist", "side_hip"), ("Back", "side_hip", "hem_side")]
    return {"pieces": [front, back], "side": (side_f, side_b), "arm_f": [("Front", "underarm", "across"),
            ("Front", "across", "shoulder")], "arm_b": [("Back", "underarm", "across"), ("Back", "across", "shoulder")],
            "darts": [("Front", "side_dart_1", "side_dart", "side_dart_2")],
            "hem_names": {"Front": ["hem_side"] + (["hem_mid"] if up else []), "Back": ["hem_side"]},
            "front_panel": "Front", "back_panel": "Back"}


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
            ("cb_waist", add(T["CBW"], (-pl, 0)), ((T["CBW"][0] - pl, 32.0), (-pl, 26.0)))] + cbtop,
            lines=[[[0.0, lining["bnf"][1] if lining.get("bnf") else T["CBN"][1]], [T["CBW"][0], T["YWb"]]]]))
    else:
        out.append(mk("Back", [
            ("center_neck", T["CBN"], T["neck_b"]), ("neck", T["Nb"], None), ("shoulder", T["SHb"], T["arm_upb"]),
            ("across", T["ACb"], G["pb_up"]), ("dart_point", T["Ab"], G["pb_lo_i"]), ("waist", T["WLbi"], ck1),
            ("hem_princess", hk1, hem_c(hk1, (-dk1[1], dk1[0]), hk2, neg)), ("hem_cb", hk2, (ck2[1], ck2[0])),
            ("cb_waist", T["CBW"], ((T["CBW"][0], 32.0), (0.0, 26.0))), ("cb_blade", (0.0, 20.0), None)]))
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
                nodes += [("vent_top", Rl(VtT), None), ("vent_corner", Rl((VtT[0] + c["vent_width"], VtT[1] + 1.0)), None),
                          ("vent_hem", Rl((BwT[0] + c["vent_width"], Ls)), None)]
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
            nodes += [("vent_hem", (BwU[0] - c["vent_width"], hem), None), ("vent_corner", (VtU[0] - c["vent_width"], VtU[1] + 1.0), None),
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


# ------------------------------------------------------------------ one-piece, raglan and kimono sleeves


def sleeve_base(arm_f, arm_b, depth, c, lower=0.0):
    """One-piece sleeve base: cap = armhole + ease, cap height 5/6 of the armhole depth (lowered by `lower` for a
    raglan), underarm points at the cap height, straight taper to the hem width."""
    CH = c["cap_height"] or 5 / 6 * depth - c["drop"] / 2

    def caps(W, ch):
        Fu, Bu, Cr = (-W / 2, ch), (W / 2, ch), (0.0, 0.0)
        return (Fu, (-W / 2 + W * 0.18, ch), (-W * 0.22, 0.0), Cr), (Bu, (W / 2 - W * 0.14, ch), (W * 0.25, 0.0), Cr)

    W = 38.0
    for _ in range(60):
        fcap, bcap = caps(W, CH)
        W += arm_f + arm_b + c["ease"] - (blen(fcap) + blen(bcap))
    CH -= lower
    fcap, bcap = caps(W, CH)
    return {"W": W, "CH": CH, "fcap": fcap, "bcap": bcap}


def one_piece_sleeve(arm_f, arm_b, depth, c):
    """Set-in one-piece sleeve (kb set-in-sleeve): the cap curves are matched to the armhole chains at the seams."""
    g = sleeve_base(arm_f, arm_b, depth, c)
    fcap, bcap, Ls, WW = g["fcap"], g["bcap"], c["length"], c["hem"]

    def piece(lining=False):
        hem = Ls - 1.5 if lining else Ls
        pc = mk("Sleeve lining" if lining else "Sleeve",
                [("crown", (0.0, 0.0), (bcap[2], bcap[1])), ("back_underarm", bcap[0], None),
                 ("back_wrist", (WW / 2, hem), None), ("front_wrist", (-WW / 2, hem), None),
                 ("front_underarm", fcap[0], (fcap[1], fcap[2]))], grain=[[0.0, g["CH"] + 4], [0.0, Ls - 14]])
        notch(pc, "crown")
        return pc
    return {"piece": piece, "W": g["W"], "CH": g["CH"]}


def _bow_controls(p0, p3, off, towards):
    """Controls of a curve from p0 to p3 bowed by `off` at its middle, on the side of point `towards`."""
    d = sub(p3, p0)
    n = unit(perp_r(d))
    if (n[0] * (towards[0] - p0[0]) + n[1] * (towards[1] - p0[1])) < 0:
        n = (-n[0], -n[1])
    return add(add(p0, d, 1 / 3), n, off * 1.33), add(add(p0, d, 2 / 3), n, off * 1.33)


def raglan(T, B, pcs, c, depth, arm_f, arm_b):
    """Classic one-piece raglan with a shoulder dart (sheet sleeves-collars 1.5, kb raglan-from-set-in): the raglan
    line is drawn on the front and the back, the shoulder pieces are cut away and laid on a one-piece sleeve whose
    cap is lowered by `cap_lower`, the gap at the shoulder tip becomes the sleeve-top dart. Seams one edge to one
    edge: raglan lines (equal by construction), the `arm` cm of armhole left under the raglan line, the dart legs."""
    rn, ra, bow, d_w = c["neck"], c["arm"], c["bow"], c["dart"]
    g = sleeve_base(arm_f, arm_b, depth, c, lower=c["cap_lower"])
    fcap, bcap, Ls, WW = g["fcap"], g["bcap"], c["length"], c["hem"]
    f_lo, _ = split(*fcap, t_len(fcap, ra))
    b_lo, _ = split(*bcap, t_len(bcap, ra))
    cut = {}
    for panel, low, x_neck, mirror in ((B["front_panel"], f_lo[3], -d_w / 2, False),
                                       (B["back_panel"], b_lo[3], d_w / 2, True)):
        pc = pcs[panel]
        split_on(pc, "center_neck", "neck", edge_len(pc, "center_neck", "neck") - rn, "raglan_neck")
        split_on(pc, "across", "underarm", edge_len(pc, "across", "underarm") - ra, "raglan_arm")
        nodes = {n["name"]: copy.deepcopy(n) for n in pc["outline"] if n.get("name")}
        away = [nodes[k] for k in ("raglan_neck", "neck", "shoulder", "across", "raglan_arm")]
        RA, SH = tuple(nodes["raglan_arm"]["p"]), tuple(nodes["shoulder"]["p"])
        RN = tuple(nodes["raglan_neck"]["p"])
        # the panel keeps the raglan line in place of neck, shoulder and across
        pc["outline"] = [n for n in pc["outline"] if n.get("name") not in ("neck", "shoulder", "across")]
        rn_node = pc["outline"][idx(pc, "raglan_neck")]
        mid = lerp(RN, RA, 0.5)
        inward = add(mid, sub(mid, SH))               # the raglan line is slightly concave on the body
        rn_node["c"] = [list(q) for q in _bow_controls(RN, RA, bow, inward)]
        rn_node.pop("dart", None)
        notch(pc, "raglan_neck", 0.0)
        # the cut-away turns about raglan_arm, set on the lowered cap, until its neck point sits half a dart
        # width from the sleeve axis, at the top: the two shoulder lines then meet as the sleeve-top dart
        NP = tuple(nodes["neck"]["p"])
        vn = sub(NP, RA)
        if mirror:
            vn = (-vn[0], vn[1])

        def at(a, v=vn):
            return add(low, rot(v, a))
        cands = []
        prev = at(0.0)[0] - x_neck
        for k in range(1, 721):
            a = k * math.pi / 360
            cur = at(a)[0] - x_neck
            if (cur < 0) != (prev < 0):
                lo_, hi_ = a - math.pi / 360, a
                for _ in range(40):
                    m_ = (lo_ + hi_) / 2
                    if ((at(m_)[0] - x_neck) < 0) == (prev < 0):
                        lo_ = m_
                    else:
                        hi_ = m_
                cands.append((at((lo_ + hi_) / 2)[1], (lo_ + hi_) / 2))
            prev = cur
        ang = min(cands)[1]                        # the branch with the neck point highest

        def tf(p, RA=RA, low=low, ang=ang, mirror=mirror):   # bound now: the loop variables change
            q = (-(p[0] - RA[0]) if mirror else p[0] - RA[0], p[1] - RA[1])
            return add(low, rot(q, ang))
        cut[panel] = {"away": away, "tf": tf, "RN": RN, "RA": RA, "SH": SH, "low": low, "inward": inward,
                      "rag_c": [tuple(q) for q in rn_node["c"]]}

    F, Bk = cut[B["front_panel"]], cut[B["back_panel"]]
    tfF, tfB = F["tf"], Bk["tf"]
    rag_f = [list(tfF(q)) for q in F["rag_c"]]
    rag_b = [list(tfB(q)) for q in Bk["rag_c"]]
    neck_c_f = [list(tfF(tuple(q))) for q in F["away"][0]["c"]]           # raglan_neck -> neck, as drawn
    neck_c_b = [list(tfB(tuple(q))) for q in Bk["away"][0]["c"]]
    SHf, SHb = tfF(F["SH"]), tfB(Bk["SH"])
    tip = lerp(SHf, SHb, 0.5)                          # the shoulder tips meet: tip of the sleeve-top dart
    Nf, Nb = tfF(tuple(F["away"][1]["p"])), tfB(tuple(Bk["away"][1]["p"]))

    def piece(lining=False):
        hem = Ls - 1.5 if lining else Ls
        nodes = [("front_wrist", (-WW / 2, hem), None), ("front_underarm", fcap[0], (f_lo[1], f_lo[2])),
                 ("cap_front_low", F["low"], (rag_f[1], rag_f[0])), ("raglan_front_neck", tfF(F["RN"]), neck_c_f),
                 ("neck_front", Nf, None), ("shoulder", tip, None),
                 ("neck_back", Nb, (neck_c_b[1], neck_c_b[0])),
                 ("raglan_back_neck", tfB(Bk["RN"]), rag_b), ("cap_back_low", Bk["low"], (b_lo[2], b_lo[1])),
                 ("back_underarm", bcap[0], None), ("back_wrist", (WW / 2, hem), None)]
        pc = mk("Sleeve lining" if lining else "Sleeve", nodes, grain=[[0.0, g["CH"] + 4], [0.0, Ls - 14]])
        pc["outline"][idx(pc, "shoulder")]["dart"] = True   # legs = the two shoulder lines, open at the neck
        for nm in ("raglan_front_neck", "raglan_back_neck", "cap_front_low", "cap_back_low"):
            notch(pc, nm)
        return pc
    return {"piece": piece, "W": g["W"], "CH": g["CH"], "cut": cut, "dart_width": dist(Nf, Nb), "tip_gap": dist(SHf, SHb),
            "tip_below_top": tip[1]}


def kimono(T, B, pcs, c, hem_allowance):
    """Kimono sleeve cut in one with the front and the back (sheet sleeves-collars 1.6, kb kimono-from-block-gusset):
    shoulder tip lowered 1 cm, sleeve top `slope` degrees below horizontal, hem `hem` wide, underarm line from the
    hem to the side seam lowered by `underarm_drop`; either a diamond gusset of side `gusset` set in a slash along
    the underarm line (opened by a 1 mm slit for CLO3D) or the corner rounded with `radius`. A dolman is a kimono
    with slope 40, underarm_drop 15 to 25 and no gusset."""
    sl = math.radians(c["slope"])
    d = (math.cos(sl), math.sin(sl))
    gus = c["gusset"]
    out = {"gusset": None, "dart_removed": False}
    front_sh = None
    for panel in (B["front_panel"], B["back_panel"]):
        pc = pcs[panel]
        SH = nodep(pc, "shoulder")
        N = nodep(pc, "neck")
        SH = (SH[0], SH[1] + 1.0)
        if front_sh is None:
            front_sh = dist(N, SH)
        else:                                          # back shoulder = front shoulder + the block's shoulder ease
            SH = add(N, unit(sub(SH, N)), front_sh + T["sh_ease"])
        Ls = c["length"] - dist(N, SH)
        wt = add(SH, d, Ls)
        wu = add(wt, perp_r((-d[0], -d[1])), c["hem"] / 2)
        UA = nodep(pc, "underarm")
        J = (UA[0], UA[1] + c["underarm_drop"])
        names = [n.get("name") for n in pc["outline"]]
        if "side_dart_1" in names and J[1] >= nodep(pc, "side_dart_1")[1] - 1.0:
            after = names[idx(pc, "side_dart_2") + 1]        # the dart is swallowed by the deep underarm
            pc["outline"] = [n for n in pc["outline"] if n.get("name") not in ("side_dart_1", "side_dart", "side_dart_2")]
            B["side"] = ([(panel, "underarm", after)] + [e for e in B["side"][0] if e[1] not in ("underarm", "side_dart_2")],
                         B["side"][1])
            B["darts"] = [d_ for d_ in B["darts"] if d_[0] != panel]
            out["dart_removed"] = True
        i_ua = idx(pc, "underarm")
        nxt = tuple(pc["outline"][(i_ua + 1) % len(pc["outline"])]["p"])
        u_in = unit(sub(J, wu))                       # along the underarm line, into the body
        new = [{"name": "shoulder", "p": list(SH)}, {"name": "wrist_top", "p": [round(wt[0], 4), round(wt[1], 4)]},
               {"name": "wrist_under", "p": [round(wu[0], 4), round(wu[1], 4)]}]
        if gus:                                        # slash as a 1 mm slit: two parallel edges, as the glove slits
            pr = (-u_in[1], u_in[0])                   # right of travel: the fabric side (the sleeve is above the line)
            tip = add(J, u_in, gus)
            new += [{"name": "slash_mouth", "p": list(add(J, pr, 0.1))}, {"name": "slash_in", "p": list(add(tip, pr, 0.05))},
                    {"name": "slash_in_b", "p": list(add(tip, pr, -0.05))}, {"name": "underarm", "p": list(J)}]
        else:
            r = c["radius"]
            a = add(J, u_in, -r)
            new += [{"name": "arm_curve", "p": list(a), "c": [list(J), list(J)]},
                    {"name": "underarm", "p": list(add(J, unit(sub(nxt, J)), r))}]
        i_sh, i_ua = idx(pc, "shoulder"), idx(pc, "underarm")
        pc["outline"] = pc["outline"][:i_sh] + new + pc["outline"][i_ua + 1:]
        allow(pc, ["wrist_top"], hem_allowance)
        notch(pc, "wrist_under" if not gus else "slash_mouth", 0.0)
        out[panel] = {"width_at_body": 2 * abs((J[0] - SH[0]) * d[1] - (J[1] - SH[1]) * d[0]), "Ls": Ls}
    if gus:
        h = gus / math.sqrt(2)
        out["gusset"] = mk("Gusset", [("tip_front", (0.0, 0.0), None), ("side_seam", (h, h), None),
                                      ("tip_back", (0.0, 2 * h), None), ("underarm_seam", (-h, h), None)],
                           grain=[[0.0, 0.5 * h], [0.0, 1.5 * h]], cut="1 pair, bias")
    return out


# ------------------------------------------------------------------ shirt, convertible collars and hoods


def _arc_cubic(center, R, a0, a1):
    """One cubic approximating the arc of radius R about `center` from angle a0 to a1 (0 = straight down... here
    angles are measured from the vertical through the centre, towards +x), as (p0, c1, c2, p3)."""
    k = 4.0 / 3.0 * math.tan((a1 - a0) / 4)
    on = lambda a: (center[0] + R * math.sin(a), center[1] + R * math.cos(a))
    tan_ = lambda a: (math.cos(a), -math.sin(a))
    p0, p3 = on(a0), on(a1)
    return p0, add(p0, tan_(a0), R * k), add(p3, tan_(a1), -R * k), p3


def fall_piece(name, L, spring, H, point, lean, toc=0.0):
    """Collar fall (or a one-piece convertible collar): neck edge of length L rising by `spring` at the front, centre
    back height H, collar point `point` long leaning `lean` degrees forward, outer edge a smooth curve."""
    xf = L
    for _ in range(40):
        cv = ((0.0, 0.0), (xf / 3, 0.0), (2 * xf / 3, -spring * 0.6), (xf, -spring))
        xf += L - blen(cv)
    fn = (xf, -spring)
    la = math.radians(lean)
    tip = add(fn, (math.sin(la), -math.cos(la)), point + toc)
    cb_top = (0.0, -(H + toc))
    aim = (xf * 0.5, -(H + toc) - 0.3)
    outer = (add(tip, unit(sub(aim, tip)), dist(tip, cb_top) / 3), add(cb_top, (1.0, 0.0), dist(tip, cb_top) / 3))
    return mk(name, [("cb_neck", (0.0, 0.0), (cv[1], cv[2])), ("front_neck", fn, None), ("point", tip, outer),
                     ("cb_top", cb_top, None)], grain=[[2.0, -H * 0.3], [2.0, -H * 0.8]])


def shirt_collar(T, c, ext):
    """Shirt collar with a separate stand (sheet sleeves-collars 2.3, kb mens-shirt-collar-stand): stand as a band
    curving up `rise` at the front (neck edge = neckline + extension), fall whose neck edge equals the stand's top
    edge minus `fall_short`, spring, points."""
    BN = blen((T["CBN"], *T["neck_b"], T["Nb"]))
    FN = blen((T["CFN"], *T["neck_f"], T["N"]))
    LN = BN + FN + ext
    lo, hi = LN, 5000.0
    for _ in range(80):                       # R(1 - cos(LN / R)) = rise
        R = (lo + hi) / 2
        lo, hi = (R, hi) if R * (1 - math.cos(LN / R)) > c["rise"] else (lo, R)
    R = (lo + hi) / 2
    phi = LN / R
    h = c["h_cb"]
    C = (0.0, h - R)
    neck = _arc_cubic(C, R, 0.0, phi)
    top_end = add(neck[3], (-math.sin(phi), -math.cos(phi)), c["h_cf"])
    t = (math.cos(phi), -math.sin(phi))
    top_len = dist((0.0, 0.0), top_end)
    top_c = (add(top_end, t, -top_len / 3), add((0.0, 0.0), (1.0, 0.0), top_len / 3))
    end_c = (add(neck[3], t, 1.2), add(top_end, t, 1.2))

    def stand(name, toc=0.0):
        return mk(name, [("cb_neck", neck[0], (neck[1], neck[2])), ("front_neck", neck[3], end_c),
                         ("front_top", top_end, top_c), ("cb_top", (0.0, 0.0), None)],
                  grain=[[2.0, h * 0.3], [2.0, h * 0.8]])
    stand_top = blen(((0.0, 0.0), top_c[1], top_c[0], top_end))
    L_fall = stand_top - c["fall_short"]

    def collar(name, toc=0.0):
        return fall_piece(name, L_fall, c["spring"], c["fall_cb"], c["point"], c["lean"], toc)

    def cf_nodes(toc=0.0):
        return [("front_neck", (-ext, T["CFN"][1]), None), ("center_neck", T["CFN"], T["neck_f"])]
    return {"cf_nodes": cf_nodes, "collar": collar, "stand": stand, "top_y": T["CFN"][1], "top_node": "front_neck",
            "BN": BN, "FN": FN, "LN": LN, "L_fall": L_fall, "stand_top": stand_top}


def convertible_collar(T, c, ext):
    """One-piece convertible (camp) collar (sheet 2.4): neck edge = neckline + extension, spring, built-in stand."""
    BN = blen((T["CBN"], *T["neck_b"], T["Nb"]))
    FN = blen((T["CFN"], *T["neck_f"], T["N"]))
    LN = BN + FN + ext

    def collar(name, toc=0.0):
        return fall_piece(name, LN, c["spring"], c["h_cb"], c["point"], c["lean"], toc)

    def cf_nodes(toc=0.0):
        return [("front_neck", (-ext, T["CFN"][1]), None), ("center_neck", T["CFN"], T["neck_f"])]
    return {"cf_nodes": cf_nodes, "collar": collar, "top_y": T["CFN"][1], "top_node": "front_neck", "LN": LN}


def hood(T, c, ext):
    """Two-piece hood (sheet 2.10, kb hood-two-piece): neck edge = neckline to the front edge, depth at least that
    long, height, top back corner rounded; the two halves are sewn from the neck up the back and over the top."""
    BN = blen((T["CBN"], *T["neck_b"], T["Nb"]))
    FN = blen((T["CFN"], *T["neck_f"], T["N"]))
    LN = BN + FN + ext
    H, rad = c["height"], c["radius"]
    Wd = max(c["depth"], LN + 1.0)             # the face edge leans forward from the neck to the depth at head level
    k = 0.552

    def piece(name, toc=0.0):
        return mk(name, [("cb_neck", (0.0, 0.0), None), ("face_neck", (LN, 0.0), None),
                         ("face_top", (Wd, -H), None), ("top_back", (rad, -H), ((rad * (1 - k), -H), (0.0, -H + rad * (1 - k)))),
                         ("cb_round", (0.0, -H + rad), None)], grain=[[Wd / 2, -H + 6], [Wd / 2, -6.0]])

    def cf_nodes(toc=0.0):
        return [("front_neck", (-ext, T["CFN"][1]), None), ("center_neck", T["CFN"], T["neck_f"])]
    return {"cf_nodes": cf_nodes, "collar": piece, "hood": True, "top_y": T["CFN"][1], "top_node": "front_neck",
            "LN": LN, "depth": Wd}


# ------------------------------------------------------------------ welt and jetted pockets


def pocket_welt(front, T, pk, allowance):
    """Breast or hip welt (kb welt-pocket): opening line on the front, welt cut folded at twice its depth, shell facing
    and pocketing bags. For CLO3D the finished welt is a strip sewn along its lower edge onto the opening line."""
    L, dep, tilt = pk["length"], pk["depth"], pk["tilt"]
    chest = pk["where"] == "chest"
    x0 = pk["x"]
    y0 = (T["BP"][1] - pk["y"]) if chest else (T["YW"] + pk["y"])
    a, b = (x0, y0), (x0 + L, y0 - tilt)
    front["lines"] = front.get("lines", []) + [[list(a), list(b)]]
    bag = pk["bag"]
    cut = [mk("Welt", [("w_top0", (0.0, 0.0), None), ("w_top1", (L, 0.0), None), ("w1", (L, 2 * dep), None),
                       ("w0", (0.0, 2 * dep), None)], grain=[[1.0, dep], [L - 1.0, dep]], cut="1 pair, folded at mid-depth",
              lines=[[[0.0, dep], [L, dep]]], allowance=allowance),
           mk("Pocket facing", [("a", (0.0, 0.0), None), ("b", (L + 2, 0.0), None), ("c", (L + 2, bag), None), ("d", (0.0, bag), None)],
              grain=[[1.0, 2.0], [1.0, bag - 2]], cut="1 pair, shell", allowance=allowance),
           mk("Pocket bag", [("a", (0.0, 0.0), None), ("b", (L + 2, 0.0), None), ("c", (L + 2, bag), None), ("d", (0.0, bag), None)],
              grain=[[1.0, 2.0], [1.0, bag - 2]], cut="1 pair, pocketing", allowance=allowance)]
    shell = mk("Welt", [("w_top0", (0.0, 0.0), None), ("w_top1", (L, 0.0), None), ("w1", (L, dep), None), ("w0", (0.0, dep), None)],
               mirror=True, fabric="shell")
    hold = {"top": "Welt", "under": front["name"], "edge": ["w0", "w1"], "at": {"w0": list(a), "w1": list(b)}}
    return cut, shell, hold


def pocket_jetted(front, T, pk, allowance):
    """Jetted (double welt) pocket (kb jetted-pocket): opening line and jet lines on the front, two jet strips, shell
    facing and pocketing bags. In 3D the lines are drawn; the jets are decorative."""
    L, jet = pk["length"], pk["jet"]
    x0, y0 = pk["x"], T["YW"] + pk["y"]
    front["lines"] = front.get("lines", []) + [[[x0, y0], [x0 + L, y0]], [[x0, y0 - jet], [x0 + L, y0 - jet]],
                                               [[x0, y0 + jet], [x0 + L, y0 + jet]]]
    bag = pk["bag"]
    rect = lambda name, w, h, cut_: mk(name, [("a", (0.0, 0.0), None), ("b", (w, 0.0), None), ("c", (w, h), None), ("d", (0.0, h), None)],
                                       grain=[[1.0, 1.0], [1.0, h - 1.0]], cut=cut_, allowance=allowance)
    return [rect("Jet", L + 3, 3.0, "2 pairs, folded"), rect("Pocket facing", L + 2, bag, "1 pair, shell"),
            rect("Pocket bag", L + 2, bag, "1 pair, pocketing")]


# ------------------------------------------------------------------ chains: seams one edge to one edge


class Seams:
    """Builds the CLO3D seam list on the 3D shell, splitting edges so every seam is one edge to one edge."""

    def __init__(self, pieces):
        self.p = pieces
        self.rows = []
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

    def match(self, A, B, knots=(), why="", sides=None):
        """Sew chain A onto chain B. knots: (posA, posB) points that must meet (sleeve seams on armhole notches);
        positions between knots are matched proportionally, and each segment's ratio is declared as ease."""
        _, LA = self._positions(A)
        _, LB = self._positions(B)
        ks = [(0.0, 0.0)] + list(knots) + [(LA, LB)]

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
            opt = [{"ease": round(ease, 4), "why": why}] if abs(ease) > 0.002 else []
            self.rows.append(((na, a1, a2), (nb, b1, b2), opt, sides))


# ------------------------------------------------------------------ garment


def run(spec, base_dir="."):
    S = merged(spec)
    library.use_table(S.get("table"))
    library.use_avatar(S.get("avatar"))
    body = S["body"]
    own = {}
    if isinstance(S["measurements"], dict):            # given in the spec itself
        own = copy.deepcopy(S["measurements"])
        body = own.pop("body", body)
    elif S["measurements"]:
        with open(os.path.join(base_dir, S["measurements"]), encoding="utf-8") as f:
            own = json.load(f)
        body = own.pop("body", body)
    ease = {**P.standard_ease(body), **own.pop("ease", {})}
    size = str(S["size"] or library.reference_size(body))
    m = P.complete({**P.standard_measurements(body, size), **own}, body)
    T = torso(m, ease, body, S["fit"])
    shoulders(T, S["shoulder"]["extend"], S["shoulder"]["pad"])
    curves(T)
    ext = S["front"]["extension"]
    if S["front"]["hold_to"] is None and S["front"]["buttons"]:
        S["front"]["hold_to"] = max(S["front"]["buttons"]) + 2.0
    ctype = S["collar"]["type"]
    K = (notched_collar(T, S["collar"], ext) if ctype == "notched" else
         stand_collar(T, S["collar"], ext) if ctype in ("stand", "funnel") else
         shirt_collar(T, S["collar"], ext) if ctype == "shirt" else
         convertible_collar(T, S["collar"], ext) if ctype == "convertible" else
         hood(T, S["collar"], ext) if ctype == "hood" else no_collar(T, ext))
    B = {"darts": body_darts, "boxy": body_boxy, "princess": body_princess}[S["shaping"]](T, S, m, K)
    stype = S["sleeve"]["type"]
    if stype in ("raglan", "kimono") and S["shaping"] == "princess":
        raise SystemExit(f"{stype} sleeve: use the darts or boxy shaping (the armhole princess seam needs the armhole)")
    if stype in ("raglan", "kimono") and S["lining"]:
        raise SystemExit(f"{stype} sleeve: lining not drafted yet, set \"lining\": null")
    pcs = {p["name"]: p for p in B["pieces"]}
    front, back = pcs[B["front_panel"]], pcs[B["back_panel"]]
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
    if K.get("hood"):
        hd = K["collar"]("Hood")
        hd.update(cut="1 pair", allowance=S["allowance"])
        cut.append(hd)
        if S["lining"]:
            hl = K["collar"]("Hood lining")
            hl.update(cut="1 pair, lining", allowance=S["allowance"])
            cut.append(hl)
        info("hood depth (face edge to centre back)", K["depth"])
    elif K["collar"]:
        toc = S["collar"].get("turn_of_cloth", 0.3)
        top_c = K["collar"]("Top collar", toc)
        top_c.update(cut="1 on fold", fold=[len(top_c["outline"]) - 1], allowance=S["allowance"])
        under_c = K["collar"]("Undercollar" if ctype == "notched" else "Inner collar", -toc)
        under_c.update(cut="1 pair, bias" if ctype == "notched" else "1 on fold", allowance=S["allowance"])
        if ctype != "notched":
            under_c["fold"] = [len(under_c["outline"]) - 1]
        cut += [top_c, under_c]
        if K.get("stand"):
            st = K["stand"]("Collar stand")
            st.update(cut="2 on fold (outer and inner), interfaced", fold=[len(st["outline"]) - 1], allowance=S["allowance"])
            cut.append(st)
            info("collar stand top edge", K["stand_top"])
            info("collar fall neck edge", K["L_fall"])

    # sleeve
    sv = s1 = km = None
    ARM_F = sum(edge_len(pcs[n], a, b) for n, a, b in B["arm_f"])
    ARM_B = sum(edge_len(pcs[n], a, b) for n, a, b in B["arm_b"])
    depth = ((T["UA"][1] - T["SH"][1]) + (T["UAb"][1] - T["SHb"][1])) / 2
    sc = dict(S["sleeve"])
    given = {k: sc[k] is not None for k in ("ease", "hem", "length")}
    if sc["ease"] is None:                             # null: the size table's own cap ease, and wrist + its wrist ease
        sc["ease"] = ease["sleeve_cap"]
    if sc["hem"] is None:
        sc["hem"] = m["wrist"] + ease["wrist"]
    sc["length"] = sc["length"] or m["arm_length"] - S["shoulder"]["extend"] + S["shoulder"]["pad"] / 2
    # what a null of the spec came to, so that `analyze --keys` can vary these values too
    resolved = {("sleeve", k): sc[k] for k, g in given.items() if not g}
    if S["shaping"] == "darts" and S["fit"]["bust_dart"] is None:
        resolved[("fit", "bust_dart")] = dist(T["L1"], T["L2"])
    if stype == "two-piece":
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
    elif stype in ("one-piece", "raglan"):
        if stype == "one-piece":
            s1 = one_piece_sleeve(ARM_F, ARM_B, depth, sc)
        else:
            sc["ease"] = sc.get("raglan_ease", 0.5)      # a raglan is set almost flat
            s1 = raglan(T, B, pcs, sc, depth, ARM_F, ARM_B)
        sl = s1["piece"]()
        sl.update(cut="1 pair", allowance=S["allowance"])
        allow(sl, ["back_wrist"], S["hem_allowance"])
        cut.append(sl)
        info("bicep width", s1["W"])
        info("sleeve cap height", s1["CH"])
        info("sleeve length", sc["length"])
        if stype == "raglan":
            info("raglan: sleeve-top dart width at the neck", s1["dart_width"])
            ck("raglan: shoulder tips meet at the dart point, gap (cm)", s1["tip_gap"], 0.0, 2.0)
            info("raglan: dart point below the cap top (1.5 to 2.5 typical; adjust cap_lower)", s1["tip_below_top"])
    elif stype == "kimono":
        km = kimono(T, B, pcs, sc, S["hem_allowance"])
        if km["gusset"]:
            km["gusset"]["allowance"] = S["allowance"]
            cut.append(km["gusset"])
        info("kimono sleeve width at the body (front)", km[B["front_panel"]]["width_at_body"])
        info("kimono sleeve length past the shoulder", km[B["front_panel"]]["Ls"])
        if km["dart_removed"]:
            info("kimono: the side bust dart is swallowed by the lowered underarm (removed)", 1)
    elif stype != "none":
        raise SystemExit(f"sleeve type {stype}: two-piece, one-piece, raglan, kimono or none")

    # facings
    ftype = S["facing"]["type"]
    if ftype == "auto":
        ftype = "panel" if S["shaping"] == "princess" else "width"
    Fs = add(T["N"], T["us"], 4.0)
    rag_left = None
    if stype == "raglan":                              # the facing follows the raglan line, the shoulder is gone
        cf_ = s1["cut"][B["front_panel"]]
        cv_ = (cf_["RN"], cf_["rag_c"][0], cf_["rag_c"][1], cf_["RA"])
        rag_left, _ = split(*cv_, t_len(cv_, 4.0))
        Fs = rag_left[3]
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
        n_top = (rag_left[0], (rag_left[1], rag_left[2])) if rag_left else (T["N"], None)
        facing = mk("Front facing", [("neck", n_top[0], n_top[1]), ("facing_shoulder", Fs, fac_c), ("facing_low", (xf, y_low), None),
                                     ("hem_in", (xf, yhem_f), None)] + front_edge(K, ext, yhem_f, None, toc),
                    within="Front")
        allow(facing, ["hem_in"], S["hem_allowance"])
        notch(facing, "facing_low")
    facing.update(cut="1 pair", allowance=S["allowance"])
    cut.append(facing)
    bnf = None
    if S["facing"]["back_neck"]:
        dep = S["facing"]["back_neck"]
        Fsb = add(T["Nb"], T["ub"], 4.0)
        bnf_c = ((Fsb[0] - 1.0, 8.0), (4.0, dep))
        bf_ = mk("Back neck facing", [("center_neck", T["CBN"], T["neck_b"]), ("neck", T["Nb"], None),
                                      ("facing_shoulder", Fsb, bnf_c), ("bnf_cb", (0.0, dep), None)],
                 fold=[3], cut="1 on fold", allowance=S["allowance"], within="Back")
        cut.append(bf_)
        bnf = (Fsb, dep, bnf_c)
        ck("front facing shoulder = back neck facing shoulder", dist(T["N"], Fs), dist(T["Nb"], Fsb))

    # pockets
    welt_shell, welt_holds = [], []
    for pk in S["pockets"] or []:
        if pk["type"] == "welt":
            wc, wsh, wh = pocket_welt(front, T, pk, S["allowance"])
            if welt_shell:
                wsh["name"] = wh["top"] = f"Welt {len(welt_shell) + 1}"
                for c_ in wc:
                    c_["name"] = f"{c_['name']} {len(welt_shell) + 1}"
            cut += wc
            welt_shell.append(wsh)
            welt_holds.append(wh)
        elif pk["type"] == "jetted":
            cut += pocket_jetted(front, T, pk, S["allowance"])
        elif pk["type"] not in ("patch", "in-seam"):
            raise SystemExit(f"pocket type {pk['type']}: patch, in-seam, welt or jetted")
    seen = {}
    for p_ in cut:                                     # two pockets: "Pocket bag", "Pocket bag 2"
        seen[p_["name"]] = seen.get(p_["name"], 0) + 1
        if seen[p_["name"]] > 1:
            p_["name"] = f"{p_['name']} {seen[p_['name']]}"
    pk = next((p for p in (S["pockets"] or []) if p["type"] in ("patch", "in-seam")), None)
    if pk and pk["type"] == "patch":
        w, h, fy = pk["w"], pk["h"], pk["facing"]
        r, x0, y0 = pk["r"], pk["x"], T["YW"] + pk["y"]
        kk = 0.55 * r
        cut.append(mk("Patch pocket", [("top_left", (0, -fy), None), ("top_right", (w, -fy), None),
                                       ("corner_r", (w, h - r), ((w, h - r + kk), (w - r + kk, h))),
                                       ("bottom_r", (w - r, h), None),
                                       ("bottom_l", (r, h), ((r - kk, h), (0, h - r + kk))), ("corner_l", (0, h - r), None)],
                      grain=[[w / 2, 2.0], [w / 2, h - 4]], lines=[[[0, 0], [w, 0]]], cut="1 pair", allowance=1.0))
        front["lines"] = front.get("lines", []) + [[[x0, y0], [x0 + w, y0]], [[x0 + w, y0], [x0 + w, y0 + h]],
                                                   [[x0 + w, y0 + h], [x0, y0 + h]], [[x0, y0 + h], [x0, y0]]]
    elif pk and pk["type"] == "in-seam":
        top_, ln = pk["top"], pk["length"]
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
        elif s1:
            lining_pieces.append(s1["piece"](True))
        for p in lining_pieces:
            p.update(cut=p.get("cut", "1 pair"), allowance=1.5 if S["shaping"] == "princess" else 1.0)
        info("lining hem above the finished hem", up)

    # 3D shell: mirror halves, every seam, wrap holds
    shell3d = {p["name"]: copy.deepcopy(p) for p in B["pieces"]}
    if K["collar"]:
        shell3d["Hood" if K.get("hood") else "Collar"] = K["collar"]("Hood" if K.get("hood") else "Collar", 0.0)
    if K.get("stand"):
        shell3d["Collar stand"] = K["stand"]("Collar stand", 0.0)
    if sv:
        shell3d["Top sleeve"], shell3d["Under sleeve"] = sv["top"](), sv["under"]()
    if s1:
        shell3d["Sleeve"] = s1["piece"]()
    if km and km["gusset"]:
        shell3d["Gusset"] = copy.deepcopy(km["gusset"])
    for w in welt_shell:
        shell3d[w["name"]] = w
    for nm, p in shell3d.items():
        for k in ("buttons", "darts_in", "fold", "allowances", "notches"):
            p.pop(k, None)
        p["mirror"] = True
        p["fabric"] = "shell"                       # read by build_garment: --fabrics shell=<index or name>
        if nm in P.WEARER_RIGHT:
            p["wearer"] = "right"                   # the original half is the wearer's right: {side} follows
        if P.arrange_for(nm):
            p["arrange"] = P.arrange_for(nm)
    if "Side back" in shell3d and P.arrange_for("Back with side panels"):   # princess: the side backs take the back points
        shell3d["Back"]["arrange"] = P.arrange_for("Back with side panels")
    for w in welt_shell:                            # a welt sits on its front, a little off the body
        if P.arrange_for(B["front_panel"]):
            shell3d[w["name"]]["arrange"] = dict(P.arrange_for(B["front_panel"]), x=50, y=50, offset=40)
    wearer = {nm: "right" if nm in ("Back", "Side back", "Collar", "Collar stand", "Hood") else "left" for nm in shell3d}
    sm = Seams(shell3d)
    sf, sb = B["side"]
    sm.match(sf, sb, why="side seam")
    for A_, B_ in B.get("princess", []):
        sm.match(A_, B_, why="princess seam")
    for nm, l1, ap, l2 in B["darts"]:
        sm.match([(nm, l1, ap)], [(nm, l2, ap)], why="dart legs, trued")
    FP, BP_ = B["front_panel"], B["back_panel"]
    if stype != "raglan":
        sm.match([(BP_, "neck", "shoulder")], [(FP, "neck", "shoulder")], why="back shoulder ease")
    if stype == "kimono":
        sm.match([(BP_, "shoulder", "wrist_top")], [(FP, "shoulder", "wrist_top")], why="kimono sleeve top seam")
        if km["gusset"]:
            sm.match([(FP, "wrist_under", "slash_mouth")], [(BP_, "wrist_under", "slash_mouth")], why="kimono underarm seam")
            sm.match([(FP, "slash_in_b", "underarm")], [("Gusset", "tip_front", "side_seam")], why="gusset, front slash")
            sm.match([(BP_, "underarm", "slash_in_b")], [("Gusset", "side_seam", "tip_back")], why="gusset, back slash")
            sm.match([(BP_, "slash_in", "slash_mouth")], [("Gusset", "tip_back", "underarm_seam")], why="gusset, back slash")
            sm.match([(FP, "slash_mouth", "slash_in")], [("Gusset", "underarm_seam", "tip_front")], why="gusset, front slash")
        else:
            sm.match([(FP, "wrist_under", "arm_curve"), (FP, "arm_curve", "underarm")],
                     [(BP_, "wrist_under", "arm_curve"), (BP_, "arm_curve", "underarm")], why="kimono underarm seam")
    if stype == "raglan":
        sm.match([("Sleeve", "cap_front_low", "raglan_front_neck")], [(FP, "raglan_arm", "raglan_neck")], why="front raglan seam")
        sm.match([("Sleeve", "cap_front_low", "front_underarm")], [(FP, "raglan_arm", "underarm")], why="armhole under the raglan, front")
        sm.match([("Sleeve", "cap_back_low", "raglan_back_neck")], [(BP_, "raglan_arm", "raglan_neck")], why="back raglan seam")
        sm.match([("Sleeve", "cap_back_low", "back_underarm")], [(BP_, "raglan_arm", "underarm")], why="armhole under the raglan, back")
        sm.match([("Sleeve", "neck_front", "shoulder")], [("Sleeve", "neck_back", "shoulder")], why="sleeve-top dart: shoulder lines, back ease")
    if s1:
        sm.match([("Sleeve", "back_underarm", "back_wrist")], [("Sleeve", "front_underarm", "front_wrist")], why="sleeve underarm seam")
    if stype == "one-piece":
        sm.match([("Sleeve", "front_underarm", "crown")], B["arm_f"], why="sleeve cap ease, front")
        sm.match([("Sleeve", "back_underarm", "crown")], B["arm_b"], why="sleeve cap ease, back")
    cb_chain, nb = [], back["outline"]
    i = idx(shell3d["Back"], "hem_cb")
    names = [n["name"] for n in shell3d["Back"]["outline"]]
    j = i
    while names[j] != "center_neck":
        cb_chain.append(("Back", names[j], names[(j + 1) % len(names)]))
        j = (j + 1) % len(names)
    sm.match(cb_chain, cb_chain, why="centre back", sides="LR")
    if K["collar"]:
        cname = "Hood" if K.get("hood") else "Collar stand" if K.get("stand") else "Collar"
        if ctype == "notched":
            col_chain = [("Collar", "cb_neck", "neck"), ("Collar", "neck", "gorge_neck"), ("Collar", "gorge_neck", "notch")]
            neck_chain = [("Back", "center_neck", "neck"), ("Front", "neck", "gorge_neck"), ("Front", "gorge_neck", "gorge_roll"),
                          ("Front", "gorge_roll", "notch")]
        else:
            col_chain = [(cname, "cb_neck", "face_neck" if K.get("hood") else "front_neck")]
            if stype == "raglan":               # the sleeve carries the neckline between the raglan lines
                neck_chain = [("Back", "center_neck", "raglan_neck"), ("Sleeve", "raglan_back_neck", "neck_back"),
                              ("Sleeve", "neck_front", "raglan_front_neck"), ("Front", "raglan_neck", "center_neck"),
                              ("Front", "center_neck", "front_neck")]
            else:
                neck_chain = [("Back", "center_neck", "neck"), ("Front", "neck", "center_neck"), ("Front", "center_neck", "front_neck")]
        sm.match(col_chain, neck_chain, why="collar on neckline")
        if K.get("hood"):
            top = [("Hood", "cb_neck", "cb_round"), ("Hood", "cb_round", "top_back"), ("Hood", "top_back", "face_top")]
            sm.match(top, top, why="hood centre back and top", sides="LR")
        else:
            sm.match([(cname, "cb_top", "cb_neck")], [(cname, "cb_top", "cb_neck")], why="collar centre back", sides="LR")
        if K.get("stand"):
            split_on(shell3d["Collar stand"], "cb_top", "front_top", K["L_fall"], "fall_end")
            sm.match([("Collar", "cb_neck", "front_neck")], [("Collar stand", "cb_top", "fall_end")], why="fall on the stand")
            sm.match([("Collar", "cb_top", "cb_neck")], [("Collar", "cb_top", "cb_neck")], why="collar centre back", sides="LR")
    if sv:
        sm.match([("Under sleeve", "underarm", "front_seam_cap"), ("Top sleeve", "front_seam_cap", "crown")], B["arm_f"],
                 knots=[(sv["f_lo"], sv["f_lo"])], why="sleeve cap ease, front")
        sm.match([("Under sleeve", "underarm", "back_seam_cap"), ("Top sleeve", "back_seam_cap", "crown")], B["arm_b"],
                 knots=[(sv["b_lo"], sv["b_lo"])], why="sleeve cap ease, back")
        sm.match([("Top sleeve", "front_seam_cap", "front_seam_elbow"), ("Top sleeve", "front_seam_elbow", "front_seam_hem")],
                 [("Under sleeve", "front_seam_cap", "front_seam_hem")], why="forearm seam")
        sm.match([("Top sleeve", "back_seam_cap", sv["back_end"])], [("Under sleeve", "back_seam_cap", sv["back_end"])],
                 why="elbow ease")
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
    for wh in welt_holds:                             # the welt's lower edge on the opening line of each front
        for side_ in ("L", "R"):
            at = {k: [v[0] if side_ == "L" else -v[0], v[1]] for k, v in wh["at"].items()}
            holds.append({"top": f"{wh['top']} {side_}", "under": f"{wh['under']} {side_}", "edge": wh["edge"], "at": at})
    if K["collar"] and ctype != "notched" and ext > 0 and "overlap_line" in K:
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
    if stype != "raglan":
        ck("back shoulder - front shoulder (ease)", edge_len(back, "neck", "shoulder") - edge_len(front, "neck", "shoulder"),
           T["sh_ease"])
    return {"spec": S, "size": size, "cut": cut, "lining": lining_pieces, "shell3d": list(shell3d.values()),
            "seams": seams, "holds": holds, "checks": checks, "measurements": m, "ease": ease, "resolved": resolved}


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
    """Exports the cut pieces (SVG, DXF, pieces JSON) and the 3D shell for CLO3D (seams validated), prints the report."""
    sz = res["size"]
    S = res["spec"]
    cut_set = [(sz, {"pieces": res["cut"] + res["lining"], "checks": list(res["checks"])})]
    P.export(cut_set, out, S["title"])
    shell = [(sz, {"pieces": res["shell3d"], "seams": res["seams"], "holds": res["holds"], "checks": []})]
    P.export(shell, os.path.join(out, "clo3d"), S["title"] + " (3D shell)")
    print("== Cut pieces")
    ok = P.report(cut_set)
    print("\n== 3D shell")
    ok &= P.report(shell)
    print(f"\nFiles written to {os.path.abspath(out)} (3D shell for CLO3D in {os.path.join(out, 'clo3d')})")
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
    sys.exit(main())
