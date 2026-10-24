"""Strict, template-agnostic 2D component coordination. No catalog or garment generator.

Named-piece recipes contain cm coordinates or bounded typed arithmetic. All geometry,
allowances, marks and export math are delegated to the sibling pattern/validation modules.
See references/workflow-and-components.md for the versioned public contract.
"""
import argparse
from collections import Counter
import copy
from functools import lru_cache
import hashlib
import io
import json
import math
from pathlib import Path
import re
import shutil
import sys
import tempfile
import xml.etree.ElementTree as ET

import pattern as P
import validation as V

SCHEMA = 'component-workflow/v1'
TARGET_SCHEMA = 'component-workflow-target/v1'
BUNDLE_SCHEMA = 'component-workflow-bundle/v1'
TOL = 0.1  # cm: ordinary seams retain the core's 1 mm tolerance
BLUEPRINTS = {
    'tops': ['tee', 'vest', 'shirt'],
    'bottoms': ['trousers', 'shorts', 'skirt'],
    'one-piece': ['dress', 'jumpsuit'],
    'outerwear': ['jacket', 'blazer', 'coat', 'hooded'],
}
FEATURES = {
    'paneling': ['front-back', 'alternative'], 'sleeves': ['none', 'set-in', 'raglan'],
    'neck': ['none', 'facing', 'collar', 'collar-stand', 'hood', 'rib'],
    'waist': ['none', 'band', 'facing', 'elastic'], 'pockets': ['none', 'patch', 'inseam', 'welt'],
    'closure': ['none', 'open', 'buttons', 'zip'], 'hem': ['turned', 'band', 'raw'],
}
PURPOSES = {'armhole', 'neck', 'cuff', 'waist', 'closure', 'pocket', 'side', 'shoulder', 'inseam', 'custom'}
BASIS = {'observed', 'inferred', 'nominal', 'engineering-selected'}
KINDS = {'body_length', 'body_girth', 'finished_length', 'finished_girth', 'seam_allowance',
         'closure_overlap', 'dart_takeup', 'pleat_takeup', 'ease', 'shrink', 'stretch', 'gather'}
RATIO_KINDS = {'shrink', 'stretch', 'gather'}
SCHEMA_PATH = Path(__file__).resolve().parents[1] / 'references/workflow.schema.json'


@lru_cache(maxsize=1)
def structural_schema():
    return json.loads(SCHEMA_PATH.read_text(encoding='utf-8'))


def check_structure(data, kind):
    """Evaluate the small JSON Schema subset used by our packaged, fixed schema.

    This is not a general schema engine. Never accepts an input-supplied schema or remote ref.
    Semantic checks below remain necessary after structural validation.
    """
    definitions=structural_schema()['$defs']
    def check(value, rule, path, depth=0):
        if depth>100: fail(path+': schema nesting limit exceeded')
        if '$ref' in rule:
            return check(value,definitions[rule['$ref'].split('/')[-1]],path,depth+1)
        if 'oneOf' in rule:
            errors=[];successes=0
            for candidate in rule['oneOf']:
                try: check(value,candidate,path,depth+1);successes+=1
                except ValueError as e: errors.append(str(e))
            if successes!=1: fail(path+': schema alternatives: '+'; '.join(errors))
            return
        if 'const' in rule and value!=rule['const']: fail(path+': unsupported schema value')
        if 'enum' in rule and value not in rule['enum']: fail(path+': unsupported schema enum')
        typ=rule.get('type')
        if typ is None: return
        types=typ if isinstance(typ,list) else [typ]
        predicates={'object':lambda: isinstance(value,dict), 'array':lambda: isinstance(value,list),
                    'string':lambda: isinstance(value,str), 'number':lambda: type(value) in (int,float),
                    'integer':lambda: type(value) is int, 'boolean':lambda: type(value) is bool,
                    'null':lambda: value is None}
        if not any(predicates[t]() for t in types): fail(path+': expected schema '+str(typ))
        if isinstance(value,dict):
            missing=set(rule.get('required',[]))-value.keys()
            if missing: fail(path+': missing '+', '.join(sorted(missing)))
            props=rule.get('properties',{});extra=rule.get('additionalProperties',True)
            for k,v in value.items():
                if k in props: check(v,props[k],path+'.'+k,depth+1)
                elif extra is False: fail(path+': unknown field '+k)
                elif isinstance(extra,dict): check(v,extra,path+'.'+k,depth+1)
        elif isinstance(value,list):
            if len(value)<rule.get('minItems',0) or len(value)>rule.get('maxItems',float('inf')): fail(path+': invalid array length')
            for i,v in enumerate(value): check(v,rule.get('items',{}),path+'['+str(i)+']',depth+1)
        elif type(value) in (int,float):
            number(value,path)
            if value<rule.get('minimum',-float('inf')): fail(path+': below schema minimum')
            if 'exclusiveMinimum' in rule and value<=rule['exclusiveMinimum']: fail(path+': must be positive (schema exclusive minimum)')
        elif isinstance(value,str) and len(value)<rule.get('minLength',0): fail(path+': empty string')
    check(data,definitions[kind],kind)


def fail(message):
    raise ValueError(message)


def obj(value, required, optional=(), label='record'):
    if not isinstance(value, dict):
        fail(label + ': expected object')
    missing = set(required) - value.keys()
    unknown = value.keys() - set(required) - set(optional)
    if missing:
        fail(label + ': missing ' + ', '.join(sorted(missing)))
    if unknown:
        fail(label + ': unknown fields ' + ', '.join(sorted(unknown)))
    return value


def seq(value, label, nonempty=False):
    if not isinstance(value, list) or (nonempty and not value):
        fail(label + ': expected ' + ('nonempty ' if nonempty else '') + 'array')
    return value


def string(value, label):
    if not isinstance(value, str) or not value.strip():
        fail(label + ': expected nonempty string')
    return value


def ident(value, label):
    string(value, label)
    if not re.fullmatch(r'[A-Za-z0-9_-]+', value):
        fail(label + ': ID must contain only letters, digits, underscore or hyphen')
    return value


def enum(value, allowed, label):
    if not isinstance(value, str) or value not in allowed:
        fail(label + ': unsupported value ' + repr(value))
    return value


def number(value, label, positive=False, nonnegative=False):
    if type(value) not in (int, float) or not math.isfinite(value):
        fail(label + ': expected finite number, not boolean')
    if positive and value <= 0:
        fail(label + ': must be positive')
    if nonnegative and value < 0:
        fail(label + ': must be nonnegative')
    return value


def integer(value, label, minimum=0):
    if type(value) is not int or value < minimum:
        fail(label + ': expected integer >= ' + str(minimum))
    return value


