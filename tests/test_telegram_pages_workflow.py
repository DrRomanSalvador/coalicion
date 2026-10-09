from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_telegram_pages_deploy_fails_fast_without_enablement_permission():
    source = (ROOT / ".github" / "workflows" / "telegram_miniapp.yml").read_text(encoding="utf-8")
    assert "Preflight GitHub Pages configuration" in source
    assert "secrets.PAGES_ADMIN_TOKEN" in source
    assert "secrets.PAGES_ADMIN_TOKEN || github.token" in source
    assert "GITHUB_TOKEN cannot create the Pages site" in source
    assert "enablement: true" in source
    assert "pages: write" in source
    assert "id-token: write" in source
