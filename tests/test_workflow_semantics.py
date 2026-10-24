"""Independent review S1/L1-L5: saved artifacts and immutable original repros.

SVG inputs are parsed as inert XML only. No browser or external resource access.
"""
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import ezdxf
import pytest
import workflow as W
from test_workflow import control, resized_companion, takeup_control

REPRO = Path(__file__).parent / 'fixtures/workflow/review'
SVG = '{http://www.w3.org/2000/svg}'


def original(name):
    return W.load(REPRO / (name + '.json'))


def rebound(out, artifact, before):
    m = W.load(out / 'workflow-bundle.json')
    m['artifacts'][artifact] = W.filehash(out / artifact)
    W.save(out / 'workflow-bundle.json', m)
    assert W.load(out / 'workflow.json') == before
    assert m['contract_sha256'] == W.digest(before)
    assert all(W.filehash(out / n) == h for n, h in m['artifacts'].items())


@pytest.fixture
def bundle(tmp_path):
    out = tmp_path / 'valid'
    W.export_workflow(control(), out)
    assert W.verify_bundle(out / 'workflow-bundle.json')['status'] == 'exported-2D-verified'
    return out


@pytest.mark.parametrize('mutation', [
    'original-active', 'event', 'script', 'external-image', 'foreign', 'local-use',
    'transform', 'style', 'viewport', 'hidden', 'text-position', 'stroke',
    'nested-svg', 'doctype', 'processing-instruction',
])
def test_svg_safe_effective_writer_format(bundle, tmp_path, mutation):
    path = bundle / 'pattern.svg'
    tree = ET.parse(path); root = tree.getroot(); group = root.find(SVG + 'g')
    if mutation in ('original-active', 'event'): root.set('onload', 'void(0)')
    if mutation in ('original-active', 'script'):
        ET.SubElement(root, SVG + 'script').text = '/* inert review marker; active content must be rejected */'
    if mutation in ('original-active', 'external-image'):
        ET.SubElement(root, SVG + 'image', {'href':'https://example.invalid/review-probe.png', 'width':'1', 'height':'1'})
    if mutation == 'foreign': ET.SubElement(group, SVG + 'foreignObject')
    if mutation == 'local-use': ET.SubElement(group, SVG + 'use', {'href':'#missing'})
    if mutation == 'transform': group.set('transform', 'scale(2)')
    if mutation == 'style': group.set('style', 'transform:scale(2)')
    if mutation == 'viewport': root.set('viewBox', '100 -120 ' + ' '.join(root.get('viewBox').split()[2:]))
    if mutation == 'hidden': group.set('display', 'none')
    if mutation == 'text-position': group.find(SVG + 'text').set('x', '999')
    if mutation == 'stroke': group.find(SVG + 'polygon').set('stroke', 'url(https://example.invalid/paint)')
    if mutation == 'nested-svg': ET.SubElement(group, SVG + 'svg')
    tree.write(path, encoding='utf-8', xml_declaration=True)
    if mutation == 'doctype': path.write_text('<!DOCTYPE svg [<!ENTITY probe "inert">]>' + path.read_text().split('?>',1)[1])
    if mutation == 'processing-instruction': path.write_text('<?xml-stylesheet href="https://example.invalid/style"?>' + path.read_text().split('?>',1)[1])
    rebound(bundle, path.name, control())
    with pytest.raises(ValueError, match='SVG.*(unsupported|writer|readback)'):
        W.verify_bundle(bundle / 'workflow-bundle.json')
    with pytest.raises(ValueError, match='SVG.*(unsupported|writer|readback)'):
        W.reexport(bundle / 'workflow-bundle.json', tmp_path / 'reexport')
    assert not (tmp_path / 'reexport').exists()


@pytest.mark.parametrize('layer', ['CUT','SEAM','INTERNAL','BUTTON','NOTCHES','GRAIN','TEXT'])
def test_all_emitted_dxf_entities_are_planar(bundle, layer):
    path = bundle / 'pattern_one.dxf'; doc = ezdxf.readfile(path)
    entity = next(e for e in doc.modelspace() if e.dxf.layer == layer)
    key = 'insert' if layer == 'TEXT' else 'end'
    pt = getattr(entity.dxf, key); setattr(entity.dxf, key, (pt.x, pt.y, 100))
    doc.saveas(path); rebound(bundle, path.name, control())
    with pytest.raises(ValueError, match='DXF.*(planar|unsupported|writer)'):
        W.verify_bundle(bundle / 'workflow-bundle.json')


