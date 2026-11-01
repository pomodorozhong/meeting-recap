import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prepare import HERE, VARIANTS, make_case, prepare, verifier_cases


class GroundingFixtures(unittest.TestCase):
    def setUp(self):
        self.families = json.loads((HERE / 'families.json').read_text())

    def test_edits_change_only_the_designated_fact(self):
        for family in self.families:
            base_lines, base_key = make_case(family, 'base')
            for variant, field in [('owner', 'owner'), ('deadline', 'due'), ('recipient', 'task')]:
                lines, key = make_case(family, variant)
                self.assertEqual(lines[0::2], base_lines[0::2])
                self.assertNotEqual(lines[1], base_lines[1])
                before, after = base_key['actions'][0], key['actions'][0]
                self.assertEqual({k for k in before if before[k] != after[k]}, {field})

    def test_invariants_and_negatives_cannot_pass_by_universal_abstention(self):
        for family in self.families:
            base, key = make_case(family, 'base')
            self.assertEqual(len(key['actions']), 1)
            for variant in ['irrelevant', 'paraphrase']:
                _, changed = make_case(family, variant)
                self.assertEqual(changed['actions'], key['actions'])
            for variant in ['cancelled', 'completed', 'unsupported', 'conditional']:
                lines, negative = make_case(family, variant)
                self.assertEqual(negative['actions'], [])
                self.assertNotEqual(lines, base)

    def test_all_references_are_unambiguous_and_resolve(self):
        for family in self.families:
            for variant in VARIANTS:
                lines, key = make_case(family, variant)
                stamps = [line[1:9] for line in lines]
                self.assertEqual(len(set(stamps)), len(stamps))
                for action in key['actions']:
                    self.assertTrue(set(action['evidence']).issubset(stamps))
                for line_id in key['required_support_ids'] + key['decisive_state_ids']:
                    self.assertTrue(1 <= int(line_id[1:]) <= len(lines))

    def test_verifier_has_one_positive_and_five_distinct_failures(self):
        for family in self.families:
            controls = verifier_cases(family)
            self.assertEqual(len(controls), 6)
            self.assertEqual([kind for kind, _, _, accept in controls if accept], ['positive'])
            _, positive_lines, positive, _ = controls[0]
            for _, lines, candidate, _ in controls[1:]:
                self.assertFalse(lines == positive_lines and candidate == positive)

    def test_materialization_binds_all_files_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / 'pack'
            prepare(root)
            manifest = json.loads((root / 'manifest.json').read_text())
            self.assertEqual(len(manifest['cases']), 96)
            self.assertEqual(sum(c['split'] == 'holdout' for c in manifest['cases']), 48)
            for case in manifest['cases']:
                for field in ['lines', 'expected', 'candidates']:
                    if field + '_sha256' in case:
                        actual = hashlib.sha256((root / case['id'] / (field + '.json')).read_bytes()).hexdigest()
                        self.assertEqual(actual, case[field + '_sha256'])
            with self.assertRaises(ValueError):
                prepare(root)
            repo = Path(temp) / 'repo'
            repo.mkdir()
            (repo / '.git').write_text('gitdir: fake-worktree')
            with self.assertRaises(ValueError):
                prepare(repo / 'outputs')
            self.assertFalse((repo / 'outputs').exists())


if __name__ == '__main__':
    unittest.main()
