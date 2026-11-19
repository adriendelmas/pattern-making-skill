#!/usr/bin/env python3
"""Pattern-making engine: parametric blocks, seam allowances, notches, unfolding, grading,
export to SVG (1:1 scale), DXF and JSON for CLO3D. Standard library only.

Inputs in cm, SVG/DXF/CLO3D outputs in mm.

  python pattern.py measurements --body women --size 38
  python pattern.py block all --body women --size 38 --out out
  python pattern.py block skirt --measurements measurements.json --out out
  python pattern.py block bodice --body men --sizes 44,48,52 --out grading
  python pattern.py piece pieces.json --out out
  python pattern.py test
"""
import argparse
import copy
import json
import math
import os
import re
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import library  # noqa: E402

# ------------------------------------------------------------------ geometry


def dist(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


def cubic(p0, c1, c2, p3, n=16):
    pts = []
    for i in range(1, n + 1):
        t = i / n
        u = 1 - t
        pts.append((u ** 3 * p0[0] + 3 * u * u * t * c1[0] + 3 * u * t * t * c2[0] + t ** 3 * p3[0],
                    u ** 3 * p0[1] + 3 * u * u * t * c1[1] + 3 * u * t * t * c2[1] + t ** 3 * p3[1]))
    return pts


def length(pts):
    return sum(dist(a, b) for a, b in zip(pts, pts[1:]))


def point_at(pts, d):
    """Point and unit tangent at distance d (d < 0: counted from the end)."""
    if d < 0:
        d += length(pts)
    for i, (a, b) in enumerate(zip(pts, pts[1:])):
        l = dist(a, b)
        if l and (d <= l or i == len(pts) - 2):
            t = max(0.0, min(d / l, 1.0))
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t), ((b[0] - a[0]) / l, (b[1] - a[1]) / l)
        d -= l
    raise ValueError("zero-length edge")


def area(pts):
    return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(pts, pts[1:] + pts[:1])) / 2


def intersection(p1, p2, q1, q2):
    d1 = (p2[0] - p1[0], p2[1] - p1[1])
    d2 = (q2[0] - q1[0], q2[1] - q1[1])
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) < 1e-9:
        return None
    t = ((q1[0] - p1[0]) * d2[1] - (q1[1] - p1[1]) * d2[0]) / den
    return (p1[0] + d1[0] * t, p1[1] + d1[1] * t)


def reflect(p, a, b):
    """Mirror image of point p across the line (a, b)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)
    px, py = a[0] + t * dx, a[1] + t * dy
    return [2 * px - p[0], 2 * py - p[1]]


def perp_ctrl(a, b, k):
    """Control point leaving b, perpendicular to (a, b), downwards and inwards."""
    l = dist(a, b)
    ux, uy = (b[0] - a[0]) / l, (b[1] - a[1]) / l
    return (b[0] - uy * k, b[1] + ux * k)

# ------------------------------------------------------------------ pieces
# Full format: references/piece-format.md
# Axes: x towards the side, y downwards, in cm. Edge i runs from node i to node i+1.


def edge(piece, i, n=16):
    nds = piece["outline"]
    a, b = nds[i], nds[(i + 1) % len(nds)]
    p0, p3 = tuple(a["p"]), tuple(b["p"])
    if "c" in a:
        return [p0] + cubic(p0, tuple(a["c"][0]), tuple(a["c"][1]), p3, n)
    return [p0, p3]


def outline(piece, n=16):
    pts = []
    for i in range(len(piece["outline"])):
        pts += edge(piece, i, n)[:-1]
    return pts


def edge_allowance(piece, i):
    if i in piece.get("fold", []):
        return 0.0
    return float(piece.get("allowances", {}).get(str(i), piece.get("allowance", 1.0)))


def cut_line(piece):
    """Outline offset by each edge's allowance; the line bridges the opening of darts."""
    nds = piece["outline"]
    n = len(nds)
    keep = [k for k in range(n) if not nds[k].get("dart")]
    segs = []
    for j, k in enumerate(keep):
        k2 = keep[(j + 1) % len(keep)]
        pts = edge(piece, k) if (k + 1) % n == k2 else [tuple(nds[k]["p"]), tuple(nds[k2]["p"])]
        m = edge_allowance(piece, k)
        segs += [(a, b, m) for a, b in zip(pts, pts[1:]) if dist(a, b) > 1e-6]
    s = 1 if area([a for a, _, _ in segs]) > 0 else -1
    off = []
    for a, b, m in segs:
        l = dist(a, b)
        nx, ny = s * (b[1] - a[1]) / l, -s * (b[0] - a[0]) / l
        off.append(((a[0] + nx * m, a[1] + ny * m), (b[0] + nx * m, b[1] + ny * m)))
    out = []
    for j in range(len(off)):
        (p1, p2), (q1, q2) = off[j - 1], off[j]
        x = intersection(p1, p2, q1, q2)
        if x is None or dist(x, segs[j][0]) > 3 * max(segs[j - 1][2], segs[j][2], 0.3):
            out += [p2, q1]
        else:
            out.append(x)
    return out


def notches(piece):
    """0.6 cm notches, cut from the cut line inwards."""
    s = 1 if area(outline(piece)) > 0 else -1
    res = []
    for c in piece.get("notches", []):
        pts = edge(piece, c["edge"])
        d = c["d"] if "d" in c else c.get("t", 0) * length(pts)
        p, (tx, ty) = point_at(pts, d)
        nx, ny = s * ty, -s * tx
        m = edge_allowance(piece, c["edge"])
        res.append(((p[0] + nx * m, p[1] + ny * m), (p[0] + nx * (m - 0.6), p[1] + ny * (m - 0.6))))
    return res


def unfold(piece):
    """Whole piece from a half piece cut on the fold (mirrored across the fold edge)."""
    if not piece.get("fold"):
        return piece
    nds, n, k = piece["outline"], len(piece["outline"]), piece["fold"][0]
    A = [dict(nds[(k + 1 + i) % n]) for i in range(n)]       # from the end of the fold to its start
    m = n - 1
    fa, fb = A[m]["p"], A[0]["p"]
    full = [dict(x) for x in A]
    full[m].pop("c", None)
    for j in range(m - 1, 0, -1):
        r = {kk: v for kk, v in A[j].items() if kk != "c"}
        r["p"], r["name"] = reflect(A[j]["p"], fa, fb), A[j].get("name", "") + "_sym"
        full.append(r)
    for i in range(m):                                        # mirror edge of A[i] -> A[i+1]
        if "c" in A[i]:
            c1, c2 = A[i]["c"]
            full[2 * m - i - 1]["c"] = [reflect(c2, fa, fb), reflect(c1, fa, fb)]
    old = lambda e: (e - k - 1) % n
    out = {kk: v for kk, v in piece.items() if kk not in ("outline", "fold", "allowances", "notches")}
    out.update(outline=full, allowances={}, notches=[], cut="1x (unfolded)")
    for e, v in piece.get("allowances", {}).items():
        i = old(int(e))
        if i < m:
            out["allowances"][str(i)] = v
            out["allowances"][str(2 * m - 1 - i)] = v
    for c in piece.get("notches", []):
        i = old(c["edge"])
        if i >= m:
            continue
        L = length(edge(piece, c["edge"]))
        d = c["d"] if "d" in c else c.get("t", 0) * L
        d = d + L if d < 0 else d
        out["notches"] += [{"edge": i, "d": d}, {"edge": 2 * m - 1 - i, "d": L - d}]
    return out


# ------------------------------------------------------------------ transformations
# Per-edge attributes (allowance, fold, notches) are attached to the edge's start node during the
# operation, then re-indexed: inserting or removing nodes does not shift them.


def _attach(piece):
    nds = piece["outline"]
    for i, n in enumerate(nds):
        n["_allowance"] = edge_allowance(piece, i)
        n["_fold"] = i in piece.get("fold", [])
        n["_notches"] = []
    for c in piece.get("notches", []):
        L = length(edge(piece, c["edge"]))
        d = c["d"] if "d" in c else c.get("t", 0) * L
        nds[c["edge"]]["_notches"].append(d + L if d < 0 else d)


def _detach(piece):
    piece["allowances"], piece["fold"], piece["notches"] = {}, [], []
    for i, n in enumerate(piece["outline"]):
        if n.pop("_fold", False):
            piece["fold"].append(i)
        m = n.pop("_allowance", piece.get("allowance", 1.0))
        if m != piece.get("allowance", 1.0):
            piece["allowances"][str(i)] = m
        piece["notches"] += [{"edge": i, "d": round(d, 3)} for d in n.pop("_notches", [])]
    return piece


def _t_at_distance(p0, c1, c2, p3, d, n=400):
    cum = 0.0
    pts = [p0] + cubic(p0, c1, c2, p3, n)
    for i in range(1, n + 1):
        l = dist(pts[i - 1], pts[i])
        if cum + l >= d:
            return (i - 1 + (d - cum) / (l or 1)) / n
        cum += l
    return 1.0


def _split_edge(piece, i, d):
    """Insert a node at distance d along edge i (attributes attached). Return its index."""
    nds = piece["outline"]
    a, b = nds[i], nds[(i + 1) % len(nds)]
    L = length(edge(piece, i, 200))
    if d <= 0.01:
        return i
    if d >= L - 0.01:
        return (i + 1) % len(nds)
    nv = {"name": a.get("name", "n") + "_split", "_allowance": a["_allowance"], "_fold": a["_fold"],
          "_notches": [x - d for x in a["_notches"] if x > d]}
    a["_notches"] = [x for x in a["_notches"] if x <= d]
    if "c" in a:
        p0, c1, c2, p3 = a["p"], a["c"][0], a["c"][1], b["p"]
        t = _t_at_distance(p0, c1, c2, p3, d)
        lp = lambda u, v: [u[0] + (v[0] - u[0]) * t, u[1] + (v[1] - u[1]) * t]
        q0, q1, q2 = lp(p0, c1), lp(c1, c2), lp(c2, p3)
        r0, r1 = lp(q0, q1), lp(q1, q2)
        a["c"], nv["p"], nv["c"] = [q0, r0], lp(r0, r1), [r1, q2]
    else:
        nv["p"] = list(point_at([tuple(a["p"]), tuple(b["p"])], d)[0])
    nds.insert(i + 1, nv)
    return i + 1


def _reverse(piece):
    """Reverse the outline direction (attributes attached), curves and notches included."""
    nds = piece["outline"]
    n = len(nds)
    edges = []
    for i in range(n):
        L = length(edge(piece, i))
        edges.append((nds[i].get("c"), nds[i]["_allowance"], nds[i]["_fold"], [L - x for x in nds[i]["_notches"]]))
    new = [{k: v for k, v in nds[i].items() if k not in ("c", "_allowance", "_fold", "_notches")} for i in range(n - 1, -1, -1)]
    for j, nd in enumerate(new):
        c, m, fold, nt = edges[(n - 2 - j) % n]
        if c:
            nd["c"] = [c[1], c[0]]
        nd["_allowance"], nd["_fold"], nd["_notches"] = m, fold, nt
    piece["outline"] = new


def _ray(piece, start, u, excluded):
    """First edge hit by the half-line start + s*u: (edge index, distance along the edge)."""
    best = None
    for i in range(len(piece["outline"])):
        if i in excluded:
            continue
        pts = edge(piece, i, 64)
        cum = 0.0
        for a, b in zip(pts, pts[1:]):
            ex, ey = b[0] - a[0], b[1] - a[1]
            den = u[0] * ey - u[1] * ex
            if abs(den) > 1e-12:
                s = ((a[0] - start[0]) * ey - (a[1] - start[1]) * ex) / den
                v = ((a[0] - start[0]) * u[1] - (a[1] - start[1]) * u[0]) / den
                if s > 1e-6 and -1e-9 <= v <= 1 + 1e-9 and (best is None or s < best[0]):
                    best = (s, i, cum + v * dist(a, b))
            cum += dist(a, b)
    if best is None:
        raise SystemExit("The given direction does not reach any edge of the piece.")
    return best[1], best[2]


def pivot(piece, pivot_name, target, angle=None, fraction=1.0, flare=False):
    """Pivot (dart closing or transfer) and slash-and-spread.

    pivot_name: a node name. If it is a dart point and no angle is given, the dart is closed
                (fully or partly, per fraction) and its value moves into the slash.
    target: ("node", name) | ("edge", i, d) | ("direction", dx, dy): end of the slash.
    flare: the opened slash is filled (fullness added) instead of becoming a new dart.
    """
    import copy
    piece = copy.deepcopy(piece)
    _attach(piece)
    nds = piece["outline"]
    idx = lambda name: next((i for i, x in enumerate(nds) if x.get("name") == name), None)
    k = idx(pivot_name)
    if k is None:
        raise SystemExit(f"Node not found: {pivot_name}")
    pivot_node = nds[k]
    is_dart = bool(pivot_node.get("dart")) and angle is None
    if target[0] == "node":
        s_node = nds[idx(target[1])] if idx(target[1]) is not None else None
        if s_node is None:
            raise SystemExit(f"Node not found: {target[1]}")
    else:
        if target[0] == "edge":
            e, d = target[1], target[2]
        else:
            l = math.hypot(target[1], target[2])
            e, d = _ray(piece, pivot_node["p"], (target[1] / l, target[2] / l), {(k - 1) % len(nds), k})
        s_node = nds[_split_edge(piece, e, d)]
    k, s = nds.index(pivot_node), nds.index(s_node)
    n = len(nds)
    if any(nds[(k + 1 + i) % n]["_fold"] for i in range((s - k - 1) % n)):    # the fold must stay fixed
        _reverse(piece)
        nds = piece["outline"]
        pivot_node = next(x for x in nds if x.get("name") == pivot_node.get("name") and x["p"] == pivot_node["p"])
        s_node = next(x for x in nds if x["p"] == s_node["p"])
        k, s = nds.index(pivot_node), nds.index(s_node)
    P = pivot_node["p"]
    if is_dart:
        l1, l2 = nds[(k - 1) % n]["p"], nds[(k + 1) % n]["p"]
        th = math.atan2(l1[1] - P[1], l1[0] - P[0]) - math.atan2(l2[1] - P[1], l2[0] - P[0])
        th = (th + math.pi) % (2 * math.pi) - math.pi
        th *= fraction
    else:
        if angle is None:
            raise SystemExit("Give --angle when the pivot is not a dart point.")
        th = math.radians(abs(angle))

    def turn(th):
        ct, st = math.cos(th), math.sin(th)
        rot = lambda q: [P[0] + ct * (q[0] - P[0]) - st * (q[1] - P[1]), P[1] + st * (q[0] - P[0]) + ct * (q[1] - P[1])]
        mob = [copy.deepcopy(nds[(k + 1 + i) % n]) for i in range((s - k - 1) % n + 1)]  # pivot+1 ... S
        for x in mob:
            x["p"] = rot(x["p"])
            if "c" in x:
                x["c"] = [rot(c) for c in x["c"]]
        mob[-1]["name"] = mob[-1].get("name", "n") + "_piv"                   # S': the only duplicated point
        mob[-1].pop("c", None)                                                # edge towards the slash
        mob[-1]["_notches"] = []
        return rot, mob

    fixed = [nds[(s + i) % n] for i in range((k - s) % n + 1)]                # S ... pivot
    if not is_dart:                                                           # direction that opens the slash
        surf = lambda m: abs(area([tuple(x["p"]) for x in fixed + m]))
        th = max((th, -th), key=lambda t: surf(turn(t)[1]))
    rot, moving = turn(th)
    if is_dart and fraction >= 0.999:
        fixed.pop()                                                           # the dart is closed
        leg1, leg2 = fixed[-1], moving[0]
        gap = dist(leg1["p"], leg2["p"])
        if gap < 1.5:                                                         # dart legs trued at their midpoint
            if gap > 0.2:
                print(f"Note: dart legs differ by {gap * 10:.0f} mm, trued at their midpoint. "
                      "Check the length of the seam concerned.")
            leg1["p"] = [(leg1["p"][0] + leg2["p"][0]) / 2, (leg1["p"][1] + leg2["p"][1]) / 2]
            leg1.pop("c", None)
            for key in ("c", "_allowance", "_fold", "_notches"):
                if key in leg2:
                    leg1[key] = leg2[key]
            moving.pop(0)
    elif "c" in fixed[-1]:                                                    # edge pivot -> next: turns too
        fixed[-1] = dict(fixed[-1], c=[rot(c) for c in fixed[-1]["c"]])
    new = fixed + moving
    if not flare:
        apex = {"name": pivot_name + "_transfer", "p": list(P), "dart": True,
                "_allowance": s_node["_allowance"], "_fold": False, "_notches": []}
        new.append(apex)
    piece["outline"] = new
    return _detach(piece)