@pytest.mark.parametrize('mutation', ['swap-labels','rotation','height','width','oblique','align','extrusion','thickness','invisible','layer-hidden','text-style'])
def test_dxf_positioned_roles_and_effective_properties(bundle, mutation):
    path = bundle / 'pattern_one.dxf'; doc = ezdxf.readfile(path)
    texts = list(doc.modelspace().query('TEXT')); text = texts[0]
    if mutation == 'swap-labels': texts[0].dxf.insert, texts[-1].dxf.insert = texts[-1].dxf.insert, texts[0].dxf.insert
    if mutation in ('rotation','height','width','oblique'): setattr(text.dxf, mutation, 20)
    if mutation == 'align': text.dxf.halign = 2
    if mutation == 'extrusion': next(iter(doc.modelspace().query('LINE'))).dxf.extrusion = (0,1,0)
    if mutation == 'thickness': next(iter(doc.modelspace().query('LINE'))).dxf.thickness = 10
    if mutation == 'invisible': text.dxf.invisible = 1
    if mutation == 'layer-hidden': doc.layers.get('SEAM').off()
    if mutation == 'text-style': doc.styles.get('Standard').dxf.width = 2
    doc.saveas(path); rebound(bundle, path.name, control())
    with pytest.raises(ValueError, match='DXF.*(text|unsupported|writer|planar)'):
        W.verify_bundle(bundle / 'workflow-bundle.json')


def test_original_saved_curve_contract_rejects_fresh_export(tmp_path):
    d = original('curve-saved-contract')
    assert W.validate(d)['status'] == 'proposal-ready'
    with pytest.raises(ValueError, match='saved.*(target|seam|precision)'):
        W.export_workflow(d, tmp_path / 'curve')
    assert not (tmp_path / 'curve').exists()


def moderate_curve():
    d = original('curve-saved-contract'); width, height = 20, 2
    r = 4 * height / width
    arc = width / 2 * (math.sqrt(1+r*r) + math.asinh(r)/r)
    d['profile']['parameters']['span']['value'] = arc * 10
    d['design']['dimensions']['attachment']['value'] = arc
    p = d['recipe']['pieces'][0]
    p['outline'][1]['p'][0] = p['outline'][2]['p'][0] = width
    p['outline'][0]['c'] = [[width/3,-height*4/3],[width*2/3,-height*4/3]]
    return d


def test_saved_curve_measurements_are_actual_mm_segments(tmp_path):
    d = moderate_curve(); out = tmp_path / 'moderate'
    result = W.export_workflow(d, out)
    doc = ezdxf.readfile(out / 'pattern_one.dxf')
    lines = list(doc.modelspace().query('LINE[layer=="SEAM"]'))
    actual_cm = sum((e.dxf.end - e.dxf.start).magnitude for e in lines[:16]) / 10
    assert result['attachments'][0]['a_cm'] == pytest.approx(actual_cm, abs=1e-10)
    assert abs(actual_cm - W.validate(d)['attachments'][0]['a_cm']) > 1e-4
    for kind in ('dxf','svg'):
        evidence = result['readback']['saved_contracts'][kind]
        assert evidence['coordinate_unit'] == 'mm'
        assert evidence['coordinate_decimals'] == 3
        assert evidence['measurement_unit'] == 'cm'
        assert evidence['ordinary_tolerance_mm'] == 1
        assert evidence['ports']['panel.opening']['raw_length_cm'] == pytest.approx(actual_cm, abs=1e-10)
    assert W.reexport(out / 'workflow-bundle.json', tmp_path / 'again')['attachments'] == result['attachments']


