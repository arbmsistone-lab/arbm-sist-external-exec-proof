import ast
import re
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name('p8-swe-rebench-smoke.py')


def load_function(name, namespace):
    tree = ast.parse(SCRIPT.read_text(encoding='utf-8'))
    function = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == name
    )
    module = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
    scope = dict(namespace)
    exec(compile(module, str(SCRIPT), 'exec'), scope)
    return scope[name]


class SmokePolicyTests(unittest.TestCase):
    def test_context_compaction_deduplicates_files(self):
        compact = load_function('_compact_public_context', {'re': re})
        context = (
            'FILE: src/writer.py\nPUBLIC_STATIC_HOTSPOT: affinity=100\n000001|write int\n\n'
            'FILE: src/writer.py\n000001|write int again\n\n'
            'FILE: test/writer_test.py\n000001|test write overflow\n'
        )
        result = compact(context, 'overflow while writing output', 2000)
        self.assertEqual(result.count('FILE: src/writer.py'), 1)
        self.assertIn('FILE: test/writer_test.py', result)

    def test_writer_hotspot_outranks_reader_for_public_write_issue(self):
        hotspot = load_function('public_static_hotspots', {'Path': Path, 're': re})
        with tempfile.TemporaryDirectory() as repo:
            writer = Path(repo, 'src/cljam/io/vcf/writer.clj')
            reader = Path(repo, 'src/cljam/io/bcf/reader.clj')
            writer.parent.mkdir(parents=True)
            reader.parent.mkdir(parents=True)
            writer.write_text('(defn write-qual [x]\n  (str (int x)))\n', encoding='utf-8')
            reader.write_text('(defn read-qual [x]\n  (int x))\n', encoding='utf-8')
            result = hotspot(
                repo,
                ['src/cljam/io/bcf/reader.clj', 'src/cljam/io/vcf/writer.clj'],
                'QUAL value overflows when writing VCF',
            )
        self.assertLess(
            result.index('FILE: src/cljam/io/vcf/writer.clj'),
            result.index('FILE: src/cljam/io/bcf/reader.clj'),
        )

    def test_issue_compaction_keeps_public_issue_and_latest_rejection(self):
        compact = load_function('_compact_public_issue', {})
        raw = (
            'PUBLIC ISSUE: huge QUAL values fail while writing VCF'
            + (' public source invariant' * 300)
            + '\n\nPUBLIC INVARIANT REJECTION: preserve the nil guard'
            + (' public validation stack' * 300)
            + ' FINAL_PUBLIC_DIAGNOSTIC'
        )
        result = compact(raw, 500)
        self.assertLessEqual(len(result), 500)
        self.assertTrue(result.startswith('PUBLIC ISSUE:'))
        self.assertIn('PUBLIC INVARIANT REJECTION', result)
        self.assertIn('FINAL_PUBLIC_DIAGNOSTIC', result)

    def test_repair_compaction_keeps_mandatory_revision_directives(self):
        compact = load_function('_compact_public_issue', {})
        raw = (
            'PUBLIC ISSUE: huge QUAL values fail while writing VCF'
            + (' public contract' * 300)
            + '\n\nPUBLIC INVARIANT REJECTION: '
            + 'public_invariant_control_flow_removed:if. '
            + 'MANDATORY REVISION: retain the named original control-flow form. '
            + ('public reasoning ' * 200)
            + 'Rejected edits: candidate-A'
        )
        result = compact(raw, 1800)
        self.assertTrue(result.startswith('PUBLIC ISSUE:'))
        self.assertIn('PUBLIC INVARIANT REJECTION', result)
        self.assertIn('MANDATORY REVISION', result)
        self.assertIn('Rejected edits: candidate-A', result)

    def test_overflow_guard_rejects_removed_control_flow_and_retained_cast(self):
        guard = load_function('public_invariant_guard', {'Path': Path, 're': re})
        with tempfile.TemporaryDirectory() as repo:
            target = Path(repo, 'src/cljam/io/vcf/writer.clj')
            target.parent.mkdir(parents=True)
            target.write_text(
                ('\n' * 189)
                + '  (when x\n'
                + '    (if (zero? (mod x 1))\n'
                + '      (str (int x))\n'
                + '      (str x))))\n',
                encoding='utf-8',
            )
            bad = [{
                'path': 'src/cljam/io/vcf/writer.clj',
                'start_line': 190,
                'end_line': 193,
                'new': '(if (zero? (mod x 1)) (str (int x)) (str x)))',
            }]
            good = [{
                'path': 'src/cljam/io/vcf/writer.clj',
                'start_line': 192,
                'end_line': 192,
                'new': '      (format "%.0f" x)',
            }]
            issue = 'QUAL value overflows when writing VCF; huge values exceed Integer range'
            bad_errors = guard(repo, bad, issue)
            good_errors = guard(repo, good, issue)
        self.assertTrue(any('fixed_width_conversion_retained' in e for e in bad_errors))
        self.assertTrue(any('control_flow_removed:when' in e for e in bad_errors))
        self.assertEqual(good_errors, [])


    def test_deterministic_public_overflow_repair_is_minimal(self):
        repair = load_function('public_deterministic_overflow_repair', {'Path': Path, 're': re})
        with tempfile.TemporaryDirectory() as repo:
            target = Path(repo, 'src/cljam/io/vcf/writer.clj')
            target.parent.mkdir(parents=True)
            target.write_text('  (when x\n    (if (zero? (mod x 1))\n      (str (int x))\n      (str x))))\n', encoding='utf-8')
            edits = repair(repo, ['src/cljam/io/vcf/writer.clj'], 'QUAL value overflows when writing VCF')
        self.assertEqual(len(edits), 1)
        self.assertEqual(edits[0]['start_line'], 2)
        self.assertEqual(edits[0]['end_line'], 4)
        self.assertIn('(let [i (bigint x)]', edits[0]['new'])
        self.assertIn('(if (== x i)', edits[0]['new'])
        self.assertIn('(str i)', edits[0]['new'])
        self.assertNotIn('(mod x 1)', edits[0]['new'])
        self.assertNotIn('(int x)', edits[0]['new'])
        self.assertEqual(
            edits[0]['new'],
            '    (if (or (Double/isNaN (double x)) (Double/isInfinite (double x)))\n      (str x)\n      (let [i (bigint x)]\n        (if (== x i)\n          (str i)\n          (str x))))))',
        )

    def test_public_issue_regression_spec_uses_only_public_example(self):
        spec_fn = load_function('public_issue_regression_spec', {'re': re})
        issue = ('QUAL value overflows when writing VCF; values can exceed Integer range. '
                 'Example QUAL: 5.60878e+09')
        spec = spec_fn(issue, ['src/cljam/io/vcf/writer.clj'])
        self.assertIsNotNone(spec)
        self.assertEqual(spec['publicExample'], '5.60878e+09')
        self.assertNotIn('expected', spec)
        self.assertIn('parseable-same?', spec['source'])
        self.assertIn('Double/parseDouble', spec['source'])
        self.assertIn('1.0e20', spec['source'])
        self.assertIn('write-variants', spec['source'])
        self.assertNotIn('PASS_TO_PASS', spec['source'])
        self.assertNotIn('FAIL_TO_PASS', spec['source'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
