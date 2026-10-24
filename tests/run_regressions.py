"""Bounded fresh CLI/readback evidence. Run with --out NEW_DIRECTORY; no private audit dependency."""
import argparse
import collections
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/pattern-making/scripts'
sys.path.insert(0, str(SCRIPTS))
import pattern as P
import garment as G
from test_acceptance import rect, marked, assert_marks, dxf_read


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    a=ap.parse_args();root=a.out.resolve();root.mkdir(parents=True,exist_ok=False)
    os.environ['PYTHONDONTWRITEBYTECODE']='1'
    result={'source_sha256':{str(p.relative_to(SCRIPTS.parent)):hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in SCRIPTS.parent.rglob('*') if p.is_file() and p.suffix in ('.py','.md')},'commands':[],'readbacks':{}}
    def save(name,data):
        path=root/name;path.write_text(json.dumps(data,indent=2));return path
    def run(name,args,expected=0,script='pattern.py'):
        cmd=[sys.executable,str(SCRIPTS/script),*map(str,args)]
        r=subprocess.run(cmd,cwd=root,text=True,capture_output=True,timeout=90)
        (root/(name+'.log')).write_text(r.stdout+r.stderr)
        result['commands'].append({'name':name,'argv':cmd,'exitcode':r.returncode,'expected':expected,'log':name+'.log'})
        save('results.json',result)
        assert r.returncode==expected,(name,r.returncode,r.stdout,r.stderr)
        return r
    def piece(name,data,expected=0):
        return run(name,['piece',save(name+'.json',data),'--out',root/name],expected)
    def readback(name,size='one'):
        data=json.loads((root/name/f'pieces_{size}.json').read_text())
        doc=dxf_read(root/name/f'pattern_{size}.dxf')
        # Graded sheets share offsets across ALL sizes, as explicitly defined by layout().
        sets=[json.loads(f.read_text())["pieces"] for f in sorted((root/name).glob("pieces_*.json"))]
        offsets,_,_=P.layout(sets)
        mark_count=assert_marks(data,doc,offsets)
        svg=ET.parse(root/name/'pattern.svg').getroot()
        result['readbacks'][name]={'pieces':len(data['pieces']),'unit':doc.header['$INSUNITS'],
            'dxfversion':doc.dxfversion,'audit_errors':len(doc.audit().errors),'audit_fixes':len(doc.audit().fixes),
            'layers':dict(collections.Counter(e.dxf.layer for e in doc.modelspace())),
            'expected_dart_internal_grain_segments':mark_count,'missing_segments':0,
            'grain_pieces':sum(bool(p.get('grain')) for p in data['pieces']),
            'svg_dimensions':svg.attrib,'shell_status':data['shell_status'],
            'seam_chain_results':data.get('seam_chain_results',[])}
        save('results.json',result)
        return data
    own=save('own.json',{'body':'women','bust':84,'waist':68,'back_length':38})
    for name,args in [('custom_single',['--size','38','--measurements',own]),
                      ('standard_single',['--size','38']),('standard_grading',['--sizes','36,38'])]:
        run(name,['block','bodice',*args,'--out',root/name])
        readback(name,'38')
    run('custom_grading',['block','bodice','--measurements',own,'--sizes','36,38','--out',root/'custom_grading'],2)
    hand=save('hand.json',{'hand':{'G':180}})
    run('glove_custom_grading',['block','glove','--measurements',hand,'--sizes','7,8','--out',root/'glove_custom_grading'],2)
    run('height_rejected',['measurements','--measurements',save('height.json',{'height':160})],2)
    run('default_not_nearest',['measurements','--measurements',save('large.json',{'bust':104})])
    data=json.loads((root/'custom_single/pieces_38.json').read_text())
    darts=[]
    for pc in data['pieces']:
        nd=pc['outline']
        for i,n in enumerate(nd):
            if n.get('dart'):
                la,lb=P.dist(nd[i-1]['p'],n['p'])*10,P.dist(nd[(i+1)%len(nd)]['p'],n['p'])*10
                darts.append({'piece':pc['name'],'dart':n['name'],'leg1_mm':la,'leg2_mm':lb,'difference_mm':abs(la-lb)})
    result['darts']=darts
    assert max(d['difference_mm'] for d in darts)<=1
    for name,file,expected in [('jacket-fitted','notched-lapel-jacket/jacket_fitted.json',0),
                               ('jacket-oversize','notched-lapel-jacket/jacket_oversize.json',0),
                               ('coat','velvet-coat/coat.json',2)]:
        run(name,['garment',SCRIPTS.parent/'examples'/file,'--out',root/name],expected)
        if expected==0:
            readback(name,'38')
            run(name+'-png',[root/name/'pieces_38.json','--width','1800','--px','7'],script='sheet.py')
    audit_spec={'title':'Synthetic 84/68 jacket regression','body':'women','size':'38','measurements':'own.json',
                'front':{'extension':2,'buttons':[22,36]},'collar':{'type':'notched'},
                'sleeve':{'length':56,'hem':26,'ease':2.5},'length':{'below_waist':23},'pockets':{'type':'patch','x':4,'y':3}}
    run('women_jacket',['garment',save('women_jacket.json',audit_spec),'--out',root/'women_jacket'])
    readback('women_jacket','38')
    for name,data in [('men_garment',{'body':'men','size':'48','shaping':'boxy'}),
                      ('women_no_darts',{'shaping':'boxy','measurements':'no_darts.json'})]:
        save('no_darts.json',{'bust':84,'waist':92})
        run(name,['garment',save(name+'.json',data),'--out',root/name],2)
    shorts=save('shorts.json',{'body':'men','bust':96,'waist':82,'trouser_length':55,'hem_width':56,'knee_width':56})
    run('men_shorts_block',['block','trousers','--body','men','--size','48','--measurements',shorts,'--out',root/'men_shorts_block'])
    readback('men_shorts_block','48')
    p=rect('Concave');p['outline']=[{'name':str(i),'p':q} for i,q in enumerate([(0,0),(10,0),(10,10),(5.5,10),(5.5,5),(4.5,5),(4.5,10),(0,10)])]
    piece('concave_widebridge',{'pieces':[p]},2)
    p['allowance']=.49
    piece('concave_valid',{'pieces':[p]});readback('concave_valid')
    piece('marks',{'pieces':[marked()]});readback('marks')
    run('marks-png',[root/'marks/pieces_one.json','--width','800'],script='sheet.py')
    bad={'pieces':[rect('A',10),rect('B',20)],'seams':[['A','a','b','B','a','b']]}
    piece('bad_seam',bad,2)
    run('bad_roundtrip',['piece',root/'bad_seam/rejected/pieces_one.json','--out',root/'bad_roundtrip'],2)
    sm=G.Seams({p['name']:p for p in bad['pieces']})
    try:
        sm.match([('A','a','b')],[('B','a','b')],why='side seam')
    except ValueError as e:
        result['auto_ease_negative']={'rejected':True,'error':str(e),'rows':len(sm.rows)}
    else:
        raise AssertionError('Invented ease accepted')
    positive={'pieces':[rect('A',21),rect('B',20)],'seams':[['A','a','b','B','a','b',{'ease':.05,'why':'declared sleeve cap ease'}]]}
    piece('declared_ease',positive);readback('declared_ease')
    for body,size in [('women','38'),('men','48')]:
        name=body+'-block'
        run(name,['block','all','--body',body,'--size',size,'--out',root/name]);readback(name,size)
    run('built-in',['test'])
    # The scale control is read from the saved DXF, not inferred from writer settings.
    doc=dxf_read(root/'marks/pattern_one.dxf')
    pts=[tuple(e.dxf.start)[:2] for e in doc.modelspace().query('LINE') if e.dxf.layer=='SEAM']
    result['scale_control_mm']=[max(x for x,y in pts)-min(x for x,y in pts),max(y for x,y in pts)-min(y for x,y in pts)]
    assert result['scale_control_mm']==[200,300]
    for row in result['commands']:
        if row['expected']:
            name=row['name']
            if (root/name).is_dir():
                assert not list((root/name).glob('pattern*.dxf')) and not (root/name/'pattern.svg').exists()
    save('results.json',result)
    print(json.dumps({'commands':len(result['commands']),'readbacks':len(result['readbacks']),'results':str(root/'results.json')},indent=2))


if __name__=='__main__':
    main()
