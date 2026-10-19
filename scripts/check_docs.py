"""Check that relative Markdown links/images point to existing repository files."""
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

root = Path(__file__).resolve().parent.parent
files = [p for p in root.glob('*.md')]
files += list((root / 'docs').rglob('*.md'))
files += list((root / '.github').rglob('*.md'))
errors = []
count = 0
for path in files:
    source = re.sub(r'```.*?```', '', path.read_text(encoding='utf-8'), flags=re.S)
    for match in re.finditer(r'!?\[[^\]]*\]\(([^)]+)\)', source):
        target = match.group(1).split(' "', 1)[0].strip('<>')
        parsed = urlsplit(target)
        if parsed.scheme or parsed.netloc or not parsed.path:
            continue
        count += 1
        resolved = (path.parent / unquote(parsed.path)).resolve()
        if not resolved.is_relative_to(root) or not resolved.exists():
            errors.append(f'{path.relative_to(root)}: {target}')
if errors:
    raise SystemExit('Broken local documentation links:\n' + '\n'.join(errors))
print(f'Checked {len(files)} Markdown files and {count} relative file/image links: PASS')
