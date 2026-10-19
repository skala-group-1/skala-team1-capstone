"""테스트는 항상 stub 모드 + 인메모리 Client (04 문서 4장)."""

import os

os.environ.setdefault("USE_STUB", "true")
