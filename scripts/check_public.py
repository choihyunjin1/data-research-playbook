"""Bounded public-package checks; not a security audit or license certification."""
from pathlib import Path
import json, re, subprocess, sys

ROOT=Path(__file__).resolve().parents[1]
EXCLUDE={'.git','.venv','.runs','__pycache__','build','dist','.pytest_cache'}
DENIED={'.nc','.zip','.pkl','.pickle','.joblib','.pt','.pth','.pdf','.log'}
TEXT={'.py','.md','.json','.csv','.txt','.toml','.yml','.yaml','.cff','.html','.mjs'}

def check():
    errors=[]; examined=0
    for p in ROOT.rglob('*'):
        if not p.is_file() or any(part in EXCLUDE or part.endswith('.egg-info') for part in p.relative_to(ROOT).parts):continue
        rel=p.relative_to(ROOT).as_posix(); examined+=1
        if p.suffix.lower() in DENIED:errors.append([rel,'disallowed artifact type'])
        if p.stat().st_size>10*1024*1024:errors.append([rel,'unexpected file over 10 MiB'])
        if p.suffix not in TEXT:continue
        text=p.read_text(encoding='utf-8-sig')
        if re.search(r'[A-Za-z]:[/\\](?:Users|home)[/\\]',text):errors.append([rel,'personal absolute path'])
        if re.search(r'gh[pousr]_[A-Za-z0-9]{30,}|AKIA[A-Z0-9]{16}|-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----',text):errors.append([rel,'recognizable credential'])
        if re.search(r'https?://[^\s"<>]+[?&](?:access_token|token|signature|X-Amz-Signature)=',text,re.I):errors.append([rel,'credential-like URL'])
        if p.suffix=='.md':
            # Simple local document links; anchors and external destinations excluded.
            for match in re.finditer(r'(?<!!)\[[^\]\n]+\]\(([^)]+)\)',text):
                link=match.group(1).strip('<>').split('#')[0]
                if not link or '://' in link or link.startswith('mailto:'):continue
                if not (p.parent/link).exists():errors.append([rel,'missing local link: '+link])
    return {'scope':'readable source/package patterns and local Markdown links only','files_examined':examined,'errors':errors,'status':'PASS' if not errors else 'FAIL'}

if __name__=='__main__':
    result=check(); print(json.dumps(result,ensure_ascii=False,indent=2))
    sys.exit(bool(result['errors']))
