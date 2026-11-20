import unittest

from analyzer.job_matcher import JOB_SKILLS, match_resume_to_job
from analyzer.skills_extractor import (
    SKILL_CATEGORIES,
    SKILLS,
    extract_skills,
    get_suggestions,
)

# The skills the app detected before the dictionary was added.
ORIGINAL_SKILLS = [
    "Python", "Java", "C++", "C", "JavaScript",
    "HTML", "CSS", "SQL", "Flask", "Django",
    "React", "Node.js", "MongoDB", "MySQL",
    "Machine Learning", "Deep Learning", "NLP",
    "Data Analysis", "Pandas", "NumPy",
    "TensorFlow", "PyTorch", "Git", "GitHub",
    "REST API", "Data Structures", "OOP",
    "Communication", "Problem Solving",
]


class ExistingBehaviourTests(unittest.TestCase):

    def test_every_original_skill_is_still_detected(self):
        for skill in ORIGINAL_SKILLS:
            with self.subTest(skill=skill):
                self.assertIn(skill, extract_skills(skill))
                self.assertIn(skill, extract_skills(f"Skills: {skill}, Git"))

    def test_original_skills_are_in_the_dictionary(self):
        for skill in ORIGINAL_SKILLS:
            self.assertIn(skill, SKILLS)

    def test_matching_ignores_case(self):
        self.assertEqual(extract_skills("PYTHON and sql"), ["Python", "SQL"])

    def test_empty_input_gives_empty_list(self):
        self.assertEqual(extract_skills(""), [])
        self.assertEqual(extract_skills(None), [])
        self.assertEqual(extract_skills("   \n  "), [])

    def test_returns_a_list_of_strings(self):
        result = extract_skills("Python, Flask")
        self.assertIsInstance(result, list)
        self.assertTrue(all(isinstance(skill, str) for skill in result))

    def test_suggestions_are_unchanged(self):
        suggestions = get_suggestions([])
        self.assertIn("Consider adding Python skills if you have experience.",
                      suggestions)
        self.assertEqual(
            get_suggestions(["Python", "SQL", "Git", "Machine Learning",
                             "Communication"]),
            ["Your listed skills cover several useful technical areas. "
             "Keep your skills updated."],
        )

    def test_get_suggestions_handles_none(self):
        suggestions = get_suggestions(None)
        self.assertIsInstance(suggestions, list)
        self.assertIn("Consider adding Python skills if you have experience.", suggestions)



class SkillVariationTests(unittest.TestCase):

    def assert_detects(self, text, skill):
        self.assertIn(skill, extract_skills(text), f"{text!r} -> {skill}")

    def test_javascript_variations(self):
        for text in ["JavaScript", "Javascript", "javascript", "JS", "js",
                     "ECMAScript"]:
            self.assert_detects(text, "JavaScript")

    def test_framework_name_variations(self):
        pairs = {
            "ReactJS": "React", "React.js": "React", "React JS": "React",
            "NodeJS": "Node.js", "Node JS": "Node.js", "node.js": "Node.js",
            "VueJS": "Vue", "Vue.js": "Vue", "Angular.js": "Angular",
            "NextJS": "Next.js", "Express.js": "Express",
            "Spring-Boot": "Spring Boot", "fast api": "FastAPI",
        }
        for text, skill in pairs.items():
            self.assert_detects(text, skill)

    def test_other_common_variations(self):
        pairs = {
            "Postgres": "PostgreSQL", "Mongo DB": "MongoDB",
            "K8s": "Kubernetes", "sklearn": "Scikit-Learn",
            "scikit learn": "Scikit-Learn", "HTML5": "HTML", "CSS3": "CSS",
            "Python3": "Python", "Golang": "Go", "C Sharp": "C#",
            "Amazon Web Services": "AWS", "Google Cloud Platform": "GCP",
            "RESTful APIs": "REST API", "REST APIs": "REST API",
            "OOPs": "OOP", "Object-Oriented Programming": "OOP",
            "DSA": "Data Structures", "ML": "Machine Learning",
            "Natural Language Processing": "NLP",
            "Problem-Solving": "Problem Solving", "CI CD": "CI/CD",
            "Power-BI": "Power BI", "Microsoft Excel": "Excel",
        }
        for text, skill in pairs.items():
            self.assert_detects(text, skill)

    def test_skill_split_over_two_lines_is_found(self):
        text = "Machine\nLearning, Data\nStructures"
        self.assertEqual(extract_skills(text),
                         ["Machine Learning", "Data Structures"])


