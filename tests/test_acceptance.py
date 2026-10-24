"""Fresh current-code CLI/export/readback contracts; no private audit inputs."""
import copy
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

import ezdxf
import pytest
from shapely.geometry import Polygon
import pattern as P
import garment as G

SCRIPTS = Path(P.__file__).parent
EXAMPLES = SCRIPTS.parent / 'examples'


def rect(name='A', w=20, h=30):
    return {'name': name, 'allowance': 1, 'outline': [dict(name=n, p=list(q)) for n, q in zip('abcd', [(0,0),(w,0),(w,h),(0,h)])]}


def invoke(tmp_path, *args):
    cmd = [sys.executable, str(SCRIPTS / 'pattern.py'), *map(str, args)]
    r = subprocess.run(cmd, cwd=tmp_path, text=True, capture_output=True, timeout=90)
    with (tmp_path / 'commands.jsonl').open('a') as f:
        f.write(json.dumps({'argv': cmd, 'exitcode': r.returncode, 'stdout': r.stdout, 'stderr': r.stderr}) + '\n')
    return r


def write(tmp_path, name, data):
    p = tmp_path / name
    p.write_text(json.dumps(data))
    return p


def piece_cli(tmp_path, data, name='out'):
    return invoke(tmp_path, 'piece', write(tmp_path, name+'.json', data), '--out', tmp_path/name)


def saved(tmp_path, folder='out', size='one'):
    return json.loads((tmp_path/folder/f'pieces_{size}.json').read_text())


def assert_no_bundle(out):
    assert not (out / 'pattern.svg').exists()
    assert not list(out.glob('pattern_*.dxf'))
    assert not list(out.glob('clo3d_*.json'))


def dxf_read(path):
    doc = ezdxf.readfile(path)
    audit = doc.audit()
    assert not audit.errors and not audit.fixes
    for layer in ('CUT', 'SEAM'):
        pts = []
        for e in doc.modelspace().query('LINE'):
            if e.dxf.layer != layer:
                continue
            a, b = tuple(e.dxf.start)[:2], tuple(e.dxf.end)[:2]
            if not pts:
                pts.append(a)
            assert pts[-1] == a
            pts.append(b)
            if pts[-1] == pts[0]:
                assert Polygon(pts).is_valid and Polygon(pts).area > 0
                assert all(P.dist(a,b)>0 for a,b in zip(pts,pts[1:]))
                pts = []
        assert not pts
    return doc


@pytest.mark.parametrize('block,sizes', [('bodice','36,38'),('glove','7,8')])
def test_measurements_grading_rejected(tmp_path, block, sizes):
    own = write(tmp_path, 'own.json', {'bust':84,'waist':68} if block=='bodice' else {'hand':{'G':180}})
    r = invoke(tmp_path,'block',block,'--measurements',own,'--sizes',sizes,'--out',tmp_path/'out')
    assert r.returncode != 0
    assert '--measurements' in r.stderr and '--sizes' in r.stderr
    assert_no_bundle(tmp_path/'out')


def test_measurement_resolution_and_custom_geometry(tmp_path):
    own = write(tmp_path,'own.json', {'bust':84,'waist':68,'back_length':38})
    for name, args in [('own',['--measurements',own]),('std',[]),('multi',['--sizes','36,38'])]:
        r = invoke(tmp_path,'block','bodice','--size','38',*args,'--out',tmp_path/name)
        assert r.returncode == 0, r.stdout+r.stderr
    d = saved(tmp_path,'own','38')
    assert d['resolved_measurements']['back_length'] == 38
    assert d['measurement_provenance']['back_length']['source'] == 'input'
    assert d['measurement_provenance']['hip']['source'] == 'table'
    assert d['measurement_provenance']['neck']['source'] == 'derived'
    assert d['pieces'] != saved(tmp_path,'std','38')['pieces']
    assert saved(tmp_path,'std','38')['pieces'] == saved(tmp_path,'multi','38')['pieces']


@pytest.mark.parametrize('own',[{'height':160},{'bustt':84},{'bust':float('nan')},{'ease':{'mystery':2}}])
def test_unsupported_measurements_fail(tmp_path,own):
    r=invoke(tmp_path,'measurements','--measurements',write(tmp_path,'own.json',own))
    assert r.returncode != 0 and 'Traceback' not in r.stderr


def test_default_table_not_nearest(tmp_path):
    r=invoke(tmp_path,'measurements','--measurements',write(tmp_path,'own.json',{'bust':104}))
    assert r.returncode == 0
    assert json.loads(r.stdout)['waist'] == 68


