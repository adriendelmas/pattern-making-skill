"""Portable catalog tests. All records here are invented, never private exports."""
import copy
import hashlib
import json
from pathlib import Path

import pytest

import size_catalog as C


LENGTH = 'рз_demo_length'
SHAPE = 'рз_demo_shape'
SOURCE = 'synthetic:fixture'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode()


def fake_data():
    templates, sizes, measurements, parameters, rules = [], [], [], [], []
    for ti, labels in [('template-a', ['00', '2/91']), ('template-b', ['00'])]:
        ids = [f'{ti}-model-{i}' for i in range(len(labels))]
        templates.append(dict(kind='standard_body_mannequin_template', name='Same synthetic title',
            not_finished_garment_or_ease=True, ordered_mannequin_ids=ids,
            ordered_size_labels=labels, raw_record_canonical_sha256='a'*64, size_count=len(ids),
            source_id=SOURCE, source_pointer='/synthetic', source_url='https://example.invalid/chart',
            template_id=ti, type='SYNTHETIC', updated_at='synthetic-date'))
        for i, (mi, label) in enumerate(zip(ids, labels)):
            sizes.append(dict(api_uid_intentionally_not_exported=True, full_field_rules_captured=False,
                mannequin_id=mi, ordinal=i, parameter_count=2, parameter_uids=[LENGTH, SHAPE],
                raw_record_canonical_sha256='b'*64, raw_unit=None, size_label=label,
                source_id=SOURCE, source_pointer='/synthetic/model', template_id=ti, type='SYNTHETIC'))
            for uid, name, value in [(LENGTH, 'Synthetic length', 12+i), (SHAPE, 'Synthetic shape', 0)]:
                observed = ti == 'template-a' and i == 0
                measurements.append(dict(display_cm=value if observed else None,
                    display_in='10 1/2' if observed else None, display_source_id=SOURCE if observed else None,
                    field_rules_captured_for_this_size=observed and uid == LENGTH, label=name,
                    mannequin_id=mi, param_uid=uid, raw_equals_display_cm=True if observed else None,
                    raw_record_canonical_sha256='c'*64, raw_unit=None, raw_value=value,
                    raw_value_json_type='int', size_label=label, source_id=SOURCE,
                    source_pointer='/synthetic/param', template_id=ti))
    for uid, name, semantic in [(LENGTH, 'Synthetic length', 'body_mannequin_measurement'),
                                 (SHAPE, 'Synthetic shape', 'body_shape_parameter_website_defined')]:
        vals = [r['raw_value'] for r in measurements if r['param_uid'] == uid]
        parameters.append(dict(param_uid=uid, uid_codepoints=[f'U+{ord(c):04X}' for c in uid], label=name,
            field_keys=['syntheticLength' if uid == LENGTH else 'syntheticShape'],
            label_evidence=[dict(field_key='syntheticLength' if uid == LENGTH else 'syntheticShape',
                                 label=name, source_id=SOURCE)],
            raw_observation_count=len(vals), observed_raw_min=min(vals), observed_raw_max=max(vals),
            observed_range_is_constraint=False, raw_unit_global=None, captured_unit_labels=['cm', 'in'],
            semantic_class=semantic, rule_observation_count=1 if uid == LENGTH else 0,
            global_allowed_min=None, global_allowed_max=None, unit_note='Synthetic unknown semantics'))
    rules.append(dict(boundary_inclusivity=None, cross_field_constraints=None, description='',
        display_cm=12, display_in='10 1/2', field_key='syntheticLength', is_active_at_capture=True,
        is_valid_at_capture=True, label='Synthetic length', mannequin_id='template-a-model-0',
        max={'cm': 20, 'in': '20'}, min={'cm': 10, 'in': '10'}, param_uid=LENGTH,
        required=None, scope='this captured mannequin field only; not universal type/chart limits',
        size_label='00', source_binding='synthetic explicit ID', source_field_sha256='d'*64,
        source_id=SOURCE, step=None, template_id='template-a', type='SYNTHETIC',
        units_status='captured UI cm/in', unknowns=['boundary semantics']))
    return {'templates.jsonl': templates, 'sizes.jsonl': sizes, 'measurements.jsonl': measurements,
            'parameter_catalog.json': parameters, 'field_rules.jsonl': rules,
            'sources.json': [dict(source_id=SOURCE, path='never-opened.json', kind='local_file',
                                  role='synthetic', bytes=0, sha256='e'*64)]}


def write_catalog(root, data=None, extra_manifest=None):
    root.mkdir(exist_ok=True)
    data = fake_data() if data is None else data
    manifest = []
    for name, rows in data.items():
        content = b'\n'.join(encoded(r) for r in rows)+b'\n' if name.endswith('.jsonl') else encoded(rows)
        (root / name).write_bytes(content)
        manifest.append(dict(name=name, bytes=len(content), sha256=digest(content)))
    if extra_manifest:
        manifest.extend(extra_manifest)
    content = encoded(manifest)
    (root / 'artifact_hashes.json').write_bytes(content)
    return digest(content)