def unique(rows, key, label):
    result = {}
    for row in rows:
        if not isinstance(row, dict) or key not in row:
            fail(label + ': missing ' + key)
        name = string(row[key], label + ' ' + key)
        if name in result:
            fail(label + ': duplicate ' + name)
        result[name] = row
    return result


def quantity(q, label, profile=False):
    obj(q, ['value', 'unit', 'source', 'basis', 'kind'] + (['uid'] if profile else []), ['range'], label)
    enum(q['kind'], KINDS, label + ' kind')
    enum(q['basis'], BASIS, label + ' basis')
    if q['basis']=='inferred':
        fail(label + ': inferred sizes are unresolved; freeze a measured, nominal or engineering-selected target and retain inference in analysis')
    enum(q['unit'], ['ratio'] if q['kind'] in RATIO_KINDS else ['cm', 'mm'], label + ' unit')
    string(q['source'], label + ' source')
    if profile:
        string(q['uid'], label + ' uid')
        enum(q['kind'], ['body_length', 'body_girth'], label + ' kind')
    number(q['value'], label, positive=q['kind'] not in {'seam_allowance','closure_overlap','dart_takeup','pleat_takeup','ease','shrink','stretch'},
           nonnegative=q['kind'] != 'ease')
    if 'range' in q:
        interval(q['range'], label)
        if not q['range'][0] <= q['value'] <= q['range'][1]:
            fail(label + ': frozen value outside uncertainty range')
    return (q['value'] / 10 if q['unit'] == 'mm' else q['value'],
            'ratio' if q['unit'] == 'ratio' else 'length')


def interval(value, label):
    seq(value, label)
    if len(value) != 2:
        fail(label + ': range needs two endpoints')
    for x in value:
        number(x, label)
    if value[0] > value[1]:
        fail(label + ': reversed range')


def analysis(a):
    obj(a, ['sources','observations','assumptions','landmarks','scale','size_basis'], label='analysis')
    sources = unique(seq(a['sources'], 'sources', True), 'id', 'sources')
    for s in sources.values():
        obj(s, ['id','identity'], label='source'); ident(s['id'], 'source id'); string(s['identity'], 'source identity')
    def source(row):
        if row['source_id'] not in sources:
            fail('analysis references unknown source_id')
    scale=a['scale']; obj(scale, ['kind','source_id'], ['reference','length','perspective'], 'scale')
    enum(scale['kind'], ['uncalibrated','measured-coplanar'], 'scale'); source(scale)
    if scale['kind']=='uncalibrated' and set(scale) != {'kind','source_id'}:
        fail('uncalibrated scale cannot contain absolute reference lengths')
    if scale['kind']=='measured-coplanar':
        for k in ('reference','length','perspective'):
            if k not in scale: fail('calibrated scale missing '+k)
        string(scale['reference'],'scale reference'); string(scale['perspective'],'scale perspective')
        quantity(scale['length'],'calibration length')
        q=scale['length']
        if q['unit'] not in ('cm','mm') or q['kind'] not in ('body_length','finished_length') or q['basis']!='observed':
            fail('calibration requires an observed absolute length reference')
        number(q['value'],'calibration length',positive=True)
    for key in ('observations','assumptions'):
        for row in seq(a[key], key):
            obj(row, ['source_id','description','uncertainty'], label=key)
            source(row); string(row['description'],key); string(row['uncertainty'],'uncertainty')
    for row in seq(a['landmarks'],'landmarks'):
        obj(row, ['source_id','description','range','unit','basis','uncertainty'], label='landmark')
        source(row); string(row['description'],'landmark'); string(row['uncertainty'],'uncertainty')
        enum(row['basis'], ['observed','inferred'], 'landmark basis')
        enum(row['unit'], ['ratio','cm','mm'], 'landmark unit'); interval(row['range'],'landmark range')
        if row['unit']!='ratio' and scale['kind']=='uncalibrated':
            fail('absolute image landmarks require measured coplanar calibration')
    string(a['size_basis'],'size_basis')


def profile(p):
    obj(p, ['id','template','selection','parameters','unused'], label='profile')
    ident(p['id'],'profile id')
    if not isinstance(p['parameters'], dict): fail('profile parameters must be an object')
    if 'height' in p['parameters']:
        fail('height is not a geometry input; map explicit vertical dimensions instead')
    t=p['template']
    obj(t, ['provider','model_id','template_id','source','rule_state','custom_allowed','parameters','standard_rows'], label='template')
    for k in ('provider','model_id','template_id','source'): string(t[k],'template '+k)
    enum(t['rule_state'], ['synthetic-declared','external-unintegrated'], 'template rule_state')
    if t['rule_state']=='synthetic-declared' and not t['provider'].startswith('synthetic-'):
        fail('synthetic rules require an explicitly synthetic provider; external catalog adapters are unintegrated')
    if t['custom_allowed'] is not None and type(t['custom_allowed']) is not bool:
        fail('custom_allowed must be boolean or null')
    if t['rule_state']=='external-unintegrated' and t['custom_allowed'] is not None:
        fail('unintegrated template rules must leave custom_allowed null')
    if not isinstance(t['parameters'],dict) or not t['parameters']: fail('template parameters required')
    if set(p['parameters']) - set(t['parameters']): fail('unknown profile parameters')
    uids=set(); values={}
    for name,spec in t['parameters'].items():
        ident(name,'parameter id')
        obj(spec,['uid','unit','required'],['min','max'],'parameter specification')
        string(spec['uid'],'parameter uid');enum(spec['unit'],['cm','mm'],'parameter unit')
        if spec['uid'] in uids: fail('duplicate parameter uid')
        uids.add(spec['uid'])
        if type(spec['required']) is not bool: fail('required must be boolean')
        for bound in ('min','max'):
            if bound in spec: number(spec[bound], 'parameter '+bound, positive=True)
        if 'min' in spec and 'max' in spec and spec['min']>spec['max']: fail('invalid parameter bounds')
        if name not in p['parameters']:
            if spec['required']: fail('missing required parameter '+name)
            continue
        q=p['parameters'][name]; values['body.'+name]=quantity(q,'body.'+name,True)
        if q['uid']!=spec['uid'] or q['unit']!=spec['unit']: fail('parameter uid/unit differs from template')
        if ('min' in spec and q['value']<spec['min']) or ('max' in spec and q['value']>spec['max']):
            fail('parameter outside declared bounds')
    if not isinstance(t['standard_rows'],dict): fail('standard_rows must be an object')
    for row_id,row in t['standard_rows'].items():
        string(row_id,'row id')
        if not isinstance(row,dict) or set(row)!=set(t['parameters']): fail('standard row must freeze every template parameter')
        for k,v in row.items():
            number(v,'standard row value',positive=True)
    sel=p['selection'];obj(sel,['kind'],['row_id'],'selection')
    enum(sel['kind'],['standard','custom-target'],'selection kind')
    if sel['kind']=='standard':
        string(sel.get('row_id'),'standard row_id')
        if sel.get('row_id') not in t['standard_rows']: fail('unknown standard row')
        if {k:q['value'] for k,q in p['parameters'].items()}!=t['standard_rows'][sel['row_id']]:
            fail('parameters differ from selected standard row')
    elif 'row_id' in sel:
        fail('custom target must not claim a selected standard row')
    elif t['custom_allowed'] is False:
        fail('custom targets forbidden by declared synthetic rules')
    state=('selected-standard-row' if sel['kind']=='standard' else 'custom-target')
    state+=('-synthetic-rules-checked' if t['rule_state']=='synthetic-declared' else '-template-rules-unverified')
    return values,state