def test_bodice_darts_keep_apex_and_intake(tmp_path):
    own={'bust':84,'waist':68,'bust_span':18,'bust_depth':25,'bust_dart':3.8}
    r=invoke(tmp_path,'block','bodice','--measurements',write(tmp_path,'own.json',own),'--out',tmp_path/'out')
    assert r.returncode == 0, r.stdout+r.stderr
    data=saved(tmp_path,size='38')
    for p in data['pieces']:
        nd=p['outline']
        for i,n in enumerate(nd):
            if n.get('dart'):
                assert abs(P.dist(nd[i-1]['p'],n['p'])-P.dist(nd[(i+1)%len(nd)]['p'],n['p']))*10 <= 1
    front=next(p for p in data['pieces'] if p['name']=='Bodice front')
    nodes={n['name']:n['p'] for n in front['outline']}
    assert nodes['side_dart'] == [11.5,25]
    assert P.dist(nodes['side_dart_1'],nodes['side_dart_2']) == pytest.approx(3.8, abs=.005)
    assert data['resolved_measurements']['bust_depth']==25


@pytest.mark.parametrize('internal', [False,True])
def test_unequal_darts_rejected(tmp_path,internal):
    p=rect()
    if internal:
        p['darts_in']=[[[10,5],[13,15],[10,25],[8,15]]]
    else:
        p['outline'][1:1]=[{'name':'leg1','p':[8,0]},{'name':'dart','p':[10,10],'dart':True},{'name':'leg2','p':[13,0]}]
    r=piece_cli(tmp_path,{'pieces':[p]})
    assert r.returncode == 2
    assert 'dart' in r.stdout.lower()+r.stderr.lower()
    assert_no_bundle(tmp_path/'out')


def test_equal_legs_but_untrued_fold_rejected(tmp_path):
    p=rect()
    p['outline'][1:1]=[{'name':'leg1','p':[8,0]},{'name':'dart','p':[10,10],'dart':True},{'name':'leg2','p':[12,0]}]
    assert piece_cli(tmp_path,{'pieces':[p]}).returncode == 2
    assert_no_bundle(tmp_path/'out')


def test_seam_match_no_invented_ease():
    a,b=rect('A',10),rect('B',20)
    sm=G.Seams({'A':a,'B':b})
    with pytest.raises(ValueError,match='seam'):
        sm.match([('A','a','b')],[('B','a','b')],why='side seam')
    assert not sm.rows


def test_declared_ease_validated_before_split():
    a,b=rect('A',21),rect('B',20)
    sm=G.Seams({'A':a,'B':b})
    sm.match([('A','a','b')],[('B','a','b')],why='sleeve cap',ease_cm=1)
    assert len(sm.rows)==1
    before=copy.deepcopy(sm.p)
    with pytest.raises(ValueError):
        sm.match([('A','a','b')],[('B','a','b')],why='sleeve cap',ease_cm=2)
    assert sm.p==before


@pytest.mark.parametrize('depth,allowance',[(3,1),(5,1),(5,.49)])
def test_concave_offset_rejection_and_valid_control(tmp_path,depth,allowance):
    p=rect();p['allowance']=allowance
    p['outline']=[dict(name=str(i),p=q) for i,q in enumerate([(0,0),(10,0),(10,10),(5.5,10),(5.5,depth),(4.5,depth),(4.5,10),(0,10)])]
    r=piece_cli(tmp_path,{'pieces':[p]})
    if allowance==1:
        assert r.returncode==2
        assert_no_bundle(tmp_path/'out')
    else:
        assert r.returncode==0,r.stdout+r.stderr
        dxf_read(tmp_path/'out/pattern_one.dxf')


@pytest.mark.parametrize('vertices',[
    [(0,0),(20,0),(20,30),(10,30),(10.00001,29),(10,29),(0,30)],
    [(0,0),(20,0),(20,30),(0,30),(0,15),(0,20)],
    [(0,0),(20,0),(20,float('inf')),(0,30)],
])
def test_degenerate_and_rounding_failure(tmp_path,vertices):
    p=rect();p['outline']=[dict(name=str(i),p=q) for i,q in enumerate(vertices)]
    r=piece_cli(tmp_path,{'pieces':[p]})
    assert r.returncode==2
    assert 'Traceback' not in r.stderr
    assert_no_bundle(tmp_path/'out')