@pytest.fixture
def catalog(tmp_path):
    root = tmp_path / 'catalog'
    pin = write_catalog(root)
    lock = C.pin_catalog(root, pin)
    return C.Catalog.load(root, lock), root, lock


def test_catalog_exact_complete_and_private_scope(catalog):
    c, root, lock = catalog
    assert c.counts == {'templates': 2, 'models': 3, 'observations': 6, 'parameters': 2,
                        'rules': 1, 'rule_models': 1, 'display_observations': 2}
    assert set(lock['files']) == set(fake_data())
    assert c.list_templates()[0]['name'] == c.list_templates()[1]['name']
    assert [r['size_label'] for r in c.list_models('template-a')] == ['00', '2/91']
    assert c.list_models('template-b')[0]['mannequin_id'] != c.list_models('template-a')[0]['mannequin_id']
    c.list_templates()[0]['name'] = 'MUTATED'
    assert c.list_templates()[0]['name'] == 'Same synthetic title'


def test_pin_does_not_read_unselected_artifacts(tmp_path):
    pin = write_catalog(tmp_path, extra_manifest=[dict(name='never-execute.py', bytes=99, sha256='0'*64)])
    assert C.pin_catalog(tmp_path, pin)['counts']['models'] == 3


@pytest.mark.parametrize('name', ['../outside.json', '/absolute.json', 'nested/../../x', 'x\\y', './x'])
def test_manifest_paths_rejected(tmp_path, name):
    pin = write_catalog(tmp_path, extra_manifest=[dict(name=name, bytes=0, sha256='0'*64)])
    with pytest.raises(C.CatalogError):
        C.pin_catalog(tmp_path, pin)


def test_symlink_escape_rejected(tmp_path):
    root = tmp_path / 'root'
    pin = write_catalog(root)
    data = (root/'sizes.jsonl').read_bytes()
    (tmp_path/'outside').write_bytes(data)
    (root/'sizes.jsonl').unlink()
    (root/'sizes.jsonl').symlink_to(tmp_path/'outside')
    with pytest.raises(C.CatalogError):
        C.pin_catalog(root, pin)


def test_wrong_manifest_pin_and_changed_bytes(catalog):
    c, root, lock = catalog
    with pytest.raises(C.CatalogError):
        C.pin_catalog(root, '0'*64)
    (root/'sizes.jsonl').write_bytes((root/'sizes.jsonl').read_bytes()+b' ')
    with pytest.raises(C.CatalogError):
        C.Catalog.load(root, lock)


@pytest.mark.parametrize('mutation', [
    lambda d: d['templates.jsonl'].append(copy.deepcopy(d['templates.jsonl'][0])),
    lambda d: d['sizes.jsonl'].append(copy.deepcopy(d['sizes.jsonl'][0])),
    lambda d: d['measurements.jsonl'].append(copy.deepcopy(d['measurements.jsonl'][0])),
    lambda d: d['parameter_catalog.json'].append(copy.deepcopy(d['parameter_catalog.json'][0])),
    lambda d: d['field_rules.jsonl'].append(copy.deepcopy(d['field_rules.jsonl'][0])),
    lambda d: d['sizes.jsonl'][0].update(template_id='template-b'),
    lambda d: d['sizes.jsonl'][0].update(parameter_count=3),
    lambda d: d['sizes.jsonl'][0].update(ordinal=True),
    lambda d: d['templates.jsonl'][0].update(size_count=3),
    lambda d: d['templates.jsonl'][0].update(kind='arbitrary_code'),
    lambda d: d['measurements.jsonl'][0].update(raw_value=True),
    lambda d: d['measurements.jsonl'][0].update(raw_value_json_type='float'),
    lambda d: d['measurements.jsonl'][0].update(size_label='0'),
    lambda d: d['measurements.jsonl'][0].update(param_uid='pз_demo_length'),
    lambda d: d['measurements.jsonl'][0].update(label='Wrong label'),
    lambda d: d['measurements.jsonl'][0].update(source_id='unknown'),
    lambda d: d['measurements.jsonl'][0].update(apiUid='SECRET'),
    lambda d: d['parameter_catalog.json'][0].update(uid_codepoints=['U+0041']),
    lambda d: d['parameter_catalog.json'][0].update(global_allowed_min=1),
    lambda d: d['field_rules.jsonl'][0].update(mannequin_id='template-b-model-0'),
])
def test_invalid_catalog_rejected_even_when_rehashed(tmp_path, mutation):
    data = fake_data()
    mutation(data)
    pin = write_catalog(tmp_path, data)
    with pytest.raises(C.CatalogError):
        C.pin_catalog(tmp_path, pin)


def test_duplicate_json_keys_and_nonfinite_rejected():
    for raw in ['{"id":1,"id":2}', '{"value":NaN}', '{"value":1e999}']:
        with pytest.raises(C.CatalogError):
            C.parse_json(raw)