def expression(e, env, deps, depth=0):
    if depth>24: fail('expression exceeds maximum depth')
    if not isinstance(e,dict): fail('typed expression object required')
    op=e.get('op')
    if op=='param':
        obj(e,['op','id'],label='param expression')
        if e['id'] not in env: fail('unknown parameter '+str(e['id']))
        deps.add(e['id']);return env[e['id']]
    if op=='literal':
        obj(e,['op','value','unit'],label='literal expression')
        number(e['value'],'literal'); enum(e['unit'],['cm','mm','ratio'],'literal unit')
        return e['value']/(10 if e['unit']=='mm' else 1), 'ratio' if e['unit']=='ratio' else 'length'
    if op not in ('add','sub','mul','div'): fail('unsupported expression op '+str(op))
    obj(e,['op','args'],label='expression');seq(e['args'],'expression args')
    if len(e['args'])!=2: fail('typed binary op requires two args')
    (a,ua),(b,ub)=[expression(v,env,deps,depth+1) for v in e['args']]
    if op in ('add','sub'):
        if ua!=ub: fail('add/sub unit mismatch')
        value=a+b if op=='add' else a-b;unit=ua
    elif op=='mul':
        if ua==ub=='length': fail('unsupported squared dimension')
        value=a*b;unit='length' if 'length' in (ua,ub) else 'ratio'
    else:
        if b==0: fail('division by zero')
        if ua=='ratio' and ub=='length': fail('unsupported inverse dimension')
        value=a/b;unit='ratio' if ua==ub else 'length'
    number(value,'expression result');return value,unit


def dimensions(d,env):
    obj(d,['dimensions','constraints','material','unused'],label='design')
    if not isinstance(d['dimensions'],dict) or not d['dimensions']: fail('design dimensions required')
    for name,q in d['dimensions'].items():
        ident(name,'dimension id');env['finished.'+name]=quantity(q,'finished.'+name)
    material=d['material'];obj(material,['id','source','description'],label='material')
    for k in material: string(material[k],'material '+k)
    deps=set()
    for c in unique(seq(d['constraints'],'constraints'),'id','constraints').values():
        obj(c,['id','left','right'],label='dimension constraint')
        a,ua=expression(c['left'],env,deps);b,ub=expression(c['right'],env,deps)
        if ua!=ub or abs(a-b)>1e-8: fail('frozen dimension constraint mismatch: '+c['id'])
    return deps


def inventory(construction, components):
    obj(construction,['family','style','features','support','recipe_id','limitations'],label='construction')
    enum(construction['family'],BLUEPRINTS,'family')
    enum(construction['style'],BLUEPRINTS[construction['family']],'style')
    enum(construction['support'],['synthetic-attachment-control','authored-named-piece-recipe','inventory-only'], 'support')
    string(construction['recipe_id'],'recipe_id')
    for limitation in seq(construction['limitations'],'limitations',True): string(limitation,'limitation')
    f=construction['features']
    obj(f,list(FEATURES)+['alternative_roles','cuffs','lining','placket','extra_roles'],label='features')
    for k,allowed in FEATURES.items(): enum(f[k],allowed,k)
    for k in ('cuffs','lining','placket'):
        if type(f[k]) is not bool: fail(k+' must be boolean')
    for k in ('alternative_roles','extra_roles'):
        for role in seq(f[k],k): ident(role,'role')
        if len(set(f[k]))!=len(f[k]): fail('duplicate '+k)
    if f['paneling']=='alternative' and not f['alternative_roles']: fail('alternative paneling needs explicit roles')
    if f['paneling']=='front-back' and f['alternative_roles']: fail('alternative_roles incompatible with front-back paneling')
    required=set(['front','back'] if f['paneling']=='front-back' else f['alternative_roles'])
    required.update(f['extra_roles'])
    if f['sleeves']!='none': required.add('sleeve')
    required.update({'none':[], 'facing':['neck_facing'], 'collar':['collar'],
                     'collar-stand':['collar','collar_stand'], 'hood':['hood'], 'rib':['rib']}[f['neck']])
    if f['cuffs']: required.update(('sleeve','cuff'))
    required.update({'none':[],'band':['waistband'],'facing':['waist_facing'],'elastic':['elastic_casing']}[f['waist']])
    required.update({'none':[],'patch':['pocket'],'inseam':['pocket_bag'],
                     'welt':['pocket_bag','pocket_facing','welt']}[f['pockets']])
    if f['lining']: required.add('lining')
    if f['closure'] in ('buttons','zip'): required.add('closure')
    if f['placket']: required.add('placket')
    if f['hem']=='band': required.add('hem_band')
    present={c['role'] for c in components}
    return sorted(required-present), sorted(required)


