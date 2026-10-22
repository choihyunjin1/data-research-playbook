"""Run repository unit tests and retain a compact, path-safe execution receipt."""
import argparse, hashlib, importlib.metadata, io, json, platform, unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
    log=io.StringIO();result=unittest.TextTestRunner(stream=log,verbosity=2).run(suite)
    versions={}
    for name in ['numpy','pandas','netCDF4']:
        try:versions[name]=importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:versions[name]=None
    hashes={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
        for folder in ['src','tests'] for p in sorted((ROOT/folder).rglob('*.py'))}
    receipt={'at_utc':datetime.now(timezone.utc).isoformat(),'status':'PASS' if result.wasSuccessful() else 'FAIL',
        'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),
        'python':platform.python_version(),'platform':platform.system(),'dependencies':versions,'source_sha256':hashes,
        'test_log':log.getvalue(),'scope':'synthetic and packaged contract checks; no full raw replay or new learning implied'}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
    print(log.getvalue());raise SystemExit(not result.wasSuccessful())

if __name__=='__main__':main()
