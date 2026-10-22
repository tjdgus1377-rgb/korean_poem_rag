"""Git 추적 파일에 로컬 비밀·캐시가 섞였는지 확인한다."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import dotenv_values
from sidam.release import check_paths


if __name__ == '__main__':
    paths = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode('utf-8').split('\0')
    private = dotenv_values(ROOT / '.env') if (ROOT / '.env').exists() else {}
    errors = check_paths(ROOT, [p for p in paths if p], [private.get('GMS_KEY'), private.get('WIKI_CONTACT')])
    if errors:
        print('\n'.join(errors), file=sys.stderr)
        raise SystemExit(1)
    print('배포 검사 완료: 개인 설정값·금지 파일 발견 0건')