def resolve_recipe(recipe, env):
    obj(recipe,['pieces'],label='recipe')
    pieces=seq(recipe['pieces'],'pieces')
    unique(pieces,'name','piece')
    dependencies={}
    def val(v, unit, deps):
        if isinstance(v,dict):
            n,u=expression(v,env,deps)
            if u!=unit: fail('recipe coordinate unit/dimension mismatch')
            return n
        return number(v,'recipe number')
    def point(v,deps):
        seq(v,'point')
        if len(v)!=2: fail('point must have two coordinates')
        return [val(x,'length',deps) for x in v]
    result=[]
    for raw in pieces:
        obj(raw,['name','cut','allowance','outline'],['allowances','grain','notches','lines','buttons','fold','darts_in','holes','within'], 'piece')
        string(raw['name'],'piece name');string(raw['cut'],'cut quantity')
        deps=set();p=copy.deepcopy(raw)
        p['allowance']=val(raw['allowance'],'length',deps);number(p['allowance'],'allowance',nonnegative=True)
        nodes=seq(raw['outline'],'outline',True)
        if len(nodes)<3: fail('outline needs at least three nodes')
        unique(nodes,'name','node')
        p['outline']=[]
        for n in nodes:
            obj(n,['name','p'],['c','dart'],'node');string(n['name'],'node name')
            nn=dict(n,p=point(n['p'],deps))
            if 'c' in n:
                seq(n['c'],'Bezier controls')
                if len(n['c'])!=2: fail('Bezier needs two controls')
                nn['c']=[point(x,deps) for x in n['c']]
            if 'dart' in n and type(n['dart']) is not bool: fail('dart must be boolean')
            p['outline'].append(nn)
        if 'allowances' in p:
            if not isinstance(p['allowances'],dict): fail('allowances must be object')
            for k,v in raw['allowances'].items():
                if k not in {str(i) for i in range(len(nodes))}: fail('allowance edge index invalid')
                p['allowances'][k]=val(v,'length',deps);number(p['allowances'][k],'allowance',nonnegative=True)
        for k in ('grain','buttons'):
            if k in raw: p[k]=[point(v,deps) for v in seq(raw[k],k)]
        if 'grain' in p and len(p['grain'])!=2: fail('grain needs two points')
        for k in ('lines','darts_in'):
            if k in raw:
                p[k]=[[point(v,deps) for v in seq(line,k,True)] for line in seq(raw[k],k)]
        if 'fold' in p:
            for i in seq(p['fold'],'fold'):
                integer(i,'fold edge')
                if i>=len(nodes): fail('fold edge index invalid')
        if 'notches' in p:
            for n in seq(p['notches'],'notches'):
                obj(n,['edge'],['d','t'],'notch'); integer(n['edge'],'notch edge')
                if n['edge']>=len(nodes) or ('d' in n)==('t' in n): fail('invalid notch edge/distance')
                key='d' if 'd' in n else 't';n[key]=val(n[key],'length' if key=='d' else 'ratio',deps)
                if key=='t' and not 0<=n[key]<=1: fail('notch fraction outside edge')
                if key=='d':
                    length=P.length(P.edge(p,n['edge'],64))
                    # garment.notch_on stores round(distance_cm, 3). Admit only
                    # that exact rounded endpoint when it exceeds edge64 length;
                    # no geometric epsilon or sewing tolerance, and no mark rewrite.
                    if abs(n[key])>length and abs(n[key])!=round(length,3):
                        fail('notch distance outside edge')
        if 'within' in p: string(p['within'],'within')
        if 'holes' in p:
            # Named hole curves use the same core outline grammar, with no separate exports.
            p['holes']=[]
            for h in seq(raw['holes'],'holes'):
                obj(h,['name','outline'],label='hole')
                hr,hd=resolve_recipe({'pieces':[dict(h,cut='1x',allowance=0)]},env)
                p['holes'].append({'name':h['name'],'outline':hr[0]['outline']});deps.update(hd[h['name']])
        result.append(p);dependencies[p['name']]=deps
    return result,dependencies


def geometry_checks(pieces):
    checks=[]
    for p in pieces:
        V.paths(P,p)
        checks+=P.fold_checks(p)+V.darts(P,p)
        c=P.neck_check(p)
        if c: checks.append(c)
    checks+=P.within_checks(pieces)
    for c in checks:
        if c['expected'] is not None and abs(c['value']-c['expected'])>c['tol']:
            fail('geometry: '+c['label'])


def edge_ref(ref, by, owned, saved_edges=None):
    obj(ref,['piece','from','to'],label='edge reference')
    if ref['piece'] not in owned or ref['piece'] not in by: fail('edge references missing/unowned piece')
    p=by[ref['piece']];names=[n['name'] for n in p['outline']]
    if ref['from'] not in names or ref['to'] not in names: fail('edge references missing node')
    i,j=names.index(ref['from']),names.index(ref['to'])
    if (i+1)%len(names)==j: index=i;reverse=False
    elif (j+1)%len(names)==i: index=j;reverse=True
    else: fail('edge endpoints must be adjacent named nodes')
    if p['outline'][i].get('dart') or p['outline'][j].get('dart'):
        fail('boundary dart legs are not a supported closed attachment measurement; author sewn edge references')
    pts=P.edge(p,index,64) if saved_edges is None else saved_edges[(p['name'],index)]
    return p,index,(list(reversed(pts)) if reverse else pts)


