"""Regression coverage for straight boundary darts and complete graded SVGs."""
import copy
import json
import xml.etree.ElementTree as ET

import pytest

import pattern as P
from validation import darts
from test_acceptance import rect, piece_cli, invoke, assert_no_bundle, dxf_read


def straight_dart():
    p = rect('Dart panel')
    p['grain'] = [[3, 10], [3, 20]]
    p['outline'][1:1] = [
        {'name': 'mouth1', 'p': [8, 0]},
        {'name': 'dart', 'p': [10, 10], 'dart': True},
        {'name': 'mouth2', 'p': [12, 0]},
    ]
    P.true_boundary_darts(p)
    return p


@pytest.mark.parametrize('leg', ['mouth1', 'dart'])
@pytest.mark.parametrize('rotation', [0, 2])
def test_curved_boundary_dart_cli_rejected(tmp_path, leg, rotation):
    p = straight_dart()
    node = next(n for n in p['outline'] if n['name'] == leg)
    node['c'] = [[5, 3], [6, 7]] if leg == 'mouth1' else [[14, 7], [15, 3]]
    p['outline'] = p['outline'][rotation:] + p['outline'][:rotation]
    before = copy.deepcopy(p)
    r = piece_cli(tmp_path, {'pieces': [p]})
    assert r.returncode == 2, r.stdout + r.stderr
    assert 'straight' in (r.stdout + r.stderr).lower()
    assert 'Traceback' not in r.stderr
    assert_no_bundle(tmp_path / 'out')
    rejected = json.loads((tmp_path / 'out/rejected/pieces_one.json').read_text())
    assert rejected['validation_status'] == 'rejected'
    assert rejected['pieces'] == [before]
    assert json.loads((tmp_path / 'out.json').read_text())['pieces'] == [before]


@pytest.mark.parametrize('leg', ['mouth1', 'dart'])
@pytest.mark.parametrize('kind', ['collinear', 'overshoot', 'near_collinear_loop'])
def test_bezier_dart_syntax_rejected_without_chord_shortcut(leg, kind):
    p = straight_dart()
    i = next(i for i, n in enumerate(p['outline']) if n['name'] == leg)
    a, b = p['outline'][i]['p'], p['outline'][i + 1]['p']
    fractions = (1 / 3, 2 / 3) if kind == 'collinear' else (2, -1)
    controls = [[a[k] + t * (b[k] - a[k]) for k in (0, 1)] for t in fractions]
    if kind == 'near_collinear_loop':
        controls[0][0] += 1e-8
    p['outline'][i]['c'] = controls
    before = copy.deepcopy(p)
    with pytest.raises(ValueError, match='straight'):
        darts(P, p)
    assert p == before


def test_straight_dart_with_curved_adjacent_seams_still_exports(tmp_path):
    p = straight_dart()
    # Truing creates curved adjacent seams; these are not the actual dart legs.
    assert 'c' in p['outline'][0] and 'c' in p['outline'][3]
    r = piece_cli(tmp_path, {'pieces': [p]})
    assert r.returncode == 0, r.stdout + r.stderr
    dxf_read(tmp_path / 'out/pattern_one.dxf')
    assert json.loads((tmp_path / 'out/pieces_one.json').read_text())['pieces'] == [p]


def marked_panel(shift=0, name='Panel'):
    p = rect(name, 20 + shift)
    p.update(cut=f'{1 + shift} on fold', fold=[3],
             grain=[[2 + shift, 10], [2 + shift, 20]],
             darts_in=[[[10 + shift, 5], [12 + shift, 15],
                        [10 + shift, 25], [8 + shift, 15]]],
             lines=[[[1 + shift, 2], [19 + shift, 2]]],
             buttons=[[10 + shift, 3]], notches=[{'edge': 1, 'd': 10}],
             holes=[{'name': 'Hole "<&', 'outline': [
                 {'p': [x + shift, y]} for x, y in [(3, 24), (5, 24), (5, 26), (3, 26)]
             ]}])
    return p


def points(element):
    return [tuple(map(float, s.split(','))) for s in element.get('points').split()]


def same_path(actual, expected, closed=False):
    if len(actual) != len(expected):
        return False
    variants = [actual]
    if closed:
        variants = [seq[i:] + seq[:i] for seq in (actual, actual[::-1]) for i in range(len(seq))]
    return any(all(P.dist(a, b) < .002 for a, b in zip(seq, expected)) for seq in variants)


def assert_svg_paths(root, expected, off, size=None, name=None):
    scope = root
    if size is not None:
        groups = [e for e in root.iter() if e.tag.endswith('}g')
                  and e.get('data-size') == size and e.get('data-piece') == name]
        assert len(groups) == 1, (size, name, 'missing size/piece group')
        scope = groups[0]
    for layer, seqs in expected.items():
        actual = [e for e in scope.iter() if e.get('data-layer') == layer]
        for seq in seqs:
            wanted = [(x * 10 + off[0], y * 10 + off[1]) for x, y in seq]
            assert any(same_path(points(e), wanted, e.tag.endswith('}polygon')) for e in actual), (size, layer, wanted)
    return scope