@pytest.mark.parametrize('mutation', [lambda d: d.update(schema='other/v1'),
    lambda d: d['counts'].update(models=4), lambda d: d.update(token='SECRET'),
    lambda d: d['files'].update({'evil.py': {'sha256':'0'*64,'bytes':0}})])
def test_lock_schema_and_counts(catalog, mutation):
    _, root, lock = catalog
    lock = copy.deepcopy(lock)
    mutation(lock)
    with pytest.raises(C.CatalogError):
        C.Catalog.load(root, lock)


def standard(model='template-a-model-0', template='template-a', sample=None):
    return dict(schema='size-catalog-request/v1', operation='standard', template_id=template,
                mannequin_id=model, rule_sample=sample)


def supplied(uid=LENGTH, value=12.375, unit='cm'):
    return dict(param_uid=uid, value=value, unit=unit,
                provenance={'source': 'synthetic:user-target', 'method': 'Explicit synthetic proposal'})


def custom(target='target-a', value=12.375, base='template-a-model-0', sample=None):
    return dict(schema='size-catalog-request/v1', operation='custom', template_id='template-a',
                target_id=target, target_label='Synthetic non-grid target', base_mannequin_id=base,
                measurements=[supplied(value=value)], rule_sample=sample)


def rule_sample():
    return {'template_id': 'template-a', 'mannequin_id': 'template-a-model-0'}


def field(profile, uid=LENGTH):
    return next(r for r in profile['measurements'] if r['param_uid'] == uid)


def test_standard_exact_types_units_provenance_and_roundtrip(catalog):
    c, _, lock = catalog
    p = c.resolve(standard())
    assert p['kind'] == 'standard' and p['standard_model']['size_label'] == '00'
    assert p['base_model'] is None and p['target'] is None
    r = field(p)
    assert r['value'] == 12 and type(r['value']) is int
    assert r['unit'] is None and r['unit_status'] == 'unavailable'
    assert r['source_observation']['display_in'] == '10 1/2'
    assert r['source_observation']['raw_value_json_type'] == 'int'
    assert r['source_observation']['raw_record_canonical_sha256'] == 'c'*64
    assert r['parameter_definition']['uid_codepoints'] == [f'U+{ord(ch):04X}' for ch in LENGTH]
    assert p['catalog_binding'] == lock
    assert p['source_evidence'][0]['evidence_sha256'] == 'e'*64
    assert p['status']['identity'] == 'exact_stored_standard'
    assert p['status']['constraints']['coverage'] == 'unavailable'
    assert p['status']['units']['status'] == 'unavailable'
    assert p['status']['sewability'] == 'not_assessed'
    assert c.verify_profile(C.parse_json(C.canonical(p))) == p
    assert c.resolve(standard()) == p


def test_two_targets_are_independent_and_no_snap(catalog):
    c, _, _ = catalog
    a, b = c.resolve_many([custom(), custom('target-b', 15.8125)])
    assert (field(a)['value'], field(b)['value']) == (12.375, 15.8125)
    assert a['profile_sha256'] != b['profile_sha256']
    assert a['standard_model'] is None and a['kind'] == 'custom'
    assert a['base_model']['mannequin_id'] == 'template-a-model-0'
    assert a['target']['target_id'] == 'target-a'
    assert a['target']['overrides_sha256'] == C.hashed(a['request']['measurements'])
    assert field(a, SHAPE)['value'] == 0 and field(a, SHAPE)['origin'] == 'inherited'
    assert field(a)['unit_status'] == 'explicit' and field(a)['source_observation'] is None
    assert a['status']['constraints']['coverage'] == 'unavailable'
    field(a)['value'] = 1
    assert field(b)['value'] == 15.8125
    assert field(c.resolve(standard()))['value'] == 12
    assert c.verify_profile(b) == b


def test_complete_profile_no_implicit_base_or_unit_inference(catalog):
    c, _, _ = catalog
    q = custom(base=None)
    q['measurements'].append(supplied(SHAPE, 0, 'site_scalar'))
    p = c.resolve(q)
    assert p['base_model'] is None
    assert [r['value'] for r in p['measurements']] == [12.375, 0]
    assert p['status']['units']['status'] == 'complete'
    assert p['status']['identity'] == 'explicit_custom'
    q['measurements'][0]['value'] = 0
    with pytest.raises(C.CatalogError):
        c.resolve(q)


@pytest.mark.parametrize('value', [0, -.125, 1000])
def test_shape_policy_is_finite_not_invented_positive_range(catalog, value):
    c, _, _ = catalog
    q = custom(); q['measurements'] = [supplied(SHAPE, value, 'site_scalar')]
    assert field(c.resolve(q), SHAPE)['value'] == value


