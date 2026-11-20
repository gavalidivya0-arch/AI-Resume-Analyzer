"""Unit tests for Resume Improvement Roadmap Generator (Issue #34).

Acceptance criteria tested:
- Roadmap is generated from actual analysis results.
- Tasks are organized by priority.
- Users can mark tasks as completed.
- The roadmap remains accessible during the current session.
"""

import io
import unittest
from fpdf import FPDF

from analyzer.roadmap_generator import (
    calculate_roadmap_progress,
    generate_roadmap,
    get_priority_weight,
)
from app import app


class RoadmapGeneratorUnitTests(unittest.TestCase):

    def test_roadmap_generated_from_actual_weaknesses(self):
        """Acceptance Criteria 1: Roadmap is generated from actual analysis results."""
        # Resume with weak contact info, missing summary, and missing projects
        score_breakdown = {
            "Contact Information": 5,       # Missing phone
            "Professional Summary": 0,      # Missing summary
            "Technical Skills": 6,          # Only 3 skills
            "Education": 15,
            "Experience": 15,
            "Projects": 0,                  # Missing projects
            "Readability": 5,
        }
        found_skills = ["Python", "Flask", "SQL"]
        ats_result = {
            "score": 65,
            "formatting_issues": ["Missing Projects section"],
        }
        keyword_analysis = {
            "keywords": [
                {"keyword": "python", "status": "overused"},
            ]
        }

        roadmap = generate_roadmap(
            resume_score=46,
            score_breakdown=score_breakdown,
            found_skills=found_skills,
            ats_result=ats_result,
            keyword_analysis=keyword_analysis,
            target_role="Backend Developer",
        )

        all_titles = [t["title"] for t in roadmap["all_tasks"]]
        all_descs = " ".join([t["description"] for t in roadmap["all_tasks"]])

        # Generated tasks must reflect the actual deficits:
        self.assertTrue(any("Contact Information" in title for title in all_titles))
        self.assertTrue(any("Summary" in title for title in all_titles))
        self.assertTrue(any("Projects" in title for title in all_titles))
        self.assertTrue(any("Quantify" in title or "metrics" in all_descs.lower() for title in all_titles))
        self.assertTrue(any("Overused" in title or "python" in all_descs.lower() for title in all_titles))

    def test_tasks_are_organized_by_priority(self):
        """Acceptance Criteria 2: Tasks are organized by priority."""
        roadmap = generate_roadmap(
            resume_score=50,
            score_breakdown={"Contact Information": 0, "Professional Summary": 0},
            found_skills=["Python"],
        )

        self.assertIn("phases", roadmap)
        self.assertEqual(len(roadmap["phases"]), 3)

        p1 = roadmap["phases"][0]
        p2 = roadmap["phases"][1]
        p3 = roadmap["phases"][2]

        # Phase 1: High Priority (Immediate Fixes)
        self.assertEqual(p1["priority"], "High")
        self.assertIn("Immediate", p1["name"])
        for task in p1["tasks"]:
            self.assertEqual(task["priority"], "High")
            self.assertEqual(task["phase_num"], 1)

        # Phase 2: Medium Priority (Core Enhancements)
        self.assertEqual(p2["priority"], "Medium")
        self.assertIn("Core", p2["name"])
        for task in p2["tasks"]:
            self.assertEqual(task["priority"], "Medium")
            self.assertEqual(task["phase_num"], 2)

        # Phase 3: Low Priority (Strategic Growth)
        self.assertEqual(p3["priority"], "Low")
        self.assertIn("Strategic", p3["name"])
        for task in p3["tasks"]:
            self.assertEqual(task["priority"], "Low")
            self.assertEqual(task["phase_num"], 3)

        # Check weight helper
        self.assertLess(get_priority_weight("High"), get_priority_weight("Medium"))
        self.assertLess(get_priority_weight("Medium"), get_priority_weight("Low"))

    def test_users_can_mark_tasks_as_completed(self):
        """Acceptance Criteria 3: Users can mark tasks as completed and calculate progress."""
        roadmap = generate_roadmap(
            resume_score=50,
            score_breakdown={"Contact Information": 0},
            found_skills=["Python"],
        )

        total = roadmap["total_tasks"]
        self.assertGreater(total, 0)
        self.assertEqual(roadmap["completed_tasks"], 0)
        self.assertEqual(roadmap["completion_percentage"], 0)

        # Mark 2 tasks as completed
        tasks_to_complete = {roadmap["all_tasks"][0]["id"], roadmap["all_tasks"][1]["id"]}
        updated = calculate_roadmap_progress(roadmap, tasks_to_complete)

        self.assertEqual(updated["completed_tasks"], 2)
        expected_pct = round((2 / total) * 100)
        self.assertEqual(updated["completion_percentage"], expected_pct)

        # Check individual task status
        completed_task = next(t for t in updated["all_tasks"] if t["id"] == roadmap["all_tasks"][0]["id"])
        self.assertTrue(completed_task["completed"])

        # Handles None and lists gracefully without TypeError
        none_res = calculate_roadmap_progress(roadmap, None)
        self.assertEqual(none_res["completed_tasks"], 0)
        list_res = calculate_roadmap_progress(roadmap, [roadmap["all_tasks"][0]["id"]])
        self.assertEqual(list_res["completed_tasks"], 1)



