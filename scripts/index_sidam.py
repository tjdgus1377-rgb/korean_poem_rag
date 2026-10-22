"""기존 자료를 검증하고 시담 검색 색인을 준비한다."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sidam.config import Config
from sidam.service import Service


if __name__ == "__main__":
    service = Service(Config.load(ROOT))
    print(json.dumps(service.index(), ensure_ascii=False))
