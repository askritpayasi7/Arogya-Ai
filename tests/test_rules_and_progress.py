from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

def test_rules_file_exists():
    rules_path = REPO_ROOT / "rules.md"
    assert rules_path.exists(), "rules.md must exist in the root of the repository."
    content = rules_path.read_text(encoding="utf-8")
    assert "progress.md" in content, "rules.md must explicitly mandate progress.md maintenance."
    assert "Rule 1" in content or "rule" in content.lower(), "rules.md must define operational rules."


def test_progress_file_exists():
    progress_path = REPO_ROOT / "progress.md"
    assert progress_path.exists(), "progress.md must exist in the root of the repository."
    content = progress_path.read_text(encoding="utf-8")
    assert "Changelog" in content or "Roadmap" in content, "progress.md must include milestone/changelog sections."
    assert "Next Steps" in content or "Immediate Next Steps" in content, "progress.md must document next steps."
