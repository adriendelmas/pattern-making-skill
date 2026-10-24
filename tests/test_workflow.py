"""Strict coordination contracts. All inputs are invented portable seam coupons."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest
import pattern as P
import workflow as W

FIXTURES = Path(__file__).parent / 'fixtures/workflow'


def control(name='top.json'):
    return json.loads((FIXTURES/name).read_text())


def bad(data, message):
    with pytest.raises(ValueError, match=message):
        W.validate(data)


@pytest.mark.parametrize('name',['top.json','bottom.json','outerwear.json','one-piece.json','cuff.json'])
def test_same_path_multiple_families(name):
    result=W.validate(control(name))
    assert result['status']=='proposal-ready'
    assert result['support']=='synthetic-attachment-control'
    assert result['fit_status']=='physical-fit-not-approved'
    assert result['attachments'][0]['a_cm']==pytest.approx(20)


@pytest.mark.parametrize('key,value', [('schema',None),('schema','v99'),('status','passed'),('status',True)])
def test_unknown_discriminator_status(key,value):
    d=control();d[key]=value;bad(d,key)


def test_unknown_fields_never_disappear():
    d=control();d['design']['mystery']=42;bad(d,'unknown')


@pytest.mark.parametrize('value',[True,False,float('nan'),float('inf'),-1,0,'20'])
def test_bad_dimensions(value):
    d=control();d['design']['dimensions']['attachment']['value']=value;bad(d,'number|positive|finite')


@pytest.mark.parametrize('key',['unit','source','basis','kind'])
def test_dimension_provenance_required(key):
    d=control();del d['design']['dimensions']['length'][key];bad(d,key)


def test_observations_not_inferred_cm():
    d=control();d['analysis']['landmarks']=[{'source_id':'synthetic-brief','description':'hem',
      'range':[58,62], 'unit':'cm','basis':'observed','uncertainty':'occluded'}]
    bad(d,'calibrat')
    d['analysis']['landmarks'][0].update(range=[.8,1],unit='ratio')
    assert W.validate(d)['status']=='proposal-ready'
    d['analysis']['scale']['kind']='head-estimate';bad(d,'scale')


def test_height_requires_explicit_vertical_mapping():
    d=control();d['profile']['parameters']['height']=copy.deepcopy(d['profile']['parameters']['span'])
    bad(d,'height')


def test_profile_uid_units_row_and_custom_state():
    d=control();d['profile']['parameters']['span']['uid']='wrong';bad(d,'uid')
    d=control();d['profile']['parameters']['span']['value']=210;bad(d,'standard row')
    d=control();d['profile']['template']['custom_allowed']=False
    target=control('custom-target.json')
    with pytest.raises(ValueError,match='custom'):
        W.extend(d,target)
    d=control();d['profile']['template'].update(rule_state='external-unintegrated', custom_allowed=None)
    changed=W.extend(d,target)
    assert W.validate(changed)['template_status']=='custom-target-template-rules-unverified'


def test_missing_component_report_and_export_fails(tmp_path):
    d=control();d['components']=[c for c in d['components'] if c['role']!='collar']
    # Analysis/proposal inventory can be inspected before geometry is drafted.
    d['recipe']['pieces']=d['recipe']['pieces'][:2];d['attachments']=[]
    d['components'][0]['ports']=[]
    result=W.validate(d,geometry=False)
    assert 'collar' in result['missing_components']
    assert result['status']=='proposal-incomplete'
    with pytest.raises(ValueError,match='missing component'):
        W.export_workflow(d,tmp_path/'out')
    assert not (tmp_path/'out/pattern.svg').exists()


@pytest.mark.parametrize('feature,value,missing',[
    ('sleeves','set-in','sleeve'),('neck','collar-stand','collar_stand'),
    ('cuffs',True,'cuff'),('pockets','inseam','pocket_bag'),('pockets','welt','pocket_facing'),
    ('lining',True,'lining'),('closure','zip','closure'),('placket',True,'placket'),
    ('waist','facing','waist_facing')])
def test_conditional_blueprint_inventory(feature,value,missing):
    d=control();d['construction']['features'][feature]=value
    assert missing in W.validate(d,geometry=False)['missing_components']


@pytest.mark.parametrize('collision',['component','piece','node','port','attachment'])
def test_ids_must_be_unique(collision):
    d=control()
    if collision=='component': d['components'][1]['id']=d['components'][0]['id']
    if collision=='piece': d['recipe']['pieces'][1]['name']='Panel'
    if collision=='node': d['recipe']['pieces'][0]['outline'][1]['name']='a'
    if collision=='port': d['components'][0]['ports']*=2
    if collision=='attachment': d['attachments']*=2
    bad(d,'duplicate|collision')


def test_profile_component_binding():
    d=control();d['components'][1]['profile_id']='another-body';bad(d,'profile')


@pytest.mark.parametrize('mutation',['piece','node','nonadjacent','unpaired','quantity','purpose','landmark','reuse'])
def test_actual_edge_pairing(mutation):
    d=control();port=d['components'][0]['ports'][0]
    if mutation=='piece': port['chain'][0]['piece']='Back'
    if mutation=='node': port['chain'][0]['from']='ghost'
    if mutation=='nonadjacent': port['chain'][0]['to']='c'
    if mutation=='unpaired': d['attachments']=[]
    if mutation=='quantity': port['quantity']=2
    if mutation=='purpose': port['purpose']='waist'
    if mutation=='landmark': port['landmarks'][1]['after']=0
    if mutation=='reuse': d['attachments'].append(dict(d['attachments'][0],id='twice'))
    bad(d,'piece|node|adjacent|unpaired|quantity|purpose|landmark|paired')


@pytest.mark.parametrize('fixture',['top.json','bottom.json','cuff.json'])
def test_independent_collar_cuff_waist_mismatch(fixture):
    d=control(fixture)
    for n in d['recipe']['pieces'][2]['outline'][1:3]:
        n['p'][0]={'op':'add','args':[n['p'][0],{'op':'literal','value':1,'unit':'cm'}]}
    bad(d,'target|mismatch')


def test_no_inferred_ease_and_fixed_material_target():
    d=control();d['attachments'][0]['relation']={'mode':'ease'};bad(d,'target|reason|material')
    d=control();d['attachments'][0]['relation']={'mode':'equal','ease_cm':1};bad(d,'unknown')


def test_dependency_coverage_and_safe_expressions():
    d=control();d['components'][2]['depends_on'].remove('finished.attachment');bad(d,'depend')
    d=control();d['recipe']['pieces'][0]['outline'][1]['p'][0]={'op':'eval','code':'1+1'};bad(d,'op|unknown')
    d=control();d['design']['dimensions']['mystery']=copy.deepcopy(d['design']['dimensions']['length']);bad(d,'unused|coverage')
    d=control();d['recipe']['pieces'][0]['outline'][1]['p'][0]={'op':'mul','args':[
        {'op':'param','id':'finished.length'},{'op':'param','id':'finished.attachment'}]};bad(d,'unit|dimension')


def test_target_extension_recomputes_companions_without_global_scaling():
    d=control();target=control('custom-target.json');changed=W.extend(d,target)
    assert changed['profile']['selection']=={'kind':'custom-target'}
    assert changed['profile']['template']==d['profile']['template']
    assert d==control()
    base=W.generate(d)['pieces'];next_=W.generate(changed)['pieces']
    for a,b in zip(base,next_):
        assert P.length(P.edge(a,0))==20
        assert P.length(P.edge(b,0))==pytest.approx(23.7)
        assert a['outline'][2]['p'][1]==b['outline'][2]['p'][1]
        for key in ('allowance','notches','grain','buttons','lines'): assert a[key]==b[key]
    assert W.validate(changed)['template_status']=='custom-target-synthetic-rules-checked'
    del target['dimensions']['length']
    with pytest.raises(ValueError,match='frozen|dimension'):
        W.extend(d,target)


def test_real_export_readback_bound_roundtrip(tmp_path):
    d=control();out=tmp_path/'bundle'
    result=W.export_workflow(d,out)
    assert result['status']=='exported-2D-verified'
    verified=W.verify_bundle(out/'workflow-bundle.json')
    assert verified['readback']['dxf_units']==4
    assert verified['readback']['missing_segments']==0
    assert verified['readback']['svg_test_square_mm']==[100,100]
    assert verified['readback']['mark_segments']>0
    assert verified['fit_status']=='physical-fit-not-approved'
    W.reexport(out/'workflow-bundle.json',tmp_path/'again')
    original=json.loads((out/'workflow.json').read_text())
    again=json.loads((tmp_path/'again/workflow.json').read_text())
    assert again==original
    assert W.verify_bundle(tmp_path/'again/workflow-bundle.json')['attachments']==verified['attachments']


@pytest.mark.parametrize('artifact',['workflow.json','pieces_one.json','pattern.svg','pattern_one.dxf'])
def test_mutated_bound_artifact_rejected(tmp_path,artifact):
    out=tmp_path/'bundle';W.export_workflow(control(),out)
    path=out/artifact
    assert path.exists(), 'workflow export must produce and bind all required artifacts'
    path.write_bytes(path.read_bytes()+b' ')
    with pytest.raises(ValueError,match='hash|binding'):
        W.verify_bundle(out/'workflow-bundle.json')


def test_contract_cannot_disappear_on_reexport(tmp_path):
    out=tmp_path/'bundle';W.export_workflow(control(),out)
    assert (out/'workflow-bundle.json').exists(), 'workflow must publish mandatory sidecar'
    (out/'workflow.json').unlink()
    with pytest.raises(ValueError,match='missing|binding'):
        W.reexport(out/'workflow-bundle.json',tmp_path/'again')
    with pytest.raises(ValueError,match='schema'):
        W.reexport(FIXTURES/'top.json',tmp_path/'bare')


def test_forged_pass_flags_recomputed_even_with_updated_hash(tmp_path):
    out=tmp_path/'bundle';W.export_workflow(control(),out)
    path=out/'pieces_one.json'
    assert path.exists(), 'workflow must save generated geometry'
    data=json.loads(path.read_text());data['pieces'][0]['outline'][1]['p'][0]=90
    data['validation_status']='passed_2d';path.write_text(json.dumps(data))
    binding=out/'workflow-bundle.json';manifest=json.loads(binding.read_text())
    manifest['artifacts']['pieces_one.json']=hashlib.sha256(path.read_bytes()).hexdigest()
    binding.write_text(json.dumps(manifest))
    with pytest.raises(ValueError,match='geometry|recipe|target|binding'):
        W.verify_bundle(binding)


def test_cli_unknown_schema_is_behavioral_rejection(tmp_path):
    path=tmp_path/'bad.json';path.write_text('{"schema":"unknown"}')
    r=subprocess.run([sys.executable,str(Path(W.__file__)),'validate',str(path)],capture_output=True,text=True)
    assert r.returncode==2 and 'schema' in r.stderr
    assert 'Traceback' not in r.stderr


def resized_companion(d, extra=1):
    """Independent frozen companion target; expression changes its actual edge geometry."""
    d['design']['dimensions']['companion']=dict(d['design']['dimensions']['attachment'],value=20+extra)
    c=d['components'][2];c['depends_on'].remove('finished.attachment');c['depends_on'].append('finished.companion')
    c['ports'][0]['target']='finished.companion'
    for n in d['recipe']['pieces'][2]['outline'][1:3]: n['p'][0]={'op':'param','id':'finished.companion'}
    return d


@pytest.mark.parametrize('mode,value,kind,unit,extra',[('ease',1,'ease','cm',1),('stretch',1.05,'stretch','ratio',1),
                                                    ('gather',1.5,'gather','ratio',10)])
def test_independently_declared_ease_stretch_gather(mode,value,kind,unit,extra):
    d=resized_companion(control(),extra)
    d['design']['dimensions']['intent']=dict(value=value,kind=kind,unit=unit,
        source='independent synthetic material construction brief',basis='engineering-selected')
    a=d['attachments'][0];a['a'],a['b']=a['b'],a['a']
    a['relation']={'mode':mode,'target':'finished.intent','reason':'declared test material behavior',
                   'material_id':'synthetic-woven'}
    result=W.validate(d)['attachments'][0]
    assert result['a_cm']==pytest.approx(20+extra)
    assert result['b_cm']==pytest.approx(20)
    assert result['mode']==mode
    d['design']['dimensions']['intent']['value']+=.4
    bad(d,'target|mismatch')


def test_curve_and_split_chain_use_actual_geometry():
    d=control()
    # Both ports become two-segment chains, one cubic and one straight.
    for index in (0,2):
        p=d['recipe']['pieces'][index]
        p['outline'].insert(1,{'name':'middle','p':[10,-2]})
        p['outline'][0]['c']=[[3,-.6],[7,-1.4]]
        port=d['components'][index]['ports'][0]
        port['chain']=[{'piece':p['name'],'from':'a','to':'middle'}, {'piece':p['name'],'from':'middle','to':'b'}]
        port['landmarks']=[{'id':'start','after':0},{'id':'middle','after':1},{'id':'end','after':2}]
    d['attachments'][0]['landmarks']=['start','middle','end']
    # The target below is an independently specified test control, not permission inferred by the validator.
    d['design']['dimensions']['sewn_curve']=dict(d['design']['dimensions']['attachment'],value=20.4)
    for i in (0,2): d['components'][i]['ports'][0]['target']='finished.sewn_curve'
    result=W.validate(d)['attachments'][0]
    assert result['a_cm']==pytest.approx(2*(10**2+2**2)**.5)
    d['recipe']['pieces'][2]['outline'][0]['c'][0][1]=-7
    bad(d,'target|landmark|mismatch')


def takeup_control(kind='pleat'):
    d=control();p=d['recipe']['pieces'][0]
    p['outline'].insert(1,{'name':'mouth1','p':[8,0]})
    p['outline'].insert(2,{'name':'mouth2','p':[10,0]})
    for n in p['outline'][3:5]:
        n['p'][0]={'op':'add','args':[{'op':'param','id':'finished.attachment'}, {'op':'literal','value':2,'unit':'cm'}]}
    port=d['components'][0]['ports'][0]
    port['chain']=[{'piece':'Panel','from':a,'to':b} for a,b in [('a','mouth1'),('mouth1','mouth2'),('mouth2','b')]]
    port['landmarks'][-1]['after']=3
    dim='pleat_takeup' if kind=='pleat' else 'closure_overlap'
    d['design']['dimensions']['takeup']=dict(d['design']['dimensions']['attachment'],value=2,kind=dim)
    port['deductions']=[{'kind':kind,'segment':1,'target':'finished.takeup','source':'synthetic folded span',
                         'from':'mouth1','to':'mouth2'}]
    return d


@pytest.mark.parametrize('kind',['pleat','overlap'])
def test_geometry_derived_closed_seam_takeup(kind):
    d=takeup_control(kind)
    result=W.validate(d)
    assert result['attachments'][0]['a_cm']==20
    assert result['ports']['panel.opening']['deduction_cm']==2
    d['components'][0]['ports'][0]['deductions']*=2
    bad(d,'duplicate|overlap')


def test_internal_dart_takeup_not_raw_width():
    d=resized_companion(control(),2)
    p=d['recipe']['pieces'][2];p['darts_in']=[[[10,5],[9,0],[11,0]]]
    port=d['components'][2]['ports'][0];port['target']='finished.attachment'
    d['design']['dimensions']['takeup']=dict(d['design']['dimensions']['attachment'],value=2,kind='dart_takeup')
    port['deductions']=[{'kind':'dart','segment':0,'target':'finished.takeup','source':'synthetic triangle mouth','dart_index':0}]
    assert W.validate(d)['attachments'][0]['b_cm']==20
    p['darts_in'][0]=[[10,5],[9,1],[11,1]]
    bad(d,'mouth|closure')


def test_ordinary_seams_keep_one_mm_tolerance():
    d=control()
    for n in d['recipe']['pieces'][2]['outline'][1:3]:
        n['p'][0]={'op':'add','args':[n['p'][0],{'op':'literal','value':.09,'unit':'cm'}]}
    assert W.validate(d)['attachments'][0]['b_cm']==pytest.approx(20.09)
    for n in d['recipe']['pieces'][2]['outline'][1:3]: n['p'][0]['args'][1]['value']=.11
    bad(d,'target|mismatch')


def test_missing_required_companion_port_even_for_coupon():
    d=control();d['components'][0]['ports']=[];d['components'][2]['ports']=[];d['attachments']=[]
    bad(d,'companion attachment')


def test_non_equal_relation_cannot_excuse_ordinary_seam():
    d=control();d['attachments'][0]['kind']='side'
    for c in (d['components'][0],d['components'][2]): c['ports'][0]['purpose']='side'
    d['attachments'][0]['relation']={'mode':'ease','target':'finished.attachment','reason':'wool','material_id':'synthetic-woven'}
    bad(d,'ordinary')


def test_external_rules_and_height_provenance():
    d=control();d['profile']['template']['provider']='PatternFast'
    bad(d,'synthetic')
    d['profile']['template'].update(rule_state='external-unintegrated',custom_allowed=None)
    assert W.validate(d)['template_status']=='selected-standard-row-template-rules-unverified'
    d=control();d['profile']['parameters']['span']['basis']='inferred'
    bad(d,'calibrat|inferred')


def test_unimplemented_closure_measurement_fails():
    d=control();d['components'][0]['ports'][0]['measurement']='raw-width-is-half-girth'
    bad(d,'unknown|unsupported')


def test_stored_unknown_status_even_rebound_is_rejected(tmp_path):
    out=tmp_path/'bundle';W.export_workflow(control(),out)
    p=out/'pieces_one.json';data=json.loads(p.read_text());data['validation_status']='production-approved';p.write_text(json.dumps(data))
    manifest=out/'workflow-bundle.json';m=json.loads(manifest.read_text())
    m['artifacts'][p.name]=hashlib.sha256(p.read_bytes()).hexdigest();manifest.write_text(json.dumps(m))
    with pytest.raises(ValueError,match='status'): W.verify_bundle(manifest)


@pytest.mark.parametrize('artifact',['pattern.svg','pattern_one.dxf'])
def test_saved_readback_catches_geometry_edit_even_if_rebound(tmp_path,artifact):
    out=tmp_path/'bundle';W.export_workflow(control(),out)
    p=out/artifact
    if p.suffix=='.svg':
        text=p.read_text().replace('20.000,25.000','2000.000,25.000',1)
        assert text!=p.read_text();p.write_text(text)
    else:
        import ezdxf
        doc=ezdxf.readfile(p);next(iter(doc.modelspace().query('LINE'))).dxf.start=(9000,9000,0);doc.saveas(p)
    manifest=out/'workflow-bundle.json';m=json.loads(manifest.read_text())
    m['artifacts'][p.name]=hashlib.sha256(p.read_bytes()).hexdigest();manifest.write_text(json.dumps(m))
    with pytest.raises(ValueError,match='readback|DXF|geometry'): W.verify_bundle(manifest)


@pytest.mark.parametrize('where',[('profile','selection','row_id'),('components',0,'pieces'),('recipe','pieces',0,'outline')])
def test_malformed_shapes_fail_with_value_error(where):
    d=control();node=d
    for k in where[:-1]: node=node[k]
    node[where[-1]]={'unexpected':'shape'}
    bad(d,'malformed|array|row')


def test_inventory_only_still_checks_structural_schema():
    d=control();d['components'][0]['ports'][0]['unknown']=True
    with pytest.raises(ValueError,match='unknown'): W.validate(d,geometry=False)


def test_packaged_schema_is_exercised():
    schema=Path(W.__file__).parents[1]/'references/workflow.schema.json'
    data=json.loads(schema.read_text())
    assert set(('proposal','target','bundle','analysis','profile','port'))<=set(data['$defs'])
    assert W.check_structure(control(),'proposal') is None
    assert W.check_structure(control('custom-target.json'),'target') is None


def test_missing_front_closure_and_pocket_pairings():
    for fixture in ('closure.json','pocket.json','sleeve.json'):
        d=control(fixture)
        assert W.validate(d)['status']=='proposal-ready'
        d['components'][2]['ports'][0]['chain'][0]['to']='c'
        bad(d,'adjacent')


def test_cuffs_require_sleeve_inventory_even_if_sleeves_feature_is_omitted():
    d=control();d['construction']['features']['cuffs']=True
    result=W.validate(d,geometry=False)
    assert {'sleeve','cuff'}<=set(result['missing_components'])