@pytest.mark.parametrize('kind', ['pleat','overlap','dart','ease','stretch','gather'])
def test_saved_deductions_relations_and_landmarks(tmp_path, kind):
    if kind in ('pleat','overlap'): d = takeup_control(kind)
    elif kind == 'dart':
        d = resized_companion(control(),2)
        d['recipe']['pieces'][2]['darts_in'] = [[[10,5],[9,0],[11,0]]]
        port = d['components'][2]['ports'][0]; port['target'] = 'finished.attachment'
        d['design']['dimensions']['takeup'] = dict(d['design']['dimensions']['attachment'], value=2, kind='dart_takeup')
        port['deductions'] = [dict(kind='dart',segment=0,target='finished.takeup',source='synthetic mouth',dart_index=0)]
    else:
        d = resized_companion(control(),1)
        d['design']['dimensions']['intent'] = dict(value=1 if kind=='ease' else 1.05,kind=kind,
            unit='cm' if kind=='ease' else 'ratio',source='fixed control',basis='engineering-selected')
        a = d['attachments'][0]; a['a'],a['b'] = a['b'],a['a']
        a['relation'] = dict(mode=kind,target='finished.intent',material_id='synthetic-woven',reason='fixed control')
    result = W.export_workflow(d, tmp_path / kind)
    for record in result['readback']['saved_contracts'].values():
        assert record['ports'] == result['ports']
        assert record['attachments'] == result['attachments']
    if kind in ('pleat','overlap'):
        assert result['ports']['panel.opening']['deduction_cm'] == pytest.approx(2)


def test_original_resolved_allowance_extension():
    with pytest.raises(ValueError, match='resolved.*allowance'):
        W.extend(original('allowance-baseline'), original('allowance-extension-target'))


@pytest.mark.parametrize('edge', ['0','2','3'])
def test_per_edge_allowance_extension(edge):
    d = control(); d['recipe']['pieces'][0]['allowances'] = {edge:original('allowance-baseline')['recipe']['pieces'][0]['allowance']}
    with pytest.raises(ValueError, match='resolved.*allowance'):
        W.extend(d, original('allowance-extension-target'))


def test_constant_resolved_allowances_allow_geometry_extension(tmp_path):
    d = original('allowance-baseline')
    d['recipe']['pieces'][0]['allowance'] = {'op':'mul','args':[
        {'op':'literal','value':1,'unit':'cm'}, {'op':'div','args':[{'op':'param','id':'finished.length'},{'op':'param','id':'finished.length'}]}]}
    changed = W.extend(d, original('allowance-extension-target'))
    assert W.generate(changed)['pieces'][0]['allowance'] == 1
    assert W.export_workflow(changed,tmp_path/'extended')['status'] == 'exported-2D-verified'


def test_original_zero_calibration():
    with pytest.raises(ValueError, match='calibrat|scale'):
        W.validate(original('zero-calibration'))


@pytest.mark.parametrize('field,value', [('value',0),('kind','seam_allowance'),('kind','body_girth'),('basis','nominal'),('basis','engineering-selected'),('unit','ratio')])
def test_measured_calibration_internal_consistency(field, value):
    d = original('zero-calibration')
    q = d['analysis']['scale']['length']; q.update(value=10,kind='finished_length',basis='observed')
    q[field] = value
    with pytest.raises(ValueError, match='calibrat|scale'):
        W.validate(d)


@pytest.mark.parametrize('unit,value', [('cm',10),('mm',100)])
def test_positive_measured_and_uncalibrated_relative(unit, value):
    d = original('zero-calibration')
    d['analysis']['scale']['length'].update(value=value,unit=unit,kind='finished_length',basis='observed')
    assert W.validate(d)['status'] == 'proposal-ready'
    assert W.validate(control())['status'] == 'proposal-ready'


@pytest.mark.parametrize('layer', ['DART','FOLD'])
def test_additional_emitted_dxf_marks_are_planar(tmp_path, layer):
    d = control(); p = d['recipe']['pieces'][0]
    if layer == 'DART': p['darts_in'] = [[[10,5],[9,0],[11,0]]]
    else: p['fold'] = [3]
    out = tmp_path / layer
    W.export_workflow(d, out)
    assert W.verify_bundle(out/'workflow-bundle.json')['status'] == 'exported-2D-verified'
    path = out/'pattern_one.dxf'; doc = ezdxf.readfile(path)
    e = next(e for e in doc.modelspace() if e.dxf.layer == layer)
    e.dxf.start = (e.dxf.start.x, e.dxf.start.y, 100)
    doc.saveas(path); rebound(out,path.name,d)
    with pytest.raises(ValueError, match='DXF.*planar'):
        W.verify_bundle(out/'workflow-bundle.json')


