"""Synthetic, deterministic controls. Not a factuality benchmark."""
import json
from pathlib import Path
from groundcheck.audit import audit
BASE = [{"id":"build", "text":"The build contains 43 unit tests. The parser supports JSON input."},
        {"id":"launch", "text":"The launch is on day 40. The report lists 12 checks."}]
def cases():
    examples = [
      ('Resolved evidence', 'The build contains 43 unit tests [1].', BASE),
      ('Wrong citation, same claim', 'The build contains 43 unit tests [2].', BASE),
      ('Negation survives overlap', 'The build does not contain 43 unit tests [1].', BASE),
      ('Missing citation', 'The build contains 43 unit tests.', BASE),
      ('Unresolvable marker', 'The build contains 43 unit tests [9].', BASE),
      ('Repeated citation', 'The build contains 43 unit tests [1][1].', BASE),
      ('Citation after punctuation', 'The build contains 43 unit tests. [1]', BASE),
      ('Multiple markers', 'The build contains 43 unit tests [1][2].', BASE),
      ('Wrong entity, same number', 'The report contains 43 unit tests [1].', BASE),
      ('Coincidental global number', 'The build contains 40 unit tests [1].', BASE),
      ('Decimal equivalence', 'The ratio is 1.570 [1].', [{'id':'ratio','text':'The ratio is 1.57.'}]),
      ('Integer precision boundary', 'The count is 9007199254740993 [1].', [{'id':'large','text':'The count is 9007199254740992.'}]),
      ('Comma literals', 'The count is 1,000 [1].', [{'id':'comma','text':'The count is 1000.'}]),
      ('Malformed comma retained', 'The count is 1,,000 [1].', [{'id':'comma','text':'The count is 1000.'}]),
      ('Vacuous content', 'The and of [1].', BASE),
      ('True paraphrase, low overlap', 'Forty-three automated verifications succeed [1].', BASE),
      ('Document combination', 'The build contains tests and supports JSON input [1].', BASE),
      ('Split across documents', 'Alpha beta gamma delta [1][2].', [{'id':'a','text':'Alpha beta.'},{'id':'b','text':'Gamma delta.'}]),
      ('Tie resolves first', 'Alpha beta [1][2].', [{'id':'a','text':'Alpha.'},{'id':'b','text':'Beta.'}]),
      ('Negative zero', 'The count is -0.00 [1].', [{'id':'z','text':'The count is 0.'}]),
      ('Empty answer', '', BASE),
      ('Line boundaries', 'The build contains 43 unit tests [1]\nThe launch is on day 40 [2]', BASE),
      ('Escaping is data', '<img src=x onerror=alert(1)> [1].', [{'id':'html','text':'<img src=x onerror=alert(1)>'}]),
      ('Version not numeric literal', 'The runtime is 3.10.1 [1].', [{'id':'v','text':'The runtime is 3.10.1.'}]),
      ('Infinity alias prevented', 'The count is '+ '9'*310 +' [1].', [{'id':'huge','text':'The count is '+'8'*310+'.'}]),
    ]
    out=[]
    for title, answer, sources in examples:
        for scope in ('all','cited'):
            spec=dict(answer=answer,sources=sources,scope=scope,threshold=.6)
            out.append({'title':title+' / '+scope,'report':audit(spec)})
    return out
if __name__ == '__main__':
    target=Path(__file__).resolve().parents[1]/'docs/audit.json'
    target.write_text(json.dumps({'cases':cases()},indent=1,allow_nan=False)+'\n',encoding='utf-8')
