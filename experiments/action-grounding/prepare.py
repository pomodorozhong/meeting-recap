"""Materialize exact-text counterfactuals and verifier controls, without model inference.

All dependencies are standard-library. Expected answers are never included in lines.json.
"""
import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
VARIANTS = ('base', 'owner', 'deadline', 'recipient', 'cancelled', 'completed',
            'unsupported', 'conditional', 'irrelevant', 'paraphrase')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def make_case(family, variant):
    owner = 'C' if variant == 'owner' else 'B'
    due = family['alternate_due'] if variant == 'deadline' else family['due']
    recipient = family['alternate_recipient'] if variant == 'recipient' else family['recipient']
    task = f"把{family['object']}{family['verb']}{recipient}"
    commitment = f'我會在{due}{task}。'
    acknowledgement = '好，就照你說的辦。'
    if variant == 'paraphrase':
        commitment = f"這件事由我負責，{family['object']}會在{due}{family['paraphrase_verb']}{recipient}。"
    elif variant == 'unsupported':
        commitment, acknowledgement = '這件事還沒有決定。', '今天先到這裡。'
    elif variant == 'conditional':
        commitment = f'如果主管批准，我才會在{due}{task}。'
        acknowledgement = '主管還沒批准，先不要執行，等批准再說。'
    lines = [f"[00:00:00] Speaker A: 接著處理{family['topic']}。",
             f'[00:00:10] Speaker {owner}: {commitment}',
             f'[00:00:20] Speaker A: {acknowledgement}']
    ending = {'cancelled': '剛才那項工作取消，不用執行。',
              'completed': '補充一下，剛才那項工作我已經完成了，沒有剩下的待辦。',
              'irrelevant': '今天會議室的窗簾是藍色的。'}
    if variant in ending:
        speaker = 'B' if variant == 'completed' else 'A'
        lines.append(f'[00:00:30] Speaker {speaker}: {ending[variant]}')
    negative = variant in {'cancelled', 'completed', 'unsupported', 'conditional'}
    answer = {'task': task, 'owner': f'Speaker {owner}', 'due': due, 'evidence': ['00:00:10']}
    expected = {'actions': [] if negative else [answer],
                'relation_to_base': ('empty' if negative else
                                     'same' if variant in {'base', 'irrelevant', 'paraphrase'} else f'change_{variant}'),
                'required_support_ids': [] if negative else ['L002'],
                'decisive_state_ids': ['L004'] if variant in {'cancelled', 'completed'} else
                                      ['L002', 'L003'] if variant == 'conditional' else ['L002']}
    return lines, expected


def verifier_cases(family):
    lines, key = make_case(family, 'base')
    item = key['actions'][0]
    # Every call contains exactly one candidate, so rejection of one cannot hide another.
    controls = [('positive', lines, item, True),
                ('wrong-owner', lines, {**item, 'owner': 'Speaker C'}, False),
                ('wrong-deadline', lines, {**item, 'due': family['alternate_due']}, False),
                ('wrong-recipient', lines, {**item, 'task': item['task'].replace(family['recipient'], family['alternate_recipient'])}, False),
                ('missing-support', make_case(family, 'unsupported')[0], item, False),
                ('cancelled', make_case(family, 'cancelled')[0], item, False)]
    return controls


def prepare(root):
    root = root.resolve()
    if root.exists():
        raise ValueError('output directory already exists; preserve it and choose a new run ID')
    if any((p / '.git').exists() for p in (root, *root.parents)):
        raise ValueError('outputs must be outside Git')
    families = json.loads((HERE / 'families.json').read_text())
    root.mkdir(parents=True)
    entries = []
    for family in families:
        for variant in VARIANTS:
            path = root / 'extract' / family['id'] / variant
            path.mkdir(parents=True)
            lines, expected = make_case(family, variant)
            write(path / 'lines.json', lines)
            write(path / 'expected.json', expected)
            entries.append({'id': f"extract/{family['id']}/{variant}", 'split': family['split'],
                            'lines_sha256': sha(path / 'lines.json'), 'expected_sha256': sha(path / 'expected.json')})
        for variant, lines, item, accept in verifier_cases(family):
            path = root / 'verify' / family['id'] / variant
            path.mkdir(parents=True)
            write(path / 'lines.json', lines)
            write(path / 'candidates.json', [item])
            write(path / 'expected.json', {'accepted_ids': [1] if accept else [],
                                         'required_support_lines': [2] if accept else []})
            entries.append({'id': f"verify/{family['id']}/{variant}", 'split': family['split'],
                            **{f'{k}_sha256': sha(path / f'{k}.json') for k in ('lines', 'candidates', 'expected')}})
    write(root / 'manifest.json', {'schema': 1, 'kind': 'prepared-not-run',
                                  'families_sha256': sha(HERE / 'families.json'),
                                  'builder_sha256': sha(Path(__file__)), 'cases': entries})
    return {'extraction_cases': 60, 'verification_cases': 36, 'manifest': str(root / 'manifest.json')}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.output), indent=2))
