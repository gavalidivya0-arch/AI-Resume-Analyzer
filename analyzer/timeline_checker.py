"""Resume Date and Timeline Consistency Checker (Issue #53).

Analyzes resume dates and timelines by:
1. Recognizing common date formats (Month YYYY, MM/YYYY, YYYY, Present/Current).
2. Detecting format inconsistencies (e.g. mixing MM/YYYY and Month YYYY).
3. Identifying incomplete date ranges (e.g. start date with trailing dash).
4. Spotting potential overlapping experience periods and reversed ranges.
5. Checking chronological ordering (reverse-chronological convention).
6. Providing advisory warnings for manual review without treating uncertain dates as errors.
7. Preserving all original text and dates without modification.
"""

from datetime import date
import re
from typing import Any, Dict, List, Optional, Set, Tuple

MONTH_NAMES = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

CURRENT_KEYWORDS = {"present", "current", "currently", "now", "ongoing"}


def _get_current_year_month() -> Tuple[int, int]:
    today = date.today()
    return today.year, today.month


def parse_date_token(token: str, is_end: bool = False) -> Optional[Tuple[int, int, str]]:
    """Parse a date token into (year, month, format_type).

    Returns None if token cannot be parsed into a date.
    """
    if not token or not isinstance(token, str):
        return None
    clean = token.strip().strip(",.;:()[]").lower()
    if not clean:
        return None

    if clean in CURRENT_KEYWORDS:
        curr_year, curr_month = _get_current_year_month()
        return (curr_year, curr_month, "Present")

    # Format 1: "MM/YYYY" or "MM-YYYY" e.g. "06/2021", "6/2021"
    m_slash = re.match(r"^(\d{1,2})[/-](\d{4})$", clean)
    if m_slash:
        month = int(m_slash.group(1))
        year = int(m_slash.group(2))
        if 1 <= month <= 12 and 1950 <= year <= 2040:
            return (year, month, "MM/YYYY")

    # Format 2: "YYYY-MM" e.g. "2021-06"
    m_iso = re.match(r"^(\d{4})-(\d{1,2})$", clean)
    if m_iso:
        year = int(m_iso.group(1))
        month = int(m_iso.group(2))
        if 1 <= month <= 12 and 1950 <= year <= 2040:
            return (year, month, "YYYY-MM")

    # Format 3: "Month YYYY" or "Mon YYYY" e.g. "January 2021", "Jan 2021", "Jan. 2021"
    m_month_year = re.match(r"^([a-z]+)\.?\s+(\d{4})$", clean)
    if m_month_year:
        mon_str = m_month_year.group(1)
        year = int(m_month_year.group(2))
        if mon_str in MONTH_NAMES and 1950 <= year <= 2040:
            return (year, MONTH_NAMES[mon_str], "Month YYYY")

    # Format 4: Year only e.g. "2021"
    m_year = re.match(r"^(\d{4})$", clean)
    if m_year:
        year = int(m_year.group(1))
        if 1950 <= year <= 2040:
            # Default start date to January (1), end date to December (12)
            month = 12 if is_end else 1
            return (year, month, "YYYY")

    return None


# Regular expression to extract date ranges from text
# Matches patterns like:
# "Jan 2020 - Dec 2022", "06/2021 – Present", "2019 - 2023", "August 2021 to Current"
DATE_RANGE_PATTERN = re.compile(
    r"(?P<start>(?:[A-Za-z]+\.?\s+\d{4}|\d{1,2}[/-]\d{4}|\d{4}-\d{1,2}|\d{4}))"
    r"\s*(?:[-–—]|to)\s*"
    r"(?P<end>(?:[A-Za-z]+\.?\s+\d{4}|\d{1,2}[/-]\d{4}|\d{4}-\d{1,2}|\d{4}|present|current|ongoing|now))",
    re.IGNORECASE,
)

# Trailing dash without an end date e.g. "Jan 2022 - "
INCOMPLETE_RANGE_PATTERN = re.compile(
    r"(?P<start>(?:[A-Za-z]+\.?\s+\d{4}|\d{1,2}[/-]\d{4}|\d{4}-\d{1,2}|\d{4}))\s*[-–—]\s*(?=[,\n\r\.\)]|$)",
    re.IGNORECASE,
)


