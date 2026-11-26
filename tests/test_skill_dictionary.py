"""Unit and integration tests for custom skill dictionary management.

Verifies:
1. Skills can be organized into categories.
2. Alternative skill names (aliases) are recognized.
3. Duplicate entries (canonical and aliases) are avoided.
4. Missing, unreadable, or invalid dictionary files are handled safely.
5. Dictionary is loaded dynamically during analysis.
"""

import json
import os
import shutil
import tempfile
import time
import unittest

from analyzer.skill_dictionary import (
    SkillDictionaryManager,
    compile_skill_patterns,
    get_all_skills_flat,
    load_skills_dictionary,
    normalize_skill_dictionary,
    save_skills_dictionary,
)
from analyzer.skills_extractor import (
    DEFAULT_SKILL_CATEGORIES,
    SKILL_CATEGORIES,
    SKILLS,
    extract_skills,
    reload_skills_dictionary,
)


class TestSkillDictionaryOrganization(unittest.TestCase):
    """Verify skills can be organized into categories."""

    def test_default_categories_structure(self):
        """Standard dictionary categories are present and contain skills."""
        categories = load_skills_dictionary()
        self.assertIsInstance(categories, dict)
        expected_categories = [
            "Programming Languages",
            "Web Development",
            "Databases",
            "Cloud & DevOps",
            "Data Science & AI",
            "Tools",
            "Core Concepts",
            "Soft Skills",
        ]
        for cat in expected_categories:
            self.assertIn(cat, categories)
            self.assertIsInstance(categories[cat], dict)
            self.assertTrue(len(categories[cat]) > 0)

    def test_custom_category_creation(self):
        """New categories can be added and normalized."""
        raw = {
            "Blockchain": {
                "Solidity": ["smart contracts", "evm"],
                "Web3": ["web3.js", "ethers.js"],
            },
            "Cloud & DevOps": {
                "Kubernetes": ["k8s"],
            },
        }
        normalized = normalize_skill_dictionary(raw)
        self.assertIn("Blockchain", normalized)
        self.assertIn("Solidity", normalized["Blockchain"])
        self.assertEqual(normalized["Blockchain"]["Solidity"], ["smart contracts", "evm"])


class TestAlternativeSkillNames(unittest.TestCase):
    """Verify alternative skill names (aliases) are recognized."""

    def test_aliases_map_to_canonical_skills(self):
        """Resume text containing aliases extracts the canonical skill name."""
        text = "Built services with python3, postgres database, and deployed on k8s."
        detected = extract_skills(text)
        self.assertIn("Python", detected)
        self.assertIn("PostgreSQL", detected)
        self.assertIn("Kubernetes", detected)

    def test_custom_skill_alternative_names_recognized(self):
        """Custom skills and their alternative names are recognized during analysis."""
        custom_dict = {
            "Mobile Development": {
                "Flutter": ["flutter framework", "dart flutter"],
                "React Native": ["rn", "react-native"],
            }
        }
        manager = SkillDictionaryManager(fallback=custom_dict)
        # Using alias "dart flutter"
        result1 = manager.extract_skills("Experienced in dart flutter and rn applications.")
        self.assertIn("Flutter", result1)
        self.assertIn("React Native", result1)

        # Using canonical name
        result2 = manager.extract_skills("Proficient in Flutter and React Native.")
        self.assertIn("Flutter", result2)
        self.assertIn("React Native", result2)

    def test_dynamic_extract_skills_with_custom_dictionary_param(self):
        """extract_skills accepts custom_dictionary and identifies alternative names."""
        custom_dict = {
            "Big Data": {
                "Apache Spark": ["spark", "pyspark"],
                "Apache Kafka": ["kafka", "event streaming"],
            }
        }
        text = "Built event streaming pipelines using pyspark and kafka."
        detected = extract_skills(text, custom_dictionary=custom_dict)
        self.assertIn("Apache Spark", detected)
        self.assertIn("Apache Kafka", detected)


class TestDuplicateEntriesAvoidance(unittest.TestCase):
    """Verify duplicate entries (canonical, aliases, extraction outputs) are avoided."""

    def test_duplicate_canonical_names_deduplicated(self):
        """Duplicate canonical names across categories or with casing differences are merged."""
        raw = {
            "Languages": {
                "Python": ["py", "python3"],
            },
            "Data Science": {
                "python": ["cpython"],  # duplicate canonical (different case)
                "R": [],
            },
        }
        normalized = normalize_skill_dictionary(raw)
        flat_skills = get_all_skills_flat(normalized)
        # Should have "Python" and "R" only once
        lower_skills = [s.lower() for s in flat_skills]
        self.assertEqual(lower_skills.count("python"), 1)

    def test_duplicate_and_self_aliases_pruned(self):
        """Duplicate aliases and aliases matching canonical names are pruned."""
        raw = {
            "Tools": {
                "Git": ["git", "Git", "git scm", "git scm", "version control"],
            }
        }
        normalized = normalize_skill_dictionary(raw)
        aliases = normalized["Tools"]["Git"]
        # 'git' matching canonical should be removed
        self.assertNotIn("git", [a.lower() for a in aliases])
        # 'git scm' should appear only once
        self.assertEqual(aliases.count("git scm"), 1)

    def test_alias_collision_prevented(self):
        """An alias already claimed by one skill cannot be claimed by another."""
        raw = {
            "Frameworks": {
                "React": ["reactjs"],
                "Preact": ["reactjs", "preactjs"],  # 'reactjs' collides with React
            }
        }
        normalized = normalize_skill_dictionary(raw)
        self.assertIn("reactjs", normalized["Frameworks"]["React"])
        self.assertNotIn("reactjs", normalized["Frameworks"]["Preact"])
        self.assertIn("preactjs", normalized["Frameworks"]["Preact"])

    def test_extracted_skills_have_no_duplicates_in_text(self):
        """Even if canonical and multiple aliases appear in resume, canonical appears once."""
        text = "Proficient in Python, python, python3, PYTHON, and py."
        custom = {"Languages": {"Python": ["python3", "py"]}}
        manager = SkillDictionaryManager(fallback=custom)
        detected = manager.extract_skills(text)
        self.assertEqual(detected, ["Python"])
        self.assertEqual(len(detected), len(set(detected)))