@pytest.mark.parametrize('mutation', [
    lambda q: q.update(schema='unknown/v1'), lambda q: q.update(operation='auto'),
    lambda q: q.update(mannequin_id='template-a-model-0'),
    lambda q: q.update(template_id='Same synthetic title'),
    lambda q: q.update(base_mannequin_id='template-b-model-0'),
    lambda q: q.update(target_id='template-a-model-0'),
    lambda q: q.update(base_mannequin_id=None),
    lambda q: q['measurements'].append(copy.deepcopy(q['measurements'][0])),
    lambda q: q['measurements'][0].update(value=True),
    lambda q: q['measurements'][0].update(value=float('nan')),
    lambda q: q['measurements'][0].update(value=float('inf')),
    lambda q: q['measurements'][0].update(value='12.375'),
    lambda q: q['measurements'][0].update(value=-1),
    lambda q: q['measurements'][0].update(unit=None),
    lambda q: q['measurements'][0].update(unit=''),
    lambda q: q['measurements'][0].update(param_uid='pз_demo_length'),
    lambda q: q['measurements'][0].update(secret='NEVER ECHO'),
    lambda q: q['measurements'][0].update(provenance={}),
    lambda q: q['measurements'][0]['provenance'].update(method=''),
])
def test_invalid_custom_inputs(catalog, mutation):
    c, _, _ = catalog
    q = custom(); mutation(q)
    with pytest.raises(C.CatalogError):
        c.resolve(q)


def test_duplicate_targets_and_conflicting_standard_selector(catalog):
    c, _, _ = catalog
    with pytest.raises(C.CatalogError):
        c.resolve_many([custom(), custom(value=15.8125)])
    q = standard(); q['target_id'] = 'target-a'
    with pytest.raises(C.CatalogError):
        c.resolve(q)
    with pytest.raises(C.CatalogError):
        c.resolve(standard(template='template-b'))


@pytest.mark.parametrize('value,comparison', [(9.875, 'outside_selected_sample'),
    (10, 'boundary_unknown'), (12.375, 'within_selected_sample'), (20, 'boundary_unknown'),
    (20.125, 'outside_selected_sample')])
def test_explicit_sample_comparison_has_no_universal_pass(catalog, value, comparison):
    c, _, _ = catalog
    p = c.resolve(custom(value=value, sample=rule_sample()))
    checks = p['status']['constraints']
    assert checks['coverage'] == 'partial' and checks['comparison'] == comparison
    assert checks['universal'] == 'unavailable'
    assert checks['selected_sample'] == rule_sample()
    assert checks['fields'][0]['rule']['source_field_sha256'] == 'd'*64
    assert p['status']['geometry_export'] == 'not_authorized'


def test_sample_is_opt_in_and_unit_aware(catalog):
    c, _, _ = catalog
    assert c.resolve(custom(value=1000))['status']['constraints']['comparison'] == 'unavailable'
    q = custom(sample=rule_sample()); q['measurements'][0]['unit'] = 'mm'
    assert c.resolve(q)['status']['constraints']['comparison'] == 'unavailable'
    q['measurements'][0]['unit'] = 'in'
    assert c.resolve(q)['status']['constraints']['comparison'] == 'within_selected_sample'
    q['rule_sample']['mannequin_id'] = 'template-a-model-1'
    with pytest.raises(C.CatalogError):
        c.resolve(q)
    q['rule_sample'] = {'template_id': 'template-b', 'mannequin_id': 'template-b-model-0'}
    with pytest.raises(C.CatalogError):
        c.resolve(q)


@pytest.mark.parametrize('mutation', [lambda p: field(p).update(value=99),
    lambda p: p['status'].update(identity='approved'), lambda p: p.update(schema='unknown/v9'),
    lambda p: p['request'].update(operation='evil'), lambda p: p.update(auth='SECRET'),
    lambda p: p['catalog_binding']['counts'].update(models=9),
    lambda p: field(p).update(value=12.0),
    lambda p: field(p)['source_observation'].update(display_in='modified')])
@pytest.mark.parametrize('rehash', [False, True])
def test_tampered_profiles_rejected(catalog, mutation, rehash):
    c, _, _ = catalog
    p = c.resolve(standard()); mutation(p)
    if rehash:
        p['profile_sha256'] = C.hashed({k: v for k, v in p.items() if k != 'profile_sha256'})
    with pytest.raises(C.CatalogError):
        c.verify_profile(p)


def test_changed_catalog_binding_and_external_profile_pin(catalog, tmp_path):
    c, _, _ = catalog
    p = c.resolve(custom())
    with pytest.raises(C.CatalogError):
        c.verify_profile(p, expected_sha256='0'*64)
    assert c.verify_profile(p, expected_sha256=p['profile_sha256']) == p
    data = fake_data(); data['templates.jsonl'][0]['updated_at'] = 'new-version'
    root = tmp_path / 'changed'; pin = write_catalog(root, data)
    changed = C.Catalog.load(root, C.pin_catalog(root, pin))
    with pytest.raises(C.CatalogError):
        changed.verify_profile(p)


def engine_input(name='body_length', landmark='Synthetic length', kind='length', unit='cm'):
    return dict(name=name, landmark=landmark, kind=kind, unit=unit,
                provenance={'source': 'synthetic:engine-contract', 'method': 'Explicit input definition'})


