"""Portable synthetic seam coupons, never a garment or a real catalog row."""
import copy
import json
from pathlib import Path


def q(value, kind='finished_length', unit='cm'):
    return dict(value=value, unit=unit, source='synthetic independent drafting brief',
                basis='engineering-selected', kind=kind)


def ref(name):
    return {'op': 'param', 'id': name}


def make(family='tops', style='shirt', attachment='neck', accessory='collar'):
    width = 'finished.attachment'
    dimensions={'attachment': q(20), 'length': q(30), 'accessory_depth': q(6),
                'allowance': q(1, 'seam_allowance')}
    pieces=[]; components=[]
    for name,role,depth,port in [('Panel','front',ref('finished.length'),'opening'),
                                  ('Back','back',ref('finished.length'),None),
                                  ('Companion',accessory,ref('finished.accessory_depth'),'join')]:
        p={'name':name,'cut':'1x','allowance':ref('finished.allowance'),
           'outline':[{'name':'a','p':[0,0]},{'name':'b','p':[ref(width),0]},
                      {'name':'c','p':[ref(width),depth]},{'name':'d','p':[0,depth]}],
           'grain':[[2,2],[2,4]],'notches':[{'edge':0,'d':2}],
           'lines':[[[2,1],[4,1]]],'buttons':[[5,2]]}
        pieces.append(p)
        component={'id':name.lower(),'role':role,'profile_id':'synthetic-profile',
                   'pieces':[{'name':name,'quantity':1}],
                   'depends_on': sorted([width,'finished.allowance',
                      'finished.accessory_depth' if name=='Companion' else 'finished.length']),
                   'ports':[]}
        if port:
            component['ports']=[{'id':port,'purpose':attachment,'quantity':1,
                'chain':[{'piece':name,'from':'a','to':'b'}], 'target':width,
                'deductions':[], 'landmarks':[{'id':'start','after':0},{'id':'end','after':1}]}]
        components.append(component)
    features=dict(paneling='front-back', alternative_roles=[], sleeves='none', neck='none',
                  cuffs=False, waist='none', pockets='none', lining=False,
                  closure='none', placket=False, hem='turned', extra_roles=[])
    if attachment=='neck': features['neck']=accessory
    elif attachment=='waist': features['waist']='band'
    elif attachment=='cuff':
        features['cuffs']=True;features['sleeves']='set-in'
        components[0]['role']='sleeve'; features['paneling']='alternative'
        features['alternative_roles']=['sleeve','back']
    elif attachment=='armhole': features['sleeves']='set-in'
    elif attachment=='pocket': features['pockets']='inseam'
    elif attachment=='closure': features['closure']='buttons'
    return {
      'schema':'component-workflow/v1','status':'proposal','id':'synthetic-'+family,
      'title':'SYNTHETIC attachment coupons — not a complete garment',
      'analysis':{'sources':[{'id':'synthetic-brief','identity':'invented test brief; no photo'}],
        'observations':[], 'assumptions':[{'source_id':'synthetic-brief','description':'Rectangle coupons, not garment panels',
            'uncertainty':'deliberate test geometry'}], 'landmarks':[],
        'scale':{'kind':'uncalibrated','source_id':'synthetic-brief'},
        'size_basis':'nominal engineering selection; no inferred wearer dimensions'},
      'profile':{'id':'synthetic-profile','template':{'provider':'synthetic-test',
        'model_id':'coupon-model','template_id':'coupon-template','source':'invented portable test rules',
        'rule_state':'synthetic-declared','custom_allowed':True,
        'parameters':{'span':{'uid':'RAW-SPAN-UID','unit':'mm','required':True}},
        'standard_rows':{'reference':{'span':200}}},
        'selection':{'kind':'standard','row_id':'reference'},
        'parameters':{'span':dict(q(200,'body_length','mm'),uid='RAW-SPAN-UID')}, 'unused':{}},
      'design':{'dimensions':dimensions,'constraints':[{'id':'body_to_attachment',
        'left':ref(width),'right':ref('body.span')}],
        'material':{'id':'synthetic-woven','source':'test brief','description':'nonstretch coupon'},
        'unused':{}},
      'construction':{'family':family,'style':style,'features':features,
        'support':'synthetic-attachment-control','recipe_id':'named-coupon-recipe/v1',
        'limitations':['No whole-garment drafting or fit claim']},
      'components':components,
      'attachments':[{'id':'paired-attachment','kind':attachment,'a':'panel.opening','b':'companion.join',
         'relation':{'mode':'equal'},'landmarks':['start','end']}],
      'recipe':{'pieces':pieces}}


if __name__=='__main__':
    root=Path(__file__).parent
    for filename,data in [('top.json',make()),('bottom.json',make('bottoms','skirt','waist','waistband')),
                           ('outerwear.json',make('outerwear','coat','neck','hood')),
                           ('one-piece.json',make('one-piece','dress','neck','rib')),
                           ('cuff.json',make('tops','shirt','cuff','cuff')),
                           ('sleeve.json',make('tops','tee','armhole','sleeve')),
                           ('pocket.json',make('bottoms','trousers','pocket','pocket_bag')),
                           ('closure.json',make('outerwear','jacket','closure','closure'))]:
        (root/filename).write_text(json.dumps(data,indent=2)+'\n')
    target={'schema':'component-workflow-target/v1','selection':{'kind':'custom-target'},
      'parameters':{'span':dict(q(237,'body_length','mm'),uid='RAW-SPAN-UID')},
      'dimensions':make()['design']['dimensions']}
    target['dimensions']['attachment']=q(23.7)
    (root/'custom-target.json').write_text(json.dumps(target,indent=2)+'\n')
