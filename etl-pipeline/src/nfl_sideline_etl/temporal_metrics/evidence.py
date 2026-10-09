"""Mechanical qualification under explicit trust premises, not authentication."""
from .times import instant, eastern_kickoff, ISO


class Policy:
    def __init__(self, resources, proofs, policy, mode, cut):
        self.resources = resources
        self.proofs = proofs
        self.origins = set(policy['trustedOrigins'])
        self.mode = mode
        self.cut = cut
        self.cache = {}
        self.active = set()

    def proof(self, envelope, subject, kinds):
        if envelope is None:
            return 'UNKNOWN', None
        evidence = self.proofs[envelope['evidence_id']]
        if (evidence['subject_id'] != subject or evidence['kind'] not in kinds or
                evidence['origin'] not in self.origins):
            return 'DECLARATION_UNPROVEN', evidence
        value = envelope['value']
        if evidence['kind'] in ('ARCHIVE_OBSERVATION', 'SYSTEM_INGESTION', 'FINAL_OBSERVATION'):
            matches = instant(value) == instant(evidence['recorded_at'])
        elif evidence['kind'] in ('EVENT_END_BOUND', 'EVENT_START_LOWER_BOUND'):
            matches = instant(value) == instant(evidence['value']) and instant(value) <= instant(evidence['recorded_at'])
        else:
            matches = type(value) is type(evidence['value']) and value == evidence['value']
            if evidence['kind'] == 'METADATA' and isinstance(value, str) and ISO.fullmatch(value):
                try:
                    matches = instant(value) == instant(evidence['value'])
                except (ValueError, TypeError):
                    matches = False
        if not matches:
            return 'DECLARATION_UNPROVEN', evidence
        if self.mode == 'POINT_IN_TIME':
            if instant(evidence['recorded_at']) >= self.cut:
                return 'EVIDENCE_NOT_KNOWN_AT_CUTOFF', evidence
            for dep in evidence['dependencies']:
                if self.resource(dep)[0]:
                    return 'EVIDENCE_DEPENDENCY_INELIGIBLE', evidence
        return 'ACCEPTED_BY_POLICY', evidence

    def resource(self, rid):
        if rid in self.cache:
            return self.cache[rid]
        if rid in self.active:
            raise ValueError('Evidence/resource knowledge cycle')
        self.active.add(rid)
        resource = self.resources[rid]
        reasons, available = [], None
        dependency_times = []
        for dep in resource['dependencies']:
            rejected, when = self.resource(dep)
            reasons.extend(rejected)
            if when is not None:
                dependency_times.append(when)
        if resource['kind'] != 'SET':
            for key, kinds in (('available_at', {'ARCHIVE_OBSERVATION', 'SYSTEM_INGESTION'}), ('ingested_at', {'SYSTEM_INGESTION'})):
                status, _ = self.proof(resource[key], rid, kinds)
                value = resource[key]['value'] if resource[key] else None
                if self.mode == 'POINT_IN_TIME' and status != 'ACCEPTED_BY_POLICY':
                    reasons.append({'reason': key.upper() + '_' + status, 'subjectId': rid})
                elif value is not None and status == 'ACCEPTED_BY_POLICY':
                    when = instant(value)
                    if self.mode == 'POINT_IN_TIME' and when >= self.cut:
                        reasons.append({'reason': key.upper() + '_NOT_BEFORE_CUTOFF', 'subjectId': rid})
                    if key == 'available_at':
                        available = when
        if dependency_times:
            available = max(dependency_times + ([available] if available is not None else []))
        # The revision's own materialized statements cannot arrive later than
        # the knowledge cutoff and silently displace an older eligible revision.
        if self.mode == 'POINT_IN_TIME':
            payload = resource['payload']
            requirements = []
            if resource['kind'] == 'CALENDAR':
                requirements.append((payload['complete'], {'CALENDAR_COMPLETE'}))
                requirements.extend(({'value': c['week'], 'evidence_id': c['evidence_id']}, {'PERIOD_CLOSED'}) for c in payload['closed_weeks'])
            elif resource['kind'] == 'STATE':
                requirements.append((payload['event_upper_bound'], {'FINAL_OBSERVATION', 'EVENT_END_BOUND'}))
                requirements.append((payload.get('event_lower_bound'), {'EVENT_START_LOWER_BOUND'}))
                requirements.append((payload.get('source_cause'), {'METADATA'}))
                k = payload['kickoff']
                if k is not None:
                    value = k['value'] if 'value' in k else eastern_kickoff(k['gameday'], k['gametime'])
                    if value is not None:
                        requirements.append(({'value': value, 'evidence_id': k['evidence_id']}, {'METADATA'}))
            for env, kinds in requirements:
                status, proof = self.proof(env, rid, kinds)
                if status == 'ACCEPTED_BY_POLICY':
                    available = max([instant(proof['recorded_at'])] + ([available] if available is not None else []))
                if status in ('EVIDENCE_NOT_KNOWN_AT_CUTOFF', 'EVIDENCE_DEPENDENCY_INELIGIBLE'):
                    reasons.append({'reason': status, 'subjectId': env['evidence_id']})
        if self.mode == 'POINT_IN_TIME' and available is None:
            reasons.append({'reason': 'AVAILABLE_AT_UNKNOWN', 'subjectId': rid})
        self.active.remove(rid)
        # Stable diagnostic order, including shared dependencies only once.
        unique = {(r['reason'], r['subjectId']): r for r in reasons}
        result = ([unique[k] for k in sorted(unique)], available)
        self.cache[rid] = result
        return result

    def closure(self, ids):
        found = set()
        def visit(rid):
            if rid in found:
                return
            found.add(rid)
            for dep in self.resources[rid]['dependencies']:
                visit(dep)
        for rid in ids:
            visit(rid)
        return sorted(found)