def projection(mappings=None, assumptions=None, required=None):
    return dict(schema='size-catalog-projection-request/v1', engine='synthetic-engine',
                required_inputs=[engine_input()] if required is None else required,
                mappings=[] if mappings is None else mappings,
                assumptions=[] if assumptions is None else assumptions)


def mapping(basis='display_cm', interpretation=None):
    return dict(input='body_length', param_uid=LENGTH, source_value=basis,
                landmark='Synthetic length', unit_interpretation=interpretation,
                provenance={'source': 'synthetic:mapper', 'method': 'Caller asserts identical landmarks'})


def assumption():
    return dict(input='arm_length', value=9.625, unit='cm', landmark='Synthetic arm datum', kind='length',
                provenance={'source': 'synthetic:engineering-proposal', 'method': 'Explicit independent design assumption'})


def test_projection_missing_and_unmapped_are_preserved(catalog):
    c, _, _ = catalog
    p = c.resolve(standard())
    r = c.project(p, projection())
    assert r['status']['mapping'] == 'incomplete'
    assert r['missing_inputs'] == [{'input': 'body_length', 'reason': 'no_mapping_or_assumption'}]
    assert r['unmapped_measurements'] == p['measurements']
    assert r['profile'] == p
    assert r['status']['geometry_export'] == 'not_authorized'


def test_projection_positive_needs_explicit_landmarks_and_individual_assumptions(catalog):
    c, _, _ = catalog
    p = c.resolve(standard())
    q = projection([mapping()], [assumption()], [engine_input(), engine_input('arm_length', 'Synthetic arm datum')])
    r = c.project(p, q)
    assert r['status']['mapping'] == 'complete' and r['missing_inputs'] == []
    assert r['engine_values']['body_length']['value'] == 12
    assert r['engine_values']['arm_length']['value'] == 9.625
    assert r['engine_values']['arm_length']['authority'] == 'engineering_assumption'
    assert r['engine_values']['body_length']['authority'] == 'caller_declared_mapping'
    assert [f['param_uid'] for f in r['unmapped_measurements']] == [SHAPE]
    assert r['status']['geometry_export'] == 'not_authorized'
    assert c.verify_projection(C.parse_json(C.canonical(r))) == r


def test_unit_interpretation_remains_an_assumption(catalog):
    c, _, _ = catalog
    p = c.resolve(standard(model='template-a-model-1'))
    q = projection([mapping('raw')])
    assert c.project(p, q)['missing_inputs'][0]['reason'] == 'source_unit_unavailable'
    interpretation = {'unit': 'cm', 'provenance': {'source': 'synthetic:user', 'method': 'Unverified caller interpretation'}}
    q['mappings'][0]['unit_interpretation'] = interpretation
    r = c.project(p, q)
    assert r['engine_values']['body_length']['unit_authority'] == 'caller_assumption'
    assert r['engine_values']['body_length']['unit_interpretation'] == interpretation
    assert field(r['profile'])['unit'] is None
    q['required_inputs'][0]['unit'] = 'mm'
    assert c.project(p, q)['missing_inputs'][0]['reason'] == 'unit_conversion_unavailable'


@pytest.mark.parametrize('source_label,target_landmark,target_name', [
    ('Shoulder width', 'Shoulder diameter', 'shoulder_diameter'),
    ('Back width', 'Back length', 'back_length'),
    ('Bust height from center back neck point', 'Bust height from HPS', 'bust_height'),
    ('Front length of center back neck point', 'Garment length from HPS', 'front_length'),
])
def test_landmark_aliases_rejected(tmp_path, source_label, target_landmark, target_name):
    d = fake_data()
    for r in d['measurements.jsonl']:
        if r['param_uid'] == LENGTH:
            r['label'] = source_label
    d['parameter_catalog.json'][0]['label'] = source_label
    d['parameter_catalog.json'][0]['label_evidence'][0]['label'] = source_label
    d['field_rules.jsonl'][0]['label'] = source_label
    pin = write_catalog(tmp_path, d); c = C.Catalog.load(tmp_path, C.pin_catalog(tmp_path, pin))
    m = mapping(); m.update(input=target_name, landmark=source_label)
    r = c.project(c.resolve(standard()), projection([m], required=[engine_input(target_name, target_landmark)]))
    assert r['status']['mapping'] == 'incomplete' and r['engine_values'] == {}
    assert r['missing_inputs'][0]['reason'] == 'unsupported_landmark_mapping'


def test_shape_scalars_cannot_be_projected_as_physical_length(catalog):
    c, _, _ = catalog
    m = mapping(); m.update(param_uid=SHAPE, landmark='Synthetic shape')
    r = c.project(c.resolve(standard()), projection([m], required=[engine_input(landmark='Synthetic shape')]))
    assert r['missing_inputs'][0]['reason'] == 'unsupported_semantic_mapping'


