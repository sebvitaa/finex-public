from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_PATHS = [
    "README.md",
    ".env.example",
    ".gitignore",
    ".python-version",
    "package.json",
    "pnpm-workspace.yaml",
    "pyproject.toml",
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
    "tests/test_phase0_structure.py",
]

FORBIDDEN_ENV_MARKERS = [
    "sk-",
    "password=",
    "client_secret=",
    "refresh_token=",
    "access_token=",
]


def main() -> int:
    missing = [path for path in REQUIRED_PATHS if not (ROOT / path).exists()]
    env_text = (ROOT / ".env.example").read_text(encoding="utf-8").lower()
    forbidden = [marker for marker in FORBIDDEN_ENV_MARKERS if marker in env_text]

    if missing:
        print("Faltan rutas requeridas:")
        for path in missing:
            print(f"- {path}")
        return 1

    if forbidden:
        print(".env.example contiene marcadores sensibles:")
        for marker in forbidden:
            print(f"- {marker}")
        return 1

    print("Fase 0 OK: estructura y privacidad basica verificadas.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