def extract_timeline_ranges(
    text: str,
    section_name: str = "general"
) -> List[Dict[str, Any]]:
    """Extract structured date ranges from section text."""
    ranges: List[Dict[str, Any]] = []
    text = text or ""

    for line in text.splitlines():
        line_clean = line.strip()
        if not line_clean:
            continue

        # Look for standard complete ranges
        for match in DATE_RANGE_PATTERN.finditer(line_clean):
            start_str = match.group("start").strip()
            end_str = match.group("end").strip()

            start_parsed = parse_date_token(start_str, is_end=False)
            end_parsed = parse_date_token(end_str, is_end=True)

            if start_parsed and end_parsed:
                ranges.append({
                    "raw_text": match.group(0),
                    "start_raw": start_str,
                    "end_raw": end_str,
                    "start_year": start_parsed[0],
                    "start_month": start_parsed[1],
                    "start_format": start_parsed[2],
                    "end_year": end_parsed[0],
                    "end_month": end_parsed[1],
                    "end_format": end_parsed[2],
                    "is_present": end_parsed[2] == "Present",
                    "is_incomplete": False,
                    "context_line": line_clean[:80],
                    "section": section_name,
                })

        # Look for incomplete ranges (start date followed by dash with no end)
        for match in INCOMPLETE_RANGE_PATTERN.finditer(line_clean):
            start_str = match.group("start").strip()
            start_parsed = parse_date_token(start_str, is_end=False)
            if start_parsed:
                ranges.append({
                    "raw_text": match.group(0),
                    "start_raw": start_str,
                    "end_raw": "",
                    "start_year": start_parsed[0],
                    "start_month": start_parsed[1],
                    "start_format": start_parsed[2],
                    "end_year": None,
                    "end_month": None,
                    "end_format": "",
                    "is_present": False,
                    "is_incomplete": True,
                    "context_line": line_clean[:80],
                    "section": section_name,
                })

    return ranges