def test_legacy_height_is_unsupported_even_with_assumption(catalog):
    c, _, _ = catalog
    a = assumption(); a.update(input='height', landmark='Standing height')
    q = projection(assumptions=[a], required=[engine_input('height', 'Standing height')]); q['engine'] = 'pattern.py'
    r = c.project(c.resolve(standard()), q)
    assert r['missing_inputs'][0]['reason'] == 'unsupported_legacy_height'
    assert r['engine_values'] == {}


@pytest.mark.parametrize('mutation', [lambda q: q.update(schema='evil'),
    lambda q: q.update(operation='execute'), lambda q: q['required_inputs'].append(copy.deepcopy(q['required_inputs'][0])),
    lambda q: q['mappings'].append(copy.deepcopy(q['mappings'][0])),
    lambda q: q['mappings'][0].update(source_value='exec'),
    lambda q: q['mappings'][0].update(param_uid='pз_demo_length'),
    lambda q: q['mappings'][0].update(input='unknown'),
    lambda q: q['mappings'][0].update(provenance={}),
    lambda q: q['required_inputs'][0].update(kind='anything'),
    lambda q: q['required_inputs'][0].update(unit=None)])
def test_projection_schema_rejection(catalog, mutation):
    c, _, _ = catalog
    q = projection([mapping()]); mutation(q)
    with pytest.raises(C.CatalogError):
        c.project(c.resolve(standard()), q)


def test_projection_tamper_and_conflicting_assumptions(catalog):
    c, _, _ = catalog
    p = c.resolve(standard()); q = projection([mapping()])
    a = assumption(); a.update(input='body_length', landmark='Synthetic length')
    q['assumptions'] = [a]
    with pytest.raises(C.CatalogError):
        c.project(p, q)
    q['assumptions'] = []; r = c.project(p, q)
    r['status']['mapping'] = 'approved'
    r['projection_sha256'] = C.hashed({k: v for k, v in r.items() if k != 'projection_sha256'})
    with pytest.raises(C.CatalogError):
        c.verify_projection(r)


def cli(catalog, tmp_path, *args, expected=0):
    import subprocess
    import sys
    _, root, lock = catalog
    lock_path = tmp_path / 'lock.json'; lock_path.write_bytes(encoded(lock))
    result = subprocess.run([sys.executable, str(Path(C.__file__)), '--catalog', str(root),
                             '--lock', str(lock_path), *map(str, args)], text=True, capture_output=True)
    assert result.returncode == expected, result.stdout + result.stderr
    return result


def test_real_cli_commands_and_full_synthetic_audit(catalog, tmp_path):
    c, root, lock = catalog
    r = cli(catalog, tmp_path, 'pin', '--manifest-sha256', lock['artifact_manifest_sha256'])
    assert json.loads(r.stdout) == lock
    assert len(json.loads(cli(catalog, tmp_path, 'list').stdout)['templates']) == 2
    shown = json.loads(cli(catalog, tmp_path, 'show', '--template-id', 'template-a').stdout)
    assert len(shown['models']) == 2
    selected = json.loads(cli(catalog, tmp_path, 'select', '--template-id', 'template-a',
                             '--mannequin-id', 'template-a-model-0').stdout)
    assert selected == c.resolve(standard())
    request_file = tmp_path / 'request.json'; request_file.write_bytes(encoded(custom()))
    profile = json.loads(cli(catalog, tmp_path, 'resolve', '--request', request_file).stdout)
    profile_file = tmp_path / 'profile.json'; profile_file.write_bytes(encoded(profile))
    assert json.loads(cli(catalog, tmp_path, 'check', '--profile', profile_file).stdout) == profile
    batch_file = tmp_path / 'batch.json'
    batch_file.write_bytes(encoded({'schema':'size-catalog-batch-request/v1', 'requests':[custom(), custom('target-b', 15.8125)]}))
    assert len(json.loads(cli(catalog, tmp_path, 'resolve-many', '--request', batch_file).stdout)['profiles']) == 2
    rows = [json.loads(line) for line in cli(catalog, tmp_path, 'audit').stdout.splitlines()]
    assert [r['kind'] for r in rows] == ['template_batch', 'template_batch', 'aggregate']
    assert rows[-1]['counts'] == c.counts and rows[-1]['standard_roundtrips'] == 3
    assert sum(r['observation_count'] for r in rows[:-1]) == 6
    projection_file = tmp_path / 'projection-request.json'; projection_file.write_bytes(encoded(projection()))
    projected = json.loads(cli(catalog, tmp_path, 'project', '--profile', profile_file,
                               '--request', projection_file, expected=3).stdout)
    assert projected['status']['mapping'] == 'incomplete'
    projection_file.write_bytes(encoded(projection([mapping('raw')])) )
    assert json.loads(cli(catalog, tmp_path, 'project', '--profile', profile_file,
                          '--request', projection_file).stdout)['status']['mapping'] == 'complete'
    request_file.write_bytes(encoded(custom(value=1000, sample=rule_sample())))
    rejected = json.loads(cli(catalog, tmp_path, 'resolve', '--request', request_file, expected=3).stdout)
    assert rejected['status']['constraints']['comparison'] == 'outside_selected_sample'