def test_saved_pair_is_checked_even_when_each_target_passes(tmp_path):
    d = original('curve-saved-contract')
    target = d['design']['dimensions']['attachment']['value'] - .07
    d['design']['dimensions']['attachment']['value'] = target
    d['profile']['parameters']['span']['value'] = target * 10
    # Both individual saved lengths are within 1 mm of this midpoint target.
    # The actual saved pair still differs by >1 mm; a port-only check is insufficient.
    for node in d['recipe']['pieces'][2]['outline'][1:3]:
        node['p'][0] = {'op':'add','args':[{'op':'param','id':'finished.attachment'},
                                        {'op':'literal','value':.065,'unit':'cm'}]}
    assert W.validate(d)['status'] == 'proposal-ready'
    with pytest.raises(ValueError, match='saved.*paired seam mismatch'):
        W.export_workflow(d,tmp_path/'paired')


def test_saved_internal_landmark_is_checked_when_totals_match(tmp_path):
    d = original('curve-saved-contract')
    arc = d['design']['dimensions']['attachment']['value']
    target = arc * 2 - .06
    d['design']['dimensions']['attachment']['value'] = target
    d['profile']['parameters']['span']['value'] = target * 10
    for i in (0,2):
        p = d['recipe']['pieces'][i]
        if i == 0:
            nodes = [{'name':'a','p':[0,0],'c':[[20,-80],[40,-80]]},
                     {'name':'middle','p':[60,0]},{'name':'b','p':[60+arc,0]}]
        else:
            nodes = [{'name':'a','p':[0,0]}, {'name':'middle','p':[arc,0],'c':[[arc+20,-80],[arc+40,-80]]},
                     {'name':'b','p':[arc+60,0]}]
            d['components'][i]['depends_on'].remove('finished.attachment')
        p['outline'] = nodes + [{'name':'c','p':[60+arc,30]}, {'name':'d','p':[0,30]}]
        if i == 2: d['components'][i]['depends_on'].remove('finished.accessory_depth')
        if i == 0: d['components'][i]['depends_on'].remove('finished.length')
        port = d['components'][i]['ports'][0]
        port['chain'] = [{'piece':p['name'],'from':'a','to':'middle'}, {'piece':p['name'],'from':'middle','to':'b'}]
        port['landmarks'] = [{'id':'start','after':0},{'id':'middle','after':1},{'id':'end','after':2}]
    d['design']['unused']['accessory_depth'] = 'constant depth for independent landmark probe'
    d['attachments'][0]['landmarks'] = ['start','middle','end']
    assert W.validate(d)['status'] == 'proposal-ready'
    with pytest.raises(ValueError, match='saved.*paired landmark mismatch'):
        W.export_workflow(d,tmp_path/'landmark')


@pytest.mark.parametrize('kind', ['pleat','overlap','dart'])
def test_saved_deduction_uses_rounded_mouth_coordinates(tmp_path, kind):
    if kind in ('pleat','overlap'):
        d = takeup_control(kind)
        p = d['recipe']['pieces'][0]
        p['outline'][1]['p'][0] = 8.00004
        p['outline'][2]['p'][0] = 10.00006
        port_key = 'panel.opening'
    else:
        d = resized_companion(control(),2)
        d['recipe']['pieces'][2]['darts_in'] = [[[10,5],[9.00004,0],[11.00006,0]]]
        port = d['components'][2]['ports'][0]; port['target'] = 'finished.attachment'
        d['design']['dimensions']['takeup'] = dict(d['design']['dimensions']['attachment'], value=2, kind='dart_takeup')
        port['deductions'] = [dict(kind='dart',segment=0,target='finished.takeup',source='rounded mouth',dart_index=0)]
        port_key = 'companion.join'
    out = tmp_path/kind
    result = W.export_workflow(d,out)
    assert W.validate(d)['ports'][port_key]['deduction_cm'] == pytest.approx(2.00002,abs=1e-10)
    for record in result['readback']['saved_contracts'].values():
        assert record['ports'][port_key]['deduction_cm'] == pytest.approx(2.0001,abs=1e-10)