def marked():
    p=rect('Marks')
    p.update(fold=[3],grain=[[2,10],[2,20]],notches=[{'edge':1,'d':-10},{'edge':0,'t':.4}],
             darts_in=[[[10,5],[12,15],[10,25],[8,15]]],lines=[[[1,2],[19,2]]],buttons=[[10,3]])
    return p


def assert_marks(data,doc,offs=None):
    if offs is None:
        offs,_,_=P.layout([data['pieces']])
    actual=[(e.dxf.layer,tuple(e.dxf.start)[:2],tuple(e.dxf.end)[:2]) for e in doc.modelspace().query('LINE')]
    count=0
    for p,off in zip(data['pieces'],offs):
        for key,layer in [('darts_in','DART'),('lines','INTERNAL'),('grain','GRAIN')]:
            seqs=[p[key]] if key=='grain' and p.get(key) else p.get(key,[])
            for seq in seqs:
                seq=seq+[seq[0]] if key=='darts_in' else seq
                for a,b in zip(seq,seq[1:]):
                    def mm(q):
                        x,y=P.mm(q,off);return x,-y
                    assert any(l==layer and ((P.dist(mm(a),c)<.03 and P.dist(mm(b),d)<.03) or (P.dist(mm(a),d)<.03 and P.dist(mm(b),c)<.03)) for l,c,d in actual),(p['name'],key,a,b)
                    count+=1
    return count


def test_formal_marks_units_svg_png(tmp_path):
    p=marked()
    r=piece_cli(tmp_path,{'pieces':[p]})
    assert r.returncode==0,r.stdout+r.stderr
    data=saved(tmp_path)
    doc=dxf_read(tmp_path/'out/pattern_one.dxf')
    assert doc.dxfversion>='AC1015' and doc.header['$INSUNITS']==4
    assert_marks(data,doc)
    layers=[e.dxf.layer for e in doc.modelspace()]
    assert 'BUTTON' in layers and 'FOLD' in layers
    points=[tuple(e.dxf.start)[:2] for e in doc.modelspace().query('LINE') if e.dxf.layer=='SEAM']
    assert max(x for x,y in points)-min(x for x,y in points)==200
    assert max(y for x,y in points)-min(y for x,y in points)==300
    svg=ET.parse(tmp_path/'out/pattern.svg').getroot()
    vb=list(map(float,svg.attrib['viewBox'].split()))
    assert float(svg.attrib['width'][:-2])==vb[2]
    assert float(svg.attrib['height'][:-2])==vb[3]
    assert {e.get('data-layer') for e in svg.iter()} >= {'DART','INTERNAL','BUTTON','FOLD','GRAIN','NOTCHES'}
    r=subprocess.run([sys.executable,str(SCRIPTS/'sheet.py'),str(tmp_path/'out/pieces_one.json'),'--width','800'],capture_output=True,text=True)
    assert r.returncode==0,r.stderr
    from PIL import Image
    im=Image.open(tmp_path/'out/pieces_one_shell.png');im.load()
    assert im.width==800
    assert data['pieces'][0]==p


def test_mirror_unfold_marks_and_no_mutation():
    p=marked();before=copy.deepcopy(p)
    q=P.mirror_piece(p,'R')
    assert q['buttons']==[[-10,3]]
    assert q['lines']==[[[-1,2],[-19,2]]]
    assert q['fold']==[3]
    assert P.notches(q)==pytest.approx([tuple((-x,y) for x,y in line) for line in P.notches(p)])
    u=P.unfold(p)
    assert len(u['darts_in'])==2 and len(u['buttons'])==2
    assert len(u['lines'])==2
    assert p==before


def test_constraints_roundtrip_and_recompute(tmp_path):
    data={'pieces':[rect('A',10),rect('B',10)],'seams':[['A','a','b','B','a','b']],
          'holds':[], 'construction':{'material':'woven'},'resolved_measurements':{'bust':84}}
    assert piece_cli(tmp_path,data).returncode==0
    first=saved(tmp_path)
    for key in ('seams','holds','construction','resolved_measurements'):
        assert first[key]==data[key]
    first['pieces'][1]['outline'][1]['p'][0]=20
    first['checks']=[{'label':'stale','value':0,'expected':0,'tol':0}]
    r=piece_cli(tmp_path,first,'bad')
    assert r.returncode==2
    assert_no_bundle(tmp_path/'bad')
    rejected=json.loads((tmp_path/'bad/rejected/pieces_one.json').read_text())
    assert rejected['seams']==data['seams']
    assert piece_cli(tmp_path,rejected,'again').returncode==2


