"""Admission regressions using invented coupons, never complete garment geometry."""
import copy
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import ezdxf
import pytest
import garment as G
import pattern as P
import workflow as W

FIXTURES = Path(__file__).parent / 'fixtures/workflow/assembly'
SVG = '{http://www.w3.org/2000/svg}'


def coupon(name):
    return W.load(FIXTURES / (name + '.json'))


def notch_piece(length=7.1236):
    p = coupon('rounded-endpoints')['recipe']['pieces'][1]
    p['outline'][1]['p'][0] = p['outline'][2]['p'][0] = length
    p['outline'][2]['p'][1] = p['outline'][3]['p'][1] = 6
    p['allowance'] = 1
    p['notches'] = []
    return p


def resolve(p):
    return W.resolve_recipe({'pieces': [p]}, {})[0][0]


@pytest.mark.parametrize('length', [7.1236, 8.1875, math.nextafter(8.0625, math.inf)])
@pytest.mark.parametrize('sign', [1, -1])
def test_rounded_endpoint_admitted_without_rewriting(length, sign):
    p = notch_piece(length)
    G.notch_on(p, 'a', 'b', sign * length)
    assert abs(p['notches'][0]['d']) > length
    before = copy.deepcopy(p)
    result = resolve(p)
    assert result == p == before
    point, _ = P.point_at(P.edge(result, 0), p['notches'][0]['d'])
    assert point == ((length, 0) if sign > 0 else (0, 0))


@pytest.mark.parametrize('length', [7.1234, 8.0625, 8.1875, 7.1236, 8.0])
@pytest.mark.parametrize('sign', [1, -1])
@pytest.mark.parametrize('distance', ['just-outside', 'inside-rounding-band', 'past-rounded', 'past-half-quantum', 'sewing-tolerance'])
def test_only_helper_endpoint_value_can_exceed_edge(length, sign, distance):
    rounded = round(length, 3)
    values = {
        'just-outside': math.nextafter(length, math.inf),
        'inside-rounding-band': length + .0001,
        'past-rounded': math.nextafter(max(length, rounded), math.inf),
        'past-half-quantum': length + .000501,
        'sewing-tolerance': length + .09,
    }
    p = notch_piece(length)
    p['notches'] = [{'edge': 0, 'd': sign * values[distance]}]
    assert abs(p['notches'][0]['d']) != rounded
    with pytest.raises(ValueError, match='notch distance outside edge'):
        resolve(p)


@pytest.mark.parametrize('d,expected_x', [(0, 0), (2, 2), (-2, 5.1236), (7.1236, 7.1236), (-7.1236, 0)])
def test_interior_and_exact_endpoint_signed_distance(d, expected_x):
    p = notch_piece(); p['notches'] = [{'edge': 0, 'd': d}]
    result = resolve(p)
    assert result['notches'] == p['notches']
    assert P.point_at(P.edge(result, 0), d)[0][0] == pytest.approx(expected_x)


@pytest.mark.parametrize('t', [0, .25, 1])
def test_fraction_bounds_unchanged(t):
    p = notch_piece(); p['notches'] = [{'edge': 0, 't': t}]
    assert resolve(p)['notches'] == p['notches']


@pytest.mark.parametrize('key,value', [
    ('t', -.00001), ('t', 1.00001), ('t', math.nan), ('t', math.inf),
    ('d', math.nan), ('d', math.inf), ('d', -math.inf), ('d', True),
])
def test_notch_invalid_numbers_still_reject(key, value):
    p = notch_piece(); p['notches'] = [{'edge': 0, key: value}]
    with pytest.raises(ValueError, match='fraction|finite|number'):
        resolve(p)


@pytest.mark.parametrize('operation', ['curve', 'rotate-translate', 'subdivide', 'reverse'])
def test_helper_endpoints_on_transformed_and_subdivided_edges(operation):
    p = notch_piece()
    p['outline'][0]['c'] = [[2, -1], [5, -1]]
    if operation == 'rotate-translate':
        for node in p['outline']:
            node['p'] = [12 - node['p'][1], node['p'][0] - 4]
            if 'c' in node:
                node['c'] = [[12 - y, x - 4] for x, y in node['c']]
    if operation == 'subdivide':
        G.split_on(p, 'a', 'b', G.edge_len(p, 'a', 'b') / 2, 'middle')
    a, b = ('middle', 'b') if operation == 'subdivide' else ('a', 'b')
    if operation == 'reverse':
        G.notch_on(p, b, a, 0)
    else:
        G.notch_on(p, a, b, G.edge_len(p, a, b))
    before = copy.deepcopy(p)
    assert resolve(p) == before
    assert P.notches(resolve(p)) == P.notches(before)
    n = p['notches'][0]
    n['d'] = P.length(P.edge(p, n['edge'], 64)) + .001
    with pytest.raises(ValueError, match='notch distance outside edge'):
        resolve(p)


