"""공유 대상 파일을 검사하되 발견한 비밀값 자체는 출력하지 않는다."""
import re
from pathlib import Path


def check_paths(root, paths, private_values=()):
    root = Path(root)
    errors = []
    for name in paths:
        normalized = name.replace('\\', '/')
        path = Path(normalized)
        forbidden = (normalized.startswith(('.sidam/', '.venv/', 'tmp/', 'data/cache/')) or
                     path.name == '.env' or (path.name.startswith('.env.') and path.name != '.env.example') or
                     path.suffix.lower() in {'.sqlite', '.sqlite3', '.db', '.pem', '.key', '.p12'})
        if forbidden:
            errors.append(f'{normalized}: 배포 제외 파일')
            continue
        try:
            text = (root / path).read_text(encoding='utf-8-sig')
        except (UnicodeDecodeError, OSError):
            continue
        if any(value and len(value) >= 6 and value in text for value in private_values):
            errors.append(f'{normalized}: 현재 개인 설정값 포함')
        if re.search(r'sk-[A-Za-z0-9_-]{24,}', text) or re.search(r'[A-Za-z]:[\\/]Users[\\/][^\s/\\]+', text):
            errors.append(f'{normalized}: 인증값 형태 또는 개인 절대 경로 포함')
        if path.name == '.env.example':
            from dotenv import dotenv_values
            values = dotenv_values(root / path)
            if values.get('GMS_KEY') or values.get('WIKI_CONTACT'):
                errors.append(f'{normalized}: 예제에 개인 키·연락처 포함')
    return errors
