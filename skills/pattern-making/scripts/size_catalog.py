"""Offline pinned body catalog. No network, geometry, imports or executable data hooks."""
import argparse
import copy
import hashlib
import json
import math
import re
from collections import Counter
from decimal import Decimal
from fractions import Fraction
from pathlib import Path, PurePosixPath


class CatalogError(ValueError):
    """Invalid data, identity, schema or binding (not a garment verdict)."""


def require(condition, message):
    if not condition:
        raise CatalogError(message)


def obj(value, keys):
    require(type(value) is dict and set(value) == set(keys.split()), 'Unknown or missing schema fields')
    return value


def string(value):
    require(type(value) is str and bool(value.strip()), 'Expected nonempty exact string')
    return value


def array(value):
    require(type(value) is list, 'Expected array')
    return value


def strings(value):
    return [string(v) for v in array(value)]


def integer(value):
    require(type(value) is int and value >= 0, 'Expected nonnegative integer')
    return value


def number(value):
    require(type(value) in (int, float), 'Expected numeric value, never boolean')
    require(type(value) is int or math.isfinite(value), 'Nonfinite number')
    return value


def boolean(value):
    require(type(value) is bool, 'Expected boolean')


def display_number(value):
    """Read a captured decimal for comparison without changing its stored type/text."""
    if type(value) is str:
        require(re.fullmatch(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)', value) is not None,
                'Invalid captured decimal text')
    else:
        number(value)
    return Decimal(str(value))


def sha(value):
    require(type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value),
            'Expected lowercase SHA-256')
    return value


def canonical(value):
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')
    except (ValueError, TypeError, UnicodeError) as exc:
        raise CatalogError('Not canonical JSON data') from exc


def hashed(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def parse_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'Duplicate JSON key')
            result[key] = value
        return result

    def reject(_):
        raise CatalogError('Nonfinite JSON constant')

    def walk(value):
        if type(value) is float:
            number(value)
        elif type(value) is dict:
            for v in value.values():
                walk(v)
        elif type(value) is list:
            for v in value:
                walk(v)
    try:
        result = json.loads(raw, object_pairs_hook=pairs, parse_constant=reject)
        walk(result)
        canonical(result)  # Reject invalid Unicode as well.
        return result
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise CatalogError('Invalid strict JSON') from exc


def read_json(path):
    try:
        return parse_json(Path(path).read_bytes())
    except OSError as exc:
        raise CatalogError('Cannot read JSON file') from exc


def rooted(root, name):
    string(name)
    require('\\' not in name and not PurePosixPath(name).is_absolute()
            and all(p not in ('', '.', '..') for p in name.split('/')), 'Unsafe manifest path')
    root = Path(root).resolve()
    path = (root / name).resolve()
    require(path.is_relative_to(root) and path != root, 'Manifest path escapes catalog root')
    return path


FILES = ('templates.jsonl', 'sizes.jsonl', 'measurements.jsonl',
         'parameter_catalog.json', 'field_rules.jsonl', 'sources.json')
COUNT_KEYS = 'templates models observations parameters rules rule_models display_observations'
TEMPLATE_KEYS = ('kind name not_finished_garment_or_ease ordered_mannequin_ids ordered_size_labels '
                 'raw_record_canonical_sha256 size_count source_id source_pointer source_url template_id type updated_at')
MODEL_KEYS = ('api_uid_intentionally_not_exported full_field_rules_captured mannequin_id ordinal parameter_count '
              'parameter_uids raw_record_canonical_sha256 raw_unit size_label source_id source_pointer template_id type')
MEASUREMENT_KEYS = ('display_cm display_in display_source_id field_rules_captured_for_this_size label mannequin_id '
                    'param_uid raw_equals_display_cm raw_record_canonical_sha256 raw_unit raw_value raw_value_json_type '
                    'size_label source_id source_pointer template_id')
PARAMETER_KEYS = ('param_uid uid_codepoints label field_keys label_evidence raw_observation_count observed_raw_min '
                 'observed_raw_max observed_range_is_constraint raw_unit_global captured_unit_labels semantic_class '
                 'rule_observation_count global_allowed_min global_allowed_max unit_note')
RULE_KEYS = ('boundary_inclusivity cross_field_constraints description display_cm display_in field_key '
             'is_active_at_capture is_valid_at_capture label mannequin_id max min param_uid required scope size_label '
             'source_binding source_field_sha256 source_id step template_id type units_status unknowns')


def unique(rows, key):
    result = {}
    for row in rows:
        k = key(row)
        require(k not in result, 'Duplicate exact identity')
        result[k] = row
    return result