def smooth(piece, start, end):
    """Replace the path between two nodes with a smooth curve, perpendicular to the neighbouring edges
    at both ends (true a hem, a waist or a neckline after a transformation)."""
    import copy
    piece = copy.deepcopy(piece)
    _attach(piece)
    nds = piece["outline"]
    n = len(nds)
    names = [x.get("name") for x in nds]
    if start not in names or end not in names:
        raise SystemExit(f"Node not found: {start if start not in names else end}")
    i, j = names.index(start), names.index(end)
    A, B = nds[i]["p"], nds[j]["p"]
    before = edge(piece, (i - 1) % n)                   # edge arriving at A
    after = edge(piece, j)                              # edge leaving B

    def perp(u, towards):
        l = math.hypot(*u) or 1
        v = (-u[1] / l, u[0] / l)
        return v if v[0] * towards[0] + v[1] * towards[1] >= 0 else (-v[0], -v[1])

    chord = (B[0] - A[0], B[1] - A[1])
    k = math.hypot(*chord) / 3
    ta = perp((before[-1][0] - before[-2][0], before[-1][1] - before[-2][1]), chord)
    tb = perp((after[1][0] - after[0][0], after[1][1] - after[0][1]), (-chord[0], -chord[1]))
    nds[i]["c"] = [[A[0] + ta[0] * k, A[1] + ta[1] * k], [B[0] + tb[0] * k, B[1] + tb[1] * k]]
    nds[i]["_notches"] = []
    dropped = [nds[(i + 1 + t) % n] for t in range((j - i - 1) % n)]
    piece["outline"] = [x for x in nds if not any(x is g for g in dropped)]
    return _detach(piece)


class Draft:
    def __init__(self, name, **attrs):
        self.piece = {"name": name, "outline": [], **attrs}
        self.idx = {}

    def pt(self, name, x, y, dart=False):
        self.idx[name] = len(self.piece["outline"])
        n = {"name": name, "p": [x, y]}
        if dart:
            n["dart"] = True
        self.piece["outline"].append(n)
        return self

    def curve(self, c1, c2):
        self.piece["outline"][-1]["c"] = [list(c1), list(c2)]
        return self

    def e(self, name):
        return self.idx[name]

    def lg(self, *names):
        return sum(length(edge(self.piece, self.idx[x])) for x in names)

# ------------------------------------------------------------------ measurements
# The tables live in data/measurements/ (size charts, grading, ease) and are read through library.py, so a
# pattern maker can add or correct one without touching this file. Always prefer real body measurements.


def standard_measurements(body, size=None, table=None):
    return library.standard(body, size, table)


def standard_ease(body):
    return library.ease(body)


def arrange_for(piece_name):
    """Arrangement of a 3D piece on the current avatar (data/avatars/): {"name": point, ...}, or None. Looked up
    by the piece's full name, then by its first word."""
    table = library.arrangement(library.STATE.get("avatar"))
    v = table.get(piece_name, table.get(piece_name.split(" ")[0]))
    if v is None:
        return None
    return {"name": v} if isinstance(v, str) else dict(v)


def complete(m, body):
    """Add the missing derived measurements (formulas proportional to the bust)."""
    m = dict(m)
    B = m["bust"]
    nk, sh, ad, bw, cw = {"women": (B / 4 + 15, 4.8, 10, 6, 5), "men": (B / 5 + 20, 7.0, 11, 7, 6.5),
                          "children": (B / 4 + 13, 4.2, 7.5, 4, 3.5)}[body]
    m.setdefault("neck", round(nk, 1))
    m.setdefault("shoulder", round(m["neck"] / 5 + sh, 1))
    m.setdefault("armhole_depth", round(B / 8 + ad, 1))
    m.setdefault("half_back_width", round(B / 8 + bw, 1))
    m.setdefault("half_chest_width", round(B / 8 + cw, 1))
    if body == "women":
        m.setdefault("bust_depth", round(B * 0.29, 1))
        m.setdefault("bust_span", round(B * 0.21, 1))
        m.setdefault("bust_dart", round(B / 22, 1))
    return m


def check(label, value, expected=None, tol=None):
    return {"label": label, "value": round(value, 2),
            "expected": None if expected is None else round(expected, 2), "tol": tol}

# ------------------------------------------------------------------ blocks


def block_skirt(m, a, body):
    W, H, hh, L = m["waist"], m["hip"], m["hip_depth"], m["skirt_length"]
    pieces, side, total = [], {}, 0
    for name, sgn in (("front", 1), ("back", -1)):
        hip = (H + a["skirt_hip"]) / 4 + 0.5 * sgn
        wst = (W + a["skirt_waist"]) / 4 + 0.5 * sgn
        supp = max(hip - wst, 0)
        c = min(supp / 2, 3.0)                       # the side seam takes up to 3 cm
        pt = supp - c
        pt = pt if pt >= 0.5 else 0                  # dart too small: the side seam absorbs it
        if pt > 6:                                   # two darts of 3 cm at most
            pt = 6
        n = 1 if pt <= 3 else 2
        lp = (9 if name == "front" else 13) * (0.75 if body == "children" else 1)
        y0, ys = (0.0 if name == "front" else 1.0), -1.0
        xs = wst + pt
        yt = lambda x: y0 + (ys - y0) * (x / xs) ** 2
        t = Draft(f"Skirt {name}", cut="1x on fold" if name == "front" else "2x", allowance=1.0)
        t.pt("center_waist", 0, y0)
        for k, cc in enumerate([0.45] if n == 1 else [0.35, 0.65]):
            xc, w = xs * cc, pt / n
            if w > 0:
                t.pt(f"dart{k}_1", xc - w / 2, yt(xc - w / 2)).pt(f"dart{k}", xc, yt(xc) + lp, dart=True)
                t.pt(f"dart{k}_2", xc + w / 2, yt(xc + w / 2))
        t.pt("side_waist", xs, ys).curve((xs + (hip - xs) * 0.6, ys + (hh - ys) * 0.15), (hip, hh - (hh - ys) * 0.45))
        t.pt("hip", hip, hh).pt("side_hem", hip, L).pt("center_hem", 0, L)
        p = t.piece
        p["allowances"] = {str(t.e("side_hem")): 3.0}
        if name == "front":
            p["fold"] = [t.e("center_hem")]
        else:
            p["allowances"][str(t.e("center_hem"))] = 1.5
        p["notches"] = [{"edge": t.e("hip"), "d": 0}]
        p["grain"] = [[hip / 2, hh + 5], [hip / 2, L - 10]]
        side[name] = t.lg("side_waist", "hip")
        total += 2 * (xs - pt)
        pieces.append(p)
    return {"pieces": pieces,
            "checks": [check("Skirt: front side seam - back side seam", side["front"] - side["back"], 0, 0.3),
                       check("Skirt: finished waist", total, W + a["skirt_waist"], 0.6)]}


def block_bodice(m, a, body, knit=False):
    B, W, N, S = m["bust"], m["waist"], m["neck"], m["shoulder"]
    AD, NW = m["armhole_depth"], m["back_length"]
    BW, CW = m["half_back_width"], m["half_chest_width"]
    women = body == "women"
    Q = (B + a["bust"]) / 4
    Wq = (W + a["bodice_waist"]) / 4
    bd = m.get("bust_dart", 0) if women and not knit else 0
    sd_back, sd_front = {"women": (4, 5), "men": (4.5, 5.5), "children": (3, 4)}[body]
    nw = N / 5 - 0.2
    ya, yw = 2 + AD, 2 + NW
    diff = max(Q - Wq, 0) if women else 0

    def share(d, maxp):
        if knit:                                     # knit: no darts, the side seam takes the whole difference
            return d, 0
        c = min(d * 0.4, 2.5)
        p = d - c
        if p < 0.5:
            return c + p, 0
        return (c + p - maxp, maxp) if p > maxp else (c, p)

    # back
    sb, pd = share(diff, 4)
    snp = (nw, 0)
    sp = (nw + math.sqrt((S + a["shoulder"]) ** 2 - sd_back ** 2), sd_back)
    yb = sd_back + (ya - sd_back) * 0.45
    t = Draft("Bodice back", cut="2x", allowance=1.0)
    t.pt("center_neck", 0, 2).curve((nw * 0.55, 2), (nw * 0.9, 0.6)).pt("neck", *snp).pt("shoulder", *sp)
    t.curve(perp_ctrl(snp, sp, (yb - sd_back) * 0.4), (BW, yb - (yb - sd_back) * 0.3)).pt("across", BW, yb)
    t.curve((BW, yb + (ya - yb) * 0.55), (BW + (Q - BW) * 0.35, ya)).pt("underarm", Q, ya)
    t.pt("side_waist", Q - sb, yw)
    if pd > 0:
        xc = Q * 0.42
        t.pt("dart_1", xc + pd / 2, yw).pt("dart", xc, ya + 2, dart=True).pt("dart_2", xc - pd / 2, yw)
    t.pt("center_waist", 0, yw)
    back = t.piece
    back["allowances"] = {str(t.e("center_waist")): 1.5}
    back["notches"] = [{"edge": t.e("across"), "d": 0}, {"edge": t.e("across"), "d": 1}]
    back["grain"] = [[BW / 2, yb], [BW / 2, yw - 5]]
    side_back, shoulder_back, neck_back = t.lg("underarm"), t.lg("neck"), t.lg("center_neck")
    arm_back, arm_low_back = t.lg("shoulder", "across"), t.lg("across")
    waist_back = Q - sb - pd

    # front
    sf, pv = share(diff, 5)
    nwf = nw - 0.2
    ndf = nwf + 1
    snpf = (nwf, 0)
    spf = (nwf + math.sqrt(S ** 2 - sd_front ** 2), sd_front)
    yc = sd_front + (ya - sd_front) * 0.55
    ywf = yw + bd
    U, SW = (Q, ya), (Q - sf, ywf)
    t = Draft("Bodice front", cut="1x on fold", allowance=1.0)
    t.pt("center_neck", 0, ndf).curve((nwf * 0.6, ndf), (nwf, ndf * 0.4)).pt("neck", *snpf).pt("shoulder", *spf)
    t.curve(perp_ctrl(snpf, spf, (yc - sd_front) * 0.4), (CW, yc - (yc - sd_front) * 0.3)).pt("across", CW, yc)
    t.curve((CW, yc + (ya - yc) * 0.6), (CW + (Q - CW) * 0.3, ya)).pt("underarm", *U)
    side_front = dist(U, SW)
    if bd > 0.2:
        ap = (m["bust_span"] / 2, m["bust_depth"])
        ux, uy = (SW[0] - U[0]) / side_front, (SW[1] - U[1]) / side_front
        t.pt("side_dart_1", U[0] + ux * 5, U[1] + uy * 5)
        t.pt("side_dart", ap[0] + 2.5, ap[1], dart=True)
        t.pt("side_dart_2", U[0] + ux * (5 + bd), U[1] + uy * (5 + bd))
        side_front -= bd
    t.pt("side_waist", *SW)
    if pv > 0:
        ap = (m["bust_span"] / 2, m["bust_depth"])
        t.pt("waist_dart_1", ap[0] + pv / 2, ywf).pt("waist_dart", ap[0], ap[1] + 2, dart=True)
        t.pt("waist_dart_2", ap[0] - pv / 2, ywf)
    t.pt("center_waist", 0, ywf)
    front = t.piece
    front["fold"] = [t.e("center_waist")]
    front["notches"] = [{"edge": t.e("across"), "d": 0}]
    front["grain"] = [[CW / 2, yc], [CW / 2, ywf - 5]]
    arm_front, arm_low_front = t.lg("shoulder", "across"), t.lg("across")
    total = 2 * (waist_back + Q - sf - pv)
    checks = [check("Bodice: front side seam - back side seam (dart closed)", side_front - side_back, 0, 0.3),
              check("Bodice: back shoulder - front shoulder (ease)", shoulder_back - t.lg("neck"), a["shoulder"], 0.05),
              check("Bodice: drafted half neckline", neck_back + t.lg("center_neck"), N / 2, 1.5),
              check("Bodice: finished waist" if women else "Bodice: finished waist (info)",
                    total, W + a["bodice_waist"] if women else None, 0.6 if women else None),
              check("Bodice: total armhole (info)", arm_back + arm_front)]
    return {"pieces": [back, front], "checks": checks,
            "armhole": arm_back + arm_front, "armhole_low": {"back": arm_low_back, "front": arm_low_front}}


def block_sleeve(m, a, body, bodice):
    AH = bodice["armhole"]
    target = AH + a["sleeve_cap"]
    capH = AH / 3 - {"women": 0.5, "men": 1.5, "children": 1.0}[body]
    cap = lambda hw: length([(0, 0)] + cubic((0, 0), (hw * 0.45, 0), (hw * 0.55, capH), (hw, capH)))
    lo, hi = 1.0, AH
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if 2 * cap(mid) < target else (lo, mid)
    hw = (lo + hi) / 2
    L, pw = m["arm_length"], (m["wrist"] + a["wrist"]) / 2
    t = Draft("Sleeve", cut="2x (mirrored pair)", allowance=1.0)
    t.pt("cap", 0, 0).curve((hw * 0.45, 0), (hw * 0.55, capH)).pt("back_underarm", hw, capH)
    t.pt("back_wrist", pw, L).pt("front_wrist", -pw, L).pt("front_underarm", -hw, capH)
    t.curve((-hw * 0.55, capH), (-hw * 0.45, 0))
    p = t.piece
    e = a["sleeve_cap"] * 0.25
    dd = t.lg("cap") - (bodice["armhole_low"]["back"] + e)
    p["allowances"] = {str(t.e("back_wrist")): 2.0}
    p["notches"] = [{"edge": t.e("cap"), "d": 0},
                    {"edge": t.e("front_underarm"), "d": bodice["armhole_low"]["front"] + e},
                    {"edge": t.e("cap"), "d": dd}, {"edge": t.e("cap"), "d": dd - 1}]
    p["grain"] = [[0, capH + 2], [0, L - 5]]
    return {"pieces": [p], "knots": {"sleeve_back": dd, "sleeve_front": bodice["armhole_low"]["front"] + e},
            "checks": [check("Sleeve: cap - armhole (ease)", t.lg("cap", "front_underarm") - AH,
                             a["sleeve_cap"], 0.2),
                       check("Sleeve: cap height (info)", capH), check("Sleeve: width (info)", 2 * hw)]}


def block_trousers(m, a, body):
    W, H, hh = m["waist"], m["hip"], m["hip_depth"]
    CD, Lp = m["body_rise"] + 1, m["trouser_length"]
    yk = CD + (Lp - CD) / 2 - 5
    pieces, meas, total = [], {}, 0
    for name in ("front", "back"):
        fr = name == "front"
        sg = -1 if fr else 1
        wid = (H + a["trouser_hip"]) / 4 + sg
        ext = H / 20 if fr else H / 10
        yf = CD if fr else CD + 1
        xc = (ext - wid) / 2
        kg = (m["knee_width"] / 2 + sg) / 2
        kb = (m["hem_width"] / 2 + sg) / 2
        cm = (-1.0, 0.0) if fr else (-3.0, -2.0)
        wn = (W + a["trouser_waist"]) / 4 + sg
        pw = min(2 if fr else 3, max(0, wid + cm[0] - wn - 1.5))
        pw = pw if pw >= 0.5 else 0
        xsw = cm[0] - wn - pw
        yl = lambda x: cm[1] * (x - xsw) / (cm[0] - xsw)
        t = Draft(f"Trousers {name}", cut="2x", allowance=1.0)
        t.pt("center_waist", *cm)
        if pw > 0:
            xd = xc if fr else (cm[0] + xsw) / 2
            xd = max(xsw + pw, min(cm[0] - pw, xd))
            lp = (9 if fr else 12) * (0.75 if body == "children" else 1)
            t.pt("dart_1", xd + pw / 2, yl(xd + pw / 2)).pt("dart", xd, yl(xd) + lp, dart=True)
            t.pt("dart_2", xd - pw / 2, yl(xd - pw / 2))
        t.pt("side_waist", xsw, 0).curve((xsw + (-wid - xsw) * 0.6, hh * 0.15), (-wid, hh * 0.55))
        t.pt("hip", -wid, hh).curve((-wid, yf), (xc - kg, yk - (yk - yf) * 0.5))
        t.pt("outer_knee", xc - kg, yk).pt("outer_hem", xc - kb, Lp).pt("inner_hem", xc + kb, Lp)
        t.pt("inner_knee", xc + kg, yk).curve((xc + kg, yk - (yk - yf) * 0.5), (ext - 0.3 * (ext - xc - kg), yf + 2))
        l = dist((0, hh), cm)
        k = (yf - hh) * 0.45
        t.pt("crotch", ext, yf).curve((ext * (0.4 if fr else 0.35), yf), (-cm[0] / l * k, hh - (cm[1] - hh) / l * k))
        t.pt("center_hip", 0, hh)
        p = t.piece
        p["allowances"] = {str(t.e("outer_hem")): 4.0}
        if not fr:
            p["allowances"].update({str(t.e("crotch")): 1.5, str(t.e("center_hip")): 1.5})
        p["notches"] = [{"edge": t.e("hip"), "d": 0}, {"edge": t.e("outer_knee"), "d": 0},
                        {"edge": t.e("inner_knee"), "d": 0}] + ([] if fr else [{"edge": t.e("inner_knee"), "d": 1}])
        p["grain"] = [[xc, hh], [xc, Lp - 10]]
        meas[name] = {"outer": t.lg("side_waist", "hip", "outer_knee"), "inner": t.lg("inner_hem", "inner_knee"),
                      "crotch": t.lg("crotch", "center_hip")}
        total += 2 * wn
        pieces.append(p)
    return {"pieces": pieces,
            "checks": [check("Trousers: front side seam - back side seam", meas["front"]["outer"] - meas["back"]["outer"], 0, 0.6),
                       check("Trousers: front inseam - back inseam", meas["front"]["inner"] - meas["back"]["inner"], 0.5, 1.0),
                       check("Trousers: finished waist", total, W + a["trouser_waist"], 0.6),
                       check("Trousers: total crotch length (info)",
                             meas["front"]["crotch"] + meas["back"]["crotch"])]}