def test_cli_fails_closed(catalog, tmp_path):
    cli(catalog, tmp_path, 'show', '--template-id', 'Same synthetic title', expected=2)
    cli(catalog, tmp_path, 'execute', expected=2)
    cli(catalog, tmp_path, 'select', '--template-id', 'template-a', expected=2)
    request = tmp_path/'bad.json'; request.write_text('{"schema":"size-catalog-request/v1","auth":"SECRET"}')
    r = cli(catalog, tmp_path, 'resolve', '--request', request, expected=2)
    assert 'SECRET' not in r.stdout+r.stderr


def full_sample_data():
    data = fake_data()
    r = copy.deepcopy(data['field_rules.jsonl'][0])
    r.update(param_uid=SHAPE, field_key='syntheticShape', label='Synthetic shape', display_cm=0,
             min={'cm':0, 'in':'0'}, max={'cm':1,'in':'1'},
             units_status='website-provided labels, not physical interpretation')
    data['field_rules.jsonl'].append(r)
    data['parameter_catalog.json'][1]['rule_observation_count'] = 1
    data['sizes.jsonl'][0]['full_field_rules_captured'] = True
    data['measurements.jsonl'][1]['field_rules_captured_for_this_size'] = True
    return data


def test_full_field_capture_flag_is_sample_coverage_not_complete_constraints(tmp_path):
    pin = write_catalog(tmp_path, full_sample_data())
    c = C.Catalog.load(tmp_path, C.pin_catalog(tmp_path, pin))
    p = c.resolve(standard(sample=rule_sample()))
    assert p['standard_model']['full_field_rules_captured'] is True
    assert p['status']['constraints']['coverage'] == 'partial'
    assert p['status']['constraints']['comparison'] == 'boundary_unknown'
    assert field(p, SHAPE)['value'] == 0


@pytest.mark.parametrize('mutation', [
    lambda d: d['sizes.jsonl'][0].update(full_field_rules_captured=True),
    lambda d: d['sources.json'][0].update(kind=[]),
    lambda d: d['field_rules.jsonl'][0]['min'].update(**{'in':'invalid fraction'}),
    lambda d: d['field_rules.jsonl'][0]['min'].update(**{'in':'99'}),
    lambda d: d['parameter_catalog.json'][0].update(label_evidence=[]),
])
def test_extra_pinned_metadata_failures(tmp_path, mutation):
    d = fake_data(); mutation(d); pin = write_catalog(tmp_path,d)
    with pytest.raises(C.CatalogError):
        C.pin_catalog(tmp_path, pin)


def test_known_projection_names_cannot_disguise_wrong_landmarks(catalog):
    c, _, _ = catalog
    m = mapping();m['input']='back_length'
    r = c.project(c.resolve(standard()), projection([m], required=[engine_input('back_length')]))
    assert r['missing_inputs'][0]['reason'] == 'unsupported_landmark_mapping'


def test_project_cli_retains_selected_sample_rejection(catalog, tmp_path):
    c, _, _ = catalog
    profile_path = tmp_path/'rejected-profile.json'
    profile_path.write_bytes(encoded(c.resolve(custom(value=99, sample=rule_sample()))))
    request_path = tmp_path/'projection.json';request_path.write_bytes(encoded(projection([mapping('raw')])))
    r = cli(catalog,tmp_path,'project','--profile',profile_path,'--request',request_path,expected=3)
    assert json.loads(r.stdout)['status']['mapping']=='complete'


def test_fraction_boundary_comparison_is_exact_and_same_unit(tmp_path):
    d=fake_data();d['field_rules.jsonl'][0]['min']['in']='10 1/2'
    pin=write_catalog(tmp_path,d);c=C.Catalog.load(tmp_path,C.pin_catalog(tmp_path,pin))
    q=custom(value=10.5,sample=rule_sample());q['measurements'][0]['unit']='in'
    assert c.resolve(q)['status']['constraints']['comparison']=='boundary_unknown'
    assert C.interval({'min':{'in':'-1 1/2'}, 'max':{'in':'1/2'}},'in')==(-1.5,.5)