def read_selected(root, files):
    require(type(files) is dict and set(files) == set(FILES), 'Selected catalog file set mismatch')
    data = {}
    for name in FILES:
        spec = obj(files[name], 'bytes sha256')
        integer(spec['bytes']); sha(spec['sha256'])
        try:
            raw = rooted(root, name).read_bytes()
        except OSError as exc:
            raise CatalogError('Cannot read selected catalog file') from exc
        require(len(raw) == spec['bytes'] and hashlib.sha256(raw).hexdigest() == spec['sha256'],
                'Catalog file hash/length mismatch')
        data[name] = ([parse_json(line) for line in raw.splitlines() if line.strip()]
                      if name.endswith('.jsonl') else array(parse_json(raw)))
    return data


def pin_catalog(root, manifest_sha256):
    sha(manifest_sha256)
    try:
        raw = rooted(root, 'artifact_hashes.json').read_bytes()
    except OSError as exc:
        raise CatalogError('Cannot read artifact manifest') from exc
    require(hashlib.sha256(raw).hexdigest() == manifest_sha256, 'Artifact manifest pin mismatch')
    files, seen = {}, set()
    for entry in array(parse_json(raw)):
        obj(entry, 'name bytes sha256')
        name = entry['name']
        rooted(root, name)  # Validate even unselected paths; never read their contents.
        require(name not in seen, 'Duplicate manifest file')
        seen.add(name); integer(entry['bytes']); sha(entry['sha256'])
        if name in FILES:
            files[name] = {k: entry[k] for k in ('bytes', 'sha256')}
    catalog = Catalog(read_selected(root, files))
    return {'schema': 'size-catalog-lock/v1', 'artifact_manifest_sha256': manifest_sha256,
            'files': files, 'counts': catalog.counts}


