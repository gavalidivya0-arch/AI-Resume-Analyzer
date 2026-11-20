"""Action Verb Analysis module for resumes (Issue #54).

Analyzes resume action verbs by:
1. Detecting professional action verbs across domain categories.
2. Identifying vague, passive, or weak verbs and phrases.
3. Flagging frequently repeated action verbs (>= 3 times).
4. Providing contextually relevant alternative verb suggestions alongside original sentences.
5. Preserving the original resume text without automatic mutations.
"""

import re
from collections import Counter
from typing import Any, Dict, List, Optional, Set, Tuple

# Professional action verbs organized by domain category
ACTION_VERB_CATEGORIES = {
    "Technical & Development": [
        "architected", "built", "coded", "constructed", "created",
        "customized", "designed", "developed", "engineered", "implemented",
        "programmed", "prototyped", "refactored", "synthesized",
    ],
    "Deployment & Operations": [
        "automated", "configured", "deployed", "executed", "installed",
        "integrated", "launched", "migrated", "orchestrated", "provisioned",
        "released", "scaled", "shipped",
    ],
    "Performance & Optimization": [
        "accelerated", "boosted", "consolidated", "curtailed", "decreased",
        "eliminated", "enhanced", "expanded", "expedited", "improved",
        "increased", "maximized", "minimized", "modernized", "optimized",
        "reduced", "restructured", "revamped", "streamlined", "upgraded",
    ],
    "Leadership & Management": [
        "championed", "coordinated", "delegated", "directed", "empowered",
        "facilitated", "fostered", "guided", "headed", "led", "managed",
        "mentored", "mobilized", "oversaw", "recruited", "spearheaded",
        "supervised", "trained",
    ],
    "Analysis & Problem-Solving": [
        "analyzed", "assessed", "audited", "benchmarked", "calculated",
        "diagnosed", "discovered", "evaluated", "examined", "forecasted",
        "identified", "investigated", "mapped", "measured", "modeled",
        "quantified", "researched", "resolved", "surveyed", "tested", "troubleshot",
    ],
    "Collaboration & Communication": [
        "authored", "briefed", "collaborated", "documented", "negotiated",
        "partnered", "presented", "published",
    ],
}

# Flat set of all recognized action verbs
ALL_ACTION_VERBS: Set[str] = {
    verb
    for group in ACTION_VERB_CATEGORIES.values()
    for verb in group
}

# Weak or vague phrases mapping to default alternative verbs
VAGUE_VERBS_MAP: Dict[str, List[str]] = {
    "responsible for": ["spearheaded", "directed", "managed", "executed", "led"],
    "worked on": ["engineered", "developed", "built", "implemented", "constructed"],
    "helped with": ["collaborated on", "facilitated", "supported", "contributed to"],
    "assisted in": ["partnered to", "facilitated", "co-engineered", "contributed to"],
    "involved in": ["participated in", "contributed to", "co-developed"],
    "tasked with": ["executed", "delivered", "spearheaded", "completed"],
    "handled": ["managed", "orchestrated", "administered", "resolved", "oversaw"],
    "did": ["executed", "completed", "implemented", "delivered"],
    "made": ["created", "built", "designed", "engineered", "produced"],
    "used": ["leveraged", "utilized", "applied", "implemented", "employed"],
    "utilized": ["leveraged", "deployed", "implemented", "integrated"],
}

# Alternatives for frequently repeated action verbs
VERB_ALTERNATIVES_MAP: Dict[str, List[str]] = {
    "built": ["engineered", "architected", "constructed", "developed", "implemented"],
    "developed": ["engineered", "built", "architected", "implemented", "designed"],
    "created": ["designed", "engineered", "formulated", "authored", "established"],
    "managed": ["orchestrated", "directed", "coordinated", "spearheaded", "supervised"],
    "led": ["spearheaded", "orchestrated", "directed", "guided", "championed"],
    "improved": ["optimized", "enhanced", "streamlined", "boosted", "accelerated"],
    "optimized": ["streamlined", "enhanced", "accelerated", "maximized", "refined"],
    "implemented": ["executed", "deployed", "integrated", "engineered", "instituted"],
    "designed": ["architected", "engineered", "modeled", "formulated", "crafted"],
    "tested": ["validated", "verified", "benchmarked", "evaluated", "audited"],
    "analyzed": ["evaluated", "assessed", "investigated", "quantified", "benchmarked"],
    "automated": ["streamlined", "orchestrated", "systematized", "engineered"],
    "deployed": ["released", "launched", "provisioned", "shipped"],
    "reduced": ["curtailed", "decreased", "minimized", "curbed", "eliminated"],
    "increased": ["accelerated", "boosted", "maximized", "expanded", "amplified"],
}

