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
                'new': '      (str (bigint x))',
            }]
            issue = 'QUAL value overflows when writing VCF; huge values exceed Integer range'
            bad_errors = guard(repo, bad, issue)
            good_errors = guard(repo, good, issue)
        self.assertTrue(any('fixed_width_conversion_retained' in e for e in bad_errors))
        self.assertTrue(any('control_flow_removed:when' in e for e in bad_errors))
        self.assertEqual(good_errors, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