# ------------------------------------------------------------------ circle skirt


def arc_nodes(prefix, r, th0, th1, cy, first_name=None):
    """Nodes of a circular arc about (0, cy), radius r, from angle th0 to th1 (0 = straight down, positive
    towards +x), as cubic Beziers of 90 degrees at most. The last node is returned without a curve."""
    n = max(1, int(math.ceil(abs(th1 - th0) / (math.pi / 2) - 1e-9)))
    step = (th1 - th0) / n
    k = 4.0 / 3.0 * math.tan(abs(step) / 4)
    sgn = 1 if step > 0 else -1
    pt = lambda th: [r * math.sin(th), cy + r * math.cos(th)]
    out = []
    for i in range(n):
        a, b = th0 + i * step, th0 + (i + 1) * step
        ta, tb = (r * math.cos(a) * sgn, -r * math.sin(a) * sgn), (r * math.cos(b) * sgn, -r * math.sin(b) * sgn)
        pa, pb = pt(a), pt(b)
        out.append({"name": first_name if (i == 0 and first_name) else f"{prefix}{i}", "p": pa,
                    "c": [[pa[0] + ta[0] * k, pa[1] + ta[1] * k], [pb[0] - tb[0] * k, pb[1] - tb[1] * k]]})
    return out, pt(th1)


def block_circle_skirt(m, a, fullness=1.0, panels=2, length_cm=None):
    """Circle skirt (full 1.0, half 0.5, quarter 0.25...) in `panels` panels of equal angle, waist radius from the
    finished waist, hems trued as arcs. Panels are full pieces (no fold), sewn side to side; 2 panels give a front
    and a back with side seams, 1 panel a single seam."""
    W = m["waist"] + a["skirt_waist"]
    L = length_cm or m["skirt_length"]
    r = W / (2 * math.pi * fullness)
    ang = 2 * math.pi * fullness / panels
    names = (["Circle skirt"] if panels == 1 else ["Circle skirt front", "Circle skirt back"] if panels == 2
             else [f"Circle skirt panel {i + 1}" for i in range(panels)])
    pieces, waist_total, hem_total, seams = [], 0.0, 0.0, []
    for nm in names:
        waist, w_end = arc_nodes("waist_", r, -ang / 2, ang / 2, -r, first_name="waist_start")
        hem, h_end = arc_nodes("hem_", r + L, ang / 2, -ang / 2, -r, first_name="hem_end")
        waist_end = {"name": "waist_end", "p": w_end}
        hem_start = {"name": "hem_start", "p": h_end}
        p = {"name": nm, "cut": "1x", "allowance": 1.0, "outline": waist + [waist_end] + hem + [hem_start],
             "grain": [[0, 3], [0, L - 5]], "fabric": "shell"}
        p["allowances"] = {str(len(waist) + 1 + i): 1.0 for i in range(len(hem))}   # narrow hem on a curve
        p["notches"] = [{"edge": 0, "d": 0}] if nm.endswith("back") else []
        pieces.append(p)
        waist_total += sum(length(edge(p, i)) for i in range(len(waist)))
        hem_total += sum(length(edge(p, len(waist) + 1 + i)) for i in range(len(hem)))
    for i, p in enumerate(pieces):                       # right side of panel i onto the left side of panel i + 1
        q = pieces[(i + 1) % panels]
        seams.append([p["name"], "waist_end", "hem_end", q["name"], "waist_start", "hem_start"])
    arrange = {1: ["Leg_Skirt_Front"], 2: ["Leg_Skirt_Front", "Leg_Skirt_Back"]}.get(panels, [])
    for p, nm in zip(pieces, arrange):
        p["arrange"] = {"name": nm}
    return {"pieces": pieces, "seams": seams,
            "checks": [check("Circle skirt: finished waist", waist_total, W, 0.3),
                       check("Circle skirt: waist radius (info)", r), check("Circle skirt: hem length (info)", hem_total)]}


# ------------------------------------------------------------------ bands (waistbands, stand collars, cuffs)


def _named_edge_len(piece, a, b):
    """Length of the edge between neighbouring nodes a and b (either direction)."""
    nds = piece["outline"]
    n = len(nds)
    names = [x.get("name") for x in nds]
    if a not in names or b not in names:
        raise SystemExit(f"{piece['name']}: no node {a if a not in names else b}")
    i, j = names.index(a), names.index(b)
    if (i + 1) % n == j:
        return length(edge(piece, i, 64))
    if (j + 1) % n == i:
        return length(edge(piece, j, 64))
    raise SystemExit(f"{piece['name']}: {a} and {b} are not neighbours")


def expand_bands(pieces, seams):
    """A piece written as {"name", "band": {"height", "along": [[piece, a, b]...], "ease", "why", "extension"}}
    becomes a straight band as long as the edges it is sewn to, its lower edge split at the same points
    (nodes b0, b1...), with one seam per edge. `extension` adds an underlap past the last edge. A folded band
    (waistband, cuff) is cut at twice the height: `height` is the finished height, as sewn in 3D."""
    by = {p["name"]: p for p in pieces}
    for p in pieces:
        b = p.get("band")
        if not b:
            continue
        h, ease = float(b["height"]), float(b.get("ease", 0.0))
        x, bottom, segs = 0.0, [{"name": "b0", "p": [0.0, h]}], []
        for k, (nm, a1, a2) in enumerate(b["along"]):
            if nm not in by:
                raise SystemExit(f"{p['name']}: band along unknown piece {nm}")
            x += _named_edge_len(by[nm], a1, a2) * (1 + ease)
            bottom.append({"name": f"b{k + 1}", "p": [round(x, 4), h]})
            segs.append((nm, a1, a2, k))
        ext = float(b.get("extension", 0.0))
        top = [{"name": "top_start", "p": [0.0, 0.0]}, {"name": "top_end", "p": [round(x + ext, 4), 0.0]}]
        if ext:
            bottom.append({"name": "b_ext", "p": [round(x + ext, 4), h]})
        p["outline"] = top + list(reversed(bottom))
        p.setdefault("cut", "1x")
        p.setdefault("allowance", 1.0)
        p.setdefault("grain", [[2.0, h / 2], [max(x - 2.0, 4.0), h / 2]])
        p["fabric"] = p.get("fabric", "shell")
        for nm, a1, a2, k in segs:
            extra = [{"ease": round(ease, 4), "why": b.get("why", "band eased onto the edge")}] if abs(ease) > 1e-6 else []
            seams.append([p["name"], f"b{k}", f"b{k + 1}", nm, a1, a2] + extra)
        del p["band"]
    return pieces, seams


# ------------------------------------------------------------------ 3D shell of the standard blocks
# The cut pieces stay as drafted (half pieces on the fold, "2x" pieces once). The shell sent to CLO3D unfolds
# the fold pieces and mirrors the others into L and R, with every seam one edge to one edge (garment.Seams
# splits the longer chain where needed and declares each ratio as ease).

WEARER_RIGHT = ("Skirt back", "Bodice back", "Trousers front", "Back", "Side back")   # original half = wearer's right
OPP = {"L": "R", "R": "L"}


def shell_from_blocks(res, knit=False):
    """3D shell (pieces and seams) of the pieces drafted by `build`."""
    import garment as G
    shell = {}
    for p in res["pieces"]:
        q = copy.deepcopy(p)
        for k in ("buttons", "lines"):
            q.pop(k, None)
        pair = str(q.get("cut", "")).startswith("2") or "pair" in str(q.get("cut", ""))
        q = unfold(q) if q.get("fold") else dict(q, mirror=True) if pair else q
        for k in ("fold", "allowances", "notches"):
            q.pop(k, None)
        q["fabric"] = q.get("fabric", "shell")
        if q["name"] in WEARER_RIGHT:
            q["wearer"] = "right"
        if not q.get("arrange") and arrange_for(q["name"]):
            q["arrange"] = arrange_for(q["name"])
        if knit and q["name"] in ("Bodice front", "Bodice back", "Sleeve"):
            q["particle_distance"] = 8          # close-fitting knit: the default 20 mm lets the skin through
        shell[q["name"]] = q
    seams = list(res.get("seams", []))
    sm = G.Seams(shell)
    has = lambda nm, *nodes: nm in shell and all(any(n.get("name") == x for n in shell[nm]["outline"]) for x in nodes)

    def node_knots(A, B):
        """Knots at every intermediate node of two chains with the same number of edges: nodes meet nodes."""
        pa = pb = 0.0
        out = []
        for (na, a1, a2), (nb, b1, b2) in list(zip(A, B))[:-1]:
            pa += G.edge_len(shell[na], a1, a2)
            pb += G.edge_len(shell[nb], b1, b2)
            out.append((pa, pb))
        return out

    def chain(nm, *nodes):
        """Consecutive edges from node to node along the outline, including nodes inserted by earlier matches."""
        names = [n.get("name", "") for n in shell[nm]["outline"]]
        n, out = len(names), []
        for a, b in zip(nodes, nodes[1:]):
            i, j = names.index(a), names.index(b)
            fwd = [(names[(i + k) % n], names[(i + k + 1) % n]) for k in range((j - i) % n)]
            bwd = [(names[(i - k) % n], names[(i - k - 1) % n]) for k in range((i - j) % n)]
            out += [(nm, x, y) for x, y in (fwd if len(fwd) <= len(bwd) else bwd)]
        return out

    def darts(nm, prefix, sides):
        names = [n.get("name", "") for n in shell[nm]["outline"]]
        for tip in [x for x in names if re.fullmatch(prefix + r"\d*(_sym)?", x)]:
            base = tip[:-4] if tip.endswith("_sym") else tip
            suf = "_sym" if tip.endswith("_sym") else ""
            if base + "_1" + suf in names and base + "_2" + suf in names:
                sm.match([(nm, base + "_1" + suf, tip)], [(nm, base + "_2" + suf, tip)], why="dart legs",
                         sides="R" if suf else sides)

    if has("Skirt front", "side_waist") and has("Skirt back", "side_waist"):
        sm.match(chain("Skirt front", "side_waist", "hip", "side_hem"), chain("Skirt back", "side_waist", "hip", "side_hem"),
                 why="side seam", sides="L")
        sm.match(chain("Skirt front", "side_waist_sym", "hip_sym", "side_hem_sym"), chain("Skirt back", "side_waist", "hip", "side_hem"),
                 why="side seam", sides="R")
        sm.match([("Skirt back", "center_hem", "center_waist")], [("Skirt back", "center_hem", "center_waist")], why="centre back", sides="LR")
        darts("Skirt front", "dart", "L")
        darts("Skirt back", "dart", None)
    if has("Bodice front", "shoulder") and has("Bodice back", "shoulder"):
        F, B = "Bodice front", "Bodice back"
        for side, nm_ in (("L", lambda x: x), ("R", lambda x: x + "_sym")):
            sm.match([(B, "neck", "shoulder")], [(F, nm_("neck"), nm_("shoulder"))], why="back shoulder ease", sides=side)
            fs = (chain(F, nm_("underarm"), nm_("side_dart_1")) + chain(F, nm_("side_dart_2"), nm_("side_waist"))
                  if has(F, "side_dart") else chain(F, nm_("underarm"), nm_("side_waist")))
            sm.match(chain(B, "underarm", "side_waist"), fs, why="side seam, bust dart closed", sides=side)
        sm.match([(B, "center_waist", "center_neck")], [(B, "center_waist", "center_neck")], why="centre back", sides="LR")
        darts(F, "waist_dart", "L")
        darts(F, "side_dart", "L")
        darts(B, "dart", None)
    if has("Sleeve", "cap") and has("Bodice back", "across") and res.get("knots"):
        S_, F, B, kn = "Sleeve", "Bodice front", "Bodice back", res["knots"]
        sm.match([(S_, "back_underarm", "back_wrist")], [(S_, "front_underarm", "front_wrist")], why="sleeve underarm seam")
        sm.match(chain(S_, "cap", "back_underarm"), chain(B, "shoulder", "across", "underarm"),
                 knots=[(kn["sleeve_back"], G.elen(shell[B], "shoulder", "across"))], why="sleeve cap ease, back")
        for side, nm_ in (("L", lambda x: x), ("R", lambda x: x + "_sym")):
            front_arm = chain(F, nm_("underarm"), nm_("across"), nm_("shoulder"))
            sm.match(chain(S_, "front_underarm", "cap"), front_arm,
                     knots=[(kn["sleeve_front"], sum(G.edge_len(shell[F], x, y) for _, x, y in chain(F, nm_("underarm"), nm_("across"))))],
                     why="sleeve cap ease, front", sides=side)
    if has("Trousers front", "crotch") and has("Trousers back", "crotch"):
        TF, TB = "Trousers front", "Trousers back"
        side_ch = lambda nm: [(nm, "side_waist", "hip"), (nm, "hip", "outer_knee"), (nm, "outer_knee", "outer_hem")]
        in_ch = lambda nm: [(nm, "inner_hem", "inner_knee"), (nm, "inner_knee", "crotch")]
        sm.match(side_ch(TF), side_ch(TB), knots=node_knots(side_ch(TF), side_ch(TB)), why="side seam")
        sm.match(in_ch(TF), in_ch(TB), knots=node_knots(in_ch(TF), in_ch(TB)), why="inseam, back eased onto the front")
        for nm in (TF, TB):
            cf = chain(nm, "crotch", "center_hip", "center_waist")
            sm.match(cf, cf, why="centre seam", sides="LR")
            darts(nm, "dart", None)
    seams += shell_seams(sm.rows, shell)
    return {"pieces": list(shell.values()), "seams": seams, "checks": []}


def shell_seams(rows, shell):
    """Seams.match rows -> seam list with piece sides: `sides` None = both wearer sides, "L"/"R" = one wearer
    side (a fold piece's original or _sym half), "LR" = the piece's left half onto its right half."""
    def suffix(nm, w):
        if not shell[nm].get("mirror"):
            return ""
        return " " + (w if shell[nm].get("wearer", "left") != "right" else OPP[w])
    out = []
    for (a, b, opt, sides) in rows:
        if sides == "LR":
            out.append([f"{a[0]} L", a[1], a[2], f"{b[0]} R", b[1], b[2]] + opt)
            continue
        for w in (("L", "R") if sides is None else (sides,)):
            out.append([a[0] + suffix(a[0], w), a[1], a[2], b[0] + suffix(b[0], w), b[1], b[2]] + opt)
    return out


# ------------------------------------------------------------------ glove
# Leather glove drafted like real glove patterns (references/techniques/accessories.md, part 1):
# one trank (back and palm side by side, fold below the index crotch, straight parallel fingers separated by
# slits ending at crotch points, the two index halves sewn on their outer side, one straight side line),
# a Bolton thumb (heart shape folded on its axis) set into a drop-shaped hole with a V tongue, and one
# fourchette arm per finger side. Hand measurements in mm, size 7 values as default (sheet, section 1.6).

FINGERS_ORDER = ("L", "R", "M", "I")              # back half, from the little finger side
GLOVE_SLIT = 0.5                                  # half width of a slit, mm (a die cut has none; CLO3D needs a gap)


def glove_hand(size=7.0, own=None):
    """Hand measurements in mm: data/measurements/glove-hand.json graded by half sizes, then personal values."""
    h = library.standard("hand", size, "glove-hand")
    h.update(own or {})
    return h


def _bez_len(p0, c1, c2, p3):
    return length([p0] + cubic(p0, c1, c2, p3, 200))