def panel_expected(shift):
    w = 20 + shift
    hole = [(3 + shift, 24), (5 + shift, 24), (5 + shift, 26), (3 + shift, 26)]
    # Explicit fixture coordinates, independent of construction_marks()/notches().
    return {
        'CUT': [[(0, -1), (w + 1, -1), (w + 1, 31), (0, 31)], hole],
        'SEAM': [[(0, 0), (w, 0), (w, 30), (0, 30)], hole],
        'DART': [[(10 + shift, 5), (12 + shift, 15), (10 + shift, 25),
                  (8 + shift, 15), (10 + shift, 5)]],
        'INTERNAL': [[(1 + shift, 2), (19 + shift, 2)]],
        'BUTTON': [[(9.7 + shift, 3), (10.3 + shift, 3)],
                   [(10 + shift, 2.7), (10 + shift, 3.3)]],
        'FOLD': [[(0, 30), (0, 0)]],
        'GRAIN': [[(2 + shift, 10), (2 + shift, 20)]],
        'NOTCHES': [[(w + 1, 10), (w + .4, 10)]],
    }


def assert_dxf_paths(doc, expected, off):
    lines = [(e.dxf.layer, tuple(e.dxf.start)[:2], tuple(e.dxf.end)[:2])
             for e in doc.modelspace().query('LINE')]
    for layer, seqs in expected.items():
        for seq in seqs:
            seq = seq + seq[:1] if layer in ('CUT', 'SEAM') else seq
            xy = [(x * 10 + off[0], -(y * 10 + off[1])) for x, y in seq]
            for a, b in zip(xy, xy[1:]):
                assert any(l == layer and same_path([c, d], [a, b]) for l, c, d in lines), (layer, a, b)


def test_two_size_svg_complete_marks_cuts_holes_and_metadata(tmp_path):
    sets = [(size, {'pieces': [marked_panel(shift)], 'seam_chains': [
        {'a': [['Panel', 'a', 'b']], 'b': [['Panel', 'a', 'b']], 'why': 'control'}
    ]}) for size, shift in [('A', 0), ('B', 3)]]
    original = copy.deepcopy(sets)
    assert P.export(sets, tmp_path / 'graded', 'Marked sizes')
    root = ET.parse(tmp_path / 'graded/pattern.svg').getroot()
    # Establish that second-size coordinates exist before checking new metadata.
    assert_svg_paths(root, {'GRAIN': panel_expected(3)['GRAIN']}, (10, 25))
    colors = []
    for (size, data), shift in zip(original, [0, 3]):
        scope = assert_svg_paths(root, panel_expected(shift), (10, 25), size, 'Panel')
        assert scope.get('data-cut') == data['pieces'][0]['cut']
        assert any(e.get('data-hole') == 'Hole "<&' for e in scope.iter())
        texts = [e.text for e in scope.iter() if e.tag.endswith('}text')]
        assert texts == ['Panel', f'Size {size}', data['pieces'][0]['cut']]
        colors.append({e.get('stroke') for e in scope.iter() if e.get('points')})
        saved = json.loads((tmp_path / f'graded/pieces_{size}.json').read_text())
        assert saved['pieces'] == data['pieces']
        assert saved['seam_chains'] == data['seam_chains']
        assert saved['validation_status'] == 'passed_2d'
        doc = dxf_read(tmp_path / f'graded/pattern_{size}.dxf')
        assert_dxf_paths(doc, panel_expected(shift), (10, 25))
    assert colors == [{'#000000'}, {'#d62728'}]
    vb = list(map(float, root.get('viewBox').split()))
    assert float(root.get('width')[:-2]) == vb[2]
    assert float(root.get('height')[:-2]) == vb[3]


def test_write_svg_single_size_scale_and_label_escaping(tmp_path):
    label = '" onload="bad & <tag> \'quoted\''
    p = marked_panel(name=label)
    p['cut'] = label
    path = tmp_path / 'single.svg'
    P.write_svg([(label, {'pieces': [p]})], path, label)
    root = ET.parse(path).getroot()
    scope = assert_svg_paths(root, panel_expected(0), (10, 25), label, label)
    assert scope.get('data-cut') == label
    assert all('onload' not in e.attrib for e in root.iter())
    texts = [e for e in scope.iter() if e.tag.endswith('}text')]
    assert [e.text for e in texts] == [label, f'Size {label}', label]
    assert [(e.get('x'), e.get('y')) for e in texts] == [('110.0', '175.0'), ('110.0', '184.0'), ('110.0', '193.0')]
    assert root.get('width') == '240.0mm' and root.get('height') == '465.0mm'
    square = next(e for e in root.iter() if e.tag.endswith('}rect') and e.get('width') == '100')
    assert square.get('height') == '100'


def test_real_cli_bodice_34_40_svg_contains_each_size(tmp_path):
    r = invoke(tmp_path, 'block', 'bodice', '--sizes', '34,40', '--out', tmp_path / 'graded')
    assert r.returncode == 0, r.stdout + r.stderr
    data = [json.loads((tmp_path / f'graded/pieces_{size}.json').read_text()) for size in ('34', '40')]
    offsets, _, _ = P.layout([d['pieces'] for d in data])
    root = ET.parse(tmp_path / 'graded/pattern.svg').getroot()
    for d in data:
        for p, off in zip(d['pieces'], offsets):
            assert_svg_paths(root, {'GRAIN': [p['grain']]}, off)
    for size, d in zip(('34', '40'), data):
        doc = dxf_read(tmp_path / f'graded/pattern_{size}.dxf')
        for p, off in zip(d['pieces'], offsets):
            # Grain comes directly from saved JSON, not the shared marker helper.
            expected = {'GRAIN': [p['grain']], 'CUT': [P.cut_line(p)], 'SEAM': [P.outline(p)]}
            assert_svg_paths(root, {'GRAIN': expected['GRAIN']}, off)
            assert_svg_paths(root, expected, off, size, p['name'])
            assert_dxf_paths(doc, expected, off)
        assert d['seam_chains'] and d['validation_status'] == 'passed_2d'