class AppRoadmapSessionIntegrationTests(unittest.TestCase):

    def setUp(self):
        self.client = app.test_client()

    def test_roadmap_accessible_during_current_session(self):
        """Acceptance Criteria 4: The roadmap remains accessible during the current session."""
        # 1. Accessing /roadmap before analyzing redirects to home
        resp_before = self.client.get("/roadmap")
        self.assertEqual(resp_before.status_code, 302)

        # 2. Upload resume
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        pdf.cell(0, 10, "John Doe\njohn@example.com\nSkills: Python, Flask, SQL, Docker", new_x="LMARGIN", new_y="NEXT")

        pdf_bytes = io.BytesIO()
        pdf.output(pdf_bytes)
        pdf_bytes.seek(0)

        upload_resp = self.client.post(
            "/analyze",
            data={"resume": (pdf_bytes, "test_resume.pdf")},
            content_type="multipart/form-data",
        )
        self.assertEqual(upload_resp.status_code, 200)
        html = upload_resp.get_data(as_text=True)

        # Result page contains the roadmap section
        self.assertIn("Resume Improvement Roadmap", html)
        self.assertIn("Phase 1: Immediate Fixes", html)
        self.assertIn("Phase 2: Core Enhancements", html)
        self.assertIn("Phase 3: Strategic Growth", html)

        # 3. Accessing /roadmap directly during session works
        roadmap_resp = self.client.get("/roadmap")
        self.assertEqual(roadmap_resp.status_code, 200)
        roadmap_html = roadmap_resp.get_data(as_text=True)
        self.assertIn("Resume Improvement Roadmap", roadmap_html)
        self.assertIn("Overall Task Completion", roadmap_html)

    def test_toggle_roadmap_task_updates_session_progress(self):
        """Acceptance Criteria 3 & 4: Users can mark tasks completed and state persists in session."""
        # Upload resume to initialize session roadmap
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Helvetica", size=12)
        pdf.cell(0, 10, "Jane Doe\nSkills: Python, SQL", new_x="LMARGIN", new_y="NEXT")
        pdf_bytes = io.BytesIO()
        pdf.output(pdf_bytes)
        pdf_bytes.seek(0)

        self.client.post(
            "/analyze",
            data={"resume": (pdf_bytes, "resume.pdf")},
            content_type="multipart/form-data",
        )

        with self.client.session_transaction() as sess:
            first_task_id = sess["roadmap"]["all_tasks"][0]["id"]

        # Toggle task completed
        toggle_resp = self.client.post(
            "/roadmap/toggle",
            json={"task_id": first_task_id, "completed": True},
        )
        self.assertEqual(toggle_resp.status_code, 200)
        data = toggle_resp.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["task_id"], first_task_id)
        self.assertTrue(data["completed"])
        self.assertGreaterEqual(data["completed_tasks"], 1)

        # Verify session was updated
        with self.client.session_transaction() as sess:
            self.assertIn(first_task_id, sess["completed_tasks"])
            self.assertEqual(sess["roadmap"]["completed_tasks"], 1)

        # Toggle back to incomplete
        untoggle_resp = self.client.post(
            "/roadmap/toggle",
            json={"task_id": first_task_id, "completed": False},
        )
        self.assertEqual(untoggle_resp.status_code, 200)
        untoggle_data = untoggle_resp.get_json()
        self.assertFalse(untoggle_data["completed"])
        self.assertEqual(untoggle_data["completed_tasks"], 0)


if __name__ == "__main__":
    unittest.main()
