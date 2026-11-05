import json
from pathlib import Path
import pytest

from health_app.fetcher.registry import PaperRegistry, PaperRecord
from health_app.fetcher.client import CandidatePaper, PaperSearchClient
from health_app.fetcher.downloader import PDFDownloader

@pytest.fixture
def temp_registry(tmp_path):
    index_file = tmp_path / "test_index.json"
    return PaperRegistry(index_path=index_file)


def test_registry_registration_and_deduplication(temp_registry):
    assert temp_registry.get_counts()["total"] == 0

    # Register first paper
    record = temp_registry.register(
        paper_id="pmc_123456",
        title="Impact of Curcumin on Lipid Profiles",
        status="kept",
        authors="Dr. Sharma et al.",
        year="2023",
        journal="Journal of Nutritional Biochemistry",
        doi="10.1016/j.jnutbio.2023.01",
        pmcid="PMC123456",
        abstract="Curcumin significantly lowered LDL and total cholesterol.",
        pdf_url="https://example.com/curcumin.pdf",
        pdf_path="data/research_papers/2023_Sharma_Curcumin.pdf"
    )

    assert record.paper_id == "pmc_123456"
    assert temp_registry.get_counts()["kept"] == 1
    assert temp_registry.get_counts()["discarded"] == 0
    assert temp_registry.get_counts()["total"] == 1

    # Check deduplication queries
    assert temp_registry.is_indexed(paper_id="pmc_123456")
    assert temp_registry.is_indexed(doi="10.1016/j.jnutbio.2023.01")
    assert temp_registry.is_indexed(pmcid="PMC123456")
    assert temp_registry.is_indexed(title="Impact of Curcumin on Lipid Profiles")
    # Normalized title matching (case and punctuation insensitive)
    assert temp_registry.is_indexed(title="impact of curcumin on lipid profiles.")

    # Unindexed queries should return False
    assert not temp_registry.is_indexed(paper_id="unknown_999")
    assert not temp_registry.is_indexed(title="Completely Unrelated Paper")

    # Register discarded paper
    temp_registry.register(
        paper_id="pmc_999999",
        title="Unrelated Botany Study",
        status="discarded",
        authors="Smith J.",
        year="2020",
    )
    counts = temp_registry.get_counts()
    assert counts["kept"] == 1
    assert counts["discarded"] == 1
    assert counts["total"] == 2

    # Verify reload from disk
    reloaded_registry = PaperRegistry(index_path=temp_registry.index_path)
    assert reloaded_registry.is_indexed(paper_id="pmc_123456")
    assert reloaded_registry.is_indexed(paper_id="pmc_999999")
    assert len(reloaded_registry.list_kept_papers()) == 1


def test_pdf_downloader_filename_sanitizer():
    downloader = PDFDownloader()
    raw_name = "What is Safe?: Evaluating FSSAI/ICMR <Rules> & |Limits| *2023*."
    sanitized = downloader._sanitize_filename(raw_name)
    assert ":" not in sanitized
    assert "<" not in sanitized
    assert ">" not in sanitized
    assert "|" not in sanitized
    assert "*" not in sanitized
    assert "/" not in sanitized
    assert "\\" not in sanitized


def test_pdf_downloader_mock_download(tmp_path, monkeypatch):
    target_dir = tmp_path / "papers"
    downloader = PDFDownloader(target_dir=target_dir)

    class MockResponse:
        status_code = 200
        def iter_content(self, chunk_size=8192):
            # Yield fake PDF header and content > 1024 bytes
            yield b"%PDF-1.4\n" + (b"0" * 2000)

    monkeypatch.setattr(downloader.session, "get", lambda *args, **kwargs: MockResponse())

    success, path, msg = downloader.download(
        pdf_url="https://example.com/fake.pdf",
        title="Test Scientific Paper",
        authors="Tester A.",
        year="2024",
        doi="10.1234/test",
        abstract="Test abstract content."
    )

    assert success
    assert path is not None
    assert path.exists()
    assert path.suffix == ".pdf"
    # Check companion markdown
    md_path = path.with_suffix(".md")
    assert md_path.exists()
    content = md_path.read_text(encoding="utf-8")
    assert "Test Scientific Paper" in content
    assert "Test abstract content." in content


def test_repair_missing_pdfs(tmp_path, monkeypatch):
    from health_app.fetcher.recovery import repair_missing_pdfs
    
    index_file = tmp_path / "index.json"
    papers_dir = tmp_path / "papers"
    papers_dir.mkdir()

    registry = PaperRegistry(index_path=index_file)
    # Register one paper with missing pdf
    registry.register(
        paper_id="missing_1",
        title="Missing Paper Title",
        status="kept",
        authors="Author A",
        year="2023",
        pdf_url="https://example.com/missing.pdf",
        pdf_path=None
    )

    class MockDownloadSuccess:
        status_code = 200
        def iter_content(self, chunk_size=8192):
            yield b"%PDF-1.4\n" + (b"x" * 2000)

    # Mock requests.Session.get inside downloader
    import requests
    monkeypatch.setattr(requests.Session, "get", lambda *args, **kwargs: MockDownloadSuccess())

    result = repair_missing_pdfs(index_path=index_file, target_dir=papers_dir)
    assert result["total_missing"] == 1
    assert result["recovered"] == 1
    assert result["failed"] == 0

    # Verify that registry now has valid pdf_path
    updated_registry = PaperRegistry(index_path=index_file)
    record = updated_registry.records["missing_1"]
    assert record.pdf_path is not None
    assert Path(record.pdf_path).exists()


def test_downloader_url_variants_europe_pmc():
    downloader = PDFDownloader()
    # Test Europe PMC web viewer URL conversion to direct PMC and NCBI mirrors
    web_url = "https://europepmc.org/articles/PMC13577035?pdf=render"
    variants = downloader._get_url_variants(web_url)
    assert any("https://europepmc.org/api/getPdf?pmcid=PMC13577035" in v for v in variants)
    assert any("https://pmc.ncbi.nlm.nih.gov/articles/PMC13577035/pdf/" in v for v in variants)
    assert any("https://www.ncbi.nlm.nih.gov/pmc/articles/PMC13577035/pdf/" in v for v in variants)

    # Test arXiv URL conversion
    arxiv_url = "https://arxiv.org/pdf/2102.13284v4.pdf"
    arxiv_variants = downloader._get_url_variants(arxiv_url)
    assert any("export.arxiv.org" in v for v in arxiv_variants)


def test_downloader_progress_bar_render(capsys):
    downloader = PDFDownloader()
    # Test known content length
    downloader._render_progress_bar(downloaded=500000, total=1000000)
    captured = capsys.readouterr()
    assert "50.0%" in captured.out
    assert "488 KB / 977 KB" in captured.out

    # Test streaming / unknown length
    downloader._render_progress_bar(downloaded=250000, total=None)
    captured = capsys.readouterr()
    assert "Streaming" in captured.out