class Catalog:
    @classmethod
    def load(cls, root, lock):
        obj(lock, 'schema artifact_manifest_sha256 files counts')
        require(lock['schema'] == 'size-catalog-lock/v1', 'Unsupported lock schema')
        sha(lock['artifact_manifest_sha256'])
        obj(lock['counts'], COUNT_KEYS)
        for value in lock['counts'].values():
            integer(value)
        result = cls(read_selected(root, lock['files']))
        require(result.counts == lock['counts'], 'Catalog coverage counts mismatch')
        result._lock = copy.deepcopy(lock)
        result.binding_sha256 = hashed(lock)
        return result

    def __init__(self, data):
        data = copy.deepcopy(data)
        for name, keys in [('templates.jsonl', TEMPLATE_KEYS), ('sizes.jsonl', MODEL_KEYS),
                           ('measurements.jsonl', MEASUREMENT_KEYS), ('parameter_catalog.json', PARAMETER_KEYS),
                           ('field_rules.jsonl', RULE_KEYS)]:
            for row in data[name]:
                obj(row, keys)
        self._validate_sources(data['sources.json'])
        self._templates = unique(data['templates.jsonl'], lambda r: string(r['template_id']))
        self._models = unique(data['sizes.jsonl'], lambda r: string(r['mannequin_id']))
        self._parameters = unique(data['parameter_catalog.json'], lambda r: string(r['param_uid']))
        self._measurements = unique(data['measurements.jsonl'], lambda r: (string(r['mannequin_id']), string(r['param_uid'])))
        self._rules = unique(data['field_rules.jsonl'], lambda r: (string(r['mannequin_id']), string(r['param_uid'])))
        require(bool(self._templates) and bool(self._models) and bool(self._parameters), 'Empty catalog')
        self._validate_rows()
        self.counts = dict(templates=len(self._templates), models=len(self._models), observations=len(self._measurements),
                           parameters=len(self._parameters), rules=len(self._rules),
                           rule_models=len({mi for mi, uid in self._rules}),
                           display_observations=sum(r['display_cm'] is not None for r in self._measurements.values()))

    def _validate_sources(self, rows):
        self._sources = {}
        variants = {
            'local_file': 'source_id path kind role bytes sha256',
            'sqlite_message': 'source_id path kind session_id message_id content_utf8_bytes content_utf8_sha256 role',
            'sqlite_query_projection': 'source_id kind path query rows canonical_projection_sha256 raw_database_file_sha256 hash_note',
        }
        for row in array(rows):
            require(type(row) is dict and type(row.get('kind')) is str and row['kind'] in variants, 'Unknown source kind')
            obj(row, variants[row['kind']])
            for key, value in row.items():
                if key in ('bytes', 'content_utf8_bytes', 'message_id', 'rows'):
                    integer(value)
                elif key == 'raw_database_file_sha256' and value is None:
                    pass
                elif key.endswith('sha256'):
                    sha(value)
                else:
                    string(value)
            sid = row['source_id']
            require(sid not in self._sources, 'Duplicate source identity')
            # Metadata only: never open source paths, databases, queries, URLs or imports.
            self._sources[sid] = row

    def _source(self, value):
        require(string(value) in self._sources, 'Unbound provenance source')

    def _record(self, row):
        self._source(row['source_id'])
        string(row['source_pointer']); sha(row['raw_record_canonical_sha256'])

    def _validate_rows(self):
        for p in self._parameters.values():
            string(p['label']); string(p['unit_note'])
            require(p['uid_codepoints'] == [f'U+{ord(c):04X}' for c in p['param_uid']], 'UID codepoints mismatch')
            keys = strings(p['field_keys']); require(len(keys) == len(set(keys)), 'Duplicate field key')
            strings(p['captured_unit_labels'])
            require(p['semantic_class'] in ('body_mannequin_measurement', 'body_shape_parameter_website_defined'),
                    'Unknown field semantic class')
            require(p['observed_range_is_constraint'] is False, 'Observed extrema are not constraints')
            require(all(p[k] is None for k in ('raw_unit_global', 'global_allowed_min', 'global_allowed_max')),
                    'Unsupported global unit/constraint assertion')
            integer(p['raw_observation_count']); integer(p['rule_observation_count'])
            number(p['observed_raw_min']); number(p['observed_raw_max'])
            require(bool(array(p['label_evidence'])), 'Missing label provenance')
            for e in p['label_evidence']:
                obj(e, 'field_key label source_id'); self._source(e['source_id'])
                require(e['label'] == p['label'] and e['field_key'] in keys, 'Label evidence mismatch')
        memberships = []
        for tid, t in self._templates.items():
            require(t['kind'] == 'standard_body_mannequin_template' and t['not_finished_garment_or_ease'] is True,
                    'Unsupported template discriminator')
            self._record(t)
            for key in ('name', 'type', 'source_url', 'updated_at'):
                string(t[key])
            ids = strings(t['ordered_mannequin_ids']); labels = strings(t['ordered_size_labels'])
            require(integer(t['size_count']) == len(ids) == len(labels) and len(ids) == len(set(ids)),
                    'Template count/identity mismatch')
            for ordinal, (mi, label) in enumerate(zip(ids, labels)):
                m = self._models.get(mi)
                require(m is not None and m['template_id'] == tid and m['size_label'] == label
                        and m['ordinal'] == ordinal and m['type'] == t['type'], 'Template/model membership mismatch')
            memberships.extend(ids)
        require(Counter(memberships) == Counter({mi: 1 for mi in self._models}), 'Orphan/duplicate model membership')
        observation_keys = []
        for mi, m in self._models.items():
            self._record(m); integer(m['ordinal']); string(m['size_label'])
            require(m['api_uid_intentionally_not_exported'] is True, 'Unsupported model privacy assertion')
            boolean(m['full_field_rules_captured'])
            require(m['raw_unit'] is None, 'Unsupported global model unit')
            uids = strings(m['parameter_uids'])
            require(integer(m['parameter_count']) == len(uids) and len(uids) == len(set(uids)),
                    'Model parameter count/uniqueness mismatch')
            require(all(uid in self._parameters for uid in uids), 'Unknown parameter UID')
            require(bool(uids) and m['full_field_rules_captured'] == all((mi, uid) in self._rules for uid in uids),
                    'Model sample-field coverage flag mismatch')
            observation_keys.extend((mi, uid) for uid in uids)
        require(set(observation_keys) == set(self._measurements), 'Incomplete or orphan observations')
        for (mi, uid), r in self._measurements.items():
            self._record(r); number(r['raw_value'])
            require(r['raw_value_json_type'] == type(r['raw_value']).__name__, 'Raw numeric type mismatch')
            m = self._models[mi]; p = self._parameters[uid]
            require(r['template_id'] == m['template_id'] and r['size_label'] == m['size_label']
                    and r['label'] == p['label'], 'Observation identity/label mismatch')
            require(r['raw_unit'] is None or r['raw_unit'] in ('cm', 'in'), 'Unknown captured raw unit')
            boolean(r['field_rules_captured_for_this_size'])
            require(r['field_rules_captured_for_this_size'] == ((mi, uid) in self._rules), 'Rule coverage flag mismatch')
            if r['display_cm'] is None:
                require(all(r[k] is None for k in ('display_in', 'display_source_id', 'raw_equals_display_cm')),
                        'Incomplete missing-display markers')
            else:
                display_number(r['display_cm']); string(r['display_in']); self._source(r['display_source_id'])
                boolean(r['raw_equals_display_cm'])
                require(r['raw_equals_display_cm'] == (display_number(r['raw_value']) == display_number(r['display_cm'])),
                        'Display equality mismatch')
        for key, r in self._rules.items():
            require(key in self._measurements, 'Orphan rule')
            m = self._models[key[0]]; p = self._parameters[key[1]]; obs = self._measurements[key]
            require(r['template_id'] == m['template_id'] and r['size_label'] == m['size_label']
                    and r['type'] == m['type'] and r['label'] == p['label'] and r['field_key'] in p['field_keys'],
                    'Rule sample binding mismatch')
            self._source(r['source_id']); sha(r['source_field_sha256']); string(r['source_binding'])
            require(r['scope'] == 'this captured mannequin field only; not universal type/chart limits', 'Unknown rule scope')
            require(r['units_status'] == ('website-provided labels, not physical interpretation'
                    if p['semantic_class'] == 'body_shape_parameter_website_defined' else 'captured UI cm/in'),
                    'Unknown rule units status')
            require(type(r['description']) is str, 'Expected description string'); strings(r['unknowns'])
            boolean(r['is_active_at_capture']); boolean(r['is_valid_at_capture'])
            require(all(r[k] is None for k in ('boundary_inclusivity', 'cross_field_constraints', 'required', 'step')),
                    'Unsupported rule semantics')
            number(r['display_cm']); string(r['display_in'])
            require(display_number(r['display_cm']) == display_number(obs['display_cm'])
                    and r['display_in'] == obs['display_in'], 'Rule display binding mismatch')
            for bound in ('min', 'max'):
                obj(r[bound], 'cm in'); number(r[bound]['cm']); string(r[bound]['in'])
            require(r['min']['cm'] <= r['max']['cm'], 'Inverted sample interval')
            inch_min, inch_max = interval(r, 'in')
            require(inch_min <= inch_max, 'Inverted captured inch interval')
        values, rules = {}, Counter(uid for mi, uid in self._rules)
        for (mi, uid), row in self._measurements.items():
            values.setdefault(uid, []).append(row['raw_value'])
        for uid, p in self._parameters.items():
            v = values.get(uid, [])
            require(bool(v) and p['raw_observation_count'] == len(v) and p['rule_observation_count'] == rules[uid]
                    and p['observed_raw_min'] == min(v) and p['observed_raw_max'] == max(v),
                    'Parameter coverage/extrema mismatch')

    def _template(self, template_id):
        require(string(template_id) in self._templates, 'Unknown exact template ID')
        return self._templates[template_id]

    def _model(self, template_id, mannequin_id):
        self._template(template_id)
        require(string(mannequin_id) in self._models, 'Unknown exact mannequin ID')
        model = self._models[mannequin_id]
        require(model['template_id'] == template_id, 'Wrong template/model binding')
        return model

    def list_templates(self):
        return copy.deepcopy(list(self._templates.values()))

    def list_models(self, template_id):
        t = self._template(template_id)
        return copy.deepcopy([self._models[mi] for mi in t['ordered_mannequin_ids']])

    def _field(self, mannequin_id, uid, origin):
        r = self._measurements[(mannequin_id, uid)]
        return dict(param_uid=uid, label=r['label'], value=r['raw_value'], value_json_type=r['raw_value_json_type'],
                    unit=r['raw_unit'], unit_status='unavailable' if r['raw_unit'] is None else 'observed_raw',
                    origin=origin, source_observation=copy.deepcopy(r), provenance=None,
                    parameter_definition=copy.deepcopy(self._parameters[uid]))

    def resolve(self, request):
        require(type(request) is dict, 'Expected request object')
        operation = request.get('operation')
        require(operation in ('standard', 'custom'), 'Unknown request operation')
        common = 'schema operation template_id rule_sample '
        obj(request, common + ('mannequin_id' if operation == 'standard' else
                               'target_id target_label base_mannequin_id measurements'))
        require(request['schema'] == 'size-catalog-request/v1', 'Unsupported request schema')
        t = self._template(request['template_id'])
        base = standard = target = None
        if operation == 'standard':
            standard = self._model(t['template_id'], request['mannequin_id'])
            fields = [self._field(standard['mannequin_id'], uid, 'standard') for uid in standard['parameter_uids']]
        else:
            target_id = string(request['target_id']); string(request['target_label'])
            require(target_id not in self._models, 'Custom target cannot impersonate stored mannequin ID')
            if request['base_mannequin_id'] is not None:
                base = self._model(t['template_id'], request['base_mannequin_id'])
                uids = base['parameter_uids']
                fields = [self._field(base['mannequin_id'], uid, 'inherited') for uid in uids]
            else:
                # Complete means the union of fields observed in this exact template; not a website rule.
                uids = list(dict.fromkeys(uid for mi in t['ordered_mannequin_ids'] for uid in self._models[mi]['parameter_uids']))
                fields = []
            overrides = {}
            for entry in array(request['measurements']):
                obj(entry, 'param_uid value unit provenance')
                uid = string(entry['param_uid'])
                require(uid in uids and uid not in overrides, 'Unknown or duplicate custom UID')
                number(entry['value']); string(entry['unit']); provenance(entry['provenance'])
                p = self._parameters[uid]
                if p['semantic_class'] == 'body_mannequin_measurement':
                    require(entry['value'] > 0, 'Explicit length/circumference must be positive (adapter policy)')
                # Shape scalars have unknown physical semantics. Finite zero/negative values are not missing.
                overrides[uid] = dict(param_uid=uid, label=p['label'], value=entry['value'],
                    value_json_type=type(entry['value']).__name__, unit=entry['unit'], unit_status='explicit',
                    origin='explicit', source_observation=None, provenance=copy.deepcopy(entry['provenance']),
                    parameter_definition=copy.deepcopy(p))
            if base is None:
                require(set(overrides) == set(uids), 'Complete explicit profile is missing template fields')
            by_uid = {f['param_uid']: f for f in fields}
            by_uid.update(overrides)
            fields = [by_uid[uid] for uid in uids]
            target = dict(target_id=target_id, target_label=request['target_label'],
                          overrides_sha256=hashed(request['measurements']))
        constraint_status = self._compare_sample(t['template_id'], fields, request['rule_sample'])
        missing = [f['param_uid'] for f in fields if f['unit'] is None]
        status = dict(schema='checked', identity='exact_stored_standard' if standard else 'explicit_custom',
                      constraints=constraint_status,
                      units=dict(status='unavailable' if len(missing) == len(fields) else 'partial' if missing else 'complete',
                                 missing_raw_units=missing, conversions='not_performed'),
                      mapping='not_requested', anatomy='not_assessed', sewability='not_assessed', geometry_export='not_authorized')
        source_ids = {t['source_id']}
        if standard or base:
            source_ids.add((standard or base)['source_id'])
        for f in fields:
            source_ids.update(e['source_id'] for e in f['parameter_definition']['label_evidence'])
            if f['source_observation']:
                r = f['source_observation']; source_ids.add(r['source_id'])
                if r['display_source_id']:
                    source_ids.add(r['display_source_id'])
        for row in constraint_status['fields']:
            if row['rule']:
                source_ids.add(row['rule']['source_id'])
        evidence = []
        for sid in sorted(source_ids):
            row = self._sources[sid]
            key = {'local_file': 'sha256', 'sqlite_message': 'content_utf8_sha256',
                   'sqlite_query_projection': 'canonical_projection_sha256'}[row['kind']]
            evidence.append(dict(source_id=sid, kind=row['kind'], evidence_sha256=row[key], hash_kind=key,
                                 verification='metadata_bound_by_catalog_lock; original_source_not_reopened'))
        profile = dict(schema='size-catalog-profile/v1', kind=operation, catalog_binding=copy.deepcopy(self._lock),
                       template=copy.deepcopy(t), standard_model=copy.deepcopy(standard), base_model=copy.deepcopy(base),
                       target=target, request=copy.deepcopy(request), measurements=fields, source_evidence=evidence, status=status)
        profile['profile_sha256'] = hashed(profile)
        return profile

    def _compare_sample(self, template_id, fields, sample):
        result = dict(coverage='unavailable', universal='unavailable', selected_sample=copy.deepcopy(sample),
                      comparison='unavailable', fields=[], boundary_inclusivity='unknown', step='unknown',
                      precision='unknown', cross_field='unknown', website_validation='unavailable')
        sample_rules = {}
        if sample is not None:
            obj(sample, 'template_id mannequin_id')
            require(sample['template_id'] == template_id, 'Selected sample must belong to explicit template')
            self._model(sample['template_id'], sample['mannequin_id'])
            sample_rules = {uid: r for (mi, uid), r in self._rules.items() if mi == sample['mannequin_id']}
            require(bool(sample_rules), 'No captured rules for selected sample')
            result['coverage'] = 'partial'  # Even full field intervals lack step/boundary/cross-field rules.
        for f in fields:
            uid = f['param_uid']; rule = sample_rules.get(uid)
            row = dict(param_uid=uid, status='unavailable', reason='no_selected_sample_rule', rule=copy.deepcopy(rule))
            if rule:
                value, unit = f['value'], f['unit']
                obs = f['source_observation']
                if unit is None and obs and obs['display_cm'] is not None:
                    value, unit = display_number(obs['display_cm']), 'cm'
                    basis = 'captured_display_cm'
                else:
                    basis = f['unit_status']
                if unit not in ('cm', 'in'):
                    row['reason'] = 'unit_not_comparable_without_conversion'
                else:
                    lo, hi = interval(rule, unit)
                    if unit == 'cm':
                        value, lo, hi = display_number(value) if not isinstance(value, Decimal) else value, display_number(lo), display_number(hi)
                    else:
                        # Compare the JSON decimal value exactly; keep the stored number/type unchanged.
                        value = Fraction(str(value))
                    # Same-unit numeric comparison only; fractional-inch strings are parsed, never converted.
                    row.update(status='outside_selected_sample' if value < lo or value > hi else
                               'boundary_unknown' if value == lo or value == hi else 'within_selected_sample',
                               reason='numeric_comparison_only', comparison_unit=unit, value_basis=basis)
            result['fields'].append(row)
        statuses = [row['status'] for row in result['fields']]
        for label in ('outside_selected_sample', 'boundary_unknown', 'within_selected_sample'):
            if label in statuses:
                result['comparison'] = label
                break
        return result

    def resolve_many(self, requests):
        profiles, seen = [], set()
        for request in array(requests):
            profile = self.resolve(request)
            key = (('custom', profile['target']['target_id']) if profile['kind'] == 'custom' else
                   ('standard', profile['template']['template_id'], profile['standard_model']['mannequin_id']))
            require(key not in seen, 'Duplicate target/model identity in batch')
            seen.add(key); profiles.append(profile)
        return profiles

    def verify_profile(self, profile, expected_sha256=None):
        obj(profile, 'schema kind catalog_binding template standard_model base_model target request measurements source_evidence status profile_sha256')
        sha(profile['profile_sha256'])
        require(profile['schema'] == 'size-catalog-profile/v1', 'Unsupported profile schema')
        if expected_sha256 is not None:
            require(profile['profile_sha256'] == sha(expected_sha256), 'External profile pin mismatch')
        require(profile['profile_sha256'] == hashed({k: v for k, v in profile.items() if k != 'profile_sha256'}),
                'Profile hash mismatch')
        require(canonical(profile['catalog_binding']) == canonical(self._lock), 'Profile catalog binding changed')
        expected = self.resolve(profile['request'])
        require(canonical(profile) == canonical(expected), 'Profile differs from deterministic request replay')
        return expected

    def project(self, profile, request):
        profile = self.verify_profile(profile)
        obj(request, 'schema engine required_inputs mappings assumptions')
        require(request['schema'] == 'size-catalog-projection-request/v1', 'Unsupported projection schema')
        string(request['engine'])
        inputs, mappings, assumptions = {}, {}, {}
        fields = {f['param_uid']: f for f in profile['measurements']}
        for r in array(request['required_inputs']):
            obj(r, 'name unit landmark kind provenance')
            name = string(r['name']); string(r['unit']); string(r['landmark']); provenance(r['provenance'])
            require(r['kind'] in ('length', 'site_scalar'), 'Unsupported engine field kind')
            require(name not in inputs, 'Duplicate engine input')
            inputs[name] = r
        require(bool(inputs), 'Explicit required input contract must not be empty')
        for m in array(request['mappings']):
            obj(m, 'input param_uid source_value landmark unit_interpretation provenance')
            name = string(m['input']); string(m['landmark']); provenance(m['provenance'])
            require(name in inputs and name not in mappings, 'Unknown/duplicate mapped input')
            require(string(m['param_uid']) in fields, 'Unknown projection UID')
            require(m['source_value'] in ('raw', 'display_cm', 'display_in'), 'Unsupported source value selector')
            if m['unit_interpretation'] is not None:
                obj(m['unit_interpretation'], 'unit provenance')
                string(m['unit_interpretation']['unit']); provenance(m['unit_interpretation']['provenance'])
            mappings[name] = m
        for a in array(request['assumptions']):
            obj(a, 'input value unit landmark kind provenance')
            name = string(a['input']); number(a['value']); string(a['unit']); string(a['landmark'])
            provenance(a['provenance'])
            require(a['kind'] in ('length', 'site_scalar'), 'Unsupported assumption field kind')
            require(a['kind'] != 'length' or a['value'] > 0, 'Length assumption must be positive')
            require(name in inputs and name not in assumptions and name not in mappings,
                    'Unknown/duplicate/conflicting engine assumption')
            assumptions[name] = a
        missing, values, used = [], {}, set()
        for name, definition in inputs.items():
            reason, value = None, None
            if request['engine'] in ('pattern', 'pattern.py') and name == 'height':
                reason = 'unsupported_legacy_height'
            elif name in assumptions:
                a = assumptions[name]
                if any(a[k] != definition[k] for k in ('unit', 'landmark', 'kind')):
                    reason = 'assumption_definition_mismatch'
                else:
                    value = dict(value=a['value'], unit=a['unit'], landmark=a['landmark'], kind=a['kind'],
                                 authority='engineering_assumption', provenance=copy.deepcopy(a['provenance']))
            elif name in mappings:
                m = mappings[name]; f = fields[m['param_uid']]
                established = {'shoulder_width': 'Shoulder width', 'shoulder_diameter': 'Shoulder diameter',
                               'back_length': 'Back length', 'back_width': 'Back width'}
                if (m['landmark'] != f['label'] or definition['landmark'] != m['landmark']
                        or name in ('front_length', 'bust_height')
                        or (name in established and definition['landmark'] != established[name])):
                    reason = 'unsupported_landmark_mapping'
                elif (definition['kind'] == 'site_scalar') != (f['parameter_definition']['semantic_class'] ==
                                                              'body_shape_parameter_website_defined'):
                    reason = 'unsupported_semantic_mapping'
                else:
                    raw_value, unit, authority = f['value'], f['unit'], f['unit_status']
                    interpretation = m['unit_interpretation']
                    if m['source_value'] != 'raw':
                        obs = f['source_observation']
                        raw_value = obs[m['source_value']] if obs else None
                        unit = 'cm' if m['source_value'] == 'display_cm' else 'in'
                        authority = 'captured_display'
                    if interpretation is not None:
                        require(m['source_value'] == 'raw' and unit is None,
                                'Unit interpretation may only fill unknown raw units')
                        unit, authority = interpretation['unit'], 'caller_assumption'
                    if raw_value is None:
                        reason = 'source_value_unavailable'
                    elif type(raw_value) not in (int, float):
                        reason = 'unsupported_value_representation'
                    elif unit is None:
                        reason = 'source_unit_unavailable'
                    elif unit != definition['unit']:
                        reason = 'unit_conversion_unavailable'
                    else:
                        value = dict(value=raw_value, unit=unit, landmark=definition['landmark'], kind=definition['kind'],
                                     authority='caller_declared_mapping', param_uid=f['param_uid'],
                                     source_value=m['source_value'], unit_authority=authority,
                                     unit_interpretation=copy.deepcopy(interpretation), provenance=copy.deepcopy(m['provenance']))
                        used.add(f['param_uid'])
            else:
                reason = 'no_mapping_or_assumption'
            if reason:
                missing.append(dict(input=name, reason=reason))
            else:
                values[name] = value
        result = dict(schema='size-catalog-projection/v1', profile=profile, request=copy.deepcopy(request),
                      engine_values=values, missing_inputs=missing,
                      unmapped_measurements=[copy.deepcopy(f) for uid, f in fields.items() if uid not in used],
                      status=dict(mapping='incomplete' if missing else 'complete', conversion='not_performed',
                                  engine_contract='caller_declared; not_engine_verified', anatomy='not_assessed',
                                  sewability='not_assessed', geometry_export='not_authorized'))
        result['projection_sha256'] = hashed(result)
        return result

    def verify_projection(self, projection, expected_sha256=None):
        obj(projection, 'schema profile request engine_values missing_inputs unmapped_measurements status projection_sha256')
        require(projection['schema'] == 'size-catalog-projection/v1', 'Unsupported projection result schema')
        sha(projection['projection_sha256'])
        if expected_sha256 is not None:
            require(projection['projection_sha256'] == sha(expected_sha256), 'External projection pin mismatch')
        require(projection['projection_sha256'] == hashed({k: v for k, v in projection.items() if k != 'projection_sha256'}),
                'Projection hash mismatch')
        expected = self.project(projection['profile'], projection['request'])
        require(canonical(projection) == canonical(expected), 'Projection differs from deterministic replay')
        return expected

    def audit(self):
        """Stream per-template receipts and independently aggregate actual visited identities."""
        models, observations, parameters, templates = set(), set(), set(), set()
        for tid, t in self._templates.items():
            templates.add(tid); rows = []; count = 0
            for mi in t['ordered_mannequin_ids']:
                p = self.resolve(standard_request(tid, mi))
                self.verify_profile(parse_json(canonical(p)), p['profile_sha256'])
                originals = []
                for f in p['measurements']:
                    uid = f['param_uid']; key = (mi, uid)
                    require(key not in observations, 'Duplicate audited observation')
                    original = self._measurements[key]
                    require(canonical(f['source_observation']) == canonical(original), 'Observation roundtrip mismatch')
                    require(canonical(f['value']) == canonical(original['raw_value']), 'Typed value roundtrip mismatch')
                    observations.add(key); parameters.add(uid); originals.append(original)
                count += len(originals); models.add(mi)
                rows.append(dict(mannequin_id=mi, size_label=p['standard_model']['size_label'],
                                 observation_count=len(originals), profile_sha256=p['profile_sha256'],
                                 source_observations_sha256=hashed(originals), roundtrip='exact'))
            yield dict(schema='size-catalog-audit/v1', kind='template_batch', template_id=tid,
                       model_count=len(rows), observation_count=count, models=rows)
        require((len(templates), len(models), len(observations), len(parameters)) ==
                tuple(self.counts[k] for k in ('templates', 'models', 'observations', 'parameters')),
                'Visited catalog coverage mismatch')
        yield dict(schema='size-catalog-audit/v1', kind='aggregate', counts=copy.deepcopy(self.counts),
                   standard_roundtrips=len(models), binding_sha256=self.binding_sha256,
                   coverage='complete_against_pinned_saved_catalog_only', geometry_export='not_authorized')


