"""Export validation. Geometry math stays in pattern.py; polygon/readback checks need Shapely/ezdxf."""
import math


def finite(data):
    if isinstance(data, float) and not math.isfinite(data):
        raise ValueError('Coordinates and measurements must be finite')
    if isinstance(data, dict):
        for v in data.values():
            finite(v)
    elif isinstance(data, (list, tuple)):
        for v in data:
            finite(v)


def polygon(points, label):
    from shapely.geometry import Polygon
    from shapely.validation import explain_validity
    finite(points)
    if len(points) < 3 or any(a == b for a, b in zip(points, points[1:] + points[:1])):
        raise ValueError(f'{label}: degenerate path / collapsed edge')
    p = Polygon(points)
    if p.area <= 1e-9 or not p.is_valid or not p.exterior.is_simple:
        raise ValueError(f'{label}: invalid closed path: {explain_validity(p)}')
    return p


def paths(P, p, off=(0, 0)):
    """Check net and allowance at source and actual writer precision; no geometry repair."""
    for label, pts in [('SEAM', P.outline(p)), ('CUT', P.cut_line(p))]:
        polygon(pts, p['name'] + ': ' + label)
        for digits, fmt in ((3, 'DXF'), (3, 'SVG')):
            q = [tuple(round(v, digits) for v in P.mm(a, off)) for a in pts]
            polygon(q, p['name'] + ': rounded ' + fmt + ' ' + label)
    outer = polygon(P.outline(p), p['name'])
    for hl in p.get('holes', []):
        hole = polygon(P.outline(hl), p['name'] + ': hole')
        if not outer.contains(hole):
            raise ValueError(p['name'] + ': hole must be strictly within SEAM')


def validate_dxf(path):
    import ezdxf
    doc = ezdxf.readfile(path)
    audit = doc.audit()
    if audit.errors or audit.fixes or doc.header.get('$INSUNITS') != 4:
        raise ValueError('DXF audit failed or millimetre units missing')
    for layer in ('CUT', 'SEAM'):
        pts = []
        for e in doc.modelspace().query('LINE'):
            if e.dxf.layer != layer:
                continue
            a, b = tuple(e.dxf.start)[:2], tuple(e.dxf.end)[:2]
            if not pts:
                pts = [a]
            if pts[-1] != a:
                raise ValueError(f'DXF {layer}: disconnected path')
            pts.append(b)
            if b == pts[0]:
                polygon(pts[:-1], 'DXF readback ' + layer)
                pts = []
        if pts:
            raise ValueError(f'DXF {layer}: unclosed path')


def darts(P, piece):
    checks = []
    nd = piece['outline']
    for i, n in enumerate(nd):
        if not n.get('dart'):
            continue
        # Controls belong to the edge leaving a node: mouth->apex and apex->mouth.
        # Even collinear controls can overshoot/backtrack; this version supports straight syntax only.
        if 'c' in nd[i-1] or 'c' in n:
            raise ValueError(f"{piece['name']}: dart {n.get('name', i)} requires straight boundary dart legs; "
                             "Bezier controls on either leg are unsupported")
        a, b, c = nd[i-1]['p'], n['p'], nd[(i+1)%len(nd)]['p']
        la, lb = P.dist(a,b), P.dist(c,b)
        checks.append(P.check(f"{piece['name']}: dart {n.get('name', i)} unequal legs (mm)", abs(la-lb)*10, 0, 1))
        if min(la,lb) <= 1e-8:
            raise ValueError('Degenerate dart legs')
        # Rotate the outgoing sewn seam into the incoming leg frame about the fixed dart apex.
        angle = math.atan2(a[1]-b[1],a[0]-b[0])-math.atan2(c[1]-b[1],c[0]-b[0])
        u = P._tangent_end(piece,(i-2)%len(nd),False)
        v = P._tangent_end(piece,(i+1)%len(nd),True)
        v = (v[0]*math.cos(angle)-v[1]*math.sin(angle),v[0]*math.sin(angle)+v[1]*math.cos(angle))
        ang = math.degrees(math.acos(max(-1,min(1,u[0]*v[0]+u[1]*v[1]))))
        checks.append(P.check(f"{piece['name']}: folded dart seam tangent (deg)",ang,0,2))
    for k, dt in enumerate(piece.get('darts_in', [])):
        if len(dt) not in (3,4):
            raise ValueError('Internal dart must be a triangle or four-point fish dart')
        a,b=dt[1],dt[-1]
        for tip in ([dt[0],dt[2]] if len(dt)==4 else [dt[0]]):
            checks.append(P.check(f"{piece['name']}: internal dart {k} unequal legs (mm)",abs(P.dist(tip,a)-P.dist(tip,b))*10,0,1))
    return checks


def proportions(P, data):
    contract = data.get('proportion_contract', {})
    by = {p['name']:p for p in data['pieces']}
    result, checks = {}, []
    def interval(label, value, bounds):
        if len(bounds)!=2 or not all(math.isfinite(x) for x in bounds) or bounds[0]>bounds[1]:
            raise ValueError('Invalid independent target range: '+label)
        lo,hi=bounds
        checks.append(P.check('Proportion '+label, value, (lo+hi)/2, (hi-lo)/2))
    for d in contract.get('dimensions', []):
        try:
            pc=by[d['piece']]; nodes={n['name']:n['p'] for n in pc['outline']}
            a,b=nodes[d['from']],nodes[d['to']]
        except KeyError as err:
            raise ValueError('Proportion contract references missing landmark') from err
        method=d.get('method','distance')
        if method=='distance':
            value=P.dist(a,b)
        elif method in ('x','y'):
            i=0 if method=='x' else 1
            value=abs(a[i]-b[i])
        else:
            raise ValueError('Proportion method must be distance, x or y')
        if d['id'] in result:
            raise ValueError('Duplicate proportion dimension id')
        result[d['id']]=value
        interval(d['id'],value,d['range_cm'])
    for r in contract.get('ratios', []):
        try:
            v=result[r['numerator']]/result[r['denominator']]
        except (KeyError, ZeroDivisionError) as err:
            raise ValueError('Invalid ratio dimension reference') from err
        interval(r['numerator']+'/'+r['denominator'],v,r['range'])
    return result,checks


def seam_chains(P, data):
    by={p['name']:p for p in data['pieces']+data.get('seam_reference_pieces',[])}
    checks, results=[],[]
    def chain_length(chain):
        total=0
        for nm,a,b in chain:
            try:
                p=by[nm]; names=[n.get('name') for n in p['outline']]
                i,j=names.index(a),names.index(b)
            except (KeyError,ValueError) as err:
                raise ValueError('Seam chain references missing piece/node') from err
            if (i+1)%len(names)==j:
                pass
            elif (j+1)%len(names)==i:
                i=j
            else:
                raise ValueError('Seam chain endpoints must be adjacent named nodes')
            total+=P.length(P.edge(p,i,64))
        return total
    for c in data.get('seam_chains',[]):
        a,b=chain_length(c['a']),chain_length(c['b'])
        ease=c.get('ease_cm',0)
        why=c.get('why','')
        if not math.isfinite(ease) or (ease and not why):
            raise ValueError('Seam chain ease needs a finite declared amount and reason')
        if ease and ('dart' in why.lower() or why.lower() in ('side seam','princess seam','forearm seam')):
            raise ValueError('Ordinary side and dart seams require zero ease')
        checks.append(P.check('Seam chain '+why+' (mm)', (a-b)*10,ease*10,1))
        results.append({'a_cm':a,'b_cm':b,'ease_cm':ease,'why':why})
    return results,checks
