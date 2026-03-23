from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from agentic_researcher.discovery import load_fixture_candidates
from agentic_researcher.fulltext import find_matching_pdf
from agentic_researcher.history import build_history_snapshot, check_duplicate, history_record_from_paper, load_workspace_history
from agentic_researcher.models import DedupeIndex
from agentic_researcher.normalize import normalize_doi, normalize_title
from agentic_researcher.query_expansion import expand_query_for_is
from agentic_researcher.scoring import heuristic_score_papers
from watch_zotero_pdf import infer_dates_from_paths


class AgenticResearcherTests(unittest.TestCase):
    def test_normalization(self) -> None:
        self.assertEqual(normalize_doi("https://doi.org/10.1000/XYZ "), "10.1000/xyz")
        self.assertEqual(normalize_title("Agentic AI: Banking Survey!"), "agentic ai banking survey")

    def test_fixture_loading_filters_whitelisted_venues(self) -> None:
        papers = load_fixture_candidates(
            ROOT / "data" / "fixtures" / "discovery_seed.json",
            ["MIS Quarterly", "Information Systems Research"],
        )
        self.assertTrue(papers)
        self.assertTrue(all(paper.venue in {"MIS Quarterly", "Information Systems Research"} for paper in papers))

    def test_query_expansion_for_is_templates(self) -> None:
        variants = expand_query_for_is("agentic ai information systems")
        self.assertIn("agentic ai information systems", variants)
        self.assertTrue(any("information systems" in item.lower() for item in variants))
        self.assertTrue(any("decision support systems" in item.lower() for item in variants))
        self.assertLessEqual(len(variants), 8)

    def test_workspace_history_dedup(self) -> None:
        papers = load_fixture_candidates(ROOT / "data" / "fixtures" / "discovery_seed.json", ["MIS Quarterly"])
        target = next(paper for paper in papers if paper.doi == "10.1000/example-001")
        snapshot = build_history_snapshot([history_record_from_paper(target, status="confirmed")])
        is_duplicate, reason = check_duplicate(
            target,
            DedupeIndex(count=snapshot.count, doi_index=snapshot.doi_index, title_index=snapshot.title_index),
        )
        self.assertTrue(is_duplicate)
        self.assertIn("Duplicate DOI", reason)

    def test_load_workspace_history_from_previous_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            (temp_root / "03_state/confirmed").mkdir(parents=True, exist_ok=True)
            config = json.loads((ROOT / "config/agentic_researcher.json").read_text(encoding="utf-8"))
            config["workspace_root"] = tempdir

            papers = load_fixture_candidates(ROOT / "data" / "fixtures" / "discovery_seed.json", ["MIS Quarterly"])
            bundle = {
                "query": "agentic ai",
                "date": "2026-03-21",
                "papers": [papers[0].to_dict()],
            }
            (temp_root / "03_state/confirmed/2026-03-21.json").write_text(
                json.dumps(bundle, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            history = load_workspace_history(config)
            is_duplicate, _ = check_duplicate(papers[0], history)
            self.assertTrue(is_duplicate)

    def test_heuristic_scoring_generates_recommendation(self) -> None:
        papers = load_fixture_candidates(ROOT / "data" / "fixtures" / "discovery_seed.json", ["MIS Quarterly"])
        scored = heuristic_score_papers(papers, "agentic ai information systems")
        self.assertGreaterEqual(scored[0].score or 0, scored[-1].score or 0)
        self.assertTrue(scored[0].recommendation_reason)
        self.assertTrue(scored[0].summary_zh)
        self.assertTrue(scored[0].research_suggestion_zh)
        self.assertTrue(scored[0].business_application_zh)

    def test_find_matching_pdf_by_filename(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            pdf_dir = temp_root / "agentic_ai_all" / "2026-3-23"
            pdf_dir.mkdir(parents=True, exist_ok=True)
            matched = pdf_dir / "Baird和Maruping - 2021 - The Next Generation of Research on IS Use A Theoretical Framework of Delegation.pdf"
            matched.write_bytes(b"%PDF-1.4\n%fake\n")
            other = pdf_dir / "Unrelated - 2020 - Another Paper.pdf"
            other.write_bytes(b"%PDF-1.4\n%fake\n")

            from agentic_researcher.models import PaperRecord

            target = PaperRecord(
                id="paper-1",
                title="The Next Generation of Research on IS Use: A Theoretical Framework of Delegation to and from Agentic IS Artifacts",
                authors=["Baird", "Maruping"],
                year=2021,
                venue="MIS Quarterly",
                venue_type="journal",
            )
            result = find_matching_pdf(temp_root, "2026-03-23", target)
            self.assertEqual(result, matched)

    def test_infer_dates_from_pdf_paths(self) -> None:
        dates = infer_dates_from_paths(
            [
                "/tmp/data/zotero_pdf/agentic_ai_all/2026-3-23/example.pdf",
                "/tmp/data/zotero_pdf/agentic_ai_all/2026-03-24/example.pdf",
            ],
            "2026-03-25",
        )
        self.assertEqual(dates, ["2026-03-23", "2026-03-24"])

    def test_cli_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            temp_root = Path(tempdir)
            for relative in [
                "data/discovery",
                "data/fulltext/2026-03-22",
                "data/fixtures",
                "01_literature",
                "02_reports/daily",
                "03_state/confirmed",
                "config",
            ]:
                (temp_root / relative).mkdir(parents=True, exist_ok=True)

            (temp_root / "data/fixtures/discovery_seed.json").write_text(
                (ROOT / "data/fixtures/discovery_seed.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            config = json.loads((ROOT / "config/agentic_researcher.json").read_text(encoding="utf-8"))
            config["workspace_root"] = tempdir
            config["discovery"]["fixture_path"] = "data/fixtures/discovery_seed.json"
            (temp_root / "config/agentic_researcher.json").write_text(
                json.dumps(config, indent=2),
                encoding="utf-8",
            )
            papers = load_fixture_candidates(ROOT / "data" / "fixtures" / "discovery_seed.json", ["MIS Quarterly"])
            scored_preview = heuristic_score_papers(papers, "agentic ai information systems")
            (temp_root / f"data/fulltext/2026-03-22/{scored_preview[0].id}.txt").write_text(
                "This full text discusses the research problem, method design, data collection, evaluation metrics, findings, limitations, and future work in detail.",
                encoding="utf-8",
            )

            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/discover_papers.py"),
                    "--query",
                    "agentic ai information systems",
                    "--source",
                    "fixture",
                    "--input",
                    str(temp_root / "data/fixtures/discovery_seed.json"),
                    "--date",
                    "2026-03-22",
                    "--config",
                    str(temp_root / "config/agentic_researcher.json"),
                ],
                check=True,
            )
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/daily_score.py"),
                    "--input",
                    str(temp_root / "data/discovery/2026-03-22/bundle.json"),
                    "--query",
                    "agentic ai information systems",
                    "--date",
                    "2026-03-22",
                    "--config",
                    str(temp_root / "config/agentic_researcher.json"),
                ],
                check=True,
            )
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/confirm_candidates.py"),
                    "--input",
                    str(temp_root / "data/discovery/2026-03-22/bundle.json"),
                    "--top",
                    "3",
                    "--date",
                    "2026-03-22",
                    "--config",
                    str(temp_root / "config/agentic_researcher.json"),
                ],
                check=True,
            )
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/daily_report.py"),
                    "--input",
                    str(temp_root / "03_state/confirmed/2026-03-22.json"),
                    "--date",
                    "2026-03-22",
                    "--config",
                    str(temp_root / "config/agentic_researcher.json"),
                ],
                check=True,
            )
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts/refresh_notes.py"),
                    "--date",
                    "2026-03-22",
                    "--config",
                    str(temp_root / "config/agentic_researcher.json"),
                ],
                check=True,
            )
            self.assertTrue((temp_root / "02_reports/daily/2026-03-22.md").exists())
            self.assertTrue((temp_root / "data/discovery/2026-03-22/bundle.json").exists())
            self.assertFalse((temp_root / "data/discovery/2026-03-22/candidates.csv").exists())
            self.assertFalse((temp_root / "data/discovery/2026-03-22/zotero_import.ris").exists())
            notes = list((temp_root / "01_literature/2026-03-22").glob("*.md"))
            self.assertEqual(len(notes), 3)
            note_content = notes[0].read_text(encoding="utf-8")
            self.assertIn("## 1. 研究问题与动机", note_content)
            self.assertIn("## 2. 模型或实验方法", note_content)
            self.assertIn("## 3. 实验过程", note_content)
            self.assertIn("## 4. 核心结论与贡献", note_content)
            self.assertIn("## 5. 扩展方向与批判性评价", note_content)
            self.assertIn("## 研究建议", note_content)
            self.assertIn("## 商业应用想法", note_content)
            self.assertIn("## 一句话定位", note_content)
            self.assertNotIn("LaTeX", note_content)
            self.assertIn("笔记依据:", note_content)
            self.assertRegex(notes[0].name, r"^(unknown-date|\d{4})_[a-z0-9-]+_[a-z0-9-]+\.md$")
            scored_md = (temp_root / "data/discovery/2026-03-22/candidates.md").read_text(encoding="utf-8")
            self.assertIn("## IS 检索模板", scored_md)
            self.assertIn("- 推荐理由:", scored_md)
            self.assertNotIn("- 中文总结:", scored_md)
            self.assertNotIn("- 研究建议:", scored_md)
            self.assertNotIn("- 商业应用想法:", scored_md)
            report_content = (temp_root / "02_reports/daily/2026-03-22.md").read_text(encoding="utf-8")
            self.assertNotIn("汇报对象", report_content)


if __name__ == "__main__":
    unittest.main()