def port_measure(port, owned, by, env, dims, used, edge_usage, owner, saved_edges=None):
    obj(port,['id','purpose','quantity','chain','target','deductions','landmarks'],label='port')
    ident(port['id'],'port id');enum(port['purpose'],PURPOSES,'port purpose');integer(port['quantity'],'port quantity',1)
    chain=seq(port['chain'],'attachment chain',True)
    lengths=[];resolved=[]
    for ref in chain:
        p,index,pts=edge_ref(ref,by,owned,saved_edges)
        if port['quantity']>owned[p['name']]: fail('port quantity exceeds piece cut quantity')
        edgekey=(p['name'],index)
        if edgekey in edge_usage: fail('edge already paired/claimed by another port')
        edge_usage.add(edgekey)
        lengths.append(P.length(pts));resolved.append((p,index,pts))
    # Cross-piece chains are explicit summed attachments. Same-piece segments must join in order.
    for a,b in zip(chain,chain[1:]):
        if a['piece']==b['piece'] and a['to']!=b['from']: fail('chain is not contiguous; split into ports')
    raw_length=sum(lengths)
    deduction_total=0; deduction_spans=[]
    for deduction in seq(port['deductions'],'deductions'):
        obj(deduction,['kind','segment','target','source'],['dart_index','from','to'],'deduction')
        enum(deduction['kind'],['dart','pleat','overlap'],'deduction kind');string(deduction['source'],'deduction source')
        segment=integer(deduction['segment'],'deduction segment')
        if segment>=len(resolved): fail('invalid deduction segment')
        p,index,pts=resolved[segment]
        if len(pts)!=2: fail('deductions only support straight attachment seams')
        if deduction['kind']=='dart':
            if set(deduction)!= {'kind','segment','target','source','dart_index'}: fail('dart deduction requires only dart_index')
            di=integer(deduction['dart_index'],'dart_index')
            if di>=len(p.get('darts_in',[])): fail('missing internal dart')
            dt=p['darts_in'][di];a,b=dt[1],dt[-1]
        else:
            if set(deduction)!= {'kind','segment','target','source','from','to'}: fail('pleat/overlap needs named span endpoints')
            nodes={n['name']:n['p'] for n in p['outline']}
            if deduction['from'] not in nodes or deduction['to'] not in nodes: fail('deduction node missing')
            a,b=nodes[deduction['from']],nodes[deduction['to']]
        # A straight projected take-up is only supported when the mouth lies on this segment.
        if any(P.seg_dist(q,*pts)>1e-7 for q in (a,b)): fail('unsupported closure: deduction mouth not on attachment segment')
        distance=P.dist(a,b)
        lo,hi=sorted((P.dist(pts[0],a),P.dist(pts[0],b)))
        if distance<=0: fail('degenerate deduction mouth')
        if any(segment==si and min(hi,h)>max(lo,l)+1e-9 for si,l,h in deduction_spans):
            fail('duplicate/overlapping deduction spans')
        deduction_spans.append((segment,lo,hi))
        wanted,unit=lookup(deduction['target'],env,used)
        kind={'dart':'dart_takeup','pleat':'pleat_takeup','overlap':'closure_overlap'}[deduction['kind']]
        if dims.get(deduction['target'],{}).get('kind')!=kind: fail('deduction target kind mismatch')
        if unit!='length' or abs(distance-wanted)>TOL: fail('geometry-derived deduction target mismatch')
        deduction_total+=distance;lengths[segment]-=distance
    if any(x < -1e-9 for x in lengths) or sum(lengths)<=0: fail('deductions consume attachment length')
    total=sum(lengths)
    target,unit=lookup(port['target'],env,used)
    if unit!='length' or dims.get(port['target'],{}).get('kind') not in ('finished_length','finished_girth'):
        fail('port target must name a frozen finished dimension')
    if abs(total-target)>TOL+1e-9: fail(owner+': attachment target mismatch (geometry %.6f cm, target %.6f cm)'%(total,target))
    landmarks={}
    last=-1
    for l in seq(port['landmarks'],'port landmarks',True):
        obj(l,['id','after'],label='port landmark');ident(l['id'],'landmark id')
        after=integer(l['after'],'landmark after')
        if l['id'] in landmarks or after<=last or after>len(lengths): fail('duplicate/out-of-order landmark')
        last=after;landmarks[l['id']]=sum(lengths[:after])
    if list(landmarks.values())[0]!=0 or list(landmarks.values())[-1]!=total:
        fail('landmarks must cover both chain endpoints')
    return dict(length_cm=total, target_cm=target, quantity=port['quantity'], purpose=port['purpose'],
                landmarks=landmarks, deduction_cm=deduction_total, raw_length_cm=raw_length)


def lookup(name, env, used):
    if not isinstance(name,str) or name not in env: fail('unknown dimension target '+str(name))
    used.add(name);return env[name]


def pair_attachments(attachments, ports, env, dims, material, used):
    result=[];paired=set()
    for a in unique(seq(attachments,'attachments'),'id','attachment').values():
        obj(a,['id','kind','a','b','relation','landmarks'],label='attachment')
        ident(a['id'],'attachment id');enum(a['kind'],PURPOSES,'attachment kind')
        if a['a']==a['b'] or a['a'] not in ports or a['b'] not in ports: fail('attachment references missing/unpaired port')
        if a['a'] in paired or a['b'] in paired: fail('port must be paired exactly once')
        paired.update([a['a'],a['b']]);pa,pb=ports[a['a']],ports[a['b']]
        if pa['quantity']!=pb['quantity']: fail('paired attachment quantity mismatch')
        if pa['purpose']!=a['kind'] or pb['purpose']!=a['kind']: fail('paired purpose mismatch')
        rel=a['relation'];obj(rel,['mode'],['target','reason','material_id'],'attachment relation')
        enum(rel['mode'],['equal','ease','stretch','gather'],'relation mode')
        delta=0;ratio=1
        if rel['mode']=='equal':
            if set(rel)!={'mode'}: fail('equal relation contains unknown ease permission')
        else:
            obj(rel,['mode','target','reason','material_id'],label='non-equal relation')
            string(rel['reason'],'relation reason')
            if rel['material_id']!=material['id']: fail('relation material mismatch')
            if a['kind'] in ('side','inseam'): fail('ordinary seam requires equal relation')
            if a['kind'] in ('shoulder','closure') and rel['mode']!='ease':
                fail('shoulder/closure seam requires equal or explicit ease relation')
            target,unit=lookup(rel['target'],env,used)
            if dims.get(rel['target'],{}).get('kind')!=rel['mode']: fail('relation target kind mismatch')
            if rel['mode']=='ease':
                if unit!='length': fail('ease target requires length unit')
                delta=target
            else:
                if unit!='ratio' or target<=0: fail('stretch/gather target requires positive ratio')
                ratio=target
        # Fixed target agreement is independent of measured mismatch.
        if abs(pa['target_cm']-(pb['target_cm']*ratio+delta))>1e-8: fail('independent paired targets disagree with relation')
        if abs(pa['length_cm']-(pb['length_cm']*ratio+delta))>TOL+1e-9: fail('paired seam mismatch')
        ids=seq(a['landmarks'],'attachment landmarks',True)
        if len(set(ids))!=len(ids) or set(ids)!=set(pa['landmarks']) or set(ids)!=set(pb['landmarks']):
            fail('paired landmark inventory mismatch')
        # Distribute only the independently fixed delta in proportion to frozen B target.
        for name in ids:
            x,y=pa['landmarks'][name],pb['landmarks'][name]
            expected=y*ratio+delta*(y/pb['target_cm'])
            if abs(x-expected)>TOL+1e-9: fail('paired landmark mismatch')
        result.append({'id':a['id'],'kind':a['kind'],'a_cm':pa['length_cm'],'b_cm':pb['length_cm'],
                       'quantity':pa['quantity'],'mode':rel['mode'],'delta_cm':delta,'ratio':ratio,
                       'landmarks':ids})
    if set(ports)!=paired: fail('unpaired attachment ports: '+', '.join(sorted(set(ports)-paired)))
    return result


