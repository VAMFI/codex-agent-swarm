#!/usr/bin/env python3
"""Pure, advisory task allocation. Reads one JSON request; never launches workers."""

import json
import sys


LEVELS = {'trivial': 0, 'simple': 1, 'standard': 2, 'hard': 3}
EFFORTS = ['low', 'medium', 'high', 'xhigh', 'max', 'ultra']
EVIDENCE = {
    'coding': ['focused regression checks after final edits', 'inspect changed behavior and integration'],
    'research': ['current primary sources with dates and links', 'separate facts, inference, and uncertainty'],
    'writing': ['check audience, exact copy, factual support, and requested format', 'inspect final rendered artifact when relevant'],
    'planning': ['check dependencies, ownership, acceptance criteria, and feasibility', 'expose assumptions and decisions requiring authority'],
    'extraction': ['validate schema, coverage, and source-to-output fidelity', 'check missing, duplicate, and ambiguous records'],
    'computer-use': ['record observed user-facing behavior and final state', 'respect account, private-data, and external-write authority'],
    'high-risk': ['confirm authority and current authoritative evidence', 'independent adversarial review before consequential action'],
}


def mapping(value, name):
    if not isinstance(value, dict):
        raise ValueError(name + ' must be an object')
    return value


def flag(value, name, default=False):
    result = value.get(name, default)
    if not isinstance(result, bool):
        raise ValueError(name + ' must be a boolean')
    return result


def number(value, name, default, minimum=0):
    result = value.get(name, default)
    if isinstance(result, bool) or not isinstance(result, int) or result < minimum:
        raise ValueError(name + ' must be an integer >= ' + str(minimum))
    return result


def strings(value, name):
    if not isinstance(value, list) or any(not isinstance(s, str) or not s.strip() for s in value):
        raise ValueError(name + ' must be a list of nonblank strings')
    return value


def pin(value, name):
    result = value.get(name)
    if result is not None and (not isinstance(result, str) or not result.strip()):
        raise ValueError(name + ' must be a nonblank string')
    return result


def model_choice(models, policy, capabilities, complexity, limits):
    model_pin = pin(policy, 'model_pin')
    effort_pin = pin(policy, 'reasoning_pin')
    if not flag(policy, 'adaptive') and not model_pin and not effort_pin:
        return {'selection': 'inherit'}
    if effort_pin and not model_pin:
        raise ValueError('reasoning_pin requires model_pin so support can be validated')
    if model_pin:
        selected = next((m for m in models if m['id'] == model_pin), None)
        if selected is None:
            raise RuntimeError('model pin is not in the live advertised inventory: ' + model_pin)
        if effort_pin and effort_pin not in selected.get('efforts', []):
            raise RuntimeError('reasoning pin is unsupported for model pin: ' + model_pin)
        missing = set(capabilities) - set(selected.get('capabilities', []))
        if missing or LEVELS.get(selected.get('max_complexity'), -1) < LEVELS[complexity]:
            limits.append('Pinned model adequacy is unconfirmed or below the task classification; pin retained. Validate evidence before continuing.')
    else:
        classified = [m for m in models if all(k in m for k in ('capabilities', 'max_complexity', 'preference', 'efforts'))]
        if not classified:
            limits.append('Model capability/ranking data absent; inherit parent configuration without an explicit override. Adequacy is unverified.')
            return {'selection': 'inherit'}
        adequate = [m for m in classified if set(capabilities) <= set(m['capabilities'])
                    and LEVELS[m['max_complexity']] >= LEVELS[complexity] and m['efforts']]
        if not adequate:
            raise RuntimeError('No classified advertised model meets task capabilities and complexity; do not silently lower quality.')
        selected = min(adequate, key=lambda m: (m['preference'], m['id']))
    result = {'selection': 'explicit', 'model': selected['id']}
    if effort_pin:
        result['reasoning'] = effort_pin
    else:
        supported = [e for e in EFFORTS if e in selected.get('efforts', [])]
        target = {'simple': 'low', 'standard': 'medium', 'hard': 'high'}[complexity]
        adequate = [e for e in supported if EFFORTS.index(e) >= EFFORTS.index(target)]
        if adequate:
            result['reasoning'] = adequate[0]
        elif supported:
            # Respect the supported schema; do not invent a higher effort.
            result['reasoning'] = supported[-1]
            limits.append('Selected model has no advertised effort at the preferred level; task evidence must establish adequacy.')
        else:
            limits.append('Selected model effort schema absent; omit reasoning override.')
    return result


