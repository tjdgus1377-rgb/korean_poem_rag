"""기존 자료를 검증하고 시담 검색 색인을 준비한다."""
import json
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sidam.config import Config
from sidam.service import Service


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='시담 검색 색인을 준비합니다.')
    parser.add_argument('--baseline', action='store_true', help='가변 캐시를 제외한 저장소 재현 기준으로 색인하고 검증합니다.')
    args = parser.parse_args()
    config = Config.load(ROOT)
    manifest = None
    if args.baseline:
        from sidam.repro import verify_manifest, verify_settings, verify_index
        manifest = verify_manifest(ROOT)
        verify_settings(config, manifest)
    service = Service(config)
    result = service.index(include_cache=not args.baseline)
    if manifest:
        verify_index(service.store, manifest)
        result['baseline_verified'] = True
    print(json.dumps(result, ensure_ascii=False))