def block_glove(h, stretch_ease=2.0):
    """Returns pieces (cm, skill format), seams by node names and checks. Coordinates drafted in mm with y up
    from the wrist crease, converted at the end."""
    G = h["G"]
    W = G + stretch_ease                                   # fine leather: G + 0 to 4
    Wb, Wp = W / 2 + 4, W / 2 - 4
    n_arms = {"I": 1, "M": 2, "R": 2, "L": 1}
    fw = (h["Cf_I"] + h["Cf_M"] + h["Cf_R"] + h["Cf_L"] - W) / 6
    tot = {f: h["Cf_" + f] - n_arms[f] * fw for f in "IMRL"}
    back_w = {f: tot[f] * Wb / W for f in "IMRL"}
    palm_w = {f: tot[f] * Wp / W for f in "IMRL"}
    tip = {f: h["h_" + f] + h["F_" + f] + 5 for f in "IMRL"}
    crotch_p = {("I", "M"): min(h["h_I"], h["h_M"]) + 4, ("M", "R"): min(h["h_M"], h["h_R"]) + 4,
                ("R", "L"): min(h["h_R"], h["h_L"]) + 4}
    crotch_b = {k: v - 5 for k, v in crotch_p.items()}    # back slits 5 mm deeper
    C0 = h["Web_T"]
    y_side = crotch_p[("R", "L")]
    y_end = -h["end_below_wrist"]
    flare = (h["end_girth"] + 10 - W) / 2                  # per side, ease 10 at the cuff

    def tip_edge(x0, x1, top, name0, name1):
        r = 0.4 * (x1 - x0)
        k = 4 / 3 * r
        return [{"name": name0, "p": [x0, top - r], "c": [[x0, top - r + k], [x1, top - r + k]]}], {"name": name1, "p": [x1, top - r]}, r

    o, r_tip = [], {}
    o.append({"name": "cuff_b", "p": [-flare, y_end]})
    o.append({"name": "side_b", "p": [0.0, y_side]})
    xb = [0.0]
    for f in FINGERS_ORDER:
        xb.append(xb[-1] + back_w[f])
    for i, f in enumerate(FINGERS_ORDER):               # back half: L R M I, left to right
        x0 = xb[i] + (GLOVE_SLIT if i > 0 else 0)
        x1 = xb[i + 1] - GLOVE_SLIT
        t0, t1, r_tip[f] = tip_edge(x0, x1, tip[f], f"b_{f}_t0", f"b_{f}_t1")
        o += t0 + [t1]
        if f != "I":
            nxt = FINGERS_ORDER[i + 1]
            key = (nxt, f)                               # crotch keys are (thumb side, little side)
            o.append({"name": f"b_{nxt}{f}", "p": [xb[i + 1], crotch_b[key]]})
    o.append({"name": "C0", "p": [Wb, C0]})
    xp = [Wb]
    for f in reversed(FINGERS_ORDER):
        xp.append(xp[-1] + palm_w[f])
    pal = list(reversed(FINGERS_ORDER))                  # palm half: I M R L, from the fold
    for i, f in enumerate(pal):
        x0 = xp[i] + GLOVE_SLIT
        x1 = xp[i + 1] - (GLOVE_SLIT if i < 3 else 0)
        t0, t1, _ = tip_edge(x0, x1, tip[f], f"p_{f}_t0", f"p_{f}_t1")
        o += t0 + [t1]
        if f != "L":
            nxt = pal[i + 1]
            o.append({"name": f"p_{f}{nxt}", "p": [xp[i + 1], crotch_p[(f, nxt)]]})
    o.append({"name": "side_p", "p": [W, y_side]})
    o.append({"name": "cuff_p", "p": [W + flare, y_end]})

    # ---- thumb hole and Bolton thumb: a digitised shape, data/shapes/bolton-thumb.json (its provenance is there),
    # scaled to the hand. Hole: along the fold, top about 40 mm under the finger bases, round bottom, a V flap at
    # the top freed by a curved slit that runs from the top corner away from the fold up to a dot. Thumb: wide oval
    # with two lobes at the top and a cleft on the fold axis; folded, the lobes sewn together make the tip; a slit
    # from the side edge to a dot takes the flap; two notches on the other side bound the part sewn to the flap.
    shape = library.load("shape", "bolton-thumb")
    sc = G / float(shape["reference"]["G"])
    TLh = (Wb + 2 * sc, crotch_p[("I", "M")] - 40 * sc)
    hp = lambda q: [TLh[0] + q[0] * sc, TLh[1] - q[1] * sc]           # shape file: mm, y down from the hole's top left
    hole = [dict({"name": n["name"], "p": hp(n["p"])}, **({"c": [hp(c) for c in n["c"]]} if "c" in n else {}))
            for n in shape["outlines"]["hole"]["nodes"]]
    hole_piece = {"outline": hole}
    hl = {n["name"]: length(edge(hole_piece, i, 200)) for i, n in enumerate(hole)}   # edge length from each node
    ease = 1.03                                          # thumb edges 3 % longer than the hole edges they meet
    seg_targets = [hl["h_TR2"] * ease, hl["h_V"] * ease, hl["h_TL"] * ease, hl["h_B"] * ease, hl["h_RM"] * ease]
    slit_target = hl["h_TR"] * ease

    # thumb outline of the shape file (unit = thumb height, x from the fold axis, y down from the top of the lobes)
    T = {q["name"]: tuple(q["p"]) for q in shape["outlines"]["thumb"]["points"]}
    order = [q["name"] for q in shape["outlines"]["thumb"]["points"]] + ["C"]
    pts_ = [T[k] for k in order]

    def catmull(pts, n=40):
        out = []
        ext = [pts[0]] + pts + [pts[-1]]                 # open spline: sharp corner at the cleft C
        for i in range(1, len(ext) - 2):
            p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
            for j in range(n):
                t = j / n
                t2, t3 = t * t, t * t * t
                out.append(tuple(0.5 * ((2 * p1[q]) + (-p0[q] + p2[q]) * t + (2 * p0[q] - 5 * p1[q] + 4 * p2[q] - p3[q]) * t2
                                        + (-p0[q] + 3 * p1[q] - 3 * p2[q] + p3[q]) * t3) for q in (0, 1)))
        out.append(pts[-1])
        return out

    dense = catmull(pts_)
    knot = {k: order.index(k) * 40 for k in ("C", "LL", "N1", "Ps", "RL")}
    knot["C_end"] = (len(order) - 1) * 40
    cum = [0.0]
    for p0, p1 in zip(dense, dense[1:]):
        cum.append(cum[-1] + dist(p0, p1))
    unit_base = cum[knot["Ps"]] - cum[knot["N1"]]
    ksc = sum(seg_targets) / unit_base                   # mm per template unit
    D = [(x * ksc, -y * ksc) for x, y in dense]          # thumb in mm, y up (lobes at the top)
    cumD = [c * ksc for c in cum]

    def at_len(L):                                       # index in the dense outline at arc length L
        return min(range(len(cumD)), key=lambda i: abs(cumD[i] - L))

    nodes_i = {"t_C": 0, "t_LL": knot["LL"], "t_N1": knot["N1"]}
    run = cumD[knot["N1"]]
    for name, L in zip(("t_Nv", "t_N2", "t_B", "t_RM"), seg_targets[:4]):
        run += L
        nodes_i[name] = at_len(run)
    nodes_i["t_Ps"] = knot["Ps"]
    # upper lip of the thumb slit: placed so both sides of the tip seam have the same length
    nodes_i["t_Ps2"] = max(knot["Ps"] + 1, at_len(cumD[knot["RL"]] - (cumD[knot["N1"]] - cumD[knot["LL"]])))
    nodes_i["t_RL"] = knot["RL"]

    def tangent(i):
        a, b = D[max(i - 1, 0)], D[min(i + 1, len(D) - 1)]
        l = dist(a, b) or 1
        return ((b[0] - a[0]) / l, (b[1] - a[1]) / l)

    def fit_seg(i0, i1):
        L = cumD[i1] - cumD[i0]
        p0, p3 = D[i0], D[i1]
        t0, t3 = tangent(i0 + 1 if i0 == 0 else i0), tangent(i1 - 1 if i1 == len(D) - 1 else i1)
        lo_, hi_ = 0.05, L
        for _ in range(60):
            k = (lo_ + hi_) / 2
            ln = _bez_len(p0, (p0[0] + t0[0] * k, p0[1] + t0[1] * k), (p3[0] - t3[0] * k, p3[1] - t3[1] * k), p3)
            lo_, hi_ = (k, hi_) if ln < L else (lo_, k)
        k = (lo_ + hi_) / 2
        return [[p0[0] + t0[0] * k, p0[1] + t0[1] * k], [p3[0] - t3[0] * k, p3[1] - t3[1] * k]]

    seq = ["t_C", "t_LL", "t_N1", "t_Nv", "t_N2", "t_B", "t_RM", "t_Ps"]
    th_o = []
    for a, b in zip(seq, seq[1:]):
        th_o.append({"name": a, "p": list(D[nodes_i[a]]), "c": fit_seg(nodes_i[a], nodes_i[b])})
    # thumb slit: from the lower lip at Ps inward to the dot, back to the upper lip
    Ps, Ps2 = D[nodes_i["t_Ps"]], D[nodes_i["t_Ps2"]]
    dot = shape["marks"]["dot"]["p"]
    dtpl = (dot[0] * ksc, -dot[1] * ksc)                 # dot of the template
    # end of the thumb slit: both lips match the trank slit lips (circles round Ps and Ps2), on the dot's side
    r1, r2 = slit_target, hl["h_D"] * ease
    dd = dist(Ps, Ps2)
    a_ = (r1 ** 2 - r2 ** 2 + dd ** 2) / (2 * dd)
    hh = math.sqrt(max(r1 ** 2 - a_ ** 2, 0.0))
    ux, uy = (Ps2[0] - Ps[0]) / dd, (Ps2[1] - Ps[1]) / dd
    cands = [(Ps[0] + ux * a_ - uy * hh * sg, Ps[1] + uy * a_ + ux * hh * sg) for sg in (1, -1)]
    Dt = min(cands, key=lambda q: dist(q, dtpl))
    th_o.append({"name": "t_Ps", "p": list(Ps)})
    th_o.append({"name": "t_D", "p": list(Dt)})
    th_o.append({"name": "t_Ps2", "p": list(Ps2), "c": fit_seg(nodes_i["t_Ps2"], nodes_i["t_RL"])})
    th_o.append({"name": "t_RL", "p": list(D[nodes_i["t_RL"]]), "c": fit_seg(nodes_i["t_RL"], knot["C_end"])})
    tip_pair = (cumD[knot["LL"]] - cumD[0], cumD[knot["C_end"]] - cumD[knot["RL"]],
                cumD[knot["N1"]] - cumD[knot["LL"]], cumD[knot["RL"]] - cumD[nodes_i["t_Ps2"]])
    drop_len = sum(hl[k] for k in ("h_TR2", "h_V", "h_TL", "h_B", "h_RM"))
    e_A = e_R = 0.0
    thumb_base_len = cumD[knot["Ps"]] - cumD[knot["N1"]]

    # ---- fourchette arms: one per finger side, back edge 5 mm longer than the palm edge
    edges_len = {}
    tr = {"outline": o}

    def elen(n1, n2):
        names = [x["name"] for x in o]
        i, j = names.index(n1), names.index(n2)
        k = i if (i + 1) % len(o) == j else j
        return length(edge(tr, k, 100))

    arms, seams = [], []
    fw_b, fw_t = 1.3 * fw, 0.6 * fw
    for a_, b_ in (("I", "M"), ("M", "R"), ("R", "L")):   # (thumb side finger, little side finger)
        for side, f in ((a_, a_), (b_, b_)):
            if side == a_:                                # the thumb-side finger's little side
                bb, bt, pb, pt = f"b_{a_}{b_}", f"b_{a_}_t0", f"p_{a_}{b_}", f"p_{a_}_t1"
            else:                                         # the little-side finger's thumb side
                bb, bt, pb, pt = f"b_{a_}{b_}", f"b_{b_}_t1", f"p_{a_}{b_}", f"p_{b_}_t0"
            Lb_, Lp_ = elen(bb, bt), elen(pb, pt)
            dx = (fw_b - fw_t) / 2
            name = f"Fourchette {f} ({a_}{b_})"
            arms.append({"name": name, "cut": "1x", "allowance": 0.15, "outline": [
                {"name": "base_b", "p": [0.0, 0.0]}, {"name": "tip_b", "p": [dx, Lb_]},
                {"name": "tip_p", "p": [dx + fw_t, Lb_]},
                {"name": "base_p", "p": [fw_b, Lb_ - math.sqrt(max(Lp_ ** 2 - (fw_b - dx - fw_t) ** 2, 1))]}]})
            seams.append(["Trank", bb, bt, name, "base_b", "tip_b"])
            seams.append(["Trank", pb, pt, name, "base_p", "tip_p"])
            edges_len[name] = (Lb_, Lp_)
        seams.append([f"Fourchette {a_} ({a_}{b_})", "base_b", "base_p", f"Fourchette {b_} ({a_}{b_})", "base_b", "base_p"])
    seams.append(["Trank", "b_I_t1", "C0", "Trank", "p_I_t0", "C0"])          # index outer seam
    for f in "IMRL":
        seams.append(["Trank", f"b_{f}_t0", f"b_{f}_t1", "Trank", f"p_{f}_t1", f"p_{f}_t0",
                      {"ease": back_w[f] / palm_w[f] - 1, "why": "back finger wider than the palm (W/2 + 4 / W/2 - 4)"}])
    seams.append(["Trank", "side_b", "b_L_t0", "Trank", "side_p", "p_L_t1"])   # little finger outer side
    seams.append(["Trank", "cuff_b", "side_b", "Trank", "cuff_p", "side_p"])   # side seam
    # CLO3D opening of the hole: slit from the nearest outline node (see slit_holes), sewn back together
    near = min(((dist(n["p"], hn["p"]), n["name"], hn["name"]) for n in o for hn in hole))
    seams.append(["Trank", near[1], near[2], "Trank", near[1] + "~", near[2] + "~"])
    seams += [["Thumb", "t_C", "t_LL", "Thumb", "t_C", "t_RL"],          # tip: the two lobes sewn together
              ["Thumb", "t_LL", "t_N1", "Thumb", "t_RL", "t_Ps2"],
              ["Thumb", "t_N1", "t_Nv", "Trank", "h_TR2", "h_V", {"ease": ease - 1, "why": "thumb eased into the hole"}],          # between the notches: the flap edges
              ["Thumb", "t_Nv", "t_N2", "Trank", "h_V", "h_TL", {"ease": ease - 1, "why": "thumb eased into the hole"}],
              ["Thumb", "t_N2", "t_B", "Trank", "h_TL", "h_B", {"ease": ease - 1, "why": "thumb eased into the hole"}],            # round the hole, notch B to notch B
              ["Thumb", "t_B", "t_RM", "Trank", "h_B", "h_RM", {"ease": ease - 1, "why": "thumb eased into the hole"}],
              ["Thumb", "t_RM", "t_Ps", "Trank", "h_RM", "h_TR", {"ease": ease - 1, "why": "thumb eased into the hole"}],
              ["Thumb", "t_Ps", "t_D", "Trank", "h_TR", "h_D", {"ease": ease - 1, "why": "thumb eased into the hole"}],            # thumb slit takes the flap
              ["Thumb", "t_D", "t_Ps2", "Trank", "h_D", "h_TR2", {"ease": ease - 1, "why": "thumb eased into the hole"}]]

    # ---- to cm, y down (skill axes), trank origin at the wrist line
    def conv(nodes, flip=True):
        out = []
        for n in nodes:
            q = dict(n)
            q["p"] = [n["p"][0] / 10, (-n["p"][1] if flip else n["p"][1]) / 10]
            if "c" in n:
                q["c"] = [[c[0] / 10, (-c[1] if flip else c[1]) / 10] for c in n["c"]]
            out.append(q)
        return out

    trank = {"name": "Trank", "cut": "1x", "allowance": 0.15, "outline": conv(o),
             "holes": [{"name": "thumb_hole", "outline": conv(hole)}],
             "grain": [[Wb / 20, -4.0], [Wb / 20, -(y_end + 40) / 10]]}   # y down: from the hand towards the cuff
    thumb_p = {"name": "Thumb", "cut": "1x", "allowance": 0.15, "outline": conv(th_o)}   # lobes up, fold on the axis
    arms = [dict(a, outline=conv(a["outline"], flip=False)) for a in arms]
    ref = area(outline({"outline": [{"p": [0, 0]}, {"p": [1, 0]}, {"p": [1, 1]}, {"p": [0, 1]}]}))
    for p in [trank, thumb_p] + arms:                   # same winding as every other piece of the engine
        if area(outline(p)) * ref < 0:
            p["outline"] = _reversed_nodes(p["outline"])
    hole_p = {"outline": conv(hole)}
    checks = [check("Glove: back finger widths = back half (mm)", sum(back_w.values()), Wb, 0.5),
              check("Glove: palm finger widths = palm half (mm)", sum(palm_w.values()), Wp, 0.5),
              check("Glove: thumb edges round the hole = hole edges + 3 % (mm)", thumb_base_len, drop_len * ease, 0.5),
              check("Glove: thumb tip seam, lobe edges differ by (mm)", abs(tip_pair[0] - tip_pair[1]), 0.0, 4.0),
              check("Glove: thumb tip seam, side edges differ by (mm)", abs(tip_pair[2] - tip_pair[3]), 0.0, 6.0),
              check("Glove: fourchette width at mid-finger (info, mm)", fw),
              check("Glove: thumb hole perimeter (info, mm)", 10 * length(outline(hole_p)))]
    return {"pieces": [trank, thumb_p] + arms, "checks": checks, "seams": seams}