def written_marks(out):
    doc = ezdxf.readfile(out / 'pattern_one.dxf')
    assert doc.header['$INSUNITS'] == 4
    layers = {'NOTCHES', 'GRAIN', 'BUTTON', 'INTERNAL', 'FOLD', 'DART'}
    dxf = [(e.dxf.layer, tuple(e.dxf.start), tuple(e.dxf.end))
           for e in doc.modelspace().query('LINE') if e.dxf.layer in layers]
    groups = ET.parse(out / 'pattern.svg').getroot().findall(SVG + 'g')
    svg = [[e.attrib['points'] for e in g.findall(SVG + 'polyline')] for g in groups]
    return dxf, svg


def test_actual_endpoint_marker_coordinates_and_unchanged_baseline(tmp_path):
    data = coupon('rounded-endpoints'); before = copy.deepcopy(data)
    pieces = W.generate(data)['pieces']
    out = tmp_path / 'workflow'; W.export_workflow(data, out)
    verified = W.verify_bundle(out / 'workflow-bundle.json')
    assert verified['readback']['missing_segments'] == 0
    assert W.load(out / 'pieces_one.json')['pieces'] == pieces
    assert W.load(out / 'workflow.json') == data == before
    offsets, _, _ = P.layout([pieces]); ox, oy = offsets[1]
    # Analytic horizontal-edge marks: allowance 1 cm, notch depth .6 cm.
    xs = [7.1236, 0, 2, 5.1236, 0, 7.1236]
    doc = ezdxf.readfile(out / 'pattern_one.dxf')
    entities = list(doc.modelspace().query('LINE[layer=="NOTCHES"]'))[1:7]
    group = ET.parse(out / 'pattern.svg').getroot().findall(SVG + 'g')[1]
    polylines = group.findall(SVG + 'polyline')[-6:]
    for x, entity, polyline in zip(xs, entities, polylines):
        expected = [(round(ox + x * 10, 3), round(oy - 10, 3)),
                    (round(ox + x * 10, 3), round(oy - 4, 3))]
        assert tuple(entity.dxf.start) == (expected[0][0], -expected[0][1], 0)
        assert tuple(entity.dxf.end) == (expected[1][0], -expected[1][1], 0)
        assert [tuple(map(float, pt.split(','))) for pt in polyline.get('points').split()] == expected
    # The unchanged core writer is an independent pre-admission baseline for ALL marks.
    native = tmp_path / 'native'
    assert P.export([('one', {'pieces': copy.deepcopy(pieces)})], str(native), data['title'])
    assert written_marks(out) == written_marks(native)
    again = tmp_path / 'again'; W.reexport(out / 'workflow-bundle.json', again)
    assert W.verify_bundle(again / 'workflow-bundle.json')['ports'] == verified['ports']
    assert W.load(again / 'pieces_one.json')['pieces'] == pieces
    assert written_marks(again) == written_marks(out)


@pytest.mark.parametrize('kind,delta', [('shoulder', .7), ('closure', .3)])
def test_explicit_ease_export_verify_reexport(tmp_path, kind, delta):
    data = coupon(kind + '-ease'); before = copy.deepcopy(data)
    proposal = W.validate(data)
    assert proposal['attachments'][0]['kind'] == kind
    out = tmp_path / kind; result = W.export_workflow(data, out)
    assert W.verify_bundle(out / 'workflow-bundle.json')['attachments'] == result['attachments']
    for saved in result['readback']['saved_contracts'].values():
        assert saved['ordinary_tolerance_mm'] == 1
        pair = saved['attachments'][0]
        assert (pair['kind'], pair['mode'], pair['delta_cm']) == (kind, 'ease', delta)
        assert pair['a_cm'] == pytest.approx(20 + delta)
        assert pair['b_cm'] == 20
        for key, length in [('panel.opening', 20), ('companion.join', 20 + delta)]:
            port = saved['ports'][key]
            assert port['purpose'] == kind
            assert port['target_cm'] == length
            assert port['landmarks'] == pytest.approx({'start': 0, 'middle': length / 2, 'end': length})
    pieces = W.load(out / 'pieces_one.json')['pieces']
    assert pieces == W.generate(data)['pieces']
    assert W.load(out / 'workflow.json') == data == before
    again = tmp_path / 'again'; W.reexport(out / 'workflow-bundle.json', again)
    assert W.verify_bundle(again / 'workflow-bundle.json')['ports'] == result['ports']
    assert W.load(again / 'workflow.json') == before
    assert W.load(again / 'pieces_one.json')['pieces'] == pieces
    assert written_marks(again) == written_marks(out)


@pytest.mark.parametrize('kind', ['shoulder', 'closure', 'side', 'inseam'])
def test_equal_remains_strict(kind):
    data = coupon('shoulder-ease')
    data['attachments'][0].update(kind=kind, relation={'mode': 'equal'})
    for c in data['components']:
        for p in c['ports']: p['purpose'] = kind
    data['design']['dimensions']['companion']['value'] = 20
    del data['design']['dimensions']['intent']
    assert W.validate(data)['attachments'][0]['mode'] == 'equal'
    data['design']['dimensions']['companion']['value'] = 20.7
    with pytest.raises(ValueError, match='independent paired targets'):
        W.validate(data)


