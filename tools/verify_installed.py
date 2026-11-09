import importlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

fixture, root = map(Path,sys.argv[1:])
root=root.resolve()
modules=['groundcheck','groundcheck.__main__','groundcheck.check','groundcheck.cli','groundcheck.report','groundcheck.sources','groundcheck.textutil','groundcheck.audit']
# __main__ invokes argparse on import, so inspect its module spec instead.
import importlib.util
for name in modules:
    origin=Path(importlib.util.find_spec(name).origin).resolve()
    assert root not in origin.parents,(name,origin)
    print(name,origin)
from groundcheck.audit import audit
cases=json.loads(fixture.read_text())['cases']
for case in cases:
    assert audit(case['report']['spec'])==case['report']
with tempfile.TemporaryDirectory() as d:
    out=Path(d)/'audit.json'
    subprocess.run([sys.executable,'-m','groundcheck','audit','--spec',str(root/'examples/audit.json'),'--json',str(out)],check=True)
    assert json.loads(out.read_text())==audit(json.loads((root/'examples/audit.json').read_text()))
    subprocess.run([sys.executable,'-m','groundcheck','check','--sources',str(root/'examples/data/sources.jsonl'),'--answer-file',str(root/'examples/data/answer_grounded.txt'),'--min-support','.8','--max-unsupported','0','--max-findings','0'],check=True)
print('Installed wheel: eight module origins, 50 full audits, audit CLI and original gated CLI pass')
