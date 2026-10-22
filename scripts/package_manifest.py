"""Record/verify tracked public file bytes, excluding this generated manifest."""
import argparse, hashlib, json, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
TARGET=ROOT/'PUBLIC_MANIFEST.json'

def current():
    names=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode('utf-8').split('\0')
    return [{'path':n,'bytes':(ROOT/n).stat().st_size,'sha256':hashlib.sha256((ROOT/n).read_bytes()).hexdigest()}
            for n in sorted(names) if n and n!='PUBLIC_MANIFEST.json']

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');args=p.parse_args()
    records=current()
    if args.verify:
        expected=json.loads(TARGET.read_text(encoding='utf-8'))['files']
        if expected!=records:raise SystemExit('Public manifest differs from current tracked files')
        print('Public manifest PASS',len(records))
    else:
        TARGET.write_text(json.dumps({'scope':'tracked public files; excludes manifest itself and private/local artifacts','files':records},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print('Public manifest written',len(records))