# Context keyword cues for smarter alternative selection
CONTEXT_CUES = [
    (r"\b(?:api|microservice|backend|frontend|react|python|sql|database|code|feature|endpoint)\b",
     ["engineered", "architected", "implemented", "developed", "built"]),
    (r"\b(?:cloud|docker|kubernetes|aws|azure|ci/cd|pipeline|server|infrastructure)\b",
     ["deployed", "automated", "orchestrated", "provisioned", "scaled"]),
    (r"\b(?:performance|speed|latency|throughput|uptime|response time|cost|efficiency)\b",
     ["optimized", "accelerated", "streamlined", "boosted", "reduced"]),
    (r"\b(?:team|cross-functional|stakeholder|engineer|client|developer|member)\b",
     ["spearheaded", "mentored", "orchestrated", "directed", "collaborated"]),
    (r"\b(?:bug|issue|incident|defect|outage|bottleneck|problem)\b",
     ["resolved", "diagnosed", "troubleshot", "remediated", "eliminated"]),
]

REPEATED_VERB_THRESHOLD = 3


def _clean_sentence(raw: str) -> str:
    """Clean bullet characters, numbers, and excess whitespace from a sentence."""
    cleaned = raw.strip()
    cleaned = re.sub(r"^[\s•*▪●◦■–\->]+", "", cleaned).strip()
    cleaned = re.sub(r"^(?:\(?\d+[\.\)\-:]\s*|\(\d+\)\s*)", "", cleaned).strip()
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    return cleaned


def _extract_candidate_sentences(
    resume_text: str,
    resume_sections: Optional[Dict[str, str]] = None
) -> List[str]:
    """Extract individual sentences/bullet points for action verb inspection."""
    sentences: List[str] = []

    # Prioritize Work Experience and Projects sections if available
    sources: List[str] = []
    if resume_sections:
        for key in ("experience", "projects"):
            sec_text = (resume_sections.get(key) or "").strip()
            if sec_text:
                sources.append(sec_text)

    # Fallback to full resume text if no targeted section content exists
    if not sources and resume_text:
        sources.append(resume_text)

    for source in sources:
        for line in source.splitlines():
            cleaned = _clean_sentence(line)
            if len(cleaned.split()) >= 4:
                sentences.append(cleaned)

    return sentences


def _get_contextual_alternatives(sentence: str, fallback_verbs: List[str]) -> List[str]:
    """Select the most relevant alternative verbs based on sentence content cues."""
    sentence_lower = sentence.lower()
    for pattern, specialized_verbs in CONTEXT_CUES:
        if re.search(pattern, sentence_lower):
            # Return specialized verbs that are not already present in the sentence
            return [v for v in specialized_verbs if v not in sentence_lower][:4]
    return fallback_verbs[:4]