def _reversed_nodes(nodes):
    """Same closed path run backwards, Bezier controls swapped onto the new start nodes."""
    n = len(nodes)
    out = [{k: v for k, v in nodes[i].items() if k != "c"} for i in range(n - 1, -1, -1)]
    for j in range(n):
        src = nodes[(n - 2 - j) % n]                      # edge out[j] -> out[j+1] is src -> nodes[src+1] reversed
        if "c" in src:
            out[j]["c"] = [src["c"][1], src["c"][0]]
    return out


def mirror_piece(p, name):
    """Left/right mirror (x -> -x) keeping the winding and node names, holes included."""
    def mir(nodes):
        q = [dict(n, p=[-n["p"][0], n["p"][1]], **({"c": [[-c[0], c[1]] for c in n["c"]]} if "c" in n else {}))
             for n in nodes]
        return _reversed_nodes(q)
    out = dict(p, name=name, outline=mir(p["outline"]))
    if p.get("holes"):
        out["holes"] = [dict(hl, outline=mir(hl["outline"])) for hl in p["holes"]]
    if p.get("grain"):
        out["grain"] = [[-g[0], g[1]] for g in p["grain"]]
    if p.get("lines"):
        out["lines"] = [[[-q[0], q[1]] for q in ln] for ln in p["lines"]]
    return out


def slit_holes(piece, gap=0.15):
    """CLO3D cannot cut a hole through its API: open each hole to the nearest outline node through a slit
    `gap` cm wide. The slit edges are sewn back together (seam C0 -> h_A / C0~ -> h_A~ style); the second copy
    of each split node is named with a trailing '~'."""
    if not piece.get("holes"):
        return piece
    q = {k: v for k, v in piece.items() if k != "holes"}
    o = [dict(n) for n in piece["outline"]]
    for hl in piece["holes"]:
        hn = [dict(n) for n in hl["outline"]]
        if area(outline({"outline": hn})) * area(outline({"outline": o})) > 0:
            hn = _reversed_nodes(hn)                     # a hole runs against the outline
        best = min(((dist(a["p"], b["p"]), i, j) for i, a in enumerate(o) for j, b in enumerate(hn)))
        _, i, j = best
        a, b = o[i]["p"], hn[j]["p"]
        ux, uy = (b[0] - a[0]) / best[0], (b[1] - a[1]) / best[0]
        nx, ny = -uy * gap / 2, ux * gap / 2
        ring = hn[j:] + hn[:j]
        first = dict(ring[0], p=[b[0] + nx, b[1] + ny])
        last = {k: v for k, v in ring[0].items() if k != "c"}
        last.update(name=ring[0].get("name", "h") + "~", p=[b[0] - nx, b[1] - ny])
        o_in = {k: v for k, v in o[i].items() if k != "c"}
        o_in["p"] = [a[0] + nx, a[1] + ny]
        o_out = dict(o[i], name=o[i].get("name", "n") + "~", p=[a[0] - nx, a[1] - ny])
        o = o[:i] + [o_in, first] + ring[1:] + [last, o_out] + o[i + 1:]
    q["outline"] = o
    return q


BLOCKS = ("skirt", "bodice", "sleeve", "trousers")


def build(block, m, a, body, knit=False, circle=None):
    res = {"pieces": [], "checks": []}
    wanted = BLOCKS if block == "all" else (block,)
    bodice = block_bodice(m, a, body, knit) if ("bodice" in wanted or "sleeve" in wanted) else None
    for b in wanted:
        r = {"skirt": lambda: block_skirt(m, a, body), "bodice": lambda: bodice,
             "sleeve": lambda: block_sleeve(m, a, body, bodice), "trousers": lambda: block_trousers(m, a, body),
             "circle_skirt": lambda: block_circle_skirt(m, a, **(circle or {}))}[b]()
        res["pieces"] += r["pieces"]
        res["checks"] += r["checks"]
        res.setdefault("seams", []).extend(r.get("seams", []))
        if r.get("knots"):
            res.setdefault("knots", {}).update(r["knots"])
    return res

# ------------------------------------------------------------------ export


def layout(pieces_per_size, width=1500):
    """Place each piece (same rank for every size) on rows of `width` mm at most (1.5 m, a fabric width)."""
    boxes = []
    for i in range(len(pieces_per_size[0])):
        pts = [q for ps in pieces_per_size for q in cut_line(ps[i])]
        boxes.append((min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)))
    offs, x, y, h, wid = [], 10.0, 15.0, 0.0, 0.0
    for b in boxes:
        w, hh = (b[2] - b[0]) * 10, (b[3] - b[1]) * 10
        if x > 10 and x + w > width:
            x, y, h = 10.0, y + h + 20, 0.0
        offs.append((x - b[0] * 10, y - b[1] * 10))
        x += w + 20
        h, wid = max(h, hh), max(wid, x)
    return offs, wid, y + h + 10


def mm(p, o):
    return (p[0] * 10 + o[0], p[1] * 10 + o[1])


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def center(p, off):
    net = outline(p)
    return mm((sum(q[0] for q in net) / len(net), sum(q[1] for q in net) / len(net)), off)


COLORS = ["#000000", "#d62728", "#1f77b4", "#2ca02c", "#9467bd", "#ff7f0e", "#8c564b", "#17becf"]


def write_svg(sets, path, title):
    offs, W, H = layout([r["pieces"] for _, r in sets])
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}mm" height="{H + 120:.0f}mm" '
         f'viewBox="0 -120 {W:.1f} {H + 120:.1f}" font-family="sans-serif">',
         '<rect x="0" y="-120" width="100%" height="100%" fill="#fff"/>',
         '<rect x="10" y="-110" width="100" height="100" fill="none" stroke="#000" stroke-width="0.5"/>',
         '<text x="14" y="-100" font-size="5">Test square 10 x 10 cm</text>',
         f'<text x="125" y="-95" font-size="9">{esc(title)}</text>']
    if len(sets) > 1:
        o.append('<text x="125" y="-80" font-size="6">' + " ".join(
            f'<tspan fill="{COLORS[i % 8]}">S{esc(sz)}</tspan>' for i, (sz, _) in enumerate(sets)) + '</text>')
    pts_txt = lambda pts, off: " ".join(f"{x:.1f},{y:.1f}" for x, y in (mm(p, off) for p in pts))
    for i, off in enumerate(offs):
        for j, (sz, r) in enumerate(sets):
            p, col = r["pieces"][i], COLORS[j % 8]
            if j == 0:
                o.append(f'<polygon points="{pts_txt(cut_line(p), off)}" fill="none" stroke="#000" stroke-width="0.6"/>')
            o.append(f'<polygon points="{pts_txt(outline(p), off)}" fill="none" stroke="{col}" stroke-width="0.3"'
                     + (' stroke-dasharray="3 1.5"/>' if j == 0 else '/>'))
            if j:
                continue
            for hl in p.get("holes", []):
                o.append(f'<polygon points="{pts_txt(outline(hl), off)}" fill="none" stroke="#000" stroke-width="0.6"/>')
            for e in p.get("fold", []):
                o.append(f'<polyline points="{pts_txt(edge(p, e), off)}" fill="none" stroke="#000" '
                         'stroke-width="1" stroke-dasharray="8 2 2 2"/>')
            for a, b in notches(p):
                (x1, y1), (x2, y2) = mm(a, off), mm(b, off)
                o.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#000" stroke-width="0.6"/>')
            if p.get("grain"):
                (x1, y1), (x2, y2) = mm(p["grain"][0], off), mm(p["grain"][1], off)
                o.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#000" stroke-width="0.4"/>')
                for (xa, ya), (xb, yb) in (((x1, y1), (x2, y2)), ((x2, y2), (x1, y1))):
                    l = math.hypot(xb - xa, yb - ya) or 1
                    ux, uy = (xb - xa) / l, (yb - ya) / l
                    for s in (1, -1):
                        o.append(f'<line x1="{xa:.1f}" y1="{ya:.1f}" x2="{xa + ux * 8 - s * uy * 3:.1f}" '
                                 f'y2="{ya + uy * 8 + s * ux * 3:.1f}" stroke="#000" stroke-width="0.4"/>')
            cx, cy = center(p, off)
            for k, txt in enumerate([p["name"], f"Size {sz}", p.get("cut", "")]):
                o.append(f'<text x="{cx:.1f}" y="{cy + k * 9:.1f}" font-size="7" text-anchor="middle">{esc(txt)}</text>')
    o.append("</svg>")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(o))


def write_dxf(pieces, offs, path, size):
    L = ["0", "SECTION", "2", "HEADER", "9", "$ACADVER", "1", "AC1009", "0", "ENDSEC", "0", "SECTION", "2", "ENTITIES"]

    def line(a, b, layer):
        L.extend(["0", "LINE", "8", layer, "10", f"{a[0]:.3f}", "20", f"{-a[1]:.3f}", "30", "0",
                  "11", f"{b[0]:.3f}", "21", f"{-b[1]:.3f}", "31", "0"])

    def closed(pts, off, layer):
        q = [mm(p, off) for p in pts]
        for a, b in zip(q, q[1:] + q[:1]):
            line(a, b, layer)

    for p, off in zip(pieces, offs):
        closed(cut_line(p), off, "CUT")
        closed(outline(p), off, "SEAM")
        for hl in p.get("holes", []):
            closed(outline(hl), off, "CUT")
            closed(outline(hl), off, "SEAM")
        for a, b in notches(p):
            line(mm(a, off), mm(b, off), "NOTCHES")
        if p.get("grain"):
            line(mm(p["grain"][0], off), mm(p["grain"][1], off), "GRAIN")
        cx, cy = center(p, off)
        for k, txt in enumerate([p["name"], f"Size {size}", p.get("cut", "")]):
            L.extend(["0", "TEXT", "8", "TEXT", "10", f"{cx:.1f}", "20", f"{-(cy + k * 9):.1f}", "30", "0",
                      "40", "6", "1", txt])
    L.extend(["0", "ENDSEC", "0", "EOF"])
    with open(path, "w", encoding="ascii", errors="replace", newline="\r\n") as f:
        f.write("\n".join(L) + "\n")


def clo3d_points(piece, off):
    """Nodes as straight points (type 0) and Bezier controls as type 3: each pattern edge becomes
    exactly one CLO3D line, numbered like the edges (verified live on CLO3D 2025.2)."""
    pts = []
    for n in piece["outline"]:
        x, y = mm(n["p"], off)
        pts.append([round(x, 2), round(-y, 2), 0])
        for c in n.get("c", []):
            cx, cy = mm(c, off)
            pts.append([round(cx, 2), round(-cy, 2), 3])
    return pts


def write_clo3d(pieces, offs, path, size, seams=None, holds=None):
    """Net outline (CLO3D adds its own allowances), fold pieces unfolded, y upwards, in mm.
    Each piece keeps its edge names: CLO3D line i is edge i of the `edges` list."""
    out = {"unit": "mm", "size": str(size), "pieces": []}
    shells = [slit_holes(unfold(p)) for p in pieces]
    offs, _, _ = layout([shells], 2800)      # laid out unfolded (the half pieces would overlap once unfolded)
    xs = [x for q, off in zip(shells, offs) for x, _ in (mm(n["p"], off) for n in q["outline"])]
    ys = [y for q, off in zip(shells, offs) for _, y in (mm(n["p"], off) for n in q["outline"])]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2   # centred on the 2D origin: CLO3D places a new
    offs = [(o[0] - cx, o[1] - cy) for o in offs]                 # piece in 3D from its 2D position
    for p, q, off in zip(pieces, shells, offs):
        rec = {"name": p["name"], "cut": q.get("cut", ""), "points": clo3d_points(q, off),
               "edges": [{"line": i, "from": n.get("name", ""), "length_mm": round(length(edge(q, i)) * 10, 1)}
                         for i, n in enumerate(q["outline"])]}
        for k in ("fabric", "particle_distance", "layer", "arrange"):   # read by build_garment (clo3d-mcp-extended)
            if p.get(k) is not None:
                rec[k] = p[k]
        if q.get("lines"):                   # internal lines (roll line, pocket opening), drawn in CLO3D
            rec["internals"] = [[[round(x, 2), round(-y, 2)] for x, y in (mm(pt, off) for pt in ln)] for ln in q["lines"]]
        out["pieces"].append(rec)
    if seams:
        out["seams"] = seams                 # [piece A, a1, a2, piece B, b1, b2, {"ease": r, "why": ...}]: a1 to b1
    if holds:                                # overlapping fronts: top edge sewn onto an internal line of the under piece
        off_by = {p["name"]: o for p, o in zip(pieces, offs)}
        out["holds"] = [dict(h, at={k: [round(v[0] * 10 + off_by[h["under"]][0], 2), round(-(v[1] * 10 + off_by[h["under"]][1]), 2)]
                                    for k, v in h["at"].items()}) for h in holds]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    return out


# ------------------------------------------------------------------ universal validation
# Applied to every export, whatever the garment. Seams follow the law of reciprocal lengths: two edges sewn
# together have the same length within 1 mm, unless an ease is declared on the seam with its reason
# (e.g. sleeve cap ease, back finger tips wider than the palm). Pieces cut on the fold meet the fold at a
# right angle. Outlines never cross themselves.

SEAM_TOL_MM = 1.0


def seam_ease(s_):
    extra = s_[6] if len(s_) > 6 and isinstance(s_[6], dict) else {}
    return float(extra.get("ease", 0.0)), extra.get("why", "")


def seam_table(cloj, seams):
    """Rows (piece A, edge A, mm, piece B, edge B, mm, ease, why, ok) for every seam, read on the pieces as
    sent to CLO3D (unfolded, holes opened)."""
    pcs = {p["name"]: p for p in cloj["pieces"]}
    rows = []
    for s_ in seams or []:
        if s_[0] not in pcs or s_[3] not in pcs:
            rows.append((s_[0], f"{s_[1]}-{s_[2]}", None, s_[3], f"{s_[4]}-{s_[5]}", None, 0, "piece missing", False))
            continue
        try:
            (la, _), (lb, _) = _clo_edge(pcs[s_[0]], s_[1], s_[2]), _clo_edge(pcs[s_[3]], s_[4], s_[5])
        except SystemExit as err:
            rows.append((s_[0], f"{s_[1]}-{s_[2]}", None, s_[3], f"{s_[4]}-{s_[5]}", None, 0, str(err), False))
            continue
        a_mm, b_mm = pcs[s_[0]]["edges"][la]["length_mm"], pcs[s_[3]]["edges"][lb]["length_mm"]
        ease, why = seam_ease(s_)
        ok = abs(a_mm - b_mm * (1 + ease)) <= SEAM_TOL_MM
        rows.append((s_[0], f"{s_[1]}-{s_[2]}", a_mm, s_[3], f"{s_[4]}-{s_[5]}", b_mm, ease, why, ok))
    return rows


def write_seam_table(rows, path):
    lines = ["| Piece A | Edge A | mm | Piece B | Edge B | mm | Ease | Why | Status |", "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        ea = "" if not r[6] else f"{r[6] * 100:+.1f} %"
        lines.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} | {ea} | {r[7]} | {'OK' if r[8] else '!!'} |")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def _tangent_end(piece, i, at_start):
    pts = edge(piece, i, 64)
    a, b = (pts[0], pts[1]) if at_start else (pts[-2], pts[-1])
    l = dist(a, b) or 1
    return ((b[0] - a[0]) / l, (b[1] - a[1]) / l)


def fold_checks(piece):
    """Right angle where the outline meets a fold edge (the unfolded piece has no point or dip there)."""
    out, n = [], len(piece["outline"])
    for k in piece.get("fold", []):
        f = _tangent_end(piece, k, True)
        for node, t in ((k, _tangent_end(piece, (k - 1) % n, False)), ((k + 1) % n, _tangent_end(piece, (k + 1) % n, True))):
            ang = math.degrees(math.acos(min(1.0, abs(f[0] * t[0] + f[1] * t[1]))))
            name = piece["outline"][node].get("name", node)
            out.append(check(f"{piece['name']}: right angle at the fold, {name} (deg)", ang, 90.0, 2.0))
    return out


def crossing_check(piece):
    pts = outline(piece, 10)
    segs = list(zip(pts, pts[1:] + pts[:1]))
    for i in range(len(segs)):
        for j in range(i + 2, len(segs) - (1 if i == 0 else 0)):
            (a, b), (c, d) = segs[i], segs[j]
            den = (b[0] - a[0]) * (d[1] - c[1]) - (b[1] - a[1]) * (d[0] - c[0])
            if abs(den) < 1e-12:
                continue
            t = ((c[0] - a[0]) * (d[1] - c[1]) - (c[1] - a[1]) * (d[0] - c[0])) / den
            u = ((c[0] - a[0]) * (b[1] - a[1]) - (c[1] - a[1]) * (b[0] - a[0])) / den
            if 0 < t < 1 and 0 < u < 1:
                return check(f"{piece['name']}: outline crosses itself (count)", 1, 0, 0)
    return None


