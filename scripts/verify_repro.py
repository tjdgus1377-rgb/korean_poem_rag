"""키 없이 저장소 기준 자료를 확인한다. --write는 검토한 변경 때만 사용한다."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sidam.repro import build_manifest, verify_manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='비밀정보 없이 시담 재현 기준을 검사합니다.')
    parser.add_argument('--write', action='store_true', help='검토한 입력의 새 기준을 명시적으로 기록합니다.')
    args = parser.parse_args()
    try:
        if args.write:
            report = build_manifest(ROOT)
            path = ROOT / 'data/repro/manifest.json'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        else:
            report = verify_manifest(ROOT)
        print('재현 기준 ' + ('작성' if args.write else '검증') + ' 완료: ' + json.dumps(report['counts'], ensure_ascii=False))
    except (ValueError, OSError, KeyError) as error:
        print('재현 검사 실패: ' + str(error), file=sys.stderr)
        raise SystemExit(1)