class TestMissingAndInvalidFilesHandling(unittest.TestCase):
    """Verify missing, unreadable, or invalid dictionary files are handled safely."""

    def test_missing_file_uses_fallback(self):
        """Non-existent file path safely loads fallback dictionary without exception."""
        non_existent_path = os.path.join(tempfile.gettempdir(), "non_existent_skills_9999.json")
        fallback = {"FallbackCategory": {"FallbackSkill": ["fb"]}}
        result = load_skills_dictionary(non_existent_path, fallback=fallback)
        self.assertIn("FallbackCategory", result)
        self.assertIn("FallbackSkill", result["FallbackCategory"])

    def test_malformed_json_uses_fallback(self):
        """Corrupted JSON file safely falls back to default dictionary."""
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as f:
            f.write("{ invalid json formatting ... ")
            bad_path = f.name

        try:
            fallback = {"SafeCategory": {"SafeSkill": []}}
            result = load_skills_dictionary(bad_path, fallback=fallback)
            self.assertIn("SafeCategory", result)
            self.assertIn("SafeSkill", result["SafeCategory"])
        finally:
            if os.path.exists(bad_path):
                os.remove(bad_path)

    def test_invalid_json_type_uses_fallback(self):
        """JSON file with root array or primitive falls back safely."""
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as f:
            json.dump(["Not", "A", "Dictionary"], f)
            bad_path = f.name

        try:
            fallback = {"DefaultCategory": {"DefaultSkill": []}}
            result = load_skills_dictionary(bad_path, fallback=fallback)
            self.assertIn("DefaultCategory", result)
        finally:
            if os.path.exists(bad_path):
                os.remove(bad_path)

    def test_empty_json_file_uses_fallback(self):
        """Empty JSON file falls back safely."""
        with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json") as f:
            f.write("")
            empty_path = f.name

        try:
            fallback = {"DefaultCategory": {"DefaultSkill": []}}
            result = load_skills_dictionary(empty_path, fallback=fallback)
            self.assertIn("DefaultCategory", result)
        finally:
            if os.path.exists(empty_path):
                os.remove(bad_path if 'bad_path' in locals() else empty_path)

    def test_extract_skills_survives_missing_file(self):
        """extract_skills works without error when pointing to a broken dictionary path."""
        manager = SkillDictionaryManager(
            filepath="totally_broken_path_xyz.json",
            fallback=DEFAULT_SKILL_CATEGORIES
        )
        detected = manager.extract_skills("Python, SQL, and Docker")
        self.assertIn("Python", detected)
        self.assertIn("SQL", detected)
        self.assertIn("Docker", detected)


class TestDynamicLoadingDuringAnalysis(unittest.TestCase):
    """Verify dictionary updates on disk are dynamically loaded during analysis."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.dict_file = os.path.join(self.temp_dir, "skills.json")
        initial_data = {
            "Languages": {
                "Python": ["python3"],
            }
        }
        with open(self.dict_file, "w", encoding="utf-8") as f:
            json.dump(initial_data, f)

        self.manager = SkillDictionaryManager(
            filepath=self.dict_file,
            fallback={},
            auto_reload=True
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_disk_modification_dynamically_loaded(self):
        """Modifying the JSON file on disk is recognized dynamically on subsequent analysis."""
        # Initial check
        initial_skills = self.manager.extract_skills("Skilled in Python and Rust.")
        self.assertEqual(initial_skills, ["Python"])

        # Small sleep to ensure mtime changes on filesystems with low timestamp resolution
        time.sleep(0.05)

        # Update file on disk
        updated_data = {
            "Languages": {
                "Python": ["python3"],
                "Rust": ["rustlang"],
            }
        }
        with open(self.dict_file, "w", encoding="utf-8") as f:
            json.dump(updated_data, f)

        # Dynamic extraction should now detect Rust without restarting manager
        updated_skills = self.manager.extract_skills("Skilled in Python and Rust.")
        self.assertIn("Python", updated_skills)
        self.assertIn("Rust", updated_skills)

    def test_add_skill_and_save(self):
        """Adding a skill programmatically updates in-memory cache and file."""
        self.manager.add_skill("DevOps", "Terraform", aliases=["tf"], save=True)
        categories = self.manager.get_categories()
        self.assertIn("DevOps", categories)
        self.assertIn("Terraform", categories["DevOps"])

        # Check file content on disk
        with open(self.dict_file, "r", encoding="utf-8") as f:
            disk_data = json.load(f)
        self.assertIn("DevOps", disk_data)
        self.assertIn("Terraform", disk_data["DevOps"])


if __name__ == "__main__":
    unittest.main()