@pytest.mark.parametrize('unit,endpoint,value', [
    pytest.param('in', '10.1', 10.1, id='inch-decimal-tenth'),
    pytest.param('in', '10 1/10', 10.1, id='inch-mixed-tenth'),
    pytest.param('in', '101/10', 10.1, id='inch-improper-tenth'),
    pytest.param('in', '10.3', 10.3, id='inch-decimal-three-tenths'),
    pytest.param('in', '10 3/10', 10.3, id='inch-mixed-three-tenths'),
    pytest.param('in', '10', 10, id='inch-integer'),
    pytest.param('in', '10', 10.0, id='inch-integral-float'),
    pytest.param('in', '10 1/2', 10.5, id='inch-half'),
    pytest.param('cm', 10.1, 10.1, id='cm-decimal'),
])
@pytest.mark.parametrize('bound', ['min', 'max'])
@pytest.mark.parametrize('position', ['equal', 'inside', 'outside'])
def test_range_decimal_endpoints_cli_preserve_exact_values(tmp_path, unit, endpoint, value, bound, position):
    import math

    data = fake_data()
    rule = data['field_rules.jsonl'][0]
    if bound == 'max':
        rule['min'][unit] = '1' if unit == 'in' else 1
    rule[bound][unit] = endpoint
    # One representable step must remain distinct: no tolerance or rounding to a boundary.
    if position != 'equal':
        upward = (bound == 'min') == (position == 'inside')
        value = math.nextafter(value, math.inf if upward else -math.inf)
    expected = {'equal': 'boundary_unknown', 'inside': 'within_selected_sample',
                'outside': 'outside_selected_sample'}[position]
    root = tmp_path / 'catalog'
    pin = write_catalog(root, data)
    lock = C.pin_catalog(root, pin)
    c = C.Catalog.load(root, lock)
    request = custom(value=value, sample=rule_sample())
    request['measurements'][0]['unit'] = unit
    request_bytes = encoded(request)
    request_path = tmp_path / 'request.json'
    request_path.write_bytes(request_bytes)
    result = cli((c, root, lock), tmp_path, 'resolve', '--request', request_path,
                 expected=3 if position == 'outside' else 0)
    assert result.stderr == ''
    profile = json.loads(result.stdout)
    checks = profile['status']['constraints']
    assert checks['comparison'] == expected
    assert checks['fields'][0]['status'] == expected
    assert checks['fields'][0]['comparison_unit'] == unit
    assert checks['boundary_inclusivity'] == 'unknown'
    assert checks['coverage'] == 'partial' and checks['universal'] == 'unavailable'
    assert encoded(checks['fields'][0]['rule']) == encoded(rule)
    assert encoded(profile['request']) == request_bytes == encoded(request)
    measurement = field(profile)
    assert type(measurement['value']) is type(value)
    assert encoded(measurement['value']) == encoded(value)
    assert measurement['value_json_type'] == type(value).__name__
    assert measurement['unit'] == unit and measurement['unit_status'] == 'explicit'
    assert measurement['provenance'] == request['measurements'][0]['provenance']
    assert measurement['source_observation'] is None
    assert encoded(field(profile, SHAPE)['source_observation']) == encoded(data['measurements.jsonl'][1])
    assert profile['catalog_binding'] == lock
    assert profile['status']['units']['conversions'] == 'not_performed'
    assert profile['status']['geometry_export'] == 'not_authorized'
    # The comparison view must not leak into source observations or serialized profiles.
    standard_profile = c.resolve(standard())
    for observed in standard_profile['measurements']:
        original = next(r for r in data['measurements.jsonl']
                        if r['mannequin_id'] == 'template-a-model-0' and r['param_uid'] == observed['param_uid'])
        assert encoded(observed['source_observation']) == encoded(original)
        assert type(observed['value']) is type(original['raw_value'])
        assert encoded(observed['value']) == encoded(original['raw_value'])
    assert C.canonical(c.resolve(request)) == C.canonical(profile)
    assert C.canonical(c.verify_profile(profile)) == C.canonical(profile)


def test_display_decimal_text_and_independent_rule_evidence_are_preserved(tmp_path):
    d=fake_data()
    d['sources.json'].append(dict(source_id='synthetic:second-capture',path='never-opened-either.json',
                                  kind='local_file',role='independent synthetic display capture',bytes=0,sha256='f'*64))
    for r in d['measurements.jsonl'][:2]:
        r['display_cm']=str(r['display_cm'])
        r['display_source_id']='synthetic:second-capture'
    pin=write_catalog(tmp_path,d);c=C.Catalog.load(tmp_path,C.pin_catalog(tmp_path,pin))
    p=c.resolve(standard(sample=rule_sample()))
    assert field(p)['source_observation']['display_cm']=='12'
    assert field(p)['source_observation']['display_source_id']=='synthetic:second-capture'
    assert p['status']['constraints']['fields'][0]['rule']['source_id']==SOURCE
    assert p['status']['constraints']['comparison']=='within_selected_sample'
    assert c.verify_profile(p)==p
    # Recording accepts exact UI text; numeric engine projection does not silently recast it.
    r=c.project(p,projection([mapping()]))
    assert r['missing_inputs'][0]['reason']=='unsupported_value_representation'


@pytest.mark.parametrize('text', ['NaN','Infinity','12oops',True,'12/1'])
def test_display_cm_must_be_numeric_decimal_not_coerced_arbitrary_text(tmp_path,text):
    d=fake_data();d['measurements.jsonl'][0]['display_cm']=text
    pin=write_catalog(tmp_path,d)
    with pytest.raises(C.CatalogError):C.pin_catalog(tmp_path,pin)
