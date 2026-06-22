from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_PATHS = [
    "README.md",
    ".env.example",
    "docs/privacy.md",
    "docs/architecture.md",
    "docs/security-checklist.md",
    "backend/app/api",
    "backend/app/core",
    "backend/app/db",
    "backend/app/models",
    "backend/app/schemas",
    "backend/app/services",
    "frontend/src",
    "frontend/public",
    "data/demo",
    "data/imports",
    "data/local",
]


def test_phase0_required_paths_exist() -> None:
    missing = [path for path in REQUIRED_PATHS if not (ROOT / path).exists()]
    assert missing == []


def test_env_example_has_no_real_secret_markers() -> None:
    env_text = (ROOT / ".env.example").read_text(encoding="utf-8").lower()
    forbidden_markers = [
        "sk-",
        "password=",
        "client_secret=",
        "refresh_token=",
        "access_token=",
    ]

    matches = [marker for marker in forbidden_markers if marker in env_text]
    assert matches == []