MIN_NECK_CM, MIN_SIDE_AREA = 4.0, 40.0     # narrowest passage allowed between two wide parts of a piece
WITHIN_TOL_CM = 0.6                        # a facing may pass its piece by the turn of cloth only


def resample(pts, step=1.0):
    """Closed polyline resampled every `step` cm."""
    out, carry = [], 0.0
    for a, b in zip(pts, pts[1:] + pts[:1]):
        l = dist(a, b)
        t = carry
        while t < l:
            out.append((a[0] + (b[0] - a[0]) * t / l, a[1] + (b[1] - a[1]) * t / l))
            t += step
        carry = t - l
    return out


def inside_polygon(q, poly):
    c = False
    for a, b in zip(poly, poly[1:] + poly[:1]):
        if (a[1] > q[1]) != (b[1] > q[1]) and q[0] < (b[0] - a[0]) * (q[1] - a[1]) / (b[1] - a[1]) + a[0]:
            c = not c
    return c


def seg_dist(q, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    l2 = dx * dx + dy * dy
    t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((q[0] - a[0]) * dx + (q[1] - a[1]) * dy) / l2))
    return dist(q, (a[0] + dx * t, a[1] + dy * t))


def neck_check(piece):
    """A piece pinched between two wide parts (a lining strip left between a facing and a seam) cannot be sewn
    or worn. Flags any chord narrower than MIN_NECK_CM that splits the piece into two parts both larger than
    MIN_SIDE_AREA. Narrow strips (bindings, flies, fourchettes) and narrow protrusions (fingers) pass."""
    closed = dict(piece, outline=[q for q in piece["outline"] if not q.get("dart")])   # darts are sewn closed
    pts = resample(outline(closed, 16))
    n = len(pts)
    if n < 8:
        return None
    arc = [i * 1.0 for i in range(n)]
    per = float(n)
    worst = None
    for i in range(n):
        for j in range(i + 2, n):
            d = dist(pts[i], pts[j])
            if d >= MIN_NECK_CM or (worst is not None and d >= worst):
                continue
            a1 = arc[j] - arc[i]
            if min(a1, per - a1) < 3 * max(d, 1.0):
                continue
            mid = ((pts[i][0] + pts[j][0]) / 2, (pts[i][1] + pts[j][1]) / 2)
            if not inside_polygon(mid, pts):
                continue
            if min(abs(area(pts[i:j + 1])), abs(area(pts[j:] + pts[:i + 1]))) > MIN_SIDE_AREA:
                worst = d
    if worst is None:
        return None
    return check(f"{piece['name']}: narrowest passage between two wide parts (cm)", worst, MIN_NECK_CM,
                 round(MIN_NECK_CM - worst - 0.01, 2))


def within_checks(pieces):
    """Pieces declaring "within": "<piece>" (facings, interfacings, pocket facings) must lie inside that piece, up
    to the turn of cloth. Linings are larger than their piece by design (underarm, side ease) and do not declare it."""
    by = {p["name"]: p for p in pieces}
    out = []
    for p in pieces:
        w = p.get("within")
        if not w:
            continue
        suffix = p["name"][-2:] if p["name"][-2:] in (" L", " R") else ""
        parent = by.get(w + suffix) or by.get(w)
        if parent is None:
            out.append(check(f"{p['name']}: piece '{w}' it should lie within is missing", 1, 0, 0))
            continue
        poly = outline(parent, 24)
        segs = list(zip(poly, poly[1:] + poly[:1]))
        worst = 0.0
        for q in resample(outline(p, 24)):
            if not inside_polygon(q, poly):
                worst = max(worst, min(seg_dist(q, a, b) for a, b in segs))
        out.append(check(f"{p['name']}: lies within {parent['name']} (cm outside)", worst, 0, WITHIN_TOL_CM))
    return out


def expand_mirrors(pieces, seams):
    """Pieces with "mirror": true become "<name> L" and its mirror "<name> R"; seams naming "{side}" are
    written once per side."""
    out = []
    opp = {"L": "R", "R": "L"}
    for p in pieces:
        if p.get("mirror"):
            base = {k: v for k, v in p.items() if k not in ("mirror", "wearer")}
            for suffix, q in (("L", dict(base, name=p["name"] + " L")), ("R", mirror_piece(base, p["name"] + " R"))):
                if "{side}" in str(q.get("arrange", {}).get("name", "")):
                    # the original half is the wearer's left (x towards the side), except for back pieces
                    w = suffix if p.get("wearer", "left") != "right" else opp[suffix]
                    q["arrange"] = dict(q["arrange"], name=q["arrange"]["name"].replace("{side}", w))
                out.append(q)
        else:
            out.append({k: v for k, v in p.items() if k != "wearer"})
    exp = []
    for s_ in seams or []:
        if any("{side}" in str(x) for x in s_[:6]):
            for side in ("L", "R"):
                exp.append([x.replace("{side}", side) if isinstance(x, str) else x for x in s_])
        else:
            exp.append(s_)
    return out, exp


def write_clo_script(json_path, py_path):
    """Standalone script to run inside CLO3D (Script Editor > Run): creates the pieces, no plugin needed."""
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    pieces = [(p["name"], [tuple(q) for q in p["points"]]) for p in data["pieces"]]
    with open(py_path, "w", encoding="utf-8") as f:
        f.write("# Generated by pattern.py. In CLO3D: Script > Script Editor, open this file, Run.\n"
                "import pattern_api\n\n"
                f"PIECES = {pieces!r}\n\n"
                "n0 = pattern_api.GetPatternCount()\n"
                "for i, (name, points) in enumerate(PIECES):\n"
                "    pattern_api.CreatePatternWithPoints(points)\n"
                "    pattern_api.SetPatternPieceName(n0 + i, name)\n"
                "    print('Pattern created:', name)\n")


def rounded(o):
    if isinstance(o, float):
        return round(o, 3)
    if isinstance(o, list):
        return [rounded(x) for x in o]
    if isinstance(o, dict):
        return {k: rounded(v) for k, v in o.items()}
    return o


def export(sets, out, title, allowance=None):
    os.makedirs(out, exist_ok=True)
    for _, r in sets:
        r["pieces"], r["seams"] = expand_mirrors(r["pieces"], r.get("seams"))
    if allowance is not None:
        for _, r in sets:
            for p in r["pieces"]:
                p["allowance"] = allowance
    write_svg(sets, os.path.join(out, "pattern.svg"), title)
    offs, _, _ = layout([r["pieces"] for _, r in sets])
    for sz, r in sets:
        write_dxf(r["pieces"], offs, os.path.join(out, f"pattern_{sz}.dxf"), sz)
        cloj = write_clo3d(r["pieces"], None, os.path.join(out, f"clo3d_{sz}.json"), sz, r.get("seams"), r.get("holds"))
        checks = r.setdefault("checks", [])
        for p in r["pieces"]:
            checks += fold_checks(p)
            for c in (crossing_check(p), neck_check(p)):
                if c:
                    checks.append(c)
        checks += within_checks(r["pieces"])
        if r.get("seams"):
            rows = seam_table(cloj, r["seams"])
            write_seam_table(rows, os.path.join(out, f"seams_{sz}.md"))
            bad = [x for x in rows if not x[8]]
            checks.append(check(f"Seams: lengths match within {SEAM_TOL_MM:.0f} mm or declared ease, "
                                f"{len(rows)} seams (failures)", len(bad), 0, 0))
            for x in bad[:12]:
                checks.append(check(f"  seam {x[0]} {x[1]} / {x[3]} {x[4]} (mm, {x[7] or 'no ease declared'})",
                                    x[2] if x[2] is not None else -1, (x[5] or 0) * (1 + x[6]), SEAM_TOL_MM))
        write_clo_script(os.path.join(out, f"clo3d_{sz}.json"), os.path.join(out, f"clo3d_{sz}.py"))
        with open(os.path.join(out, f"pieces_{sz}.json"), "w", encoding="utf-8") as f:
            json.dump(rounded({"title": title, "size": sz, "pieces": r["pieces"]}), f, ensure_ascii=False, indent=1)


def report(sets):
    ok = True
    for sz, r in sets:
        print(f"\n== Size {sz}")
        for c in r["checks"]:
            lab = c["label"]
            unit = ("mm" if "(mm" in lab or "mm)" in lab else "deg" if "(deg)" in lab
                    else "" if "(failures)" in lab or "(count)" in lab else "cm")
            label = (lab.replace(" (mm)", "").replace(", mm)", ")").replace(" (deg)", "")
                     .replace(" (failures)", ", failures").replace(" (count)", ""))
            if c["expected"] is None:
                print(f"   {label}: {c['value']} {unit}")
                continue
            good = abs(c["value"] - c["expected"]) <= c["tol"]
            ok &= good
            print(f" {'OK' if good else '!!'} {label}: {c['value']} {unit} (expected {c['expected']} ± {c['tol']})")
    return ok

# ------------------------------------------------------------------ direct send to CLO3D
# File protocol of the clo3d-mcp-extended plugin: write request.json, the plugin answers in response.json.
# Works without the MCP server, so from any agent able to run Python.


def clo3d_command(folder, type_, params, timeout=180):
    import time
    import uuid
    req, rep = os.path.join(folder, "request.json"), os.path.join(folder, "response.json")
    rid = str(uuid.uuid4())
    if os.path.exists(rep):
        os.remove(rep)
    with open(req + ".tmp", "w", encoding="utf-8") as f:
        json.dump({"id": rid, "type": type_, "params": params}, f)
    os.replace(req + ".tmp", req)
    t0 = time.time()
    while time.time() - t0 < timeout:
        if os.path.exists(rep):
            try:
                with open(rep, encoding="utf-8") as f:
                    r = json.load(f)
            except (ValueError, OSError):
                r = {}
            if r.get("id") == rid:
                os.remove(rep)
                if r.get("status") == "error":
                    raise SystemExit("CLO3D: " + str(r.get("message")))
                return r.get("result", {})
        time.sleep(0.05)
    raise SystemExit("No answer from CLO3D: is the plugin listening?")


def _clo_edge(piece, n1, n2):
    """Line index and direction of the edge n1-n2; names split by a hole slit may carry a trailing '~'."""
    e = piece["edges"]
    for a in (n1, n1 + "~"):
        for b in (n2, n2 + "~"):
            for i, x in enumerate(e):
                nxt = e[(i + 1) % len(e)]["from"]
                if (x["from"], nxt) == (a, b):
                    return i, True
                if (x["from"], nxt) == (b, a):
                    return i, False
    raise SystemExit(f"{piece['name']}: no edge {n1}-{n2}")


# ------------------------------------------------------------------ knowledge base
# references/kb/*.md: one entry per garment, piece or technique ("## Name {#id}", then bullet fields).
# The technique sheets (references/techniques/*.md) are searched by their headings too.

KB_DIRS = ("kb", "techniques")


def _kb_root():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "references")


def _fold_text(t):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFKD", t.lower()) if not unicodedata.combining(c))


def kb_entries():
    """List of entries: id, name, file, line, aliases, family, status, text. Knowledge-base entries are one file
    each (references/kb/<family>/<id>.md); the technique sheets are indexed by their headings."""
    out = []
    root = _kb_root()
    paths = []
    for sub in KB_DIRS:
        for base, dirs, names in os.walk(os.path.join(root, sub)):
            dirs.sort()
            paths += [os.path.join(base, n) for n in sorted(names) if n.endswith(".md") and n == n.lower()]
    for path in paths:
        rel = os.path.relpath(path, root).replace("\\", "/")
        entry_file = rel.startswith("kb/") and rel.count("/") == 2          # kb/<family>/<id>.md
        with open(path, encoding="utf-8") as f:
            lines = f.read().split("\n")
        cur = None
        for i, line in enumerate(lines):
            m = re.match(r"^(#{1,3})\s+(.*?)\s*(\{#([a-z0-9\-]+)\})?\s*$", line)
            if m and (len(m.group(1)) > 1 or (entry_file and m.group(4))):
                if cur:
                    out.append(cur)
                name, eid = m.group(2).strip(), m.group(4)
                if name.lower() == "sources":
                    cur = None
                    continue
                slug = re.sub(r"[^a-z0-9]+", "-", _fold_text(re.sub(r"^[A-Z]?[0-9.]+\s+", "", name))).strip("-")[:48]
                cur = {"id": eid or slug, "name": name, "file": rel, "line": i + 1, "aliases": "", "family": "",
                       "status": "", "text": [], "kb": eid is not None}
                continue
            if cur is not None:
                cur["text"].append(line)
                low = line.lower()
                for key in ("aliases", "family", "status"):
                    if low.startswith(f"- **{key}**"):
                        cur[key] = line.split(":", 1)[-1].strip()
        if cur:
            out.append(cur)
    return out


def kb_search(query, limit=15):
    words = [_fold_text(w) for w in query.split() if w.strip()]
    scored = []
    for e in kb_entries():
        head = _fold_text(f"{e['name']} {e['id']} {e['aliases']} {e['family']}")
        body = _fold_text(" ".join(e["text"]))
        score = 0
        for w in words:
            if w in head:
                score += 5
            elif w in body:
                score += 1
            else:
                score -= 3
        if score > 0:
            scored.append((score + (1 if e["kb"] else 0), e))
    scored.sort(key=lambda t: -t[0])
    return [e for _, e in scored[:limit]]


def cmd_kb(args):
    if args.action == "search":
        res = kb_search(" ".join(args.words))
        if not res:
            print("No entry found. Look up published patterns and books, then add an entry (references/kb/FORMAT.md, CONTRIBUTING.md).")
            return 1
        for e in res:
            print(f"{e['id']:<34} {e['name'][:48]:<48} {e['file']}:{e['line']}")
        return 0
    if args.action == "show":
        target = " ".join(args.words)
        e = next((x for x in kb_entries() if x["id"] == target), None) or next(iter(kb_search(target, 1)), None)
        if not e:
            raise SystemExit(f"No entry: {target}")
        print(f"## {e['name']}  (references/{e['file']})")
        print("\n".join(e["text"]).strip())
        return 0
    return library.cmd_check(argparse.Namespace(write=True))         # "kb index": regenerate the index and friends


def _views(d, folder, tag, views=((2, "front"), (4, "side"))):
    out = []
    for vi, nm in views:
        path = os.path.join(folder, f"{tag}_{nm}.png")
        clo3d_command(d, "set_camera_view", {"view_index": vi, "zoom_to_garment": False})
        clo3d_command(d, "export_view_image", {"view_index": vi, "output_path": path, "width": 600, "height": 900})
        out.append(path)
    return out