def analyze_action_verbs(
    resume_text: Optional[str],
    resume_sections: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """Analyze action verbs across the resume.

    Identifies used action verbs, highlights repeated verbs (>= 3 times), detects
    vague/weak phrasing, and generates contextually relevant suggestions alongside
    the original sentences.
    """
    if not resume_text or not resume_text.strip():
        return {
            "total_action_verbs": 0,
            "unique_action_verbs": 0,
            "action_verb_diversity": 0.0,
            "action_verbs_by_category": {},
            "all_verbs_found": {},
            "repeated_verbs": [],
            "sentence_suggestions": [],
            "has_repeated_verbs": False,
            "has_vague_verbs": False,
            "recommendations": ["No text found to analyze action verbs."],
        }

    sentences = _extract_candidate_sentences(resume_text, resume_sections)

    # 1. Count all action verbs across the text
    text_words = [re.sub(r"[^a-zA-Z-]", "", w).lower() for w in resume_text.split() if w.strip()]
    verb_counter: Counter = Counter()

    for word in text_words:
        if word in ALL_ACTION_VERBS:
            verb_counter[word] += 1

    total_action_verbs = sum(verb_counter.values())
    unique_action_verbs = len(verb_counter)
    diversity = round((unique_action_verbs / total_action_verbs * 100), 1) if total_action_verbs > 0 else 0.0

    # Categorize detected verbs
    categorized_verbs: Dict[str, List[Dict[str, Any]]] = {}
    for cat_name, verb_list in ACTION_VERB_CATEGORIES.items():
        matched = [
            {"verb": v, "count": verb_counter[v]}
            for v in verb_list
            if verb_counter[v] > 0
        ]
        if matched:
            categorized_verbs[cat_name] = matched

    # 2. Identify frequently repeated verbs
    repeated_verbs: List[Dict[str, Any]] = []
    for verb, count in verb_counter.most_common():
        if count >= REPEATED_VERB_THRESHOLD:
            default_alts = VERB_ALTERNATIVES_MAP.get(verb, ["engineered", "orchestrated", "implemented", "streamlined"])
            repeated_verbs.append({
                "verb": verb,
                "count": count,
                "suggested_alternatives": default_alts[:4],
            })

    # 3. Analyze candidate sentences for vague verbs and repeated verbs
    sentence_suggestions: List[Dict[str, Any]] = []
    seen_sentence_keys = set()

    for sentence in sentences:
        sentence_lower = sentence.lower()
        first_few_words = " ".join(sentence_lower.split()[:4])

        # Check for vague phrases first
        found_vague = False
        for vague_phrase, default_alts in VAGUE_VERBS_MAP.items():
            if vague_phrase in first_few_words or sentence_lower.startswith(vague_phrase):
                context_alts = _get_contextual_alternatives(sentence, default_alts)
                key = (sentence, vague_phrase)
                if key not in seen_sentence_keys:
                    seen_sentence_keys.add(key)
                    sentence_suggestions.append({
                        "original_sentence": sentence,
                        "verb": vague_phrase,
                        "issue_type": "vague",
                        "message": f"Replace passive or vague phrase '{vague_phrase}' with a strong action verb.",
                        "suggested_alternatives": context_alts,
                    })
                    found_vague = True
                    break

        if found_vague:
            continue

        # Check for repeated verbs in the sentence
        for item in repeated_verbs:
            rep_verb = item["verb"]
            # Look for repeated verb near the beginning of the sentence
            if re.search(rf"\b{rep_verb}\b", first_few_words):
                context_alts = _get_contextual_alternatives(sentence, item["suggested_alternatives"])
                key = (sentence, rep_verb)
                if key not in seen_sentence_keys:
                    seen_sentence_keys.add(key)
                    sentence_suggestions.append({
                        "original_sentence": sentence,
                        "verb": rep_verb,
                        "issue_type": "repeated",
                        "message": f"Action verb '{rep_verb}' is used {item['count']} times in your resume. Diversify with a synonym.",
                        "suggested_alternatives": [a for a in context_alts if a != rep_verb][:4],
                    })
                    break

    # 4. Generate overall recommendations
    recommendations: List[str] = []
    if total_action_verbs < 5:
        recommendations.append(
            "Found few strong action verbs. Start each bullet point with a powerful past-tense action verb (e.g. Engineered, Spearheaded, Accelerated)."
        )

    if repeated_verbs:
        verbs_str = ", ".join(f"'{item['verb']}' ({item['count']}×)" for item in repeated_verbs[:3])
        recommendations.append(
            f"Frequently repeated verbs detected: {verbs_str}. Replace repetitive verbs with context-specific alternatives to keep recruiters engaged."
        )

    vague_count = sum(1 for s in sentence_suggestions if s["issue_type"] == "vague")
    if vague_count > 0:
        recommendations.append(
            f"Identified {vague_count} statement(s) using passive or weak phrasing (like 'worked on' or 'responsible for'). Use direct, results-oriented action verbs instead."
        )

    if not recommendations:
        recommendations.append(
            "Excellent action verb usage! Your resume uses a diverse, high-impact vocabulary that clearly highlights your contributions."
        )

    return {
        "total_action_verbs": total_action_verbs,
        "unique_action_verbs": unique_action_verbs,
        "action_verb_diversity": diversity,
        "action_verbs_by_category": categorized_verbs,
        "all_verbs_found": dict(verb_counter.most_common()),
        "repeated_verbs": repeated_verbs,
        "sentence_suggestions": sentence_suggestions[:10],
        "has_repeated_verbs": len(repeated_verbs) > 0,
        "has_vague_verbs": vague_count > 0,
        "recommendations": recommendations,
    }