@pytest.mark.parametrize('kind,mode', [(k, m) for k in ['shoulder', 'closure', 'side', 'inseam']
                                     for m in ['ease', 'stretch', 'gather']
                                     if k in ('side', 'inseam') or m != 'ease'])
def test_unsupported_modes_remain_rejected(kind, mode):
    data = coupon('shoulder-ease'); data['attachments'][0]['kind'] = kind
    data['attachments'][0]['relation']['mode'] = mode
    for c in data['components']:
        for p in c['ports']: p['purpose'] = kind
    if mode != 'ease':
        data['design']['dimensions']['intent'].update(value=1.035, kind=mode, unit='ratio')
    with pytest.raises(ValueError, match='ordinary seam|only.*equal|requires equal'):
        W.validate(data)


@pytest.mark.parametrize('kind', ['shoulder', 'closure'])
@pytest.mark.parametrize('mutation', ['missing-target', 'unknown-target', 'missing-reason', 'blank-reason',
                                    'missing-material', 'wrong-material', 'wrong-kind', 'wrong-unit',
                                    'changed-amount', 'unknown-mode'])
def test_ease_needs_independent_material_bound_permission(kind, mutation):
    data = coupon(kind + '-ease'); rel = data['attachments'][0]['relation']
    if mutation.startswith('missing-'):
        del rel[{'missing-target': 'target', 'missing-reason': 'reason', 'missing-material': 'material_id'}[mutation]]
    if mutation == 'unknown-target': rel['target'] = 'finished.absent'
    if mutation == 'blank-reason': rel['reason'] = ' '
    if mutation == 'wrong-material': rel['material_id'] = 'another-synthetic-material'
    if mutation == 'wrong-kind': data['design']['dimensions']['intent']['kind'] = 'finished_length'
    if mutation == 'wrong-unit': data['design']['dimensions']['intent']['unit'] = 'ratio'
    if mutation == 'changed-amount': data['design']['dimensions']['intent']['value'] += .2
    if mutation == 'unknown-mode': rel['mode'] = 'custom'
    with pytest.raises(ValueError, match='target|reference|reason|material|kind|unit|mode|relation'):
        W.validate(data)


@pytest.mark.parametrize('kind', ['shoulder', 'closure'])
def test_ease_length_units_and_signed_delta(kind):
    data = coupon(kind + '-ease')
    q = data['design']['dimensions']['intent']; q.update(value=q['value'] * 10, unit='mm')
    W.validate(data)
    a = data['attachments'][0]; a['a'], a['b'] = a['b'], a['a']
    q['value'] *= -1
    assert W.validate(data)['attachments'][0]['delta_cm'] == pytest.approx(q['value'] / 10)


def shift(node, amount):
    node['p'][0] = {'op': 'add', 'args': [node['p'][0], {'op': 'literal', 'value': amount, 'unit': 'cm'}]}


@pytest.mark.parametrize('kind', ['shoulder', 'closure'])
def test_ease_does_not_grow_one_mm_residual_policy(tmp_path, kind):
    data = coupon(kind + '-ease')
    # Each port is within its own target, but their combined residual exceeds 1 mm.
    for i, amount in [(0, -.06), (2, .06)]:
        for node in data['recipe']['pieces'][i]['outline'][2:4]: shift(node, amount)
    with pytest.raises(ValueError, match='paired seam mismatch'):
        W.validate(data)
    data = coupon(kind + '-ease')
    for node in data['recipe']['pieces'][2]['outline'][2:4]: shift(node, .09)
    W.export_workflow(data, tmp_path / 'within')
    for node in data['recipe']['pieces'][2]['outline'][2:4]: shift(node, .02)
    with pytest.raises(ValueError, match='target mismatch'):
        W.export_workflow(data, tmp_path / 'beyond')
    assert not (tmp_path / 'beyond').exists()


@pytest.mark.parametrize('kind', ['shoulder', 'closure'])
def test_ease_internal_landmarks_measured_independently(kind):
    data = coupon(kind + '-ease')
    shift(data['recipe']['pieces'][2]['outline'][1], .11)
    with pytest.raises(ValueError, match='paired landmark mismatch'):
        W.validate(data)


@pytest.mark.parametrize('kind', ['shoulder', 'closure'])
def test_saved_ease_pair_and_landmark_checks(kind):
    data = coupon(kind + '-ease'); pieces = W.generate(data)['pieces']
    by = {p['name']: p for p in pieces}
    edges = {(p['name'], i): P.edge(p, i) for p in pieces for i in range(len(p['outline']))}
    W.saved_contract(data, by, edges, 'synthetic readback control')
    for failure in ('paired seam', 'paired landmark'):
        changed = copy.deepcopy(edges)
        if failure == 'paired seam':
            changed[('Panel', 1)][-1] = (19.94, 0)
            changed[('Companion', 1)][-1] = (pieces[2]['outline'][2]['p'][0] + .06, 0)
        else:
            middle = (pieces[2]['outline'][1]['p'][0] + .11, 0)
            changed[('Companion', 0)][-1] = middle
            changed[('Companion', 1)][0] = middle
        with pytest.raises(ValueError, match='saved.*' + failure + ' mismatch'):
            W.saved_contract(data, by, changed, 'synthetic readback control')