def cmd_clo3d(args):
    """Build the garment of a clo3d_<size>.json in CLO3D in one plugin call (build_garment of clo3d-mcp-extended):
    pieces, collision thickness 0, mesh, fabric by role, arrangement by point name, seams, wrap holds. Then read
    the line lengths back, capture the views, optionally simulate and show the fit maps, and save."""
    d = args.dir or os.environ.get("CLO3D_MCP_DIR") or os.path.join(
        os.environ.get("TEMP", tempfile.gettempdir()), "clo3d_mcp")
    if not os.path.isdir(d):
        raise SystemExit(f"Exchange folder not found: {d}. Start the plugin in CLO3D.")
    with open(args.file, encoding="utf-8") as f:
        data = json.load(f)
    if args.arrange:                       # {piece: index | "Point_Name" | {"point": i, "name": s, "orientation": deg}}
        with open(args.arrange, encoding="utf-8") as f:
            for name, v in json.load(f).items():
                for p in data["pieces"]:
                    if p["name"] == name:
                        ar = v if isinstance(v, dict) else {"index": v} if isinstance(v, int) else {"name": v}
                        if "point" in ar:
                            ar = dict(ar, index=ar.pop("point"))
                        p["arrange"] = ar
    if args.pieces_only:
        data.pop("seams", None)
        data.pop("holds", None)
        for p in data["pieces"]:
            p.pop("arrange", None)
    fabrics = {}
    for item in (args.fabrics.split(",") if args.fabrics else []):
        role, _, val = item.partition("=")
        if not val:
            role, val = "*", role
        fabrics[role.strip()] = int(val) if val.strip().isdigit() else val.strip()
    if args.fabric is not None:
        fabrics.setdefault("*", args.fabric)
    clo3d_command(d, "ping", {}, 10)
    print("Before sending: the simulation must be stopped in CLO3D (a running simulation while pieces are "
          "created has crashed CLO3D).", flush=True)
    if args.save:
        before = os.path.splitext(args.save)[0] + "_before.zprj"
        clo3d_command(d, "save_project", {"file_path": before})
        print(f"Project saved before the build: {before}", flush=True)
    res = clo3d_command(d, "build_garment", {"garment": data, "fabrics": fabrics or None, "collision_thickness": 0,
                                             "particle_distance": args.mesh, "arrange": not args.pieces_only}, timeout=900)
    bad = 0
    for p in res["pieces"]:
        dev = p.get("max_deviation_mm")
        flag = "!!" if dev is not None and dev > 1.0 else "OK"
        bad += flag == "!!"
        print(f" {flag} {p['name']}: index {p['index']}, {p.get('lines', '?')} lines, max deviation "
              f"{dev if dev is not None else '?'} mm, placed on {p.get('arranged') or '-'}", flush=True)
    print(f"{res['seams_sewn']} seams sewn, {len(res['seams_failed'])} failed; {res['holds_sewn']} holds, "
          f"{len(res['holds_failed'])} failed.", flush=True)
    for x in res["seams_failed"] + res["holds_failed"]:
        print(" !! failed:", x, flush=True)
    for w in res.get("warnings", []):
        print(" !! " + w, flush=True)
    if res.get("unplaced"):
        print("Not placed (no arrangement point): " + ", ".join(res["unplaced"]) +
              ". Place them by hand in CLO3D before simulating.", flush=True)
    if args.snapshots:
        os.makedirs(args.snapshots, exist_ok=True)
        clo3d_command(d, "export_snapshot_2d", {"output_path": os.path.join(args.snapshots, "patterns_2d.png")})
        print("Views before simulation:", ", ".join(_views(d, args.snapshots, "arranged")), flush=True)
    if args.save:
        clo3d_command(d, "save_project", {"file_path": args.save})
        print(f"Project saved: {args.save}", flush=True)
    if args.simulate:
        clo3d_command(d, "simulate", {"steps": args.simulate}, timeout=900)
        if args.snapshots:
            files = _views(d, args.snapshots, "simulated", ((2, "front"), (4, "side"), (8, "back")))
            clo3d_command(d, "set_fit_maps", {"stress": True})
            files += _views(d, args.snapshots, "stress", ((2, "front"), (8, "back")))
            clo3d_command(d, "set_fit_maps", {"stress": False})
            print("Views after simulation:", ", ".join(files), flush=True)
        if args.save:
            clo3d_command(d, "save_project", {"file_path": args.save})
            print(f"Project saved after simulation: {args.save}", flush=True)
    if args.stop:
        clo3d_command(d, "stop", {}, 10)
    return 0 if not bad and not res["seams_failed"] else 2

# ------------------------------------------------------------------ command line


def load_measurements(args):
    own = {}
    if args.measurements:
        with open(args.measurements, encoding="utf-8") as f:
            own = json.load(f)
    body = own.pop("body", None) or args.body
    a = standard_ease(body)
    if getattr(args, "knit", False):           # medium-stretch knit (references/ease.md): negative ease, no cap ease
        a.update({"bust": -4, "bodice_waist": -4, "sleeve_cap": 0, "wrist": 2, "shoulder": 0})
    a.update(own.pop("ease", {}))
    return body, own, a


def cmd_glove(args):
    own = {}
    if args.measurements:
        with open(args.measurements, encoding="utf-8") as f:
            own = json.load(f).get("hand", {})
    sizes = args.sizes.split(",") if args.sizes else [args.size or "7"]
    sets = []
    for sz in sizes:
        h = glove_hand(float(sz), own if not args.sizes else {})
        if args.length is not None:
            h["end_below_wrist"] = args.length * 10
        if args.end_girth is not None:
            h["end_girth"] = args.end_girth * 10
        left = block_glove(h)
        for p in left["pieces"]:               # fingers up as on real patterns: orientation 0 on the arm points
            p["fabric"] = "shell"
            p["particle_distance"] = 4 if p["name"].startswith("Fourchette") else 6
            p["arrange"] = arrange_for(p["name"]) or {"name": "Arm_Inside_3_{side}", "orientation": 0}
        right = [mirror_piece(p, "Glove R " + p["name"]) for p in left["pieces"]]
        for side, group in (("L", left["pieces"]), ("R", right)):
            for p in group:
                p["arrange"] = dict(p["arrange"], name=p["arrange"]["name"].replace("{side}", side))
        for p in left["pieces"]:
            p["name"] = "Glove L " + p["name"]
        seams = [[f"Glove {side} {a[0]}", a[1], a[2], f"Glove {side} {a[3]}", a[4], a[5]] + list(a[6:])
                 for side in ("L", "R") for a in left["seams"]]
        sets.append((sz, {"pieces": left["pieces"] + right, "checks": left["checks"], "seams": seams}))
    export(sets, args.out, "glove", args.allowance)
    ok = report(sets)
    print(f"\nFiles written to {os.path.abspath(args.out)}")
    return 0 if ok else 2


def cmd_block(args):
    if args.block == "glove":
        return cmd_glove(args)
    body, own, a = load_measurements(args)
    default = str(library.reference_size(body))
    sizes = args.sizes.split(",") if args.sizes else [args.size or default]
    sets = []
    for i, sz in enumerate(sizes):
        std = standard_measurements(body, sz)
        m = complete({**std, **(own if not args.sizes else {})}, body)
        if i == 0 and own and not args.sizes:
            missing = sorted(set(std) - set(own))
            if missing:
                print("Measurements taken from the standard table:", ", ".join(missing))
        if args.sleeve_length is not None:
            m["arm_length"] = args.sleeve_length
        if args.sleeve_hem is not None:
            a = dict(a, wrist=args.sleeve_hem - m["wrist"])
        circle = {"fullness": args.fullness, "panels": args.panels, "length_cm": args.length} if args.block == "circle_skirt" else None
        sets.append((sz, build(args.block, m, a, body, args.knit, circle)))
    title = f"{args.block} {body}" + (" knit" if args.knit else "")
    export(sets, args.out, title, args.allowance)
    ok = report(sets)
    shells = [(sz, shell_from_blocks(r, args.knit)) for sz, r in sets]
    export(shells, os.path.join(args.out, "clo3d"), title + " (3D shell)")
    print("\n== 3D shell (clo3d/)")
    ok &= report(shells)
    print(f"\nFiles written to {os.path.abspath(args.out)} (3D shell with seams in {os.path.join(args.out, 'clo3d')})")
    return 0 if ok else 2


def _load_pieces(path, name):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    pieces = data["pieces"] if isinstance(data, dict) else data
    j = next((i for i, p in enumerate(pieces) if p["name"] == name), None)
    if j is None:
        raise SystemExit(f"Piece not found: {name}. Pieces: " + ", ".join(p["name"] for p in pieces))
    return data, pieces, j


def cmd_pivot(args):
    data, pieces, j = _load_pieces(args.file, args.piece)
    if args.to_node:
        target = ("node", args.to_node)
    elif args.to_edge is not None:
        target = ("edge", args.to_edge, args.to_d)
    else:
        dx, dy = (float(v) for v in args.direction.split(","))
        target = ("direction", dx, dy)
    before = pieces[j]
    pieces[j] = pivot(before, args.pivot, target, args.angle, args.fraction, args.flare)
    output = args.output or args.file
    with open(output, "w", encoding="utf-8") as f:
        json.dump(rounded(data), f, ensure_ascii=False, indent=1)
    p = pieces[j]
    print(f"{p['name']}: {len(before['outline'])} -> {len(p['outline'])} nodes, written to {output}")
    for i, nd in enumerate(p["outline"]):
        print(f"  edge {i} from {nd.get('name', '?')}{' (dart)' if nd.get('dart') else ''}: "
              f"{length(edge(p, i)):.2f} cm")
    return 0


def cmd_smooth(args):
    data, pieces, j = _load_pieces(args.file, args.piece)
    pieces[j] = smooth(pieces[j], args.start, args.end)
    output = args.output or args.file
    with open(output, "w", encoding="utf-8") as f:
        json.dump(rounded(data), f, ensure_ascii=False, indent=1)
    p = pieces[j]
    i = [n.get("name") for n in p["outline"]].index(args.start)
    print(f"{p['name']}: {args.start} -> {args.end} smoothed, {length(edge(p, i)):.2f} cm, written to {output}")
    return 0


