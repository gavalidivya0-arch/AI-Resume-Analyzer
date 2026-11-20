import unittest
from analyzer.timeline_checker import (
    parse_date_token,
    extract_timeline_ranges,
    check_timeline_consistency,
)


class TestParseDateToken(unittest.TestCase):

    def test_month_year_formats(self):
        self.assertEqual(parse_date_token("January 2021"), (2021, 1, "Month YYYY"))
        self.assertEqual(parse_date_token("Jan 2021"), (2021, 1, "Month YYYY"))
        self.assertEqual(parse_date_token("Sep. 2020"), (2020, 9, "Month YYYY"))
        self.assertEqual(parse_date_token("August 2019"), (2019, 8, "Month YYYY"))

    def test_month_slash_year_formats(self):
        self.assertEqual(parse_date_token("06/2021"), (2021, 6, "MM/YYYY"))
        self.assertEqual(parse_date_token("6/2021"), (2021, 6, "MM/YYYY"))
        self.assertEqual(parse_date_token("12-2020"), (2020, 12, "MM/YYYY"))

    def test_iso_year_month_format(self):
        self.assertEqual(parse_date_token("2021-06"), (2021, 6, "YYYY-MM"))

    def test_year_only_format(self):
        self.assertEqual(parse_date_token("2021", is_end=False), (2021, 1, "YYYY"))
        self.assertEqual(parse_date_token("2021", is_end=True), (2021, 12, "YYYY"))

    def test_present_keywords(self):
        res_present = parse_date_token("Present")
        self.assertIsNotNone(res_present)
        self.assertEqual(res_present[2], "Present")

        res_current = parse_date_token("current")
        self.assertIsNotNone(res_current)
        self.assertEqual(res_current[2], "Present")

        res_ongoing = parse_date_token("Ongoing")
        self.assertIsNotNone(res_ongoing)
        self.assertEqual(res_ongoing[2], "Present")

    def test_invalid_tokens(self):
        self.assertIsNone(parse_date_token("Python"))
        self.assertIsNone(parse_date_token("13/2020"))
        self.assertIsNone(parse_date_token("1800"))
        self.assertIsNone(parse_date_token(""))
        self.assertIsNone(parse_date_token(None))



class TestExtractTimelineRanges(unittest.TestCase):

    def test_extract_complete_ranges(self):
        text = """
        Software Engineer, Tech Corp | Jan 2020 - Dec 2022
        Associate Developer | 06/2021 – Present
        Education: B.S. Computer Science | 2016 to 2020
        """
        ranges = extract_timeline_ranges(text, section_name="experience")
        self.assertGreaterEqual(len(ranges), 3)

        first = ranges[0]
        self.assertEqual(first["start_raw"], "Jan 2020")
        self.assertEqual(first["end_raw"], "Dec 2022")
        self.assertFalse(first["is_incomplete"])

        second = ranges[1]
        self.assertTrue(second["is_present"])

    def test_extract_incomplete_ranges(self):
        text = """
        Backend Developer | March 2022 -
        Frontend Intern | 2021 - 2022
        """
        ranges = extract_timeline_ranges(text, section_name="experience")
        incomplete = [r for r in ranges if r["is_incomplete"]]
        self.assertEqual(len(incomplete), 1)
        self.assertEqual(incomplete[0]["start_raw"], "March 2022")


class TestCheckTimelineConsistency(unittest.TestCase):

    def test_empty_resume_text(self):
        result = check_timeline_consistency("")
        self.assertEqual(result["total_ranges_detected"], 0)
        self.assertEqual(result["timeline_status"], "No Dates Found")
        self.assertFalse(result["has_inconsistencies"])

    def test_consistent_timeline(self):
        text = """
        EXPERIENCE
        Senior Engineer, Alpha Corp (Jan 2022 - Present)
        • Led migration of cloud infrastructure
        Software Engineer, Beta Ltd (Jan 2019 - Dec 2021)
        • Built high-performance microservices

        EDUCATION
        B.Tech Computer Science (Jan 2015 - Dec 2018)
        """
        sections = {
            "experience": "Senior Engineer, Alpha Corp (Jan 2022 - Present)\nSoftware Engineer, Beta Ltd (Jan 2019 - Dec 2021)",
            "education": "B.Tech Computer Science (Jan 2015 - Dec 2018)",
        }
        result = check_timeline_consistency(text, resume_sections=sections)
        self.assertEqual(result["total_ranges_detected"], 3)
        self.assertFalse(result["has_mixed_formats"])
        self.assertFalse(result["has_inconsistencies"])
        self.assertEqual(result["timeline_status"], "Consistent")

    def test_mixed_date_formats_detection(self):
        text = """
        EXPERIENCE
        Software Engineer (01/2022 - Present)
        Junior Developer (Jan 2019 - Dec 2021)
        Intern (2018 - 2018)
        """
        result = check_timeline_consistency(text)
        self.assertTrue(result["has_mixed_formats"])
        format_inc = [inc for inc in result["inconsistencies"] if inc["type"] == "format_inconsistency"]
        self.assertTrue(len(format_inc) > 0)
        self.assertEqual(format_inc[0]["severity"], "advisory")

    def test_reversed_date_range_warning(self):
        text = """
        EXPERIENCE
        Software Engineer (2024 - 2021)
        """
        result = check_timeline_consistency(text)
        rev_inc = [inc for inc in result["inconsistencies"] if inc["type"] == "reversed_range"]
        self.assertEqual(len(rev_inc), 1)
        self.assertEqual(rev_inc[0]["severity"], "warning")
        self.assertEqual(result["timeline_status"], "Review Recommended")

    def test_incomplete_date_range_detection(self):
        text = """
        EXPERIENCE
        Software Engineer (Jan 2022 - )
        """
        result = check_timeline_consistency(text)
        inc_list = [inc for inc in result["inconsistencies"] if inc["type"] == "incomplete_range"]
        self.assertEqual(len(inc_list), 1)
        self.assertEqual(inc_list[0]["severity"], "advisory")

    def test_overlapping_experience_detection(self):
        text = """
        EXPERIENCE
        Tech Lead, Company A (Jan 2021 - Dec 2023)
        Consultant, Company B (Jun 2022 - May 2024)
        """
        sections = {
            "experience": "Tech Lead, Company A (Jan 2021 - Dec 2023)\nConsultant, Company B (Jun 2022 - May 2024)"
        }
        result = check_timeline_consistency(text, resume_sections=sections)
        overlap_inc = [inc for inc in result["inconsistencies"] if inc["type"] == "overlapping_period"]
        self.assertEqual(len(overlap_inc), 1)
        self.assertEqual(overlap_inc[0]["severity"], "advisory")

    def test_original_text_preserved(self):
        original = "Developer (Jan 2020 - Dec 2022)\nEducation (2016 - 2020)"
        copy_text = str(original)
        check_timeline_consistency(copy_text)
        self.assertEqual(copy_text, original)


if __name__ == "__main__":
    unittest.main()