def _prepare(data, geometry=True):
    if not isinstance(data,dict) or data.get('schema')!=SCHEMA: fail('unknown/missing workflow schema')
    check_structure(data,'proposal')
    obj(data,['schema','status','id','title','analysis','profile','design','construction','components','attachments','recipe'],label='workflow')
    enum(data['status'],['proposal'],'status');ident(data['id'],'workflow id');string(data['title'],'title')
    analysis(data['analysis']);env,template_status=profile(data['profile'])
    used=dimensions(data['design'],env)
    pieces,deps=resolve_recipe(data['recipe'],env);by={p['name']:p for p in pieces}
    components=list(unique(seq(data['components'],'components'),'id','component').values())
    owned_all=set();ports={};edge_usage=set();dims={'finished.'+k:v for k,v in data['design']['dimensions'].items()}
    for c in components:
        obj(c,['id','role','profile_id','pieces','depends_on','ports'],label='component')
        ident(c['id'],'component id');ident(c['role'],'component role')
        if c['profile_id']!=data['profile']['id']: fail('component has incompatible body profile')
        own={}
        for piece in seq(c['pieces'],'component pieces',True):
            obj(piece,['name','quantity'],label='component piece');integer(piece['quantity'],'cut quantity',1)
            name=piece['name']
            if name in owned_all: fail('piece ownership collision')
            if name not in by: fail('component references missing piece')
            if by[name]['cut']!=str(piece['quantity'])+'x': fail('cut label must match explicit component quantity (expanded pieces only)')
            own[name]=piece['quantity'];owned_all.add(name)
        actual=set().union(*(deps[name] for name in own))
        declared=seq(c['depends_on'],'depends_on')
        if any(not isinstance(x,str) for x in declared) or len(set(declared))!=len(declared) or set(declared)!=actual:
            fail('component dependency coverage mismatch: '+c['id'])
        used.update(actual)
        for port in unique(seq(c['ports'],'ports'),'id','port').values():
            key=c['id']+'.'+port['id']
            if geometry: ports[key]=port_measure(port,own,by,env,dims,used,edge_usage,key)
    if owned_all!=set(by): fail('recipe has unowned piece / missing component')
    missing,required=inventory(data['construction'],components)
    result={'status':'proposal-incomplete' if missing else 'proposal-ready',
            'support':data['construction']['support'],'missing_components':missing,'required_roles':required,
            'fit_status':'physical-fit-not-approved','template_status':template_status,'attachments':[],
            'geometry_checked':False,'assembly_scope':'declared-attachments-only'}
    if geometry:
        if missing: fail('missing component roles: '+', '.join(missing))
        if not pieces or data['construction']['support']=='inventory-only': fail('inventory-only is not an executable recipe')
        geometry_checks(pieces)
        result['attachments']=pair_attachments(data['attachments'],ports,env,dims,data['design']['material'],used)
        # Every conditional companion requires at least one attachment with the correct purpose.
        companion={'sleeve':'armhole','collar':'neck','collar_stand':'neck','hood':'neck','rib':'neck',
                   'neck_facing':'neck','cuff':'cuff','waistband':'waist','waist_facing':'waist',
                   'elastic_casing':'waist','closure':'closure','pocket_bag':'pocket','pocket_facing':'pocket'}
        for c in components:
            purpose=companion.get(c['role'])
            # Coupons can isolate one joint (e.g. cuff); their explicit scope is never a full garment.
            if purpose:
                if c['role']=='sleeve' and data['construction']['support']=='synthetic-attachment-control':
                    purpose='cuff' if data['construction']['features']['cuffs'] else purpose
                if not any(p['purpose']==purpose for p in c['ports']): fail('missing companion attachment: '+c['id'])
        ignored=set()
        for prefix,record in [('body.',data['profile']['unused']),('finished.',data['design']['unused'])]:
            if not isinstance(record,dict): fail('unused coverage must be an object of reasons')
            for k,reason in record.items():
                string(reason,'unused reason');name=prefix+k
                if name not in env or name in used: fail('invalid unused dependency declaration')
                ignored.add(name)
        if set(env)!=used|ignored: fail('unused dimension without coverage/reason: '+', '.join(sorted(set(env)-used-ignored)))
        result['geometry_checked']=True
        result['ports']=ports
        result['measurement_basis']='recipe edge chains, 64 segments per curve; cm; saved output not yet checked'
    return result,pieces


def validate(data, geometry=True):
    try:
        return _prepare(data,geometry)[0]
    except (KeyError,TypeError,IndexError,OverflowError) as e:
        raise ValueError('malformed workflow record: '+str(e)) from e


def generate(data):
    result=validate(data)
    env,_=profile(data['profile']);dimensions(data['design'],env)
    pieces,_=resolve_recipe(data['recipe'],env)
    return {'pieces':pieces, 'workflow_contract_sha256':digest(data), 'workflow_result':result,
            'shell_status':{'supported':False,'reason':'Workflow verifies 2D only; physical fit not approved'}}


def extend(data,target):
    _,before=_prepare(data)
    if not isinstance(target,dict) or target.get('schema')!=TARGET_SCHEMA: fail('unknown/missing target schema')
    check_structure(target,'target')
    obj(target,['schema','selection','parameters','dimensions'],label='target')
    if not isinstance(target['dimensions'],dict) or set(target['dimensions'])!=set(data['design']['dimensions']):
        fail('target must contain every frozen dimension')
    if not isinstance(target['parameters'],dict) or set(target['parameters'])!=set(data['profile']['parameters']):
        fail('target must contain every frozen profile parameter')
    result=copy.deepcopy(data)
    result['profile']['selection']=copy.deepcopy(target['selection'])
    result['profile']['parameters']=copy.deepcopy(target['parameters'])
    result['design']['dimensions']=copy.deepcopy(target['dimensions'])
    # Allowances/construction are invariants of size extension. A redesign needs a new proposal.
    for name,q in data['design']['dimensions'].items():
        if q['kind'] in ('seam_allowance','closure_overlap','dart_takeup','pleat_takeup','shrink','stretch','gather'):
            if result['design']['dimensions'][name]!=q: fail('size extension must preserve construction/allowance targets')
    _,after=_prepare(result)
    for a,b in zip(before,after):
        def allowances(p):
            return (p['allowance'],p.get('allowances',{}),
                    [P.edge_allowance(p,i) for i in range(len(p['outline']))])
        if allowances(a)!=allowances(b):
            fail('size extension must preserve resolved default/per-edge allowances (cm): '+a['name'])
    return result


def digest(data):
    return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest()


def filehash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    def pairs(items):
        result={}
        for k,v in items:
            if k in result: fail('duplicate JSON key '+k)
            result[k]=v
        return result
    with Path(path).open(encoding='utf-8') as f:
        return json.load(f,object_pairs_hook=pairs,parse_constant=lambda x: fail('nonfinite JSON number '+x))