def cmd_piece(args):
    with open(args.file, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        data = {"pieces": data}
    for p in data["pieces"]:
        if p.get("band"):
            continue
        if len(p.get("outline", [])) < 3 or not all(len(n.get("p", [])) == 2 for n in p["outline"]):
            raise SystemExit(f"Invalid piece: {p.get('name', '?')} (at least 3 nodes with \"p\": [x, y])")
    sz = str(data.get("size", "one"))
    pieces, seams = expand_bands(data["pieces"], list(data.get("seams", [])))
    sets = [(sz, {"pieces": pieces, "checks": [], "seams": seams})]
    export(sets, args.out, data.get("title", "pattern"), args.allowance)
    ok = report(sets)
    for p in sets[0][1]["pieces"]:
        print(f"{p['name']}: " + ", ".join(f"edge {i} = {length(edge(p, i)):.2f} cm" for i in range(len(p["outline"]))))
    print(f"Files written to {os.path.abspath(args.out)}")
    return 0 if ok else 2


def test():
    for body, sizes in (("women", ["34", "38", "46"]), ("men", ["44", "48", "56"]), ("children", ["4", "8", "14"])):
        for sz in sizes:
            res = build("all", complete(standard_measurements(body, sz), body), standard_ease(body), body)
            for c in res["checks"]:
                assert c["expected"] is None or abs(c["value"] - c["expected"]) <= c["tol"], (body, sz, c)
            for p in res["pieces"]:
                net, cut = outline(p), cut_line(p)
                assert abs(area(cut)) > abs(area(net)), (body, sz, p["name"], "allowance")
                assert all(math.isfinite(v) for q in cut for v in q)
                d = unfold(p)
                if p.get("fold"):
                    assert abs(abs(area(outline(d))) - 2 * abs(area(net))) < 0.01 * abs(area(net)), (p["name"], "unfold")
                assert len(notches(d)) == len(notches(p)) * (2 if p.get("fold") else 1)
    # pivot: A-line skirt (darts closed towards the hem) and bust dart transferred to the shoulder
    m, a = complete(standard_measurements("women", 38), "women"), standard_ease("women")
    sf = block_skirt(m, a, "women")["pieces"][0]
    al = sf
    for dn in [n["name"] for n in sf["outline"] if n.get("dart")]:
        al = pivot(al, dn, ("direction", 0, 1), flare=True)
    assert not any(n.get("dart") for n in al["outline"]), "dart not closed"
    sm = smooth(al, "side_hem", "center_hem")
    i = [n["name"] for n in sm["outline"]].index("side_hem")
    assert sm["outline"][(i + 1) % len(sm["outline"])]["name"] == "center_hem", "smoothing"
    c2, b = sm["outline"][i]["c"][1], sm["outline"][(i + 1) % len(sm["outline"])]["p"]
    assert abs(c2[1] - b[1]) < 1e-6, "the hem must meet the fold at a right angle"
    assert sm["fold"] == [(i + 1) % len(sm["outline"])], "the fold moved while smoothing"
    assert abs(area(outline(al))) > abs(area(outline(sf))), "no fullness added"

    def path_length(p, start, end):
        names_ = [n["name"] for n in p["outline"]]
        i, L = names_.index(start), 0.0
        while names_[i] != end:
            if not p["outline"][i].get("dart") and not p["outline"][(i + 1) % len(names_)].get("dart"):
                L += length(edge(p, i))
            i = (i + 1) % len(names_)
        return L
    waist_al, waist_sf = path_length(al, "center_waist", "side_waist"), path_length(sf, "center_waist", "side_waist")
    sback = block_skirt(m, a, "women")["pieces"][1]
    two = pivot(pivot(sback, "dart0", ("direction", 0, 1), flare=True), "dart1", ("direction", 0, 1), flare=True)
    assert not any(n.get("dart") for n in two["outline"]), "back darts not closed"
    assert abs(waist_al - waist_sf) < 0.3, ("waist changed", waist_al, waist_sf)
    assert al["fold"] and al["outline"][al["fold"][0]]["name"] == "center_hem", "the fold moved"
    bod = block_bodice(m, a, "women")
    fr = bod["pieces"][1]
    tr = pivot(fr, "side_dart", ("direction", 0, -1))
    names = [n["name"] for n in tr["outline"]]
    assert "side_dart" not in names and "side_dart_transfer" in names, names
    i_fold = tr["fold"][0]
    assert tr["outline"][i_fold]["p"][0] == 0 and tr["outline"][(i_fold + 1) % len(names)]["p"][0] == 0, "center front moved"
    assert len(notches(tr)) == len(notches(fr))
    fl = pivot(sf, "center_waist", ("direction", 0, 1), angle=5, flare=True)
    assert abs(area(outline(fl))) > abs(area(outline(sf)))
    h = [block_skirt(complete(standard_measurements("women", t), "women"), standard_ease("women"), "women")["pieces"][0]["outline"][-3]["p"][0]
         for t in (36, 38, 40)]
    assert h[0] < h[1] < h[2], "grading"
    with tempfile.TemporaryDirectory() as d:
        sets = [(t, build("all", complete(standard_measurements("women", t), "women"), standard_ease("women"), "women"))
                for t in ("36", "38")]
        export(sets, d, "test")
        assert len(os.listdir(d)) == 9
        with open(os.path.join(d, "clo3d_38.json"), encoding="utf-8") as f:
            clo = json.load(f)
        for pc in clo["pieces"]:
            straight = sum(1 for q in pc["points"] if q[2] == 0)
            assert straight == len(pc["edges"]), (pc["name"], "one CLO3D line per edge")
            assert all(q[2] in (0, 3) for q in pc["points"])
        with open(os.path.join(d, "clo3d_38.py"), encoding="utf-8") as f:
            compile(f.read(), "clo3d_38.py", "exec")
    # glove: real-pattern construction, seams that exist and match, hole opened by a slit for CLO3D
    g = block_glove(glove_hand(7))
    for c in g["checks"]:
        assert c["expected"] is None or abs(c["value"] - c["expected"]) <= c["tol"], c
    tr_ = next(p for p in g["pieces"] if p["name"] == "Trank")
    xs_ = sorted({round(n["p"][0], 2) for n in tr_["outline"] if n["name"].endswith(("_t0", "_t1"))})
    assert len(xs_) >= 8, "straight parallel fingers expected"
    with tempfile.TemporaryDirectory() as d:
        offs_, _, _ = layout([g["pieces"]])
        write_clo3d(g["pieces"], offs_, os.path.join(d, "g.json"), "7", g["seams"])
        with open(os.path.join(d, "g.json"), encoding="utf-8") as f:
            gj = json.load(f)
        pcs_ = {p["name"]: p for p in gj["pieces"]}
        bad = [r for r in seam_table(gj, gj["seams"]) if not r[8]]
        assert not bad, bad                                              # reciprocal lengths, declared ease
    # recipe: any garment as data (mirror pairs, seams per side, declared ease) is validated the same way
    recipe = {"pieces": [
        {"name": "Panel", "mirror": True, "outline": [{"name": "tl", "p": [0, 0]}, {"name": "tr", "p": [20, 0]},
                                                       {"name": "br", "p": [22, 30]}, {"name": "bl", "p": [0, 30]}]},
        {"name": "Front", "fold": [3], "outline": [{"name": "cw", "p": [0, 0]}, {"name": "sw", "p": [18, 0]},
                                                    {"name": "sh", "p": [24, 30]}, {"name": "ch", "p": [0, 30]}]}],
        "seams": [["Panel {side}", "tr", "br", "Front", "sw", "sh"], ["Panel L", "tl", "bl", "Panel R", "tl", "bl"]]}
    with tempfile.TemporaryDirectory() as d:
        sets_ = [("one", {"pieces": recipe["pieces"], "seams": recipe["seams"], "checks": []})]
        export(sets_, d, "recipe")
        names_ = [p["name"] for p in sets_[0][1]["pieces"]]
        assert names_ == ["Panel L", "Panel R", "Front"], names_
        assert len(sets_[0][1]["seams"]) == 3
        ck = {c["label"]: c for c in sets_[0][1]["checks"]}
        assert any("right angle at the fold" in k for k in ck), ck
        fails = next(c for k, c in ck.items() if k.startswith("Seams:"))
        assert fails["value"] == 2, fails             # side seams 30.07 vs 30.59 cm: flagged on both sides
    # pinched pieces and pieces that pass the piece they belong to
    def box(nm, x0, x1, y0, y1, **kw):
        return dict({"name": nm, "outline": [{"p": [x0, y0]}, {"p": [x1, y0]}, {"p": [x1, y1]}, {"p": [x0, y1]}]}, **kw)
    pinched = {"name": "Lining", "outline": [{"p": [0, 0]}, {"p": [12, 0]}, {"p": [12, 15]}, {"p": [3, 30]},
                                             {"p": [12, 45]}, {"p": [12, 60]}, {"p": [0, 60]}]}
    assert neck_check(pinched) and neck_check(pinched)["value"] < MIN_NECK_CM, "pinched lining not flagged"
    assert neck_check(box("Fly", 0, 4.5, 0, 60)) is None, "a narrow strip is not a pinch"
    assert all(neck_check(p) is None for p in g["pieces"]), "glove fingers are protrusions, not pinches"
    wc = {c["label"]: c for c in within_checks([box("Front", -8, 15, 0, 100), box("Facing", -8, 5, 0, 100, within="Front"),
                                                 box("Wide facing", -8, 20, 0, 100, within="Front")])}
    assert wc["Facing: lies within Front (cm outside)"]["value"] == 0
    assert wc["Wide facing: lies within Front (cm outside)"]["value"] > WITHIN_TOL_CM
    # whole garments from specs: every check and every 3D seam passes (darts, boxy, princess with a wrap)
    import garment
    ex = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")
    for sp_ in ("notched-lapel-jacket/jacket_fitted.json", "notched-lapel-jacket/jacket_oversize.json",
                "velvet-coat/coat.json"):
        with open(os.path.join(ex, sp_), encoding="utf-8") as f:
            res_ = garment.run(json.load(f))
        with tempfile.TemporaryDirectory() as d:
            cut_ = [("t", {"pieces": res_["cut"] + res_["lining"], "checks": list(res_["checks"])})]
            sh_ = [("t", {"pieces": res_["shell3d"], "seams": res_["seams"], "holds": res_["holds"], "checks": []})]
            export(cut_, d, "t")
            export(sh_, os.path.join(d, "3d"), "t")
            for c in cut_[0][1]["checks"] + sh_[0][1]["checks"]:
                assert c["expected"] is None or abs(c["value"] - c["expected"]) <= c["tol"], (sp_, c)
    gr = tr_["grain"]
    ys_ = [n["p"][1] for n in tr_["outline"]]
    assert all(min(ys_) <= g[1] <= max(ys_) for g in gr), ("grain line outside the trank", gr)
    # data library: every shipped file is valid; a contributed size chart drafts; broken files are named in words
    for kind, i, path in library.files():
        with open(path, encoding="utf-8") as f:
            assert library.validate(kind, i, json.load(f)) == [], (kind, i, library.validate(kind, i, json.load(open(path, encoding="utf-8"))))
    eu = library.load("measurements", "standard-eu")
    chart = {"id": "t-chart", "kind": "measurements", "title": "t", "unit": "cm",
             "bodies": {"women": {"reference_size": "M", "sizes": {"S": standard_measurements("women", 36), "M": standard_measurements("women", 40)}}},
             "provenance": {"source": "test", "rights": "test", "confidence": "practice", "extraction": {"method": "transcribed"}}}
    library._cache[("measurements", "t-chart")] = chart
    assert standard_measurements("women", "S", "t-chart")["bust"] == 84 and standard_measurements("women", None, "t-chart")["bust"] == 92
    assert library.validate("measurements", "t-chart", chart) == []
    assert library.ease("women", "t-chart") == eu["ease"]["women"], "a table without ease uses the default ease"
    bad = json.loads(json.dumps(chart))
    bad["bodies"]["women"]["sizes"]["S"]["waist"] = 140                     # larger than the hip: the blocks must refuse it
    bad["provenance"]["confidence"] = "sure"
    library._cache[("measurements", "t-chart")] = bad
    msgs = library.validate("measurements", "t-chart", bad)
    assert any("confidence" in x for x in msgs) and any("size S" in x for x in msgs), msgs
    del library._cache[("measurements", "t-chart")]
    sq = [{"p": [0, 0], "name": "tl", "corner": True}, {"p": [4, 0], "name": "tr", "corner": True}, {"p": [4, 3], "name": "br"},
          {"p": [0, 3], "name": "low", "corner": True}]
    nd = library.smooth_nodes(sq)
    assert "c" not in nd[0] and "c" in nd[1] and nd[3]["name"] == "low", nd
    shp = {"id": "t-shape", "kind": "shape", "title": "t", "unit": "cm", "reference": {"w": 4}, "scale": {"measure": "w"},
           "outlines": {"o": {"type": "other", "points": sq, "edges": {"hem": [["tl", "tr"]], "applied": [["tr", "br"], ["br", "low"], ["low", "tl"]]}}},
           "provenance": {"source": "t", "rights": "t", "confidence": "measured",
                                                              "extraction": {"method": "ruler", "line": "seam", "deviation_mm": 1.0}}}
    assert library.validate("shape", "t-shape", shp) == []
    far = json.loads(json.dumps(shp))
    far["provenance"]["extraction"]["deviation_mm"] = 3.5                 # more than 2 mm off its paper: digitise again
    assert any("digitise again" in x for x in library.validate("shape", "t-shape", far))
    far["provenance"]["extraction"] = {"method": "diagram", "line": "seam", "deviation_mm": None}
    assert any("measured" in x for x in library.validate("shape", "t-shape", far)), "a diagram is not a measured shape"
    assert "<polygon" in library.preview_svg(library.shape_pieces(shp), "t") and library._same("a 1.04 b", "a 1.05 b")
    assert not library._same("a 1.0 b", "a 1.3 b") and not library._same("a 1.0 b", "c 1.0 b")
    assert abs(library.shape_pieces(shp, {"w": 8})[0]["outline"][1]["p"][0] - 8) < 1e-9, "a shape scales by its measure"
    loose = json.loads(json.dumps(shp))
    del loose["outlines"]["o"]["edges"]["hem"]                           # an edge nobody accounts for: the pattern is incomplete
    assert any("tl..tr is not accounted for" in x for x in library.validate("shape", "t-shape", loose))
    # the analysis measures the engine's own blocks and finds the ease they were drafted with
    mw = complete(standard_measurements("women", 38), "women")
    tp = {"Bodice back": "bodice_back", "Bodice front": "bodice_front", "Sleeve": "sleeve"}
    blk = {"id": "t-blk", "unit": "cm", "reference": mw, "outlines": {
        x["name"]: {"type": tp[x["name"]], "nodes": x["outline"]} for x in build("all", mw, standard_ease("women"), "women")["pieces"] if x["name"] in tp}}
    an = library.analyze(blk)
    gm = {g["name"]: g for g in an["garment"]}
    assert abs(gm["finished_bust"]["ease"] - standard_ease("women")["bust"]) < 0.01, gm["finished_bust"]
    assert abs(gm["cap_ease"]["value"] - standard_ease("women")["sleeve_cap"]) < 0.2, gm["cap_ease"]
    assert [d_["name"] for d_ in an["pieces"]["Bodice back"]["darts"]] == ["dart"]
    blk["outlines"]["Sleeve"]["nodes"] = [dict(x, name="top") if x["name"] == "cap" else x for x in blk["outlines"]["Sleeve"]["nodes"]]
    assert any("points to name: cap" in x for x in library.analyze(blk)["problems"]), "a typed piece needs its standard points"
    bow = dict(shp, outlines={"o": {"points": [{"p": [0, 0]}, {"p": [4, 3.4]}, {"p": [4, 0]}, {"p": [0, 3]}]}})
    assert any("crosses itself" in x for x in library.validate("shape", "t-shape", bow)), "a bow-tie outline must be refused"
    assert any("TODO" in x for x in library.validate("shape", "t-shape", dict(shp, title="TODO: name it")))
    pn = library._path_nodes("M 0,0 C 1,-1 3,-1 4,0 l 0,3 h -4 z")
    assert len(pn) == 4 and "c" in pn[0] and pn[3]["p"] == [0.0, 3.0], pn
    typ, vals = library.preset("shirt-collar", "collar")
    assert typ == "shirt" and vals["point"] == 7.0
    assert garment.merged({"collar": {"preset": "shirt-collar", "point": 9}})["collar"] == dict(vals, type="shirt", point=9)
    assert arrange_for("Fourchette I (IM)")["orientation"] == 0 and arrange_for("no such piece") is None
    print("All tests pass.")
    return 0


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows consoles default to cp1252
    ap = argparse.ArgumentParser(description="Pattern-making engine (inputs in cm).")
    sp = ap.add_subparsers(dest="cmd", required=True)
    for name in ("block", "measurements"):
        p = sp.add_parser(name)
        if name == "block":
            p.add_argument("block", choices=BLOCKS + ("all", "glove", "circle_skirt"))
            p.add_argument("--length", type=float, help="glove: end below the wrist crease; circle_skirt: skirt length, cm")
            p.add_argument("--knit", action="store_true", help="bodice and sleeve for a knit: no darts, negative ease, no cap ease, 8 mm mesh")
            p.add_argument("--sleeve-length", type=float, help="sleeve length in cm (default: arm length)")
            p.add_argument("--sleeve-hem", type=float, help="finished sleeve hem circumference in cm")
            p.add_argument("--fullness", type=float, default=1.0, help="circle_skirt: 1 full, 0.5 half, 0.25 quarter")
            p.add_argument("--panels", type=int, default=2, help="circle_skirt: number of panels (2: front and back)")
            p.add_argument("--end-girth", type=float, help="glove: arm girth at the end of the glove, cm")
            p.add_argument("--out", default="pattern_out")
            p.add_argument("--sizes", help="list for grading, e.g. 36,38,40")
            p.add_argument("--allowance", type=float, help="default seam allowance in cm (hems unchanged)")
        p.add_argument("--body", choices=("women", "men", "children"), default="women")
        p.add_argument("--table", help="measurement table of data/measurements/ (default: standard-eu); `data list` shows them")
        p.add_argument("--avatar", help="avatar file of data/avatars/ for the arrangement points of the 3D shell")
        p.add_argument("--size", help="standard size (women 34-48, men 44-58, children: age 4-14; glove: 6 to 10)")
        p.add_argument("--measurements", help="JSON file of personal measurements in cm")
    p = sp.add_parser("garment", help="draft a whole garment from a spec (references/garment-spec.md)")
    p.add_argument("spec")
    p.add_argument("--out", default="garment_out")
    p.add_argument("--table", help="measurement table of data/measurements/ (the spec's \"table\" key wins)")
    p.add_argument("--avatar", help="avatar file of data/avatars/ (the spec's \"avatar\" key wins)")
    p = sp.add_parser("piece")
    p.add_argument("file")
    p.add_argument("--out", default="pattern_out")
    p.add_argument("--allowance", type=float)
    p = sp.add_parser("pivot", help="close or transfer a dart, or open a slash (slash and spread)")
    p.add_argument("file", help="pieces file (pieces_<size>.json)")
    p.add_argument("--piece", required=True, help="piece name")
    p.add_argument("--pivot", required=True, help="pivot node: dart point, or a point of the outline")
    p.add_argument("--direction", default="0,1", help="slash direction from the pivot (default 0,1: downwards)")
    p.add_argument("--to-node", help="the slash runs to this node")
    p.add_argument("--to-edge", type=int, help="the slash runs to this edge...")
    p.add_argument("--to-d", type=float, default=0, help="...at this distance from the edge start, in cm")
    p.add_argument("--angle", type=float, help="opening angle in degrees (required unless the pivot is a dart)")
    p.add_argument("--fraction", type=float, default=1.0, help="share of the dart to close, 0 to 1")
    p.add_argument("--flare", action="store_true", help="fill the slash: adds fullness instead of a dart")
    p.add_argument("--output", help="output file (default: overwrite the input file)")
    p = sp.add_parser("smooth", help="redraw the path between two nodes as a smooth curve")
    p.add_argument("file")
    p.add_argument("--piece", required=True)
    p.add_argument("--from", dest="start", required=True, help="start node")
    p.add_argument("--to", dest="end", required=True, help="end node, following the outline")
    p.add_argument("--output")
    p = sp.add_parser("clo3d", help="build a clo3d_<size>.json garment in CLO3D through the plugin (one call)")
    p.add_argument("file")
    p.add_argument("--dir", help="plugin exchange folder (default: %%TEMP%%/clo3d_mcp)")
    p.add_argument("--stop", action="store_true", help="stop the plugin listener after sending")
    p.add_argument("--assemble", action="store_true", help="kept for compatibility: seams and arrangement are the default")
    p.add_argument("--pieces-only", action="store_true", help="create the pieces only: no seams, no arrangement")
    p.add_argument("--fabrics", help="fabric per role: shell=2,lining=Cotton,*=0 (index or name of a project fabric)")
    p.add_argument("--fabric", type=int, help="fabric index for pieces without a role (same as --fabrics *=i)")
    p.add_argument("--mesh", type=float, help="mesh size in mm for pieces without their own (8 fitted knits, 4 to 6 gloves)")
    p.add_argument("--arrange", help="JSON file {piece name: point index, \"Point_Name\" or {\"name\": s, \"orientation\": deg}}")
    p.add_argument("--snapshots", help="folder for the 2D capture and the front and side views, before and after simulation")
    p.add_argument("--simulate", type=int, help="run this many simulation steps, then export the views and stress map")
    p.add_argument("--save", help=".zprj path: the project is saved before the build, after it, and after simulation")
    p = sp.add_parser("template", help="template bank: list, show <id>, draft <id> --param k=v --out folder")
    p.add_argument("action", choices=("list", "show", "draft"))
    p.add_argument("id", nargs="?")
    p.add_argument("--param", action="append", help="k=v, repeatable (see `show`)")
    p.add_argument("--out", default="template_out")
    p = sp.add_parser("kb", help="knowledge base: search <words>, show <id>, index")
    p.add_argument("action", choices=("search", "show", "index"))
    p.add_argument("words", nargs="*")
    p = sp.add_parser("check", help="validate every data file and knowledge-base entry (run it before a pull request)")
    p.add_argument("--write", action="store_true", help="maintainers and the merge workflow: rebuild the index, COVERAGE.md, "
                   "CREDITS.md and the previews")
    p.add_argument("--base", help="pull requests: the branch to compare with (origin/main); generated files must be untouched")
    p = sp.add_parser("data", help="data library: list, show <kind> <id>")
    p.add_argument("action", choices=("list", "show"))
    p.add_argument("kind", nargs="?")
    p.add_argument("id", nargs="?")
    p = sp.add_parser("shape", help="draw a digitised shape of data/shapes/, scaled: shape <id> --measure G=190 --out folder")
    p.add_argument("id")
    p.add_argument("--measure", action="append", help="k=v, repeatable: the measurements the shape scales by")
    p.add_argument("--out", default="shape_out")
    p = sp.add_parser("digitize", help="turn a real pattern piece into a shape file: a photo (PNG), a tracing (SVG) or points (CSV)")
    p.add_argument("file", help="photo.png (click tool), tracing.svg, or points.csv (x, y[, name][, corner])")
    p.add_argument("--id", required=True, help="name of the shape file, lowercase with dashes")
    p.add_argument("--title")
    p.add_argument("--scale-length", type=float, help="real length in cm of the ruler segment (photo) or of the `scale` line (SVG)")
    p.add_argument("--px-per-cm", type=float, help="SVG without a scale line: drawing units per cm")
    p.add_argument("--unit", choices=("cm", "mm", "in"), default="cm", help="unit of a CSV of points")
    p.add_argument("--out", help="output file (default: data/shapes/<id>.json); an existing file gets the outline added")
    p.add_argument("--outline", help="name of this outline in the shape file (back, front, sleeve...)")
    p.add_argument("--type", help="its piece type: bodice_back, bodice_front, sleeve, skirt_front, skirt_back, trousers_front, "
                   "trousers_back, collar, other")
    p = sp.add_parser("analyze", help="measure a digitised pattern: every standard dimension, seam and ease, and what is missing")
    p.add_argument("shape", help="id of a shape of data/shapes/, or the path of a shape file")
    p.add_argument("--measure", action="append", help="k=v: analyse it scaled to another size")
    sp.add_parser("test")
    args = ap.parse_args()
    library.use_table(getattr(args, "table", None))
    library.use_avatar(getattr(args, "avatar", None))
    if args.cmd == "check":
        return library.cmd_check(args)
    if args.cmd == "data":
        return library.cmd_data(args)
    if args.cmd == "shape":
        return library.cmd_shape(args)
    if args.cmd == "digitize":
        return library.cmd_digitize(args)
    if args.cmd == "analyze":
        return library.cmd_analyze(args)
    if args.cmd == "kb":
        return cmd_kb(args)
    if args.cmd == "test":
        return test()
    if args.cmd == "clo3d":
        return cmd_clo3d(args)
    if args.cmd == "pivot":
        return cmd_pivot(args)
    if args.cmd == "smooth":
        return cmd_smooth(args)
    if args.cmd == "piece":
        return cmd_piece(args)
    if args.cmd == "template":
        import templates
        return templates.main(args)
    if args.cmd == "garment":
        import garment
        return garment.main([args.spec, "--out", args.out])
    if args.cmd == "measurements":
        body, own, a = load_measurements(args)
        m = complete({**standard_measurements(body, args.size), **own}, body)
        print(json.dumps({"body": body, **m, "ease": a}, ensure_ascii=False, indent=1))
        return 0
    return cmd_block(args)


if __name__ == "__main__":
    sys.exit(main())
