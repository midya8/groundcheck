import json
import math
import random
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from groundcheck.audit import audit, load_spec
from groundcheck.check import check_grounding
from groundcheck.textutil import numbers_present, extract_numbers
from tools.build_audits import cases

BASE=[{'id':'a','text':'The build has 43 tests.'},{'id':'b','text':'The launch is on day 40.'}]
def spec(answer='The build has 43 tests [1].',scope='all',**kw):
    return dict(answer=answer,sources=BASE,scope=scope,**kw)

class AuditTests(unittest.TestCase):
    def test_same_claim_wrong_citation(self):
        a=audit(spec('The build has 43 tests [2].'))
        b=audit(spec('The build has 43 tests [2].','cited'))
        self.assertEqual(a['units'][0]['support'],1)
        self.assertEqual(b['units'][0]['support'],0)
        self.assertTrue(a['units'][0]['numbers'][0]['present'])
        self.assertFalse(b['units'][0]['numbers'][0]['present'])
    def test_complete_token_occurrences(self):
        r=audit(spec())
        for src in r['sources']:
            for t in src['tokens']:
                self.assertEqual(src['text'][t['start']:t['end']].lower(),t['token'])
        for u in r['units']:
            self.assertEqual(r['spec']['answer'][u['start']:u['end']],u['raw'])
            for t in u['token_occurrences']:
                self.assertEqual(r['spec']['answer'][t['start']:t['end']].lower(),t['token'])
    def test_source_numbers_all_occurrences(self):
        r=audit({'answer':'43 and 43 [1].','sources':[{'id':'x','text':'43, 43 and 43 tests.'}]})
        self.assertEqual(len(r['units'][0]['numbers']),2)
        self.assertEqual(len(r['units'][0]['numbers'][0]['matches']),3)
    def test_negation_still_not_entailment(self):
        r=audit(spec('The build does not have 43 tests [1].','cited',threshold=.5))
        self.assertTrue(r['units'][0]['supported'])
        self.assertEqual(r['findings'],[])
    def test_scope_does_not_union_documents(self):
        r=audit({'answer':'alpha beta [1][2].','sources':[{'id':'a','text':'alpha'},{'id':'b','text':'beta'}],'scope':'cited'})
        self.assertEqual(r['units'][0]['support'],.5)
    def test_tie_first_even_zero_overlap(self):
        r=audit(spec('quantum [1][2].','cited'))
        self.assertEqual(r['units'][0]['best_source'],0)
    def test_vacuity_visible(self):
        r=audit(spec('The and of [1].','cited'))
        self.assertTrue(r['units'][0]['no_content'])
        self.assertEqual(r['units'][0]['support'],1)
    def test_citation_after_period_separate_unit(self):
        r=audit(spec('The build has 43 tests. [1]','cited'))
        self.assertEqual(len(r['units']),2)
        self.assertEqual(r['units'][0]['citations'],[])
        self.assertTrue(r['units'][1]['no_content'])
    def test_repeated_valid_invalid_markers(self):
        r=audit(spec('The build [1][1][0][9].','cited'))
        self.assertEqual(r['units'][0]['eligible_sources'],[0])
        self.assertEqual(len(r['units'][0]['citations']),4)
        self.assertEqual(sum(f['kind']=='citation_unresolvable' for f in r['findings']),2)
    def test_empty_answer_no_evidence(self):
        r=audit(spec('','cited'));self.assertEqual(r['units'],[]);self.assertEqual(r['mean_support'],1)
    def test_threshold_all_scores(self):
        for threshold in [0,.5,.6,1]:
            r=audit(spec(threshold=threshold))
            for u in r['units']:
                self.assertEqual(u['supported'],u['support']>=threshold)
    def test_numeric_precision_and_infinity(self):
        self.assertFalse(numbers_present('9007199254740993',{'9007199254740992'}))
        self.assertFalse(numbers_present('9'*310,{'8'*310}))
        self.assertTrue(numbers_present('1.570',{'1.57'}))
        self.assertTrue(numbers_present('-0.000',{'0'}))
        self.assertFalse(numbers_present('Infinity',{'Infinity'}))
    def test_numeric_random_fraction_reference(self):
        rng=random.Random(81)
        for _ in range(400):
            a=str(rng.randrange(-10**40,10**40))+'.'+str(rng.randrange(10**8)).zfill(8)
            for b in [a+'0',a[:-1]+str((int(a[-1])+1)%10)]:
                self.assertEqual(numbers_present(a,[b]),Fraction(a)==Fraction(b))
    def test_terminal_period_and_versions(self):
        self.assertEqual(extract_numbers('The count is 40. The ratio is 1.57.'),['40','1.57'])
        self.assertEqual(extract_numbers('3.10.1 and v40 and 40x'),[])
    def test_legacy_mean_not_rounded_before_gate(self):
        r=check_grounding('alpha beta gamma.',[{'id':'x','text':'alpha beta.'}])
        self.assertEqual(r['mean_support'],2/3)
        self.assertLess(r['mean_support'],.66668)
    def test_invalid_thresholds(self):
        for x in [True,math.nan,math.inf,-1,2,'0.6']:
            with self.assertRaises(ValueError):audit(spec(threshold=x))
            with self.assertRaises(ValueError):check_grounding('x',BASE,x)
    def test_strict_spec_and_limits(self):
        for x in [spec(extra=1),spec(answer='é'),spec(answer='x'*4097),spec(answer='[1234567]'),
                  dict(answer='x',sources=[]),dict(answer='x',sources=BASE*2),
                  spec(answer='x\x00'),spec(answer=('x.\n'*65)),spec(answer=('40 '*129))]:
            with self.assertRaises(ValueError):audit(x)
    def test_strict_json(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'s.json'
            for text in ['{"answer":"x","answer":"y"}', '{"threshold":NaN}', 'x'*65537]:
                p.write_text(text)
                with self.assertRaises(ValueError):load_spec(p)
    def test_fixture_exact_regeneration(self):
        expected=json.loads((Path(__file__).resolve().parents[1]/'docs/audit.json').read_text())
        self.assertEqual(expected,{'cases':cases()})
    def test_cli_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'s.json').write_text(json.dumps(spec()))
            r=subprocess.run([sys.executable,'-m','groundcheck','audit','--spec',str(p/'s.json'),'--json',str(p/'out.json')],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)
            self.assertEqual(json.loads((p/'out.json').read_text()),audit(spec()))
    def test_cli_rejects_nan_gate(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'s.jsonl';p.write_text(json.dumps(BASE[0])+'\n')
            for flag,value in [('--min-support','nan'),('--support-threshold','nan'),('--max-findings','-1')]:
                r=subprocess.run([sys.executable,'-m','groundcheck','check','--sources',str(p),'--answer','x',flag,value],capture_output=True,text=True)
                self.assertNotEqual(r.returncode,0)
    def test_exhaustive_fraction_containment(self):
        words=['alpha','beta','gamma','delta','epsilon','zeta']
        for mask in range(64):
            chosen=[w for bit,w in enumerate(words) if mask>>bit&1]
            for threshold in [0,.5,2/3,1]:
                r=audit({'answer':' '.join(words)+' [1].','sources':[{'id':'subset','text':' '.join(chosen)}], 'threshold':threshold,'scope':'cited'})
                row=r['units'][0]
                self.assertEqual(Fraction(row['source_scores'][0]['numerator'],row['source_scores'][0]['denominator']),Fraction(len(chosen),6))
                self.assertEqual(row['support'],len(chosen)/6)
                self.assertEqual(row['supported'],Fraction(len(chosen),6)>=Fraction(threshold))
    def test_cli_unrounded_mean_gate(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'s.jsonl';p.write_text('{"id":"x","text":"alpha beta."}\n')
            r=subprocess.run([sys.executable,'-m','groundcheck','check','--sources',str(p),'--answer','alpha beta gamma.','--min-support','.66668'],capture_output=True,text=True)
            self.assertEqual(r.returncode,1,r.stderr)
