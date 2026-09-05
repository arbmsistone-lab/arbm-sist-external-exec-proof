import ast
import json
import re
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


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
    def test_sovereign_receives_separate_public_failures_and_rejected_candidate(self):
        compact_issue=load_function('_compact_public_issue',{})
        compact_output=load_function('_compact_public_validation_output',{'re':re})
        requests=[]
        class Response:
            def __enter__(self): return self
            def __exit__(self,*args): pass
            def read(self): return json.dumps({'choices':[{'message':{'content':'{"edits":[]}'}}]}).encode()
        def request(url,data,method):
            return SimpleNamespace(data=data,add_header=lambda *args:None)
        def urlopen(req,timeout):
            requests.append(json.loads(req.data))
            return Response()
        sovereign=load_function('_sovereign_json',{
            'json':json,'re':re,'os':SimpleNamespace(environ={'ARBM_SOVEREIGN_ENDPOINT':'http://synthetic.invalid'}),
            'urllib':SimpleNamespace(request=SimpleNamespace(Request=request,urlopen=urlopen)),
            '_compact_public_issue':compact_issue,'_compact_public_context':lambda *args:'FILE: src/example.py\n000001|public_source()',
            '_compact_public_validation_output':compact_output,
        })
        rejected=[{'path':'src/example.py','start_line':1,'end_line':1,'new':'rejected_behavior()'}]
        feedback=('FAIL in (ordinary-public-contract)\nexpected: preserved formatting\nactual: changed formatting\n'
                  +'stack frame\n'*400+'ERROR in (public-edge-case)\nexpected: numeric behavior\nactual: NumberFormatException: NaN\n')
        code,_,_,_=sovereign({'phase':'solve','issue':'public issue '+('public contract '*300)+'\n\nPUBLIC REPOSITORY VALIDATION FAILED\nPUBLIC CAUSAL LINE HINT obsolete focus',
                             'public_validation_feedback':feedback,'rejected_edits':rejected})
        self.assertEqual(code,0)
        prompt=requests[0]['messages'][-1]['content']
        for text in ('REJECTED CANDIDATE','rejected_behavior()','PUBLIC VALIDATION FAILURES','preserved formatting','NumberFormatException: NaN','complete candidate against the original numbered source'):
            self.assertIn(text,prompt)
        self.assertNotIn('obsolete focus',prompt)
        self.assertEqual(requests[0]['max_tokens'],224)

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

    def test_issue_compaction_prioritizes_public_causal_line_hint(self):
        compact = load_function('_compact_public_issue', {})
        raw = ('PUBLIC ISSUE: QUAL overflow while writing VCF ' + ('public contract ' * 200)
               + '\n\nPUBLIC INVARIANT REJECTION: preserve control flow ' + ('detail ' * 150)
               + '\nPUBLIC CAUSAL LINE HINT derived only from the public repository: '
               + '{"path":"src/cljam/io/vcf/writer.clj","line":192,"source":"(str (int x))"}. '
               + 'MANDATORY: prefer start_line=end_line and preserve surrounding when/if.')
        result = compact(raw, 900)
        self.assertIn('PUBLIC CAUSAL LINE HINT', result)
        self.assertIn('writer.clj', result)
        self.assertIn('(str (int x))', result)
        self.assertIn('start_line=end_line', result)

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


    def test_public_causal_hint_targets_only_fixed_width_line(self):
        hints_fn = load_function('public_causal_fixed_width_hints', {'Path': Path, 're': re})
        with tempfile.TemporaryDirectory() as repo:
            target = Path(repo, 'src/cljam/io/vcf/writer.clj')
            target.parent.mkdir(parents=True)
            target.write_text('  (when x\n    (if (zero? (mod x 1))\n      (str (int x))\n      (str x))))\n', encoding='utf-8')
            hints = hints_fn(repo, [{'path':'src/cljam/io/vcf/writer.clj','start_line':1,'end_line':4,'new':'(str x)'}])
        self.assertEqual(hints, [{'path':'src/cljam/io/vcf/writer.clj','line':3,'source':'(str (int x))'}])


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
        self.assertIn('(Math/rint (double x))', edits[0]['new'])
        self.assertIn('(format "%.0f" (double x))', edits[0]['new'])
        self.assertNotIn('(mod x 1)', edits[0]['new'])
        self.assertNotIn('(int x)', edits[0]['new'])
        self.assertNotIn('(bigint x)', edits[0]['new'])
        self.assertEqual(
            edits[0]['new'],
            '    (if (== (double x) (Math/rint (double x)))\n      (format "%.0f" (double x))\n      (str x))))',
        )


    def test_public_validation_compaction_keeps_public_failure_signal(self):
        compact = load_function('_compact_public_validation_output', {'re': re})
        raw = ('stack frame\n' * 400
               + 'ERROR in (qual-overflow-public-contract)\n'
               + 'expected: parseable-same?\n'
               + 'actual: java.lang.NumberFormatException: Infinite or NaN\n'
               + ('more stack\n' * 400))
        result = compact(raw, 500)
        self.assertLessEqual(len(result), 500)
        self.assertIn('ERROR in (qual-overflow-public-contract)', result)
        self.assertIn('NumberFormatException', result)
        self.assertIn('NaN', result)

    def test_followup_public_repair_is_bounded_and_public_only(self):
        source = SCRIPT.read_text(encoding='utf-8')
        self.assertIn('PUBLIC REPOSITORY VALIDATION FAILED AFTER FIRST PUBLIC REPAIR', source)
        self.assertIn('PUBLIC VALIDATION OUTPUT SUMMARY (public tests only)', source)
        self.assertIn("rec['publicValidationRepair']=frec", source)
        self.assertIn("if applied>0 and not errs and attempted and vcode!=0:", source)


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
        self.assertNotIn('Double/POSITIVE_INFINITY', spec['source'])
        self.assertNotIn('Double/NaN', spec['source'])
        self.assertNotIn('PASS_TO_PASS', spec['source'])
        self.assertNotIn('FAIL_TO_PASS', spec['source'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