def save(path,data):
    Path(path).write_text(json.dumps(data,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')


def writer_svg(root, pieces, title):
    """Accept only the core's fixed single-size SVG tree, without executing content.

    The expected tree is also the element/attribute/value/reference allowlist. This
    writer emits no references: even local use/href/url structures are unsupported.
    Parsing UTF-8 ourselves and rejecting declarations/PIs prevents DTD/entity or
    stylesheet processing before the structural comparison.
    """
    raw=(root/'pattern.svg').read_text(encoding='utf-8')
    if re.search(r'<!|<\?(?!xml\s)',raw):
        fail('SVG unsupported declaration or processing instruction')
    actual=ET.fromstring(raw)
    with tempfile.TemporaryDirectory(prefix='.workflow-svg-',dir=root.parent) as folder:
        path=Path(folder)/'expected.svg'
        P.write_svg([('one',{'pieces':pieces})],str(path),title)
        expected=ET.parse(path).getroot()
    def shape(node):
        return (node.tag,node.attrib,(node.text or '') if not len(node) else (node.text or '').strip(),
                (node.tail or '').strip(),[shape(child) for child in node])
    if shape(actual)!=shape(expected):
        fail('SVG unsupported writer structure, attributes, or effective geometry/text readback')
    return actual


def planar_dxf(doc, pieces, offsets):
    """Fixed LINE/TEXT format: no extra entity semantics; labels have positioned roles."""
    import ezdxf
    common={'handle','owner','layer'}
    for e in doc.modelspace():
        typ=e.dxftype()
        if typ not in ('LINE','TEXT'): fail('DXF unsupported writer entity '+typ)
        fields={'start','end'} if typ=='LINE' else {'insert','height','text'}
        if set(e.dxfattribs())-common-fields or e.xdata or e.appdata or e.has_extension_dict or e.reactors:
            fail('DXF unsupported writer entity properties')
        for field in ('start','end') if typ=='LINE' else ('insert',):
            point=tuple(getattr(e.dxf,field))
            if any(not math.isfinite(v) for v in point) or point[2]!=0:
                fail('DXF must contain finite planar entities with zero Z')
    # Layer and text-style tables also affect visibility and text geometry. The
    # writer uses only these defaults; reject overrides rather than interpret CAD.
    reference=ezdxf.new('R2010')
    for name in ('CUT','SEAM','DART','INTERNAL','BUTTON','FOLD','NOTCHES','GRAIN','TEXT'):
        reference.layers.new(name)
    stream=io.StringIO();reference.write(stream);stream.seek(0)
    reference=ezdxf.read(stream)
    def properties(record):
        return {k:v for k,v in record.dxfattribs().items() if k not in ('handle','owner')}
    for table in ('layers','styles','linetypes'):
        actual={e.dxf.name:properties(e) for e in getattr(doc,table)}
        expected={e.dxf.name:properties(e) for e in getattr(reference,table)}
        if actual!=expected: fail('DXF unsupported writer '+table+' properties')
    for e in doc.linetypes:
        if e.pattern_tags.tags!=reference.linetypes.get(e.dxf.name).pattern_tags.tags:
            fail('DXF unsupported writer linetype pattern')
    expected_text=Counter()
    for p,off in zip(pieces,offsets):
        cx,cy=P.center(p,off)
        for k,text in enumerate((p['name'],'Size one',p['cut'])):
            expected_text[('TEXT',text,(cx,-(cy+k*9),0),6)]+=1
    actual_text=Counter((e.dxf.layer,e.dxf.text,tuple(e.dxf.insert),e.dxf.height)
                        for e in doc.modelspace().query('TEXT'))
    if actual_text!=expected_text: fail('DXF positioned text/quantity role readback mismatch')


def saved_contract(data, by, edges, representation):
    """Reapply all port/deduction/target/relation/landmark checks to read file coordinates."""
    env,_=profile(data['profile']);used=dimensions(data['design'],env)
    dims={'finished.'+k:v for k,v in data['design']['dimensions'].items()}
    ports={};edge_usage=set()
    try:
        for c in data['components']:
            owned={p['name']:p['quantity'] for p in c['pieces']}
            for port in c['ports']:
                key=c['id']+'.'+port['id']
                ports[key]=port_measure(port,owned,by,env,dims,used,edge_usage,key,edges)
        attachments=pair_attachments(data['attachments'],ports,env,dims,data['design']['material'],used)
    except ValueError as e:
        fail('saved '+representation+' contract at writer precision (0.001 mm coordinates, 1 mm tolerance): '+str(e))
    return dict(representation=representation,coordinate_unit='mm',coordinate_decimals=3,
                curve_segments_per_edge=16,measurement_unit='cm',ordinary_tolerance_mm=1,
                ports=ports,attachments=attachments)


def readback(root,pieces,data):
    """Bind the fixed writer format, then measure contracts on BOTH actual saved paths.

    Writer geometry is used only to identify ordered paths/edge boundaries. Measurements
    consume the parsed LINE endpoints / polygon points, including saved rounding. Recipe
    coordinates and its 64-sample measurements are never substituted for those points.
    """
    import ezdxf
    path=root/'pattern_one.dxf';V.validate_dxf(path);doc=ezdxf.readfile(path)
    if doc.dxfversion!='AC1024': fail('DXF must be R2010')
    offsets,_,_=P.layout([pieces])
    planar_dxf(doc,pieces,offsets)
    root_svg=writer_svg(root,pieces,data['title'])
    groups=root_svg.findall('{http://www.w3.org/2000/svg}g')
    lines=list(doc.modelspace().query('LINE'));cursor=0;marks=0
    saved={kind:{p['name']:copy.deepcopy(p) for p in pieces} for kind in ('dxf','svg')}
    edges={kind:{} for kind in saved}
    for p,off,g in zip(pieces,offsets,groups):
        paths=[('CUT',P.cut_line(p),True,None),('SEAM',P.outline(p),True,None)]
        paths += [(layer,P.outline(h),True,h['name']) for h in p.get('holes',[]) for layer in ('CUT','SEAM')]
        paths += [(layer,pts,False,None) for layer,pts in P.construction_marks(p)]
        svg_paths=[e for e in g if e.tag in ('{http://www.w3.org/2000/svg}polygon','{http://www.w3.org/2000/svg}polyline')]
        dart_index=0
        # The canonical SVG comparison above guarantees the same path inventory/order.
        for (layer,pts,closed,hole),element in zip(paths,svg_paths):
            mm=[P.mm(v,off) for v in pts]
            coords=[(round(x,3),round(-y,3)) for x,y in mm]
            expected=[(layer,a,b) for a,b in zip(coords,coords[1:]+(coords[:1] if closed else []))]
            entities=lines[cursor:cursor+len(expected)];cursor+=len(expected)
            actual=[(e.dxf.layer,tuple(e.dxf.start)[:2],tuple(e.dxf.end)[:2]) for e in entities]
            if actual!=expected: fail('DXF ordered geometry/mark readback mismatch')
            if not closed: marks+=len(expected)
            dxf_pts=[tuple(e.dxf.start)[:2] for e in entities]
            if not closed: dxf_pts.append(tuple(entities[-1].dxf.end)[:2])
            svg_pts=[tuple(float(x) for x in q.split(',')) for q in element.attrib['points'].split()]
            for kind,points in (('dxf',dxf_pts),('svg',svg_pts)):
                local=[((x-off[0])/10,((-y if kind=='dxf' else y)-off[1])/10) for x,y in points]
                piece=saved[kind][p['name']]
                if layer=='SEAM' and hole is None:
                    loop=local+[local[0]];start=0
                    for i,node in enumerate(piece['outline']):
                        count=len(P.edge(p,i))-1
                        edges[kind][(p['name'],i)]=loop[start:start+count+1]
                        node['p']=loop[start];start+=count
                    if start!=len(local): fail('saved edge boundary count mismatch')
                if layer=='DART':
                    piece['darts_in'][dart_index]=local[:-1]
            if layer=='DART': dart_index+=1
    if cursor!=len(lines): fail('DXF unexpected extra geometry/mark readback')
    contracts={kind:saved_contract(data,saved[kind],edges[kind],representation)
               for kind,representation in (('dxf','DXF LINE chains'),('svg','SVG polygon/polyline chains'))}
    return {'dxf_units':doc.header['$INSUNITS'],'dxf_version':doc.dxfversion,'missing_segments':0,
            'geometry_and_mark_segments':cursor,'mark_segments':marks,
            'pieces':len(pieces),'svg_test_square_mm':[100,100],'saved_contracts':contracts}


def engine_sources():
    return {**{name:filehash(Path(__file__).with_name(name)) for name in ('workflow.py','pattern.py','validation.py')},
            'workflow.schema.json':filehash(SCHEMA_PATH)}


def export_workflow(data,out):
    generated=generate(data)
    out=Path(out).resolve()
    if out.exists(): fail('choose a fresh output directory')
    out.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.workflow-stage-',dir=out.parent) as folder:
        stage=Path(folder)
        sets=[('one',generated)]
        if not P.export(sets,str(stage),data['title']):
            # Keep editable diagnostics but publish no deliverables on failed core geometry checks.
            out.mkdir();shutil.copytree(stage/'rejected',out/'rejected');fail('core export geometry rejected')
        save(stage/'workflow.json',data)
        manifest={'schema':BUNDLE_SCHEMA,'status':'exported-2D-verified','fit_status':'physical-fit-not-approved',
                  'contract_sha256':digest(data),'engine_sources':engine_sources(),
                  'artifacts':{name:filehash(stage/name) for name in ('workflow.json','pieces_one.json','pattern.svg','pattern_one.dxf')}}
        save(stage/'workflow-bundle.json',manifest)
        result=verify_bundle(stage/'workflow-bundle.json')
        # Publication happens only after both saved-file readbacks pass.
        stage.rename(out)
    result['bundle']=str(out/'workflow-bundle.json')
    return result


def verify_bundle(path):
    path=Path(path).resolve();m=load(path)
    if not isinstance(m,dict) or m.get('schema')!=BUNDLE_SCHEMA: fail('unknown/missing bound bundle schema')
    check_structure(m,'bundle')
    obj(m,['schema','status','fit_status','contract_sha256','engine_sources','artifacts'],label='bundle')
    enum(m['status'],['exported-2D-verified'],'bundle status');enum(m['fit_status'],['physical-fit-not-approved'],'fit_status')
    if m['engine_sources']!=engine_sources(): fail('source binding differs; regenerate under current engine')
    names={'workflow.json','pieces_one.json','pattern.svg','pattern_one.dxf'}
    if not isinstance(m['artifacts'],dict) or set(m['artifacts'])!=names: fail('missing/unknown artifact binding')
    for name,wanted in m['artifacts'].items():
        f=path.parent/name
        if f.is_symlink() or not f.is_file(): fail('missing or unsafe bound artifact '+name)
        if filehash(f)!=wanted: fail('artifact hash binding mismatch: '+name)
    data=load(path.parent/'workflow.json')
    if digest(data)!=m['contract_sha256']: fail('workflow contract binding mismatch')
    generated=generate(data);saved=load(path.parent/'pieces_one.json')
    enum(saved.get('validation_status'),['passed_2d'],'saved geometry status')
    if saved.get('pieces')!=generated['pieces'] or saved.get('workflow_contract_sha256')!=m['contract_sha256']:
        fail('saved geometry differs from bound recipe/contract')
    result=validate(data)
    result.update(status='exported-2D-verified',readback=readback(path.parent,generated['pieces'],data),bundle=str(path))
    measured=result['readback']['saved_contracts']['dxf']
    result.update(ports=measured['ports'],attachments=measured['attachments'],
                  measurement_basis=measured['representation']+'; saved mm coordinates, measurements in cm')
    return result


def reexport(path,out):
    verify_bundle(path)
    return export_workflow(load(Path(path).resolve().parent/'workflow.json'),out)


def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    subs=ap.add_subparsers(dest='command',required=True)
    p=subs.add_parser('blueprints');p.set_defaults(file=None)
    for name in ('validate','export','verify','reexport','extend'):
        p=subs.add_parser(name);p.add_argument('file',type=Path)
        if name=='validate': p.add_argument('--inventory-only',action='store_true')
        if name in ('export','reexport','extend'): p.add_argument('--out',type=Path,required=True)
        if name=='extend': p.add_argument('--target',type=Path,required=True)
    args=ap.parse_args(argv)
    try:
        if args.command=='blueprints': result={'families':BLUEPRINTS,'features':FEATURES,'scope':'inventory requirements; not executable whole-garment recipes'}
        elif args.command=='validate': result=validate(load(args.file),not args.inventory_only)
        elif args.command=='export': result=export_workflow(load(args.file),args.out)
        elif args.command=='verify': result=verify_bundle(args.file)
        elif args.command=='reexport': result=reexport(args.file,args.out)
        else:
            data=extend(load(args.file),load(args.target))
            if args.out.exists(): fail('choose a fresh target proposal path')
            args.out.parent.mkdir(parents=True,exist_ok=True);save(args.out,data)
            result=dict(validate(data),proposal=str(args.out.resolve()))
        print(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False));return 0
    except (ValueError,KeyError,TypeError,IndexError,OverflowError,OSError,ET.ParseError) as e:
        print('workflow: '+str(e),file=sys.stderr);return 2


if __name__=='__main__':
    raise SystemExit(main())