def route(request):
    request = mapping(request, 'request')
    task = mapping(request.get('task', {}), 'task')
    policy = mapping(request.get('policy', {}), 'policy')
    host = mapping(request.get('host', {}), 'host')
    kind = task.get('kind', 'coding')
    complexity = task.get('complexity', 'standard')
    if not isinstance(kind, str) or not isinstance(complexity, str) or kind not in EVIDENCE or complexity not in LEVELS:
        raise ValueError('unsupported task kind or complexity')
    model_pin = pin(policy, 'model_pin')
    effort_pin = pin(policy, 'reasoning_pin')
    adaptive = flag(policy, 'adaptive')
    status_only = flag(task, 'status_only')
    ambiguous = flag(task, 'ambiguous')
    risk = task.get('risk', 'normal')
    if risk not in ('normal', 'high'):
        raise ValueError('risk must be normal or high')
    result = {
        'mode': 'direct', 'worker_count': 0, 'peak_active': 0,
        'assignments': [], 'waves': [], 'evidence': list(EVIDENCE[kind]),
        'limits': [], 'blockers': [], 'next_action': 'perform task directly',
        'coordinator_model': {'selection': 'inherit',
                              'limit': 'Helper cannot switch the coordinator model; current parent configuration applies.'},
    }
    if model_pin:
        result['coordinator_model']['requested'] = model_pin
    if effort_pin:
        result['coordinator_model']['requested_reasoning'] = effort_pin
    if status_only:
        result['next_action'] = 'inspect status read-only'
        return result
    if ambiguous:
        result['next_action'] = 'clarify acceptance and scope'
        return result
    if complexity == 'trivial' and kind != 'high-risk' and risk != 'high':
        return result

    max_workers = min(number(policy, 'max_workers', 4, 1), number(host, 'max_workers', 4, 0))
    if not flag(policy, 'allow_more_workers'):
        max_workers = min(max_workers, 4)
    blockers = result['blockers']
    for capability in ('spawn', 'message', 'wait'):
        if not flag(host, capability):
            blockers.append('Native ' + capability + ' capability is unavailable; no swarm was started.')
    if max_workers < 2:
        blockers.append('Independent review requires two distinct allocated native slots, including the verifier.')

    models = host.get('models', [])
    if not isinstance(models, list):
        raise ValueError('models must be a list')
    model_ids = set()
    for model in models:
        mapping(model, 'model')
        model_id = pin(model, 'id')
        if not model_id or model_id in model_ids:
            raise ValueError('model IDs must be present and unique')
        model_ids.add(model_id)
        if 'capabilities' in model:
            strings(model['capabilities'], 'model capabilities')
        if 'efforts' in model:
            strings(model['efforts'], 'model efforts')
        if 'max_complexity' in model and model['max_complexity'] not in ('simple', 'standard', 'hard'):
            raise ValueError('invalid model max_complexity')
        if 'preference' in model:
            number(model, 'preference', 0)

    units = task.get('units', [{'id': 'work'}])
    if not isinstance(units, list) or not units:
        raise ValueError('units must be a nonempty list')
    assignments = []
    ids = set()
    hard = kind == 'high-risk' or risk == 'high'
    if hard:
        result['evidence'] += [e for e in EVIDENCE['high-risk'] if e not in result['evidence']]
    for unit in units:
        mapping(unit, 'unit')
        unit_id = pin(unit, 'id')
        if not unit_id or unit_id in ids or unit_id == 'verify':
            raise ValueError('unit IDs must be present, unique, and not reserved verify')
        ids.add(unit_id)
        role = unit.get('role', 'reader' if kind in ('research', 'planning', 'high-risk') else 'author')
        if role not in ('reader', 'author'):
            raise ValueError('unit role must be reader or author; verifier is allocated independently')
        required = strings(unit.get('capabilities', ['computer-use' if kind == 'computer-use' else 'coding' if kind == 'coding' else 'text']), 'unit capabilities')
        deps = strings(unit.get('depends_on', []), 'depends_on')
        assignments.append({'unit': unit_id, 'role': role, 'depends_on': list(dict.fromkeys(deps)),
                            'capabilities': list(required), 'complexity': 'hard' if hard else complexity})
    for assignment in assignments:
        if assignment['unit'] in assignment['depends_on'] or not set(assignment['depends_on']) <= ids:
            raise ValueError('unit dependencies must reference other declared units')
    if 'capabilities' in host:
        available = set(strings(host['capabilities'], 'host capabilities'))
        required = set(c for a in assignments for c in a['capabilities'])
        if not required <= available:
            blockers.append('Execution capabilities unavailable on host: ' + ', '.join(sorted(required - available)))
    else:
        result['limits'].append('Host execution capability inventory absent; coordinator must check task tools before dispatch. Model capability alone is insufficient.')

    # Reserve a distinct verifier slot; its native worker starts only at handoff.
    capacity = max(1, max_workers - 1)
    roles = sorted(set(a['role'] for a in assignments))
    if len(roles) > capacity:
        blockers.append('Distinct reader and author roles plus independent verifier do not fit available native slots.')
    role_slots = {role: 1 for role in roles}
    totals = {role: sum(a['role'] == role for a in assignments) for role in roles}
    for _ in range(max(0, capacity - len(roles))):
        candidates = [role for role in roles if role_slots[role] < totals[role]]
        if not candidates:
            break
        role = max(candidates, key=lambda r: (totals[r] - role_slots[r], r))
        role_slots[role] += 1
    width = 1 if any('computer-use' in a['capabilities'] for a in assignments) else capacity
    remaining = list(assignments)
    done = set()
    waves = []
    while remaining:
        ready = []
        counts = {role: 0 for role in roles}
        for assignment in remaining:
            if (set(assignment['depends_on']) <= done and len(ready) < width
                    and counts[assignment['role']] < role_slots[assignment['role']]):
                ready.append(assignment)
                counts[assignment['role']] += 1
        if not ready:
            raise ValueError('unit dependency cycle')
        waves.append([a['unit'] for a in ready])
        done.update(a['unit'] for a in ready)
        remaining = [a for a in remaining if a not in ready]
    for wave in waves:
        counts = {role: 0 for role in roles}
        for unit_id in wave:
            assignment = next(a for a in assignments if a['unit'] == unit_id)
            counts[assignment['role']] += 1
            assignment['slot'] = assignment['role'] + '_' + str(counts[assignment['role']])
    producer_slots = len(set(a['slot'] for a in assignments))
    peak_active = max(map(len, waves))
    verifier = {'unit': 'verify', 'role': 'verifier', 'slot': 'verifier', 'independent': True,
                'depends_on': [a['unit'] for a in assignments],
                'capabilities': list(dict.fromkeys(c for a in assignments for c in a['capabilities'])),
                'complexity': 'hard' if hard else complexity}
    assignments.append(verifier)
    slots = list(dict.fromkeys(a['slot'] for a in assignments))
    overrides = flag(host, 'model_overrides')
    if not overrides and (model_pin or effort_pin):
        blockers.append('Explicit model/reasoning pin cannot be applied: native model override support is unavailable.')
    elif not overrides and adaptive:
        result['limits'].append('Native model override support unavailable; inherit current configuration with adequacy unverified.')
    for slot in slots:
        members = [a for a in assignments if a['slot'] == slot]
        required = list(dict.fromkeys(c for a in members for c in a['capabilities']))
        level = max((a['complexity'] for a in members), key=lambda c: LEVELS[c])
        try:
            choice = model_choice(models, policy, required, level, result['limits']) if overrides else {'selection': 'inherit'}
            for assignment in members:
                assignment.update(choice)
        except RuntimeError as error:
            blockers.append(str(error))
    result['limits'] = list(dict.fromkeys(result['limits']))
    if adaptive:
        result['limits'].append('Model capability, adequacy, and preference labels are caller-supplied hypotheses; evaluate on actual task evidence. No cost or token savings are measured.')
    if blockers:
        result['blockers'] = list(dict.fromkeys(blockers))
        result['mode'] = 'blocked'
        result['next_action'] = 'resolve reported capability or policy blocker before dispatch'
        return result
    result.update(mode='parallel' if peak_active > 1 else 'sequential',
                  worker_count=producer_slots + 1, peak_active=peak_active,
                  assignments=assignments, waves=waves + [['verify']],
                  next_action='review plan, register native handles, then dispatch bounded waves')
    return result


def main():
    try:
        value = json.load(sys.stdin)
        print(json.dumps(route(value), indent=2, sort_keys=True))
    except (ValueError, TypeError) as error:
        print('route: ' + str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