class DuplicateTests(unittest.TestCase):

    def test_different_spellings_give_one_entry(self):
        result = extract_skills("JavaScript, JS, Javascript, javascript, js")
        self.assertEqual(result, ["JavaScript"])

    def test_no_duplicates_in_a_full_resume(self):
        text = ("Python python PYTHON, Postgres, PostgreSQL, ReactJS, "
                "React.js, React, Node.js, NodeJS, K8s, Kubernetes")
        result = extract_skills(text)
        self.assertEqual(len(result), len(set(result)))

    def test_result_follows_dictionary_order(self):
        result = extract_skills("Git, Python, SQL, Java")
        self.assertEqual(result, [s for s in SKILLS if s in result])


class FalsePositiveTests(unittest.TestCase):

    def test_cpp_does_not_also_give_c(self):
        self.assertEqual(extract_skills("C++"), ["C++"])
        self.assertEqual(extract_skills("Skills: Python, C++, Java"),
                         ["Python", "Java", "C++"])

    def test_csharp_does_not_also_give_c(self):
        self.assertEqual(extract_skills("C#"), ["C#"])

    def test_c_in_normal_sentences_is_ignored(self):
        for text in ["Plan C was approved.", "Vitamin C", "Hepatitis C",
                     "Grade C students", "Section C of the report"]:
            self.assertNotIn("C", extract_skills(text), text)

    def test_c_in_real_skill_lists_is_found(self):
        for text in ["Languages: C, C++, Java", "C/C++", "Proficient in C",
                     "knowledge of C and C++", "Python, Java, C."]:
            self.assertIn("C", extract_skills(text), text)

    def test_r_and_go_need_a_skill_context(self):
        self.assertNotIn("R", extract_skills("R&D team"))
        self.assertNotIn("Go", extract_skills("Go to market strategy"))
        self.assertNotIn("Go", extract_skills("We need to go and see"))
        self.assertIn("R", extract_skills("Languages: Python, R, SQL"))
        self.assertIn("Go", extract_skills("Backend: Python, Go, Rust"))

    def test_english_words_are_ignored(self):
        self.assertNotIn("Express", extract_skills("to express my interest"))
        self.assertNotIn("Swift", extract_skills("swift delivery of tasks"))
        self.assertNotIn("Excel", extract_skills("I excel in teamwork"))
        self.assertNotIn("Oracle", extract_skills("Interned at Oracle"))
        self.assertNotIn("Node.js", extract_skills("root node of the tree"))

    def test_those_words_are_found_in_skill_lists(self):
        self.assertEqual(
            extract_skills("React, Node, Express, MongoDB"),
            ["React", "Node.js", "Express", "MongoDB"],
        )

    def test_skills_inside_longer_words_are_ignored(self):
        self.assertEqual(extract_skills("MySQL"), ["MySQL"])
        self.assertEqual(extract_skills("NoSQL"), [])
        self.assertEqual(extract_skills("JavaScript"), ["JavaScript"])
        self.assertEqual(extract_skills("GitHub"), ["GitHub"])
        self.assertEqual(extract_skills("Pythonic"), [])

    def test_node_js_is_not_javascript(self):
        for text in ["Node.js", "Node JS", "React JS", "Vue.js", "Next.js"]:
            self.assertNotIn("JavaScript", extract_skills(text), text)


class DictionaryTests(unittest.TestCase):

    def test_canonical_names_are_unique(self):
        self.assertEqual(len(SKILLS), len(set(SKILLS)))

    def test_aliases_belong_to_one_skill_only(self):
        owner = {}
        for group in SKILL_CATEGORIES.values():
            for skill, aliases in group.items():
                for term in [skill] + aliases:
                    key = term.lower()
                    self.assertNotIn(key, owner,
                                     f"{term!r} is used by {skill} and "
                                     f"{owner.get(key)}")
                    owner[key] = skill

    def test_every_job_matcher_skill_can_be_detected(self):
        # Keeps skills_extractor and job_matcher in sync.
        for skill in JOB_SKILLS:
            with self.subTest(skill=skill):
                self.assertIn(skill, extract_skills(skill))
                self.assertIn(skill, extract_skills(f"Skills: {skill}, Git"))

    def test_every_dictionary_skill_is_detected_when_written_out(self):
        for skill in SKILLS:
            with self.subTest(skill=skill):
                self.assertIn(skill, extract_skills(f"Skills: {skill}, Git"))


class JobMatchingTests(unittest.TestCase):

    def test_resume_with_js_matches_javascript_job(self):
        skills = extract_skills("Skills: JS, ReactJS, Docker, Postgres")
        match = match_resume_to_job(
            skills, "Need JavaScript, React, Docker and PostgreSQL."
        )
        self.assertEqual(match["match_percentage"], 100)
        self.assertEqual(match["missing_skills"], [])


if __name__ == "__main__":
    unittest.main()