def test_repeat_export_no_double_mirror(tmp_path):
    p=marked();p['mirror']=True
    data={'pieces':[p],'seams':[['Marks {side}','a','b','Marks {side}','a','b']],
          'holds':[{'top':'Marks {side}','edge':['a','b'],'under':'Marks {side}','at':{'a':[0,1],'b':[10,1]}}]}
    assert piece_cli(tmp_path,data).returncode==0
    first=saved(tmp_path)
    assert len(first['pieces'])==2 and len(first['holds'])==2
    assert piece_cli(tmp_path,first,'again').returncode==0
    assert saved(tmp_path,'again')['pieces']==first['pieces']
    assert_marks(first,dxf_read(tmp_path/'out/pattern_one.dxf'))


@pytest.mark.parametrize('data',[{'body':'men','size':'48','shaping':'boxy'}, {'body':'children'}, {'shaping':'boxy','measurements':'own.json'}])
def test_unsupported_garment_body_actionable(tmp_path,data):
    write(tmp_path,'own.json',{'bust':84,'waist':92})
    r=invoke(tmp_path,'garment',write(tmp_path,'spec.json',data),'--out',tmp_path/'out')
    assert r.returncode!=0 and 'Traceback' not in r.stderr
    assert 'block' in r.stderr.lower() and 'piece' in r.stderr.lower()
    assert_no_bundle(tmp_path/'out')


def test_fitted_jacket_marks_grain_and_shell_status(tmp_path):
    r=invoke(tmp_path,'garment',EXAMPLES/'notched-lapel-jacket/jacket_fitted.json','--out',tmp_path/'out')
    assert r.returncode==0,r.stdout+r.stderr
    data=saved(tmp_path,size='38')
    assert_marks(data,dxf_read(tmp_path/'out/pattern_38.dxf'))
    assert all(p.get('grain') for p in data['pieces'])
    assert data['shell_status']['supported'] is False
    assert not list((tmp_path/'out').rglob('clo3d_*.json'))
    assert sum(len(p.get('darts_in',[])) for p in data['pieces'])>=4
    assert data['seams']


def test_photo_contract_measures_actual_landmarks(tmp_path):
    data={'pieces':[rect('Panel',20,30)],'proportion_contract':{
        'dimensions':[{'id':'length','piece':'Panel','from':'a','to':'d','method':'distance','range_cm':[28,32]},
                      {'id':'width','piece':'Panel','from':'a','to':'b','method':'distance','range_cm':[19,21]}],
        'ratios':[{'numerator':'length','denominator':'width','range':[1.4,1.6]}]}}
    assert piece_cli(tmp_path,data).returncode==0
    for h in (5,120):
        bad=copy.deepcopy(data);bad['pieces']=[rect('Panel',20,h)]
        r=piece_cli(tmp_path,bad,str(h))
        assert r.returncode==2
        assert_no_bundle(tmp_path/str(h))
    repeat=saved(tmp_path)
    assert repeat['proportion_contract']==data['proportion_contract']
    assert repeat['proportion_results']['length']==30


def test_direct_shell_writer_refuses_internal_darts(tmp_path):
    p=marked()
    with pytest.raises(ValueError,match='dart'):
        P.write_clo3d([p],[(0,0)],tmp_path/'shell.json','one')
    assert not (tmp_path/'shell.json').exists()


@pytest.mark.parametrize('file,expected',[('notched-lapel-jacket/jacket_oversize.json',0),('velvet-coat/coat.json',2)])
def test_prior_garment_examples(tmp_path,file,expected):
    r=invoke(tmp_path,'garment',EXAMPLES/file,'--out',tmp_path/'out')
    assert r.returncode==expected,r.stdout+r.stderr
    if expected==2:
        assert 'Back: CUT:' in r.stdout and 'Back neck facing: CUT:' in r.stdout
        assert 'Self-intersection' in r.stdout
        assert_no_bundle(tmp_path/'out')
        assert (tmp_path/'out/rejected/pieces_38.json').exists()
        return
    dxf_read(tmp_path/'out/pattern_38.dxf')
    data=saved(tmp_path,size='38')
    assert_marks(data,dxf_read(tmp_path/'out/pattern_38.dxf'))


def test_no_ease_for_ordinary_side_or_dart():
    for why in ('side seam','dart legs'):
        sm=G.Seams({'A':rect('A',10),'B':rect('B',20)})
        with pytest.raises(ValueError):
            sm.match([('A','a','b')],[('B','a','b')],why=why,ease_cm=-10)


