#!/usr/bin/env python3
"""Pattern-making engine: parametric blocks, seam allowances, notches, unfolding, grading,
export to SVG (1:1 scale), modern mm DXF and supported outline-transfer JSON.
Core math uses the standard library; validated export requires ezdxf and Shapely.

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
import shutil
import json
import math
import os
import sys
import tempfile

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
            out += [p2] if dist(p2, q1) < 1e-10 else [p2, q1]
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



def construction_marks(piece):
    """Semantic paths in source cm, shared by all drawing writers. Buttons are crosses, not holes."""
    for key, layer in (("darts_in", "DART"), ("lines", "INTERNAL")):
        for pts in piece.get(key, []):
            yield layer, list(pts) + ([pts[0]] if key == "darts_in" else [])
    for q in piece.get("buttons", []):
        x, y = q
        yield "BUTTON", [(x - .3, y), (x + .3, y)]
        yield "BUTTON", [(x, y - .3), (x, y + .3)]
    for k in piece.get("fold", []):
        yield "FOLD", edge(piece, k)
    if piece.get("grain"):
        yield "GRAIN", piece["grain"]
    for a, b in notches(piece):
        yield "NOTCHES", [a, b]


def transform_marks(piece, transform, duplicate=False):
    """Transform absolute marks; indexed folds/notches are remapped by the caller."""
    out = {}
    for key in ("darts_in", "lines"):
        if key in piece:
            changed = [[transform(q) for q in pts] for pts in piece[key]]
            out[key] = copy.deepcopy(piece[key]) + changed if duplicate else changed
    if "buttons" in piece:
        changed = [transform(q) for q in piece["buttons"]]
        out["buttons"] = copy.deepcopy(piece["buttons"]) + changed if duplicate else changed
    if piece.get("grain"):
        out["grain"] = copy.deepcopy(piece["grain"]) if duplicate else [transform(q) for q in piece["grain"]]
    return out

def unfold(piece):
    """Whole piece from a half piece cut on the fold (mirrored across the fold edge)."""
    if not piece.get("fold"):
        return copy.deepcopy(piece)
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
    out.update(transform_marks(piece, lambda q: reflect(q, fa, fb), duplicate=True))
    return copy.deepcopy(out)


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
# Indicative values (France / Europe): starting point, fallback when a measurement is missing,
# and basis for grading. Always prefer real body measurements.

BASE = {
    "women": {"ref": 38, "bust": 88, "waist": 68, "hip": 94, "back_length": 41, "hip_depth": 20,
              "skirt_length": 60, "arm_length": 59, "wrist": 16, "body_rise": 27,
              "trouser_length": 102, "knee_width": 42, "hem_width": 38},
    "men": {"ref": 48, "bust": 96, "waist": 82, "hip": 98, "back_length": 45, "hip_depth": 21,
            "skirt_length": 60, "arm_length": 64, "wrist": 17.5, "body_rise": 27,
            "trouser_length": 106, "knee_width": 46, "hem_width": 42},
}
GRAD = {"bust": 4, "waist": 4, "hip": 4, "back_length": 0.5, "arm_length": 0.5,
        "wrist": 0.5, "body_rise": 0.5, "knee_width": 1, "hem_width": 1}
CHILDREN = {4: (104, 56, 53, 58), 6: (116, 60, 55, 63), 8: (128, 64, 57, 68),
            10: (140, 70, 60, 74), 12: (152, 76, 63, 80), 14: (164, 82, 66, 87)}  # age: height, bust, waist, hip
CHILDREN_LENGTHS = {"back_length": 29, "hip_depth": 13, "skirt_length": 35, "arm_length": 43,
                    "wrist": 13, "body_rise": 20, "trouser_length": 76, "knee_width": 32,
                    "hem_width": 30}                                               # at age 8, 128 cm

EASE = {
    "women": {"bust": 8, "bodice_waist": 4, "skirt_waist": 1, "skirt_hip": 4, "trouser_waist": 1,
              "trouser_hip": 4, "sleeve_cap": 2.5, "wrist": 8, "shoulder": 0.8},
    "men": {"bust": 10, "bodice_waist": 6, "skirt_waist": 1, "skirt_hip": 4, "trouser_waist": 1,
            "trouser_hip": 6, "sleeve_cap": 1.5, "wrist": 10, "shoulder": 0.6},
    "children": {"bust": 8, "bodice_waist": 6, "skirt_waist": 2, "skirt_hip": 6, "trouser_waist": 2,
                 "trouser_hip": 6, "sleeve_cap": 1.5, "wrist": 8, "shoulder": 0.5},
}


def standard_measurements(body, size=None):
    if body == "children":
        age = int(size or 8)
        if age not in CHILDREN:
            raise SystemExit(f"Available children's ages: {sorted(CHILDREN)}")
        st, B, W, H = CHILDREN[age]
        return {"bust": B, "waist": W, "hip": H,
                **{c: round(v * st / 128, 1) for c, v in CHILDREN_LENGTHS.items()}}
    base = BASE[body]
    k = (float(size or base["ref"]) - base["ref"]) / 2
    return {c: round(v + GRAD.get(c, 0) * k, 1) for c, v in base.items() if c != "ref"}


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



def resolve_measurements(body, size=None, own=None):
    own = copy.deepcopy(own or {})
    body = own.pop("body", body)
    if body not in EASE:
        raise ValueError("Unsupported body; choose women, men or children")
    extras = own.pop("ease", {})
    if not isinstance(extras, dict) or set(extras) - set(EASE[body]):
        raise ValueError("Unsupported ease fields")
    std = standard_measurements(body, size)
    allowed = set(complete(std, body))
    unknown = set(own) - allowed
    if unknown:
        raise ValueError("Unsupported measurement fields (not consumed): " + ", ".join(sorted(unknown)))
    for key, value in {**own, **extras}.items():
        if not isinstance(value, (float, int)) or not math.isfinite(value) or (key not in extras and value <= 0):
            raise ValueError(f"Invalid finite measurement: {key}")
    m = complete({**std, **own}, body)
    reference = str(size or (8 if body == "children" else BASE[body]["ref"]))
    provenance = {k: {"source": "input" if k in own else "table" if k in std else "derived",
                      "body": body, "reference_size": reference} for k in m}
    return body, m, {**EASE[body], **extras}, provenance

def check(label, value, expected=None, tol=None):
    return {"label": label, "value": value, "expected": expected, "tol": tol}


def true_boundary_darts(piece):
    """Keep each apex and intake chord; place the mouth perpendicular to its apex bisector.

    Adjacent seam tangents are perpendicular to the legs so they coincide when sewn closed.
    Body/design landmarks elsewhere are retained. This is a local construction operation, never
    an export repair: user-authored unequal/untrued darts fail validation unchanged.
    """
    nd = piece["outline"]
    for i, n in enumerate(nd):
        if not n.get("dart"):
            continue
        j, k = (i-1)%len(nd), (i+1)%len(nd)
        a, b, c = nd[j]["p"], n["p"], nd[k]["p"]
        width = dist(a,c)
        if width < 1e-8:
            raise ValueError("Dart intake must be positive")
        u = [(c[t]-a[t])/width for t in (0,1)]
        foot = [(a[t]+c[t])/2 for t in (0,1)]
        v = [-(foot[1]-b[1]), foot[0]-b[0]]
        if sum(v[t]*u[t] for t in (0,1)) < 0:
            v = [-x for x in v]
        vlen = math.hypot(*v)
        if vlen < 1e-8:
            raise ValueError("Dart apex lies on its mouth")
        u = [x/vlen for x in v]
        nd[j]["p"] = a = [foot[t]-u[t]*width/2 for t in (0,1)]
        nd[k]["p"] = c = [foot[t]+u[t]*width/2 for t in (0,1)]
        for start, end, mouth, incoming in (((j-1)%len(nd),j,a,True),(k,(k+1)%len(nd),c,False)):
            p0,p3=nd[start]["p"],nd[end]["p"]
            v=[-(mouth[1]-b[1]),mouth[0]-b[0]]
            if sum(v[t]*(p3[t]-p0[t]) for t in (0,1))<0:
                v=[-x for x in v]
            l=math.hypot(*v)
            span=dist(p0,p3)
            handle=min(span/3,1.0)
            controls=nd[start].get("c",[[p0[t]+(p3[t]-p0[t])/3 for t in (0,1)],
                                          [p0[t]+2*(p3[t]-p0[t])/3 for t in (0,1)]])
            controls=copy.deepcopy(controls)
            controls[1 if incoming else 0]=[mouth[t]+(-1 if incoming else 1)*v[t]/l*handle for t in (0,1)]
            nd[start]["c"]=controls
    return piece


def lengthen_edge(piece, i, target, preserve_tangents=False):
    """Fit a smooth edge to a construction length with fixed endpoints (cm)."""
    a,b=piece["outline"][i]["p"],piece["outline"][(i+1)%len(piece["outline"])]["p"]
    chord=dist(a,b)
    if target < chord-.001:
        raise ValueError("Seam target shorter than endpoint distance")
    ux,uy=(b[0]-a[0])/chord,(b[1]-a[1])/chord
    def controls(bow):
        return [[a[0]+(b[0]-a[0])/3-uy*bow,a[1]+(b[1]-a[1])/3+ux*bow],
                [a[0]+2*(b[0]-a[0])/3-uy*bow,a[1]+2*(b[1]-a[1])/3+ux*bow]]
    if preserve_tangents and "c" in piece["outline"][i]:
        old = copy.deepcopy(piece["outline"][i]["c"])
        def controls(scale):
            return [[a[t]+(old[0][t]-a[t])*scale for t in (0,1)],
                    [b[t]+(old[1][t]-b[t])*scale for t in (0,1)]]
    lo,hi=0.0,max(target,1)
    for _ in range(50):
        v=(lo+hi)/2
        c=controls(v)
        if length([a]+cubic(a,*c,b,64))>target:
            hi=v
        else:
            lo=v
    piece["outline"][i]["c"]=controls((lo+hi)/2)

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
        true_boundary_darts(p)
        side[name] = t.lg("side_waist", "hip")
        total += 2 * (xs - pt)
        pieces.append(p)
    return {"pieces": pieces,
            "checks": [check("Skirt: front side seam - back side seam", side["front"] - side["back"], 0, 0.3),
                       check("Skirt: finished waist", total, W + a["skirt_waist"], 0.6)]}


def block_bodice(m, a, body):
    B, W, N, S = m["bust"], m["waist"], m["neck"], m["shoulder"]
    AD, NW = m["armhole_depth"], m["back_length"]
    BW, CW = m["half_back_width"], m["half_chest_width"]
    women = body == "women"
    Q = (B + a["bust"]) / 4
    Wq = (W + a["bodice_waist"]) / 4
    bd = m.get("bust_dart", 0) if women else 0
    sd_back, sd_front = {"women": (4, 5), "men": (4.5, 5.5), "children": (3, 4)}[body]
    nw = N / 5 - 0.2
    ya, yw = 2 + AD, 2 + NW
    diff = max(Q - Wq, 0) if women else 0

    def share(d, maxp):
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
    true_boundary_darts(back)
    true_boundary_darts(front)
    side_front = sum(length(edge(front, i, 64)) for i,n in enumerate(front["outline"])
                     if n["name"] in ("underarm", "side_dart_2"))
    side_back = length(edge(back, 4, 64))
    if side_front >= side_back:
        lengthen_edge(back, 4, side_front)
        side_back = length(edge(back, 4, 64))
    else:
        i = t.e("side_dart_2") if bd > .2 else t.e("underarm")
        lengthen_edge(front, i, length(edge(front,i,64)) + side_back-side_front, preserve_tangents=True)
        side_front = side_back
    arm_front, arm_low_front = t.lg("shoulder", "across"), t.lg("across")
    total = 2 * (waist_back + Q - sf - pv)
    checks = [check("Bodice: front side seam - back side seam (dart closed)", side_front - side_back, 0, 0.1),
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
    return {"pieces": [p],
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
        true_boundary_darts(p)
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


# ------------------------------------------------------------------ glove
# Leather glove drafted like real glove patterns (references/techniques/accessories.md, part 1):
# one trank (back and palm side by side, fold below the index crotch, straight parallel fingers separated by
# slits ending at crotch points, the two index halves sewn on their outer side, one straight side line),
# a Bolton thumb (heart shape folded on its axis) set into a drop-shaped hole with a V tongue, and one
# fourchette arm per finger side. Hand measurements in mm, size 7 values as default (sheet, section 1.6).

GLOVE_HAND = {"G": 178, "HL": 175, "h_I": 94, "h_M": 98, "h_R": 94, "h_L": 85, "F_I": 66, "F_M": 77, "F_R": 69,
              "F_L": 55, "Cf_I": 56, "Cf_M": 58, "Cf_R": 54, "Cf_L": 48, "T_o": 60, "T_p": 45, "T_g": 62,
              "Web_T": 80, "end_below_wrist": 120, "end_girth": 160}
FINGERS_ORDER = ("L", "R", "M", "I")              # back half, from the little finger side
GLOVE_SLIT = 0.5                                  # half width of a slit, mm (a die cut has none; CLO3D needs a gap)


def glove_hand(size=7.0, own=None):
    """Hand measurements in mm: size 7 table graded by half sizes (sheet 1.5), then personal values."""
    k = (float(size) - 7.0) * 2                   # half sizes away from 7
    h = dict(GLOVE_HAND)
    h["G"] += 12.7 * k
    for key in ("HL", "h_I", "h_M", "h_R", "h_L", "Web_T"):
        h[key] += 4.5 * k
    for key in ("F_I", "F_M", "F_R", "F_L", "T_o", "T_p"):
        h[key] += 1.2 * k
    for key in ("Cf_I", "Cf_M", "Cf_R", "Cf_L"):
        h[key] += 3.2 * k
    h["T_g"] += 2 * k
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

    # ---- thumb hole and Bolton thumb, digitised from a published leather glove pattern (The Shapes of Fabric,
    # size about 7) and scaled to the hand. Hole: along the fold, top about 40 mm under the finger bases, round
    # bottom with a notch near the wrist, a V flap at the top freed by a curved slit that runs from the top
    # corner away from the fold up to a dot. Thumb: wide oval (width about 0.72 of the height) with two lobes
    # at the top and a cleft on the fold axis; folded, the lobes sewn together make the tip; a slit from the
    # side edge to a dot takes the flap; two notches on the other side bound the part sewn to the flap edges.
    sc = G / 180.0
    TLh = (Wb + 2 * sc, crotch_p[("I", "M")] - 40 * sc)
    hp = lambda x, y: (TLh[0] + x * sc, TLh[1] + y * sc)           # hole template, mm, y up from the top left
    hTL, hB, hRM, hTR, hV, hD = hp(0, 0), hp(13.6, -54), hp(30.6, -24), hp(27.9, -3.9), hp(14.3, -9.3), hp(19.4, 10)
    vx, vy = hV[0] - hTR[0], hV[1] - hTR[1]
    vl = math.hypot(vx, vy)
    hTR2 = (hTR[0] + vx / vl * 1.0, hTR[1] + vy / vl * 1.0)       # the two lips of the slit, 1 mm apart
    hc = lambda x, y: [x * sc, y * sc]
    hole = [{"name": "h_TL", "p": list(hTL), "c": [[hTL[0] - 1 * sc, hTL[1] - 25 * sc], [hB[0] - 10 * sc, hB[1]]]},
            {"name": "h_B", "p": list(hB), "c": [[hB[0] + 10 * sc, hB[1]], [hRM[0], hRM[1] - 12 * sc]]},
            {"name": "h_RM", "p": list(hRM), "c": [[hRM[0], hRM[1] + 8 * sc], [hTR[0] + 2 * sc, hTR[1] - 5 * sc]]},
            {"name": "h_TR", "p": list(hTR), "c": [[hTR[0] - 2 * sc, hTR[1] + 6 * sc], [hD[0] + 5 * sc, hD[1] - 2 * sc]]},
            {"name": "h_D", "p": list(hD), "c": [[hD[0] + 5 * sc, hD[1] - 2.6 * sc], [hTR2[0] - 2 * sc, hTR2[1] + 6 * sc]]},
            {"name": "h_TR2", "p": list(hTR2)},
            {"name": "h_V", "p": list(hV)}]
    hole_piece = {"outline": hole}
    hl = {n["name"]: length(edge(hole_piece, i, 200)) for i, n in enumerate(hole)}   # edge length from each node
    ease = 1.03                                          # thumb edges 3 % longer than the hole edges they meet
    seg_targets = [hl["h_TR2"] * ease, hl["h_V"] * ease, hl["h_TL"] * ease, hl["h_B"] * ease, hl["h_RM"] * ease]
    slit_target = hl["h_TR"] * ease

    # thumb template (unit = thumb height, x from the fold axis, y down from the top of the lobes)
    T = {"C": (0, 0.15), "LL": (-0.15, 0), "a": (-0.29, 0.20), "N1": (-0.32, 0.39), "N2": (-0.38, 0.58),
         "b": (-0.30, 0.85), "B": (0, 1.0), "c": (0.27, 0.85), "RM": (0.34, 0.48), "Ps": (0.35, 0.39),
         "d": (0.30, 0.15), "RL": (0.15, 0)}
    order = ["C", "LL", "a", "N1", "N2", "b", "B", "c", "RM", "Ps", "d", "RL", "C"]
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
    dtpl = (0.19 * ksc, -0.54 * ksc)                     # dot of the template
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
    out = copy.deepcopy(dict(p, name=name, outline=mir(p["outline"])))
    n = len(p["outline"])
    rev = lambda i: (n - 2 - i) % n
    if "fold" in p:
        out["fold"] = [rev(i) for i in p["fold"]]
    if "allowances" in p:
        out["allowances"] = {str(rev(int(i))): v for i, v in p["allowances"].items()}
    if "notches" in p:
        out["notches"] = []
        for nt in p["notches"]:
            L = length(edge(p, nt["edge"]))
            d = nt["d"] if "d" in nt else nt.get("t", 0) * L
            if d < 0:
                d += L
            out["notches"].append({"edge": rev(nt["edge"]), "d": L - d})
    if p.get("holes"):
        out["holes"] = [dict(hl, outline=mir(hl["outline"])) for hl in p["holes"]]
    out.update(transform_marks(p, lambda q: [-q[0], q[1]]))
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


def build(block, m, a, body):
    res = {"pieces": [], "checks": [], "seam_chains": []}
    wanted = BLOCKS if block == "all" else (block,)
    bodice = block_bodice(m, a, body) if ("bodice" in wanted or "sleeve" in wanted) else None
    for b in wanted:
        r = {"skirt": lambda: block_skirt(m, a, body), "bodice": lambda: bodice,
             "sleeve": lambda: block_sleeve(m, a, body, bodice), "trousers": lambda: block_trousers(m, a, body)}[b]()
        res["pieces"] += r["pieces"]
        res["checks"] += r["checks"]
        chains=[]
        if b=="skirt":
            chains=[([["Skirt front","side_waist","hip"],["Skirt front","hip","side_hem"]],
                     [["Skirt back","side_waist","hip"],["Skirt back","hip","side_hem"]],0,"side seam")]
        elif b=="trousers":
            chains=[([["Trousers front",a,b] for a,b in zip(names,names[1:])],
                     [["Trousers back",a,b] for a,b in zip(names,names[1:])],0,why)
                    for names,why in [(["side_waist","hip","outer_knee","outer_hem"],"side seam"),
                                      (["inner_hem","inner_knee","crotch"],"inseam")]]
        elif b=="bodice":
            front=r["pieces"][1]
            hasdart=any(n.get("dart") and n["name"]=="side_dart" for n in front["outline"])
            ca=([["Bodice front","underarm","side_dart_1"],["Bodice front","side_dart_2","side_waist"]]
                if hasdart else [["Bodice front","underarm","side_waist"]])
            chains=[(ca,[["Bodice back","underarm","side_waist"]],0,"side seam"),
                    ([["Bodice back","neck","shoulder"]],[["Bodice front","neck","shoulder"]],a["shoulder"],"back shoulder ease")]
        by={p["name"]:p for p in r["pieces"]}
        def edge_ref(row):
            nm,a,b=row
            p=by[nm]; ns=[n["name"] for n in p["outline"]];i,j=ns.index(a),ns.index(b)
            return p,i if (i+1)%len(ns)==j else j
        def clen(chain):
            return sum(length(edge(*edge_ref(row),64)) for row in chain)
        for ca,cb,ease,why in chains:
            if b in ("skirt","trousers"):
                la,lb=clen(ca),clen(cb)
                short=ca if la<lb else cb
                # Fit an existing curved edge, preserving anatomical endpoints/tangents.
                curved=[row for row in short if "c" in edge_ref(row)[0]["outline"][edge_ref(row)[1]]]
                row=max(curved or short,key=lambda row:length(edge(*edge_ref(row),64)))
                pc,i=edge_ref(row)
                lengthen_edge(pc,i,length(edge(pc,i,64))+abs(la-lb),preserve_tangents=True)
            if b in ("skirt","trousers"):
                suffix="front side seam - back side seam" if why=="side seam" else "front inseam - back inseam"
                for old in res["checks"]:
                    if old["label"]==b.capitalize()+": "+suffix:
                        old.update(value=clen(ca)-clen(cb),expected=0,tol=.1)
            res["seam_chains"].append({"a":ca,"b":cb,"ease_cm":ease,"why":why})
    return res

# ------------------------------------------------------------------ export


def layout(pieces_per_size):
    """Place each piece (same rank for every size) on rows of 1.5 m at most, in mm."""
    boxes = []
    for i in range(len(pieces_per_size[0])):
        pts = [q for ps in pieces_per_size for q in cut_line(ps[i])]
        boxes.append((min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)))
    offs, x, y, h, wid = [], 10.0, 15.0, 0.0, 0.0
    for b in boxes:
        w, hh = (b[2] - b[0]) * 10, (b[3] - b[1]) * 10
        if x > 10 and x + w > 1500:
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
    from xml.sax.saxutils import quoteattr

    offs, W, H = layout([r["pieces"] for _, r in sets])
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.1f}mm" height="{H + 120:.1f}mm" '
         f'viewBox="0 -120 {W:.1f} {H + 120:.1f}" font-family="sans-serif">',
         '<rect x="0" y="-120" width="100%" height="100%" fill="#fff"/>',
         '<rect x="10" y="-110" width="100" height="100" fill="none" stroke="#000" stroke-width="0.5"/>',
         '<text x="14" y="-100" font-size="5">Test square 10 x 10 cm</text>',
         f'<text x="125" y="-95" font-size="9">{esc(title)}</text>']
    if len(sets) > 1:
        o.append('<text x="125" y="-80" font-size="6">' + " ".join(
            f'<tspan fill="{COLORS[i % 8]}">S{esc(sz)}</tspan>' for i, (sz, _) in enumerate(sets)) + '</text>')
        o.append('<text x="125" y="-68" font-size="5">All sizes: solid CUT, dashed SEAM; marks match size color</text>')
    pts_txt = lambda pts, off: " ".join(f"{x:.3f},{y:.3f}" for x, y in (mm(p, off) for p in pts))
    for i, off in enumerate(offs):
        for j, (sz, r) in enumerate(sets):
            p, col = r["pieces"][i], COLORS[j % 8]
            o.append(f'<g data-size={quoteattr(str(sz))} data-piece={quoteattr(str(p["name"]))} '
                     f'data-cut={quoteattr(str(p.get("cut", "")))}>')
            o.append(f'<polygon data-layer="CUT" points="{pts_txt(cut_line(p), off)}" '
                     f'fill="none" stroke="{col}" stroke-width="0.6"/>')
            o.append(f'<polygon data-layer="SEAM" points="{pts_txt(outline(p), off)}" fill="none" '
                     f'stroke="{col}" stroke-width="0.3" stroke-dasharray="3 1.5"/>')
            for hl in p.get("holes", []):
                for layer, style in (("CUT", 'stroke-width="0.6"'),
                                     ("SEAM", 'stroke-width="0.3" stroke-dasharray="3 1.5"')):
                    o.append(f'<polygon data-layer="{layer}" data-hole={quoteattr(str(hl.get("name", "")))} '
                             f'points="{pts_txt(outline(hl), off)}" fill="none" stroke="{col}" {style}/>')
            for layer, pts in construction_marks(p):
                o.append(f'<polyline data-layer="{layer}" points="{pts_txt(pts, off)}" fill="none" '
                         f'stroke="{col}" stroke-width="0.4"/>')
            cx, cy = center(p, off)
            for k, txt in enumerate([p["name"], f"Size {sz}", p.get("cut", "")]):
                o.append(f'<text x="{cx:.1f}" y="{cy + j * 27 + k * 9:.1f}" font-size="7" '
                         f'fill="{col}" text-anchor="middle">{esc(txt)}</text>')
            o.append('</g>')
    o.append("</svg>")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(o))


def write_dxf(pieces, offs, path, size):
    """R2010 DXF, explicit millimetres; no unitless legacy fallback."""
    try:
        import ezdxf
    except ImportError as err:
        raise ValueError("Validated DXF export requires ezdxf; install the documented export dependencies") from err
    doc = ezdxf.new("R2010")
    doc.units = 4
    ms = doc.modelspace()
    for layer in ("CUT", "SEAM", "DART", "INTERNAL", "BUTTON", "FOLD", "NOTCHES", "GRAIN", "TEXT"):
        doc.layers.new(layer)
    def line(a, b, layer):
        ms.add_line((round(a[0],3), round(-a[1],3)), (round(b[0],3), round(-b[1],3)), dxfattribs={"layer":layer})
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
        for layer, pts in construction_marks(p):
            for a, b in zip(pts, pts[1:]):
                line(mm(a, off), mm(b, off), layer)
        cx, cy = center(p, off)
        for k, txt in enumerate([p["name"], f"Size {size}", p.get("cut", "")]):
            ms.add_text(str(txt), dxfattribs={"layer":"TEXT", "height":6, "insert":(cx, -(cy+k*9))})
    doc.saveas(path)
    from validation import validate_dxf
    validate_dxf(path)


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
    if any(p.get("darts_in") for p in pieces):
        raise ValueError("Internal dart sewing topology unsupported for CLO3D export")
    out = {"unit": "mm", "size": str(size), "pieces": []}
    for p, off in zip(pieces, offs):
        q = slit_holes(unfold(p))
        out["pieces"].append({"name": p["name"], "cut": q.get("cut", ""), "points": clo3d_points(q, off),
                              "edges": [{"line": i, "from": n.get("name", ""), "length_mm": round(length(edge(q, i)) * 10, 1)}
                                        for i, n in enumerate(q["outline"])]})
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
    ease,why=float(extra.get("ease", 0.0)),extra.get("why", "")
    if not math.isfinite(ease) or ease <= -1 or (ease and not why):
        raise ValueError("Seam ease must be finite, greater than -1, and have an independent reason")
    if ease and ("dart" in why.lower() or why.lower() in ("side seam","princess seam","forearm seam")):
        raise ValueError("Ordinary side and dart seams require zero ease")
    return ease,why


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
    nds = piece["outline"]
    n, end = nds[i], nds[(i + 1) % len(nds)]["p"]
    if "c" in n:
        a, b = (n["p"], n["c"][0]) if at_start else (n["c"][1], end)
    else:
        a, b = n["p"], end
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
        out.append(check(f"{p['name']}: lies within {parent['name']} (cm outside)", 0.0 if worst < 1e-10 else worst, 0, WITHIN_TOL_CM))
    return out


def expand_mirrors(pieces, seams):
    """Pieces with "mirror": true become "<name> L" and its mirror "<name> R"; seams naming "{side}" are
    written once per side."""
    out = []
    for p in pieces:
        if p.get("mirror"):
            base = {k: v for k, v in p.items() if k != "mirror"}
            out += [dict(base, name=p["name"] + " L"), mirror_piece(base, p["name"] + " R")]
        else:
            out.append(p)
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
    """Stage a whole bundle; failed checks retain editable diagnostics only under rejected/."""
    from validation import finite, paths, darts, proportions, seam_chains
    work = copy.deepcopy(sets)
    os.makedirs(out, exist_ok=True)
    # Refuse to replace existing deliverables: callers use fresh output directories.
    if any(n.startswith(("pattern", "clo3d_", "pieces_")) for n in os.listdir(out)):
        raise ValueError("Output contains a previous bundle; choose a fresh --out directory")
    with tempfile.TemporaryDirectory(prefix="pattern-stage-", dir=out) as stage:
        for sz, r in work:
            finite(r)
            r["pieces"], r["seams"] = expand_mirrors(r["pieces"], r.get("seams"))
            expanded_chains = []
            for contract in r.get("seam_chains", []):
                sides=("L","R") if any("{side}" in row[0] for key in ("a","b") for row in contract[key]) else (None,)
                for side in sides:
                    c=copy.deepcopy(contract)
                    if side:
                        for key in ("a","b"):
                            c[key]=[[nm.replace("{side}",side),a,b] for nm,a,b in c[key]]
                    expanded_chains.append(c)
            r["seam_chains"]=expanded_chains
            expanded_holds = []
            for h in r.get("holds", []):
                sides = ("L", "R") if any("{side}" in str(h.get(k, "")) for k in ("top", "under")) else (None,)
                for side in sides:
                    q = copy.deepcopy(h)
                    if side:
                        for k in ("top", "under"):
                            q[k] = q[k].replace("{side}", side)
                        if side == "R":
                            q["at"] = {k: [-v[0], v[1]] for k, v in q["at"].items()}
                    expanded_holds.append(q)
            r["holds"] = expanded_holds
            by_name={p["name"]:p for p in r["pieces"]}
            for h in expanded_holds:
                if h.get("top") not in by_name or h.get("under") not in by_name:
                    raise ValueError("Hold references a missing top/under piece")
                names=[n.get("name") for n in by_name[h["top"]]["outline"]]
                if len(h.get("edge",[]))!=2 or any(n not in names for n in h["edge"]):
                    raise ValueError("Hold references a missing top edge")
                if set(h.get("at",{}))!=set(h["edge"]):
                    raise ValueError("Hold placement must name both edge endpoints")
            if allowance is not None:
                for p in r["pieces"]:
                    p["allowance"] = allowance
            checks = r.setdefault("checks", [])
            for p in r["pieces"]:
                try:
                    paths(self_module(), p)
                    checks += fold_checks(p) + darts(self_module(), p)
                    c = neck_check(p)
                    if c:
                        checks.append(c)
                except ValueError as err:
                    checks.append(check(str(err), 1, 0, 0))
            checks += within_checks(r["pieces"])
            r["proportion_results"], pc = proportions(self_module(), r)
            checks += pc
            r["seam_chain_results"], cc = seam_chains(self_module(), r)
            checks += cc
            # Named seam lengths are checked even when fitted shell export is unsupported.
            cloj = {"pieces": []}
            for p in r["pieces"]:
                q = slit_holes(unfold(p))
                cloj["pieces"].append({"name":p["name"], "edges":[
                    {"line":i, "from":n.get("name", ""), "length_mm":length(edge(q,i,64))*10}
                    for i,n in enumerate(q["outline"])]})
            if r.get("seams"):
                rows = seam_table(cloj, r["seams"])
                write_seam_table(rows, os.path.join(stage, f"seams_{sz}.md"))
                bad = [x for x in rows if not x[8]]
                checks.append(check(f"Seams: lengths match within {SEAM_TOL_MM:.0f} mm or declared ease, "
                                    f"{len(rows)} seams (failures)", len(bad), 0, 0))
                for x in bad:
                    checks.append(check(f"seam {x[0]} {x[1]} / {x[3]} {x[4]} (mm)",
                                        x[2] if x[2] is not None else -1, (x[5] or 0)*(1+x[6]), 1))
            internal = any(p.get("darts_in") for p in r["pieces"])
            r["shell_status"] = {"supported": not internal and r.get("shell_status", {}).get("supported", True),
                                 "reason": "Internal dart sewing topology unsupported" if internal else
                                 r.get("shell_status", {}).get("reason", "Outline transfer only; no simulation or fit validation")}
            # Full precision editable data avoids losing constraints through coordinate rounding.
            data = {k:v for k,v in r.items() if k != "checks"}
            data.update(title=title, size=sz, validation_status="pending")
            with open(os.path.join(stage, f"pieces_{sz}.json"), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=1, allow_nan=False)
        good = all(c["expected"] is None or abs(c["value"]-c["expected"]) <= c["tol"]
                   for _,r in work for c in r["checks"])
        if good:
            try:
                offs, _, _ = layout([r["pieces"] for _,r in work])
                for sz,r in work:
                    for p,off in zip(r["pieces"],offs):
                        paths(self_module(), p, off)
                    write_dxf(r["pieces"], offs, os.path.join(stage, f"pattern_{sz}.dxf"), sz)
                    if r["shell_status"]["supported"]:
                        path = os.path.join(stage,f"clo3d_{sz}.json")
                        write_clo3d(r["pieces"],offs,path,sz,r.get("seams"),r.get("holds"))
                        write_clo_script(path,os.path.join(stage,f"clo3d_{sz}.py"))
                write_svg(work, os.path.join(stage,"pattern.svg"), title)
            except ValueError as err:
                work[0][1]["checks"].append(check(str(err),1,0,0))
                good = False
        target = out if good else os.path.join(out,"rejected")
        os.makedirs(target,exist_ok=True)
        for name in os.listdir(stage):
            if not good and not name.startswith(("pieces_", "seams_")):
                continue
            path = os.path.join(stage,name)
            if name.startswith("pieces_"):
                with open(path,encoding="utf-8") as f:
                    data=json.load(f)
                data["validation_status"]="passed_2d" if good else "rejected"
                with open(path,"w",encoding="utf-8") as f:
                    json.dump(data,f,ensure_ascii=False,indent=1,allow_nan=False)
            shutil.move(path,os.path.join(target,name))
        if not good:
            with open(os.path.join(target,"checks.json"),"w",encoding="utf-8") as f:
                json.dump({str(sz):r["checks"] for sz,r in work},f,indent=1)
        for (_, original), (_, computed) in zip(sets, work):
            original.update(computed)
        return good


def self_module():
    return sys.modules[__name__]


def report(sets):
    ok = True
    for sz, r in sets:
        print(f"\n== Size {sz}")
        for c in r["checks"]:
            lab = c["label"]
            display_value = f'{c["value"]:.3f}'
            unit = ("mm" if "(mm" in lab or "mm)" in lab else "deg" if "(deg)" in lab
                    else "" if "(failures)" in lab or "(count)" in lab else "cm")
            label = (lab.replace(" (mm)", "").replace(", mm)", ")").replace(" (deg)", "")
                     .replace(" (failures)", ", failures").replace(" (count)", ""))
            if c["expected"] is None:
                print(f"   {label}: {display_value} {unit}")
                continue
            good = abs(c["value"] - c["expected"]) <= c["tol"]
            ok &= good
            print(f" {'OK' if good else '!!'} {label}: {display_value} {unit} (expected {c['expected']} ± {c['tol']})")
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
    """List of entries: id, name, file, line, aliases, family, text."""
    import re
    out = []
    for sub in KB_DIRS:
        folder = os.path.join(_kb_root(), sub)
        if not os.path.isdir(folder):
            continue
        for fn in sorted(os.listdir(folder)):
            if not fn.endswith(".md") or fn in ("FORMAT.md", "INDEX.md"):
                continue
            path = os.path.join(folder, fn)
            with open(path, encoding="utf-8") as f:
                lines = f.read().split("\n")
            cur = None
            for i, line in enumerate(lines):
                m = re.match(r"^(#{2,3})\s+(.*?)\s*(\{#([a-z0-9\-]+)\})?\s*$", line)
                if m and not line.startswith("####"):
                    if cur:
                        out.append(cur)
                    name, eid = m.group(2).strip(), m.group(4)
                    if name.lower() == "sources":
                        cur = None
                        continue
                    slug = re.sub(r"[^a-z0-9]+", "-", _fold_text(re.sub(r"^[A-Z]?[0-9.]+\s+", "", name))).strip("-")[:48]
                    cur = {"id": eid or slug, "name": name, "file": f"{sub}/{fn}",
                           "line": i + 1, "aliases": "", "family": "", "text": [], "kb": eid is not None}
                    continue
                if cur is not None:
                    cur["text"].append(line)
                    low = line.lower()
                    if low.startswith("- **aliases**"):
                        cur["aliases"] = line.split(":", 1)[-1].strip()
                    elif low.startswith("- **family**"):
                        cur["family"] = line.split(":", 1)[-1].strip()
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
            print("No entry found. Look up published patterns and books, then add an entry (references/kb/FORMAT.md).")
            return 1
        for e in res:
            print(f"{e['id']:<34} {e['name'][:48]:<48} {e['file']}:{e['line']}")
        return 0
    if args.action == "show":
        target = " ".join(args.words)
        e = next((x for x in kb_entries() if x["id"] == target), None) or next(iter(kb_search(target, 1)), None)
        if not e:
            raise SystemExit(f"No entry: {target}")
        print(f"## {e['name']}  ({e['file']}:{e['line']})")
        print("\n".join(e["text"]).strip())
        return 0
    entries = [e for e in kb_entries() if e["kb"]]
    by_file = {}
    for e in entries:
        by_file.setdefault(e["file"], []).append(e)
    lines = ["# Knowledge base index", "", f"{len(entries)} entries. Search: `python scripts/pattern.py kb search <words>`;",
             "full entry: `python scripts/pattern.py kb show <id>`. Format: `FORMAT.md`.", ""]
    for fn, es in by_file.items():
        lines += [f"## {fn}", ""]
        lines += [f"- `{e['id']}`: {e['name']}" + (f" ({e['aliases'][:80]})" if e["aliases"] else "") for e in es]
        lines.append("")
    path = os.path.join(_kb_root(), "kb", "INDEX.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    ids = [e["id"] for e in entries]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    print(f"{len(entries)} entries indexed in {path}" + (f"; duplicate ids: {', '.join(dup)}" if dup else ""))
    return 0


def cmd_clo3d(args):
    d = args.dir or os.environ.get("CLO3D_MCP_DIR") or os.path.join(
        os.environ.get("TEMP", tempfile.gettempdir()), "clo3d_mcp")
    if not os.path.isdir(d):
        raise SystemExit(f"Exchange folder not found: {d}. Start the plugin in CLO3D.")
    with open(args.file, encoding="utf-8") as f:
        data = json.load(f)
    clo3d_command(d, "ping", {}, 10)
    arrange = {}
    if args.arrange:
        with open(args.arrange, encoding="utf-8") as f:
            arrange = json.load(f)
    n0 = clo3d_command(d, "get_pattern_count", {}).get("count", 0)
    idx = {}
    for i, p in enumerate(data["pieces"]):
        k = n0 + i
        clo3d_command(d, "create_pattern", {"points": p["points"]})
        clo3d_command(d, "set_pattern_name", {"pattern_index": k, "name": p["name"]})
        idx[p["name"]] = k
        if args.assemble:
            clo3d_command(d, "set_collision_thickness", {"pattern_index": k, "thickness": 0})  # fabrics have one
            if args.fabric is not None:
                clo3d_command(d, "set_pattern_fabric", {"pattern_index": k, "fabric_index": args.fabric})
            if args.mesh is not None:
                clo3d_command(d, "set_particle_distance", {"pattern_index": k, "distance": args.mesh})
            if p["name"] in arrange:                       # point index, or {"point": i, "orientation": deg}
                ar = arrange[p["name"]]
                ar = ar if isinstance(ar, dict) else {"point": ar}
                params = {"pattern_index": k, "arrangement_index": ar["point"]}
                if ar.get("orientation") is not None:
                    params["orientation"] = ar["orientation"]
                clo3d_command(d, "arrange_pattern", params)
        print(f"{p['name']}: created in CLO3D ({p.get('cut', '')})", flush=True)
    if args.assemble:
        pieces = {p["name"]: p for p in data["pieces"]}
        failed = 0
        for s_ in data.get("seams", []):
            if s_[0] not in pieces or s_[3] not in pieces:
                continue
            (la, sa), (lb, sb) = _clo_edge(pieces[s_[0]], s_[1], s_[2]), _clo_edge(pieces[s_[3]], s_[4], s_[5])
            try:
                clo3d_command(d, "sew", {"pattern_a": idx[s_[0]], "line_a": la, "pattern_b": idx[s_[3]], "line_b": lb,
                                         "direction_a": sa, "direction_b": sb})
            except SystemExit as err:
                failed += 1
                print("seam failed:", s_, err, flush=True)
        for h in data.get("holds", []):     # wrap: the top front's edge onto an internal line of the under front
            if h["top"] not in pieces or h["under"] not in pieces:
                continue
            line, fwd = _clo_edge(pieces[h["top"]], h["edge"][0], h["edge"][1])
            a, b = (h["edge"][0], h["edge"][1]) if fwd else (h["edge"][1], h["edge"][0])
            ch = clo3d_command(d, "create_internal_shape", {"pattern_index": idx[h["under"]],
                                                            "points": [h["at"][a], h["at"][b]], "closed": False})
            try:
                clo3d_command(d, "sew", {"pattern_a": idx[h["top"]], "line_a": line, "pattern_b": idx[h["under"]],
                                         "line_b": 0, "child_b": ch["child_index"], "direction_a": True, "direction_b": True})
                if h.get("layer"):
                    clo3d_command(d, "set_pattern_state", {"pattern_index": idx[h["top"]], "layer": h["layer"]})
            except SystemExit as err:
                failed += 1
                print("hold failed:", h["top"], err, flush=True)
        print(f"{len(data.get('seams', [])) - failed} seams sewn, {failed} failed. Pieces without an arrangement "
              "point must be placed by hand in CLO3D before simulating.", flush=True)
    if args.stop:
        clo3d_command(d, "stop", {}, 10)
    return 0

# ------------------------------------------------------------------ command line


def load_measurements(args):
    own = {}
    if args.measurements:
        with open(args.measurements, encoding="utf-8") as f:
            own = json.load(f)
    body, _, ease, _ = resolve_measurements(args.body, args.size, own)
    return body, {k:v for k,v in own.items() if k not in ("body", "ease")}, ease


def cmd_glove(args):
    if args.measurements and args.sizes:
        raise ValueError("--measurements and --sizes cannot be combined; use a single personal size")
    own = {}
    if args.measurements:
        with open(args.measurements, encoding="utf-8") as f:
            data = json.load(f)
            if set(data) - {"hand"}:
                raise ValueError("Glove measurements accept only hand (in mm)")
            own = data.get("hand", {})
            if set(own) - set(GLOVE_HAND) or any(not isinstance(v, (int,float)) or not math.isfinite(v) or v <= 0 for v in own.values()):
                raise ValueError("Unsupported or invalid hand measurements")
    sizes = args.sizes.split(",") if args.sizes else [args.size or "7"]
    sets = []
    for sz in sizes:
        h = glove_hand(float(sz), own if not args.sizes else {})
        if args.length is not None:
            h["end_below_wrist"] = args.length * 10
        if args.end_girth is not None:
            h["end_girth"] = args.end_girth * 10
        left = block_glove(h)
        right = [mirror_piece(p, "Glove R " + p["name"]) for p in left["pieces"]]
        for p in left["pieces"]:
            p["name"] = "Glove L " + p["name"]
        seams = [[f"Glove {side} {a[0]}", a[1], a[2], f"Glove {side} {a[3]}", a[4], a[5]] + list(a[6:])
                 for side in ("L", "R") for a in left["seams"]]
        sources = {k: {"source": "input" if k in own else "table", "reference_size":str(sz)} for k in h}
        if args.length is not None:
            sources["end_below_wrist"]={"source":"command_line", "input_unit":"cm"}
        if args.end_girth is not None:
            sources["end_girth"]={"source":"command_line", "input_unit":"cm"}
        sets.append((sz, {"pieces": left["pieces"] + right, "checks": left["checks"], "seams": seams, "resolved_measurements": h, "measurement_unit": "mm",
                          "measurement_provenance": sources}))
    export(sets, args.out, "glove", args.allowance)
    ok = report(sets)
    print(f"\nFiles written to {os.path.abspath(args.out)}")
    return 0 if ok else 2


def cmd_block(args):
    if args.measurements and args.sizes:
        raise ValueError("--measurements and --sizes cannot be combined; use a single personal size")
    if args.block == "glove":
        return cmd_glove(args)
    body, own, a = load_measurements(args)
    default = "8" if body == "children" else str(BASE[body]["ref"])
    sizes = args.sizes.split(",") if args.sizes else [args.size or default]
    sets = []
    for i, sz in enumerate(sizes):
        std = standard_measurements(body, sz)
        m = complete({**std, **(own if not args.sizes else {})}, body)
        if i == 0 and own and not args.sizes:
            missing = sorted(set(std) - set(own))
            if missing:
                print("Measurements taken from the standard table:", ", ".join(missing))
        res = build(args.block, m, a, body)
        _, _, _, prov = resolve_measurements(body, sz, own)
        res.update(resolved_measurements=m, measurement_provenance=prov, resolved_ease=a, measurement_unit="cm", body=body)
        sets.append((sz, res))
    export(sets, args.out, f"{args.block} {body}", args.allowance)
    ok = report(sets)
    print(f"\nFiles written to {os.path.abspath(args.out)}")
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
        if len(p.get("outline", [])) < 3 or not all(len(n.get("p", [])) == 2 for n in p["outline"]):
            raise SystemExit(f"Invalid piece: {p.get('name', '?')} (at least 3 nodes with \"p\": [x, y])")
    sz = str(data.get("size", "one"))
    sets = [(sz, dict(data, checks=[], seams=data.get("seams", [])))]
    export(sets, args.out, data.get("title", "pattern"), args.allowance)
    ok = report(sets)
    for p in sets[0][1]["pieces"]:
        print(f"{p['name']}: " + ", ".join(f"edge {i} = {length(edge(p, i)):.2f} cm" for i in range(len(p["outline"]))))
    print(f"Output diagnostics/files: {os.path.abspath(args.out)}")
    return 0 if ok else 2


def test():
    for body, sizes in (("women", ["34", "38", "46"]), ("men", ["44", "48", "56"]), ("children", ["4", "8", "14"])):
        for sz in sizes:
            res = build("all", complete(standard_measurements(body, sz), body), EASE[body], body)
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
    m, a = complete(standard_measurements("women", 38), "women"), EASE["women"]
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
    h = [block_skirt(complete(standard_measurements("women", t), "women"), EASE["women"], "women")["pieces"][0]["outline"][-3]["p"][0]
         for t in (36, 38, 40)]
    assert h[0] < h[1] < h[2], "grading"
    with tempfile.TemporaryDirectory() as d:
        sets = [(t, build("all", complete(standard_measurements("women", t), "women"), EASE["women"], "women"))
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
            # Keep the original construction assertions, then test the narrowed export contract.
            for c in res_["checks"]:
                assert c["expected"] is None or abs(c["value"]-c["expected"]) <= c["tol"], (sp_,c)
            ok_ = garment.write(res_, d)
            if sp_ == "velvet-coat/coat.json":
                assert not ok_, "Known wide collar allowance must be rejected, not repaired silently"
                assert not os.path.exists(os.path.join(d,"pattern.svg"))
                with open(os.path.join(d,"rejected","checks.json"),encoding="utf-8") as f:
                    rejected_ = json.load(f)
                assert any("Back: CUT:" in c["label"] for rows in rejected_.values() for c in rows)
            else:
                assert ok_, sp_
                with open(os.path.join(d,"pieces_38.json"),encoding="utf-8") as f:
                    saved_ = json.load(f)
                if sp_.endswith("jacket_fitted.json"):
                    assert saved_["shell_status"]["supported"] is False
                    assert any(p.get("darts_in") for p in saved_["pieces"])
                    assert not os.path.exists(os.path.join(d,"clo3d")), "Fitted shell must be suppressed"
                else:
                    assert os.path.exists(os.path.join(d,"clo3d","clo3d_38.json"))
    gr = tr_["grain"]
    ys_ = [n["p"][1] for n in tr_["outline"]]
    assert all(min(ys_) <= g[1] <= max(ys_) for g in gr), ("grain line outside the trank", gr)
    print("All bounded tests pass; fitted shell unsupported, velvet coat allowance rejected as expected.")
    return 0


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows consoles default to cp1252
    ap = argparse.ArgumentParser(description="Pattern-making engine (inputs in cm).")
    sp = ap.add_subparsers(dest="cmd", required=True)
    for name in ("block", "measurements"):
        p = sp.add_parser(name)
        if name == "block":
            p.add_argument("block", choices=BLOCKS + ("all", "glove"))
            p.add_argument("--length", type=float, help="glove: end of the glove below the wrist crease, cm")
            p.add_argument("--end-girth", type=float, help="glove: arm girth at the end of the glove, cm")
            p.add_argument("--out", default="pattern_out")
            p.add_argument("--sizes", help="standard-only grading, e.g. 36,38,40; incompatible with --measurements")
            p.add_argument("--allowance", type=float, help="default seam allowance in cm (hems unchanged)")
        p.add_argument("--body", choices=("women", "men", "children"), default="women")
        p.add_argument("--size", help="standard size (women 34-48, men 44-58, children: age 4-14; glove: 6 to 10)")
        p.add_argument("--measurements", help="personal body JSON in cm (glove hand in mm); unsupported keys and --sizes combination rejected")
    p = sp.add_parser("garment", help="draft a whole garment from a spec (references/garment-spec.md)")
    p.add_argument("spec")
    p.add_argument("--out", default="garment_out")
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
    p = sp.add_parser("clo3d", help="send a clo3d_<size>.json file to the CLO3D plugin")
    p.add_argument("file")
    p.add_argument("--dir", help="plugin exchange folder (default: %%TEMP%%/clo3d_mcp)")
    p.add_argument("--stop", action="store_true", help="stop the plugin listener after sending")
    p.add_argument("--assemble", action="store_true", help="also sew the seams of the file, collision thickness 0")
    p.add_argument("--fabric", type=int, help="fabric index for every piece")
    p.add_argument("--mesh", type=float, help="mesh size in mm for every piece (8 fitted knits, 4 to 6 gloves)")
    p.add_argument("--arrange", help="JSON file {piece name: point index or {\"point\": i, \"orientation\": deg}}")
    p = sp.add_parser("kb", help="knowledge base: search <words>, show <id>, index")
    p.add_argument("action", choices=("search", "show", "index"))
    p.add_argument("words", nargs="*")
    sp.add_parser("test")
    args = ap.parse_args()
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
    try:
        sys.exit(main())
    except (ValueError, OSError, ImportError) as err:
        print(f"Error: {err}", file=sys.stderr)
        sys.exit(2)
