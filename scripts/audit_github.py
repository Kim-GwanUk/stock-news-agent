"""Inspect Git candidates without printing secrets or modifying application data."""
import json
import re
import subprocess
from pathlib import Path
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)

def main():
    paths = sorted(set(p.decode('utf-8') for p in
        git('ls-files', '-z', '--cached', '--others', '--exclude-standard').split(b'\0') if p))
    secrets = {key: value for key, value in dotenv_values(ROOT / '.env.local').items()
               if value and len(value) >= 8 and any(x in key.upper() for x in ('KEY', 'SECRET', 'TOKEN', 'PASSWORD', 'CLIENT_ID'))}
    findings, review, url_exceptions = [], [], []
    patterns = {
        'private_key': rb'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
        'openai_key': rb'\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{32,}',
        'github_token': rb'\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})',
        'aws_access_key': rb'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b',
        'credential_in_url': rb'https?://[^\s/:]+:[^\s/@]+@',
    }
    for name in paths:
        file = ROOT / name
        if not file.is_file():
            continue
        data = file.read_bytes()
        if file.name.startswith('.env') and file.name != '.env.example':
            findings.append({'file': name, 'rule': 'environment_file'})
        for key, value in secrets.items():
            if value.encode() in data:
                findings.append({'file': name, 'rule': 'matches_local_credential', 'variable': key})
        for rule, pattern in patterns.items():
            scanned = data
            if rule == 'openai_key':
                # Reviewed official SK article slugs resemble the legacy sk- token prefix.
                scanned, count = re.subn(rb'https://(?:eng\.sk\.com/news|news\.skhynix\.com/en)/sk-(?:hynix|siltron)-[a-z0-9-]+/?', b'[official-article-url]', data)
                if count:
                    url_exceptions.append({'file': name, 'count': count})
            if re.search(pattern, scanned):
                findings.append({'file': name, 'rule': rule})
        if re.search(rb'[A-Za-z]:[\\/]+Users[\\/]+[^\s\\/]+', data):
            review.append({'file': name, 'reason': 'personal_absolute_path'})
        if b'\x00' in data or file.suffix.lower() in ('.png', '.jpg', '.pdf', '.pptx', '.docx', '.zip'):
            review.append({'file': name, 'reason': 'binary_or_media_manual_review'})
        if re.search(rb'(?i)[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|\b01[016789][- ]?\d{3,4}[- ]?\d{4}\b', data):
            review.append({'file': name, 'reason': 'contact_pattern_review'})
    probes = ['.env.local', 'data/app.sqlite', 'output/before-market-verification.sqlite',
              'tmp/probe.log', '.streamlit/secrets.toml', '.env.example']
    ignores = {p: subprocess.run(['git', 'check-ignore', '-q', p], cwd=ROOT).returncode == 0 for p in probes}
    result = {'candidate_count': len(paths), 'credential_variables_checked': sorted(secrets),
              'findings': findings, 'manual_review': review, 'ignore_checks': ignores,
              'official_article_url_exceptions': url_exceptions,
              'candidate_files': paths,
              'limitations': 'Checks working files, not historical commits or OCR. Review staged diff before push.'}
    out = ROOT / 'output'
    out.mkdir(exist_ok=True)
    (out / 'github-readiness-audit.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k != 'candidate_files'}, ensure_ascii=False, indent=2))
    return 1 if findings or not all(ignores[p] for p in probes[:-1]) or ignores['.env.example'] else 0

if __name__ == '__main__':
    raise SystemExit(main())