def standard_request(template_id, mannequin_id, rule_sample=None):
    return dict(schema='size-catalog-request/v1', operation='standard', template_id=template_id,
                mannequin_id=mannequin_id, rule_sample=rule_sample)


def provenance(value):
    obj(value, 'source method')
    string(value['source']); string(value['method'])


def interval(rule, unit):
    if unit == 'cm':
        return rule['min']['cm'], rule['max']['cm']
    def fraction(text):
        try:
            parts = text.split()
            require(1 <= len(parts) <= 2, 'Unsupported captured inch syntax')
            if len(parts) == 1:
                return Fraction(parts[0])
            whole, remainder = Fraction(parts[0]), Fraction(parts[1])
            require(whole.denominator == 1 and 0 <= remainder < 1, 'Invalid mixed fraction')
            return whole - remainder if parts[0].startswith('-') else whole + remainder
        except (ValueError, ZeroDivisionError) as exc:
            raise CatalogError('Invalid captured inch number') from exc
    return fraction(rule['min']['in']), fraction(rule['max']['in'])


def main(argv=None):
    import sys
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', type=Path, required=True, help='Private normalized catalog root')
    parser.add_argument('--lock', type=Path, help='Previously pinned selected-file lock')
    sub = parser.add_subparsers(dest='command', required=True)
    pin = sub.add_parser('pin'); pin.add_argument('--manifest-sha256', required=True)
    listing = sub.add_parser('list'); listing.add_argument('--template-id')
    show = sub.add_parser('show'); show.add_argument('--template-id', required=True)
    select = sub.add_parser('select'); select.add_argument('--template-id', required=True)
    select.add_argument('--mannequin-id', required=True); select.add_argument('--rule-sample', type=Path)
    for command in ('resolve', 'resolve-many'):
        sub.add_parser(command).add_argument('--request', type=Path, required=True)
    check = sub.add_parser('check'); check.add_argument('--profile', type=Path, required=True)
    check.add_argument('--expected-sha256')
    project = sub.add_parser('project'); project.add_argument('--profile', type=Path, required=True)
    project.add_argument('--request', type=Path, required=True)
    project.add_argument('--expected-sha256', help='Optional externally retained profile hash')
    sub.add_parser('audit')
    args = parser.parse_args(argv)
    def emit(value):
        print(canonical(value).decode('utf-8'), flush=True)
    try:
        if args.command == 'pin':
            emit(pin_catalog(args.catalog, args.manifest_sha256))
            return 0
        require(args.lock is not None, 'A pinned lock is required')
        c = Catalog.load(args.catalog, read_json(args.lock))
        code = 0
        if args.command == 'list':
            result = {'schema': 'size-catalog-list/v1', 'binding_sha256': c.binding_sha256}
            result.update({'models': c.list_models(args.template_id)} if args.template_id is not None else
                          {'templates': c.list_templates()})
        elif args.command == 'show':
            result = dict(schema='size-catalog-show/v1', template=copy.deepcopy(c._template(args.template_id)),
                          models=c.list_models(args.template_id), binding_sha256=c.binding_sha256)
        elif args.command == 'select':
            result = c.resolve(standard_request(args.template_id, args.mannequin_id,
                                               read_json(args.rule_sample) if args.rule_sample else None))
        elif args.command == 'resolve':
            result = c.resolve(read_json(args.request))
        elif args.command == 'resolve-many':
            request = obj(read_json(args.request), 'schema requests')
            require(request['schema'] == 'size-catalog-batch-request/v1', 'Unsupported batch schema')
            result = dict(schema='size-catalog-batch/v1', profiles=c.resolve_many(request['requests']))
            code = 3 if any(p['status']['constraints']['comparison'] == 'outside_selected_sample'
                            for p in result['profiles']) else 0
        elif args.command == 'check':
            value = read_json(args.profile)
            require(type(value) is dict, 'Expected profile/projection object')
            if value.get('schema') == 'size-catalog-projection/v1':
                result = c.verify_projection(value, args.expected_sha256)
                code = 3 if result['missing_inputs'] else 0
            else:
                result = c.verify_profile(value, args.expected_sha256)
        elif args.command == 'project':
            p = c.verify_profile(read_json(args.profile), args.expected_sha256)
            result = c.project(p, read_json(args.request))
            code = 3 if result['missing_inputs'] else 0
        elif args.command == 'audit':
            for result in c.audit():
                emit(result)
            return 0
        else:
            raise CatalogError('Unsupported CLI operation')
        if result.get('schema') == 'size-catalog-profile/v1':
            code = 3 if result['status']['constraints']['comparison'] == 'outside_selected_sample' else 0
        elif result.get('schema') == 'size-catalog-projection/v1':
            if result['profile']['status']['constraints']['comparison'] == 'outside_selected_sample':
                code = 3
        emit(result)
        return code
    except (CatalogError, OSError) as exc:
        # Never echo imported records, unknown keys, auth values or application stores.
        print(canonical(dict(schema='size-catalog-error/v1', status='rejected', error=str(exc))).decode(), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
