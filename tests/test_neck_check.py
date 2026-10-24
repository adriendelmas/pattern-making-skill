"""Uniform strips versus broad hosts: portable geometry and real CLI regressions."""
import copy
import json
import math
from pathlib import Path

import pytest
from shapely.geometry import Polygon

import pattern as P
from test_acceptance import piece_cli, assert_no_bundle, dxf_read
from test_review_fixes import assert_dxf_paths


def actual_rib():
    return json.loads((Path(__file__).parent / 'fixtures/uniform-rib.json').read_text())


def polygon(points, name='Anonymous panel'):
    return {'name': name, 'allowance': .7,
            'outline': [{'name': str(i), 'p': list(q)} for i, q in enumerate(points)]}


def pinched():
    # Exact existing built-in / parent control: 585 cm², 12 cm ends, 3 cm waist.
    return polygon([(0, 0), (12, 0), (12, 15), (3, 30),
                    (12, 45), (12, 60), (0, 60)], 'pinched control')


def bridge(width=3, host=12):
    lo, hi = (host - width) / 2, (host + width) / 2
    return polygon([(0, 0), (30, 0), (30, lo), (50, lo), (50, 0),
                    (80, 0), (80, host), (50, host), (50, hi),
                    (30, hi), (30, host), (0, host)])


def finger():
    # The protrusion alone exceeds 40 cm²; area cannot establish a broad lobe.
    return polygon([(0, 0), (12, 0), (12, 4.5), (62, 4.5),
                    (62, 7.5), (12, 7.5), (12, 12), (0, 12)])


def transformed(p, angle, reverse, subdivide):
    p = copy.deepcopy(p)
    nodes = p['outline']
    if subdivide:
        nodes = [dict(p=[a['p'][k] + t * (b['p'][k] - a['p'][k]) for k in (0, 1)])
                 for a, b in zip(nodes, nodes[1:] + nodes[:1]) for t in (0, .23, .61)]
    if reverse:
        nodes = nodes[::-1]
    c, s = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    for n in nodes:
        x, y = n['p']
        n['p'] = [c*x - s*y + 123.45, s*x + c*y - 67.89]
    p['outline'] = nodes
    return p


CASES = [
    ('actual', actual_rib(), False),
    ('parent-pinch', pinched(), True),
    ('thin-bridge', bridge(), True),
    ('near-neck-below', bridge(3.8), True),
    ('near-neck-above', bridge(4.01), False),
    ('narrow-hosts', bridge(3, 3.9), False),
    ('broad-hosts', bridge(3, 4.1), True),
    ('long-finger', finger(), False),
] + [(f'rect-{w}-{h}', polygon([(0, 0), (w, 0), (w, h), (0, h)]), False)
     for w, h in [(8, 3.6), (30, 3.6), (53.7929, 3.6), (120, 1.5),
                  (70, 3.99), (70, 4), (70, 4.01)]]


@pytest.mark.parametrize('angle', [0, 37, 90])
@pytest.mark.parametrize('reverse,subdivide', [(False, False), (True, False),
                                             (False, True), (True, True)])
@pytest.mark.parametrize('case,p,reject', CASES, ids=[c[0] for c in CASES])
def test_neck_geometry(case, p, reject, angle, reverse, subdivide):
    p = transformed(p, angle, reverse, subdivide)
    assert Polygon(P.outline(p)).is_valid
    before = copy.deepcopy(p)
    result = P.neck_check(p)
    assert p == before
    assert (result is not None) == reject, result
    if reject:
        assert result['expected'] == 4
        assert result['value'] < 4
        assert abs(result['value'] - result['expected']) > result['tol']


@pytest.mark.parametrize('name', ['Neck rib', 'Lining', 'Anonymous panel'])
def test_name_does_not_decide_neck_check(name):
    rib, host = actual_rib(), pinched()
    rib['name'] = host['name'] = name
    assert P.neck_check(rib) is None
    assert P.neck_check(host) is not None


def test_exact_parent_pinched_measurement_and_constants():
    assert (P.MIN_NECK_CM, P.MIN_SIDE_AREA, P.WITHIN_TOL_CM) == (4, 40, .6)
    assert abs(P.area(P.outline(pinched()))) == 585
    result = P.neck_check(pinched())
    assert result['value'] == pytest.approx(3.279095379403766)
    assert result['tol'] == .71


def test_actual_rib_cli_unchanged_mm_dxf(tmp_path):
    p = actual_rib()
    r = piece_cli(tmp_path, {'pieces': [p]})
    assert r.returncode == 0, r.stdout + r.stderr
    data = json.loads((tmp_path / 'out/pieces_one.json').read_text())
    assert data['validation_status'] == 'passed_2d'
    assert data['pieces'] == [p]
    assert json.loads((tmp_path / 'out.json').read_text()) == {'pieces': [p]}
    doc = dxf_read(tmp_path / 'out/pattern_one.dxf')
    assert doc.header['$INSUNITS'] == 4 and doc.dxfversion == 'AC1024'
    # Source coordinates/marks and explicit layout offset, independent of neck_check.
    expected = {'SEAM': [[n['p'] for n in p['outline']]],
                'GRAIN': [p['grain']], 'INTERNAL': p['lines'],
                'NOTCHES': [[(x, -.7), (x, -.1)] for x in (0, 15.8109, 26.8965, 37.982)]}
    # CUT retains the attachment-station collinear splits as well.
    expected['CUT'] = [[(-.7, -.7), (15.8109, -.7), (26.8965, -.7), (37.982, -.7),
                        (54.4929, -.7), (54.4929, 4.3), (37.982, 4.3),
                        (26.8965, 4.3), (15.8109, 4.3), (-.7, 4.3)]]
    assert_dxf_paths(doc, expected, (17, 22))
    lines = list(doc.modelspace().query('LINE'))
    assert sum(e.dxf.layer == 'NOTCHES' for e in lines) == 4
    seam = [tuple(e.dxf.start)[:2] for e in lines if e.dxf.layer == 'SEAM']
    assert len(seam) == 10
    assert max(x for x, y in seam) - min(x for x, y in seam) == pytest.approx(537.929)
    assert max(y for x, y in seam) - min(y for x, y in seam) == 36


@pytest.mark.parametrize('make', [pinched, bridge])
def test_pinched_cli_rejected_without_bundle(tmp_path, make):
    p = make()
    p['name'] = 'Neck rib'  # A narrow-sounding name must not bypass validation.
    r = piece_cli(tmp_path, {'pieces': [p]})
    assert r.returncode == 2, r.stdout + r.stderr
    assert 'narrowest passage between two wide parts' in r.stdout
    assert_no_bundle(tmp_path / 'out')
    data = json.loads((tmp_path / 'out/rejected/pieces_one.json').read_text())
    assert data['validation_status'] == 'rejected'
    assert data['pieces'] == [p]
    assert json.loads((tmp_path / 'out.json').read_text()) == {'pieces': [p]}
