"""Run portable workflow CLI controls, retain raw logs and machine-readable readbacks.

No garment data, private catalog, installs, live API or network is used. --out must be fresh.
"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=ROOT/'skills/pattern-making/scripts'
FIXTURES=ROOT/'tests/fixtures/workflow'
sys.path.insert(0,str(SCRIPTS))
import pattern as P
import validation as V
import workflow as W


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();out=args.out.resolve();out.mkdir(parents=True,exist_ok=False)
    result={'scope':'SYNTHETIC attachment controls; no whole-garment or physical-fit approval',
            'python':sys.executable,'startup_sources':{m.__name__:str(Path(m.__file__).resolve()) for m in (P,V,W)},
            'source_sha256':W.engine_sources(),'commands':[],'readbacks':{},'size_extension':{}}
    assert all(Path(m.__file__).resolve().parent==SCRIPTS for m in (P,V,W))
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
    def save(name,data):
        p=out/name;W.save(p,data);return p
    def run(name,args,expected=0):
        cmd=[sys.executable,str(SCRIPTS/'workflow.py'),*map(str,args)]
        r=subprocess.run(cmd,cwd=out,env=env,text=True,capture_output=True,timeout=90)
        log=out/(name+'.log');log.write_text(r.stdout+r.stderr)
        result['commands'].append({'id':name,'argv':cmd,'cwd':str(out),'exitcode':r.returncode,
                                   'expected_exitcode':expected,'log':str(log)})
        save('results.json',result)
        assert r.returncode==expected,(name,r.returncode,r.stdout,r.stderr)
        return json.loads(r.stdout) if r.stdout else None
    run('blueprints',['blueprints'])
    run('proposal',['validate',FIXTURES/'top.json'])
    for name in ('top','bottom','outerwear','one-piece','cuff','sleeve','closure','pocket'):
        run(name+'-export',['export',FIXTURES/(name+'.json'),'--out',out/name])
        check=run(name+'-verify',['verify',out/name/'workflow-bundle.json'])
        result['readbacks'][name]=check
        assert check['status']=='exported-2D-verified' and check['readback']['dxf_units']==4
        assert check['readback']['missing_segments']==0
        assert check['support']=='synthetic-attachment-control'
    run('extend',['extend',FIXTURES/'top.json','--target',FIXTURES/'custom-target.json','--out',out/'extended.json'])
    run('extended-export',['export',out/'extended.json','--out',out/'extended'])
    result['readbacks']['extended']=run('extended-verify',['verify',out/'extended/workflow-bundle.json'])
    run('reexport',['reexport',out/'top/workflow-bundle.json','--out',out/'reexport'])
    result['readbacks']['reexport']=run('reexport-verify',['verify',out/'reexport/workflow-bundle.json'])
    base=W.load(out/'top/pieces_one.json')['pieces'];changed=W.load(out/'extended/pieces_one.json')['pieces']
    for a,b in zip(base,changed):
        before=P.length(P.edge(a,0,64));after=P.length(P.edge(b,0,64))
        assert before==20 and abs(after-23.7)<1e-8
        assert a['outline'][2]['p'][1]==b['outline'][2]['p'][1]
        for k in ('notches','grain','buttons','lines','allowance'): assert a[k]==b[k]
        result['size_extension'][a['name']]={'attachment_cm_before':before,'attachment_cm_after':after,
            'depth_cm_before':a['outline'][2]['p'][1],'depth_cm_after':b['outline'][2]['p'][1],
            'allowance_and_marks_unchanged':True}
    d=W.load(FIXTURES/'top.json');d['schema']='unrecognized'
    run('bad-schema',['validate',save('bad-schema.json',d)],2)
    d=W.load(FIXTURES/'top.json');d['components'][2]['profile_id']='different-profile'
    run('bad-profile',['export',save('bad-profile.json',d),'--out',out/'bad-profile'],2)
    for name in ('top','cuff','bottom'):
        d=W.load(FIXTURES/(name+'.json'))
        for n in d['recipe']['pieces'][2]['outline'][1:3]:
            n['p'][0]={'op':'add','args':[n['p'][0],{'op':'literal','value':1,'unit':'cm'}]}
        run(name+'-mismatch',['export',save(name+'-mismatch.json',d),'--out',out/(name+'-mismatch')],2)
    d=W.load(FIXTURES/'top.json');d['attachments']=[]
    run('unpaired',['export',save('unpaired.json',d),'--out',out/'unpaired'],2)
    d=W.load(FIXTURES/'top.json');d['components']=d['components'][:2];d['recipe']['pieces']=d['recipe']['pieces'][:2]
    d['attachments']=[];d['components'][0]['ports']=[]
    incomplete=save('missing-component.json',d)
    inventory=run('inventory-incomplete',['validate',incomplete,'--inventory-only'])
    assert inventory['status']=='proposal-incomplete' and inventory['missing_components']==['collar']
    run('missing-component',['export',incomplete,'--out',out/'missing-component'],2)
    run('bare-reexport',['reexport',out/'top/pieces_one.json','--out',out/'bare-reexport'],2)
    # Mutation controls are disposable copies; keep the matching controls intact.
    import shutil
    shutil.copytree(out/'top',out/'mutated')
    f=out/'mutated/pattern.svg';f.write_bytes(f.read_bytes()+b' ')
    run('mutated-binding',['verify',out/'mutated/workflow-bundle.json'],2)
    shutil.copytree(out/'top',out/'dropped-contract');(out/'dropped-contract/workflow.json').unlink()
    run('dropped-contract',['reexport',out/'dropped-contract/workflow-bundle.json','--out',out/'dropped-reexport'],2)
    for row in result['commands']:
        if row['expected_exitcode'] and '--out' in row['argv']:
            dest=Path(row['argv'][row['argv'].index('--out')+1])
            assert not (dest/'pattern.svg').exists() and not list(dest.glob('*.dxf'))
    # Reopened DXF measurement for the 200 mm width control, using its SEAM entities.
    import ezdxf
    doc=ezdxf.readfile(out/'top/pattern_one.dxf')
    lines=[e for e in doc.modelspace().query('LINE') if e.dxf.layer=='SEAM']
    result['dxf_width_control_mm']=abs(lines[0].dxf.end.x-lines[0].dxf.start.x)
    assert result['dxf_width_control_mm']==200
    result['artifact_hashes']={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(out.rglob('*')) if p.is_file() and p.name!='results.json'}
    save('results.json',result)
    print(json.dumps({'commands':len(result['commands']),'readbacks':len(result['readbacks']),
                      'results':str(out/'results.json')},indent=2))


if __name__=='__main__':
    main()