def check_timeline_consistency(
    resume_text: Optional[str],
    resume_sections: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Perform consistency and chronological analysis on resume dates and timelines."""
    if not resume_text or not resume_text.strip():
        return {
            "total_ranges_detected": 0,
            "detected_formats": [],
            "has_mixed_formats": False,
            "has_inconsistencies": False,
            "inconsistencies": [],
            "timeline_status": "No Dates Found",
            "recommendations": ["No dates found to analyze."],
        }

    # Extract ranges from experience and education sections, or full text
    ranges: List[Dict[str, Any]] = []
    if resume_sections:
        for sec_key in ("experience", "education", "projects", "internships"):
            sec_text = (resume_sections.get(sec_key) or "").strip()
            if sec_text:
                ranges.extend(extract_timeline_ranges(sec_text, section_name=sec_key))

    # If no ranges found in structured sections, scan the full resume text
    if not ranges:
        ranges = extract_timeline_ranges(resume_text, section_name="general")

    # 1. Identify all detected date formats
    format_counts: Dict[str, int] = {}
    for r in ranges:
        for fmt in (r["start_format"], r["end_format"]):
            if fmt and fmt != "Present":
                format_counts[fmt] = format_counts.get(fmt, 0) + 1

    detected_formats = list(format_counts.keys())
    has_mixed_formats = len(detected_formats) > 1

    inconsistencies: List[Dict[str, Any]] = []

    # 2. Check for format inconsistency
    if has_mixed_formats:
        formats_str = ", ".join(f"'{f}'" for f in detected_formats)
        inconsistencies.append({
            "type": "format_inconsistency",
            "severity": "advisory",
            "title": "Mixed Date Formats",
            "message": (
                f"Multiple date formats detected across your entries ({formats_str}). "
                "Consider standardizing to a single format (e.g. 'Month YYYY' or 'MM/YYYY') for visual consistency."
            ),
        })

    # 3. Check for incomplete ranges
    for r in ranges:
        if r["is_incomplete"]:
            inconsistencies.append({
                "type": "incomplete_range",
                "severity": "advisory",
                "title": "Incomplete Date Range",
                "message": (
                    f"Date entry '{r['raw_text']}' appears incomplete (missing end date or 'Present'). "
                    f"Context: \"{r['context_line']}\""
                ),
            })

    # 4. Check for reversed date ranges (End before Start)
    complete_ranges = [r for r in ranges if not r["is_incomplete"]]
    for r in complete_ranges:
        if not r["is_present"]:
            start_num = r["start_year"] * 12 + r["start_month"]
            end_num = r["end_year"] * 12 + r["end_month"]
            if end_num < start_num:
                inconsistencies.append({
                    "type": "reversed_range",
                    "severity": "warning",
                    "title": "Reversed Date Range",
                    "message": (
                        f"End date '{r['end_raw']}' is earlier than start date '{r['start_raw']}' in '{r['raw_text']}'. "
                        "Please verify whether this is a typographical error."
                    ),
                })

    # 5. Check for potentially overlapping experience periods
    exp_ranges = [r for r in complete_ranges if r["section"] in ("experience", "general")]
    seen_overlap_pairs = set()

    for i in range(len(exp_ranges)):
        for j in range(i + 1, len(exp_ranges)):
            r1 = exp_ranges[i]
            r2 = exp_ranges[j]

            # Compare chronological overlap
            start1 = r1["start_year"] * 12 + r1["start_month"]
            end1 = r1["end_year"] * 12 + r1["end_month"]
            start2 = r2["start_year"] * 12 + r2["start_month"]
            end2 = r2["end_year"] * 12 + r2["end_month"]

            # Overlap check: start of one falls before end of another and vice-versa
            if max(start1, start2) < min(end1, end2):
                pair_key = tuple(sorted([r1["raw_text"], r2["raw_text"]]))
                if pair_key not in seen_overlap_pairs:
                    seen_overlap_pairs.add(pair_key)
                    inconsistencies.append({
                        "type": "overlapping_period",
                        "severity": "advisory",
                        "title": "Potential Overlapping Experience",
                        "message": (
                            f"Overlapping period between '{r1['raw_text']}' and '{r2['raw_text']}'. "
                            "If these were concurrent roles, part-time positions, or internships, "
                            "recruiters may appreciate a brief clarifying note."
                        ),
                    })

    # 6. Check chronological ordering (reverse-chronological convention)
    if len(exp_ranges) >= 2:
        for i in range(len(exp_ranges) - 1):
            curr = exp_ranges[i]
            nxt = exp_ranges[i + 1]
            curr_start = curr["start_year"] * 12 + curr["start_month"]
            nxt_start = nxt["start_year"] * 12 + nxt["start_month"]

            # In reverse-chronological order, previous entry should start after or equal to next entry
            # If current starts significantly earlier than the next listed entry (by > 1 year), warn
            if nxt_start - curr_start > 12:
                inconsistencies.append({
                    "type": "chronological_order",
                    "severity": "advisory",
                    "title": "Chronological Ordering Note",
                    "message": (
                        f"Entry with date '{curr['raw_text']}' is listed before a newer entry '{nxt['raw_text']}'. "
                        "Resumes typically follow reverse-chronological order (most recent position first)."
                    ),
                })
                break

    # 7. Generate overall recommendations
    recommendations: List[str] = []
    if not ranges:
        recommendations.append("Include clear date ranges (e.g. 'Jan 2022 - Present') for each work experience and education entry.")
    else:
        for inc in inconsistencies:
            recommendations.append(inc["message"])

    if not inconsistencies:
        recommendations.append(
            "Great timeline consistency! Your date formatting is standardized and timelines appear clean and well-ordered."
        )

    timeline_status = "Consistent" if not any(inc["severity"] == "warning" for inc in inconsistencies) else "Review Recommended"

    return {
        "total_ranges_detected": len(ranges),
        "detected_formats": detected_formats,
        "has_mixed_formats": has_mixed_formats,
        "has_inconsistencies": len(inconsistencies) > 0,
        "inconsistencies": inconsistencies,
        "timeline_status": timeline_status,
        "recommendations": recommendations,
        "date_ranges": ranges,
    }