@pytest.mark.parametrize('body,size',[('women','38'),('men','48'),('children','8')])
def test_block_ordinary_seams_and_roundtrip_contracts(tmp_path,body,size):
    r=invoke(tmp_path,'block','all','--body',body,'--size',size,'--out',tmp_path/'out')
    assert r.returncode==0,r.stdout+r.stderr
    data=saved(tmp_path,size=size)
    assert data['seam_chains']
    assert all(abs(row['a_cm']-row['b_cm']-row['ease_cm'])<=.1 for row in data['seam_chain_results'])
    assert piece_cli(tmp_path,data,'again').returncode==0
    dxf_read(tmp_path/'again'/f'pattern_{size}.dxf')
    # Persisted chain declarations must still fail after intentional geometry editing.
    pc=next(p for p in data['pieces'] if p['name']=='Trousers front')
    next(n for n in pc['outline'] if n['name']=='outer_hem')['p'][1]+=10
    assert piece_cli(tmp_path,data,'bad-chain').returncode==2


def test_garment_shell_failure_cannot_publish_partial_bundle(tmp_path,monkeypatch):
    res=G.run(json.loads((EXAMPLES/'notched-lapel-jacket/jacket_oversize.json').read_text()))
    res['shell3d'][0]['outline'][0]['p']=[float('nan'),0]
    try:
        ok=G.write(res,tmp_path/'out')
    except ValueError:
        ok=False
    assert not ok
    assert_no_bundle(tmp_path/'out')


def test_unknown_shaping_actionable(tmp_path):
    r=invoke(tmp_path,'garment',write(tmp_path,'spec.json',{'shaping':'unsupported'}),'--out',tmp_path/'out')
    assert r.returncode==2 and 'Traceback' not in r.stderr
    assert 'shaping' in r.stderr
    assert_no_bundle(tmp_path/'out')


def test_mirrored_chain_contract_roundtrip(tmp_path):
    p=rect('Panel');p['mirror']=True
    data={'pieces':[p], 'seam_chains':[{'a':[['Panel {side}','a','b']], 'b':[['Panel {side}','c','d']], 'ease_cm':0,'why':'side seam'}]}
    r=piece_cli(tmp_path,data)
    assert r.returncode==0,r.stdout+r.stderr
    j=saved(tmp_path)
    assert len(j['seam_chains'])==2
    assert piece_cli(tmp_path,j,'again').returncode==0


def test_seam_tolerance_is_not_rounded_into_pass(tmp_path):
    # 1.004 mm is outside 1 mm, even though display rounding would print 1.00.
    data={'pieces':[rect('A',20.1004),rect('B',20)], 'seam_chains':[{'a':[['A','a','b']],'b':[['B','a','b']],'why':'side seam'}]}
    assert piece_cli(tmp_path,data).returncode==2
    assert_no_bundle(tmp_path/'out')


def test_invalid_hold_reference_rejected(tmp_path):
    data={'pieces':[rect()], 'holds':[{'top':'A','under':'Missing','edge':['a','b'],'at':{'a':[0,0],'b':[20,0]}}]}
    r=piece_cli(tmp_path,data)
    assert r.returncode==2 and 'Traceback' not in r.stderr
    assert_no_bundle(tmp_path/'out')


def test_raw_ordinary_seam_cannot_declare_mismatch_as_ease(tmp_path):
    data={'pieces':[rect('A',10),rect('B',20)], 'seams':[['A','a','b','B','a','b',{'ease':-.5,'why':'side seam'}]]}
    assert piece_cli(tmp_path,data).returncode==2
    assert_no_bundle(tmp_path/'out')


@pytest.mark.parametrize('personal',[False,True])
def test_glove_default_allowance_is_explicitly_rejected(tmp_path,personal):
    args=['--sizes','7,8']
    if personal:
        args=['--size','7','--measurements',write(tmp_path,'hand.json',{'hand':{'G':180}})]
    r=invoke(tmp_path,'block','glove',*args,'--out',tmp_path/'out')
    assert r.returncode==2 and 'Trank: CUT:' in r.stdout and 'Thumb: CUT:' in r.stdout
    assert 'Self-intersection' in r.stdout
    assert_no_bundle(tmp_path/'out')
    j=json.loads((tmp_path/'out/rejected/pieces_7.json').read_text())
    assert j['resolved_measurements']['G']==(180 if personal else 178)
    assert j['measurement_provenance']['G']['source']==('input' if personal else 'table')
