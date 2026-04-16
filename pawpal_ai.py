"""
pawpal_ai.py
Local retrieval-and-classification layer for PawPal Care Coach.

The advisor is intentionally lightweight and reproducible:
- symptom classification is based on nearest-neighbour text similarity
- retrieval uses a small local knowledge base with trusted source URLs
- response generation is template-based so outputs stay grounded and safe
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import csv
import json
import logging
import math
from pathlib import Path
import re

from pawpal_system import Pet, Task

LOGGER = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
KNOWLEDGE_BASE_DIR = BASE_DIR / "knowledge_base"
DEFAULT_SYMPTOM_DATASET = DATA_DIR / "pet_health_symptoms_dataset.csv"
DEFAULT_KB_PATH = KNOWLEDGE_BASE_DIR / "pet_care_docs.json"

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from",
    "has", "have", "he", "her", "his", "i", "in", "is", "it", "its", "my",
    "now", "of", "on", "or", "our", "she", "that", "the", "their", "them",
    "they", "this", "to", "until", "very", "was", "we", "with",
}

CONDITION_KEYWORDS: dict[str, set[str]] = {
    "Digestive Issues": {
        "abdomen", "abdominal", "appetite", "bloat", "bloated", "diarrhea",
        "digestive", "droppings", "eating", "feces", "food", "nausea",
        "stool", "vomit", "vomiting", "water",
    },
    "Ear Infections": {
        "canal", "discharge", "ear", "ears", "head", "hearing", "itchy",
        "painful", "scratch", "shaking", "smell", "swollen",
    },
    "Skin Irritations": {
        "bald", "coat", "crusty", "hotspot", "itch", "itchy", "nodule",
        "patches", "rash", "raw", "red", "redness", "scale", "scaly", "skin",
    },
    "Parasites": {
        "flea", "fleas", "heartworm", "larvae", "lice", "mite", "mites",
        "parasite", "parasites", "stool", "tick", "ticks", "worm", "worms",
    },
    "Mobility Problems": {
        "accident", "arthritis", "broken", "dragging", "hip", "jumping",
        "lame", "leg", "limb", "limping", "mobility", "pain", "paralyzed",
        "paresis", "stiff", "walk", "walking", "weakness",
    },
}

URGENT_KEYWORDS = {
    "bleed", "bleeding", "bloated", "collapse", "collapsed", "distension",
    "distended", "dragging", "labored", "paralyzed", "paralysis", "seizure",
    "severe", "shut", "straining", "unresponsive", "unable",
}

REPEATED_DIGESTIVE_HINTS = {"again", "constant", "continues", "multiple", "repeated"}

SUPPORTED_SPECIES = {"dog", "cat"}


def _normalize_token(token: str) -> str:
    """Apply a tiny amount of stemming so similar symptom words line up."""
    token = token.lower()
    if len(token) > 5 and token.endswith("ing"):
        token = token[:-3]
    elif len(token) > 4 and token.endswith("ed"):
        token = token[:-2]
    elif len(token) > 3 and token.endswith("s"):
        token = token[:-1]
    return token


def tokenize(text: str) -> list[str]:
    """Convert free text into simple normalized word tokens."""
    raw_tokens = re.findall(r"[a-zA-Z']+", text.lower())
    return [
        _normalize_token(token)
        for token in raw_tokens
        if token not in STOPWORDS
    ]


def vectorize(text: str) -> Counter[str]:
    """Return a bag-of-words Counter for a text snippet."""
    return Counter(tokenize(text))


def cosine_similarity(left: Counter[str], right: Counter[str]) -> float:
    """Compute cosine similarity for sparse bag-of-words vectors."""
    if not left or not right:
        return 0.0
    common_terms = set(left) & set(right)
    numerator = sum(left[term] * right[term] for term in common_terms)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        key = item.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append(item.strip())
    return ordered


@dataclass(frozen=True)
class SymptomExample:
    text: str
    condition: str
    record_type: str


@dataclass(frozen=True)
class ClassificationResult:
    condition: str
    confidence: float
    matched_examples: list[SymptomExample]


@dataclass(frozen=True)
class TaskSuggestion:
    title: str
    duration_minutes: int
    priority: str
    frequency: str = "daily"
    category: str = "follow-up"
    rationale: str = ""

    def to_task(self) -> Task:
        """Convert the suggestion into a PawPal task."""
        return Task(
            title=self.title,
            duration_minutes=self.duration_minutes,
            priority=self.priority,
            frequency=self.frequency,
            category=self.category,
        )


@dataclass(frozen=True)
class KnowledgeDocument:
    doc_id: str
    title: str
    conditions: list[str]
    species: list[str]
    topics: list[str]
    source_name: str
    source_url: str
    summary: str
    care_steps: list[str]
    warning_signs: list[str]
    suggested_tasks: list[TaskSuggestion]

    @property
    def searchable_text(self) -> str:
        parts = [
            self.title,
            self.summary,
            " ".join(self.conditions),
            " ".join(self.topics),
            " ".join(self.care_steps),
            " ".join(self.warning_signs),
        ]
        return " ".join(parts)


@dataclass(frozen=True)
class SourceCitation:
    title: str
    source_name: str
    source_url: str


@dataclass(frozen=True)
class AdviceResult:
    pet_name: str
    species: str
    user_query: str
    condition: str
    confidence: float
    is_urgent: bool
    simple_summary: str
    care_steps: list[str]
    warning_signs: list[str]
    escalation_message: str | None
    scope_note: str | None
    citations: list[SourceCitation]
    suggested_tasks: list[TaskSuggestion]
    matched_examples: list[SymptomExample]


def load_symptom_examples(csv_path: Path = DEFAULT_SYMPTOM_DATASET) -> list[SymptomExample]:
    """Load the seed symptom dataset from CSV."""
    examples: list[SymptomExample] = []
    with csv_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            text = (row.get("text") or "").strip()
            condition = (row.get("condition") or "").strip()
            record_type = (row.get("record_type") or "").strip()
            if not text or not condition:
                continue
            examples.append(SymptomExample(text=text, condition=condition, record_type=record_type))
    if not examples:
        raise ValueError(f"No symptom examples found in {csv_path}")
    return examples


def load_knowledge_documents(json_path: Path = DEFAULT_KB_PATH) -> list[KnowledgeDocument]:
    """Load the local knowledge base from JSON."""
    with json_path.open(encoding="utf-8") as handle:
        raw_docs = json.load(handle)

    documents: list[KnowledgeDocument] = []
    for raw_doc in raw_docs:
        documents.append(
            KnowledgeDocument(
                doc_id=raw_doc["doc_id"],
                title=raw_doc["title"],
                conditions=list(raw_doc["conditions"]),
                species=list(raw_doc["species"]),
                topics=list(raw_doc["topics"]),
                source_name=raw_doc["source_name"],
                source_url=raw_doc["source_url"],
                summary=raw_doc["summary"],
                care_steps=list(raw_doc["care_steps"]),
                warning_signs=list(raw_doc["warning_signs"]),
                suggested_tasks=[
                    TaskSuggestion(**task_data) for task_data in raw_doc["suggested_tasks"]
                ],
            )
        )
    if not documents:
        raise ValueError(f"No knowledge-base documents found in {json_path}")
    return documents


class SymptomClassifier:
    """Classify symptom text into one of the known care categories."""

    def __init__(self, examples: list[SymptomExample]):
        self.examples = examples
        self.example_vectors = [(example, vectorize(example.text)) for example in examples]

    def classify(self, query: str, top_k: int = 5) -> ClassificationResult:
        query_vector = vectorize(query)
        scores_by_condition: dict[str, float] = defaultdict(float)
        scored_examples: list[tuple[float, SymptomExample]] = []

        for example, example_vector in self.example_vectors:
            score = cosine_similarity(query_vector, example_vector)
            if score > 0:
                scored_examples.append((score, example))
                scores_by_condition[example.condition] += score

        query_tokens = set(query_vector)
        for condition, keywords in CONDITION_KEYWORDS.items():
            overlap_count = len(query_tokens & keywords)
            if overlap_count:
                scores_by_condition[condition] += 0.18 * overlap_count

        if not scores_by_condition:
            fallback = "Digestive Issues"
            return ClassificationResult(condition=fallback, confidence=0.2, matched_examples=[])

        ranked_conditions = sorted(
            scores_by_condition.items(),
            key=lambda item: item[1],
            reverse=True,
        )
        best_condition, best_score = ranked_conditions[0]
        second_score = ranked_conditions[1][1] if len(ranked_conditions) > 1 else 0.0
        confidence = max(0.2, min(best_score / (best_score + second_score + 0.35), 0.98))
        matched_examples = [
            example
            for _, example in sorted(scored_examples, key=lambda item: item[0], reverse=True)[:top_k]
        ]

        LOGGER.info(
            "Classified symptom text",
            extra={
                "condition": best_condition,
                "confidence": round(confidence, 3),
            },
        )
        return ClassificationResult(
            condition=best_condition,
            confidence=round(confidence, 2),
            matched_examples=matched_examples,
        )


class KnowledgeBase:
    """Retrieve the most relevant local documents for a classified symptom query."""

    def __init__(self, documents: list[KnowledgeDocument]):
        self.documents = documents
        self.document_vectors = {
            document.doc_id: vectorize(document.searchable_text) for document in documents
        }

    def retrieve(self, query: str, condition: str, species: str, limit: int = 3) -> list[KnowledgeDocument]:
        query_vector = vectorize(query)
        normalized_species = species.lower()
        candidate_documents = [
            document
            for document in self.documents
            if condition in document.conditions or "all" in document.conditions
        ]
        if not candidate_documents:
            candidate_documents = list(self.documents)
        scored_documents: list[tuple[float, KnowledgeDocument]] = []

        for document in candidate_documents:
            score = cosine_similarity(query_vector, self.document_vectors[document.doc_id])
            if condition in document.conditions:
                score += 0.9
            if "all" in document.conditions:
                score += 0.15
            if normalized_species in document.species:
                score += 0.2
            elif normalized_species not in SUPPORTED_SPECIES:
                score += 0.05
            topic_overlap = len(set(tokenize(query)) & set(tokenize(" ".join(document.topics))))
            score += topic_overlap * 0.08
            scored_documents.append((score, document))

        ranked_documents = [
            document
            for score, document in sorted(scored_documents, key=lambda item: item[0], reverse=True)
            if score > 0
        ]
        if not ranked_documents:
            return self.documents[:limit]
        return ranked_documents[:limit]


class PetCareAdvisor:
    """Combine classification, retrieval, and safe response generation."""

    def __init__(self, classifier: SymptomClassifier, knowledge_base: KnowledgeBase):
        self.classifier = classifier
        self.knowledge_base = knowledge_base

    def advise(self, pet: Pet, query: str) -> AdviceResult:
        cleaned_query = query.strip()
        if not cleaned_query:
            raise ValueError("Please describe the symptom or care question first.")

        classification = self.classifier.classify(cleaned_query)
        retrieved_docs = self.knowledge_base.retrieve(
            cleaned_query,
            condition=classification.condition,
            species=pet.species,
        )
        urgent = self._is_urgent(cleaned_query, classification.condition, retrieved_docs)
        care_steps = _dedupe_keep_order(
            [step for document in retrieved_docs for step in document.care_steps]
        )[:4]
        warning_signs = _dedupe_keep_order(
            [sign for document in retrieved_docs for sign in document.warning_signs]
        )[:5]
        suggested_tasks = self._build_task_suggestions(retrieved_docs, urgent)
        escalation_message = self._build_escalation_message(classification.condition, urgent)
        scope_note = None
        if pet.species.lower() not in SUPPORTED_SPECIES:
            scope_note = (
                "This knowledge base is focused on dogs and cats, so guidance for other species "
                "should be treated as limited and checked with a veterinarian."
            )

        summary = self._build_summary(
            pet=pet,
            condition=classification.condition,
            confidence=classification.confidence,
            urgent=urgent,
            docs=retrieved_docs,
        )
        citations = [
            SourceCitation(
                title=document.title,
                source_name=document.source_name,
                source_url=document.source_url,
            )
            for document in retrieved_docs
        ]

        LOGGER.info(
            "Generated care advice",
            extra={
                "pet_name": pet.name,
                "species": pet.species,
                "condition": classification.condition,
                "urgent": urgent,
                "citations": len(citations),
            },
        )
        return AdviceResult(
            pet_name=pet.name,
            species=pet.species,
            user_query=cleaned_query,
            condition=classification.condition,
            confidence=classification.confidence,
            is_urgent=urgent,
            simple_summary=summary,
            care_steps=care_steps,
            warning_signs=warning_signs,
            escalation_message=escalation_message,
            scope_note=scope_note,
            citations=citations,
            suggested_tasks=suggested_tasks,
            matched_examples=classification.matched_examples[:3],
        )

    def _is_urgent(self, query: str, condition: str, documents: list[KnowledgeDocument]) -> bool:
        query_tokens = set(tokenize(query))
        if query_tokens & URGENT_KEYWORDS:
            return True
        if {"vomit", "vomiting"} & query_tokens:
            repeated_hint = bool(query_tokens & REPEATED_DIGESTIVE_HINTS)
            repeated_hint = repeated_hint or bool(re.search(r"\b([3-9]|\d{2,})\b", query))
            if repeated_hint:
                return True
        if condition == "Mobility Problems" and {"broken", "paralyzed", "dragging"} & query_tokens:
            return True
        if condition == "Digestive Issues" and {"distension", "bloated", "bloat"} & query_tokens:
            return True
        warning_tokens = {
            token
            for document in documents
            for sign in document.warning_signs
            for token in tokenize(sign)
        }
        return bool(query_tokens & (warning_tokens & URGENT_KEYWORDS))

    def _build_escalation_message(self, condition: str, urgent: bool) -> str | None:
        if urgent:
            return (
                "This description includes warning signs. Contact a veterinarian promptly "
                "or seek urgent care today."
            )
        if condition in {"Digestive Issues", "Mobility Problems"}:
            return (
                "If symptoms get worse, your pet stops eating, or pain increases, contact "
                "your veterinarian for next steps."
            )
        return None

    def _build_summary(
        self,
        pet: Pet,
        condition: str,
        confidence: float,
        urgent: bool,
        docs: list[KnowledgeDocument],
    ) -> str:
        confidence_label = "high" if confidence >= 0.7 else "moderate" if confidence >= 0.45 else "low"
        first_doc = docs[0]
        summary = (
            f"This sounds most related to {condition.lower()} for {pet.name}. "
            f"My match confidence is {confidence_label}, so use this as general guidance rather "
            f"than a diagnosis. {first_doc.summary}"
        )
        if urgent:
            summary += " Because the symptoms may be urgent, same-day veterinary contact is the safest next step."
        return summary

    def _build_task_suggestions(
        self,
        documents: list[KnowledgeDocument],
        urgent: bool,
    ) -> list[TaskSuggestion]:
        suggestions = [
            task
            for document in documents
            for task in document.suggested_tasks
        ]
        deduped: list[TaskSuggestion] = []
        seen_titles: set[str] = set()
        if urgent:
            urgent_task = TaskSuggestion(
                title="Call veterinary clinic",
                duration_minutes=15,
                priority="high",
                frequency="as-needed",
                category="medical",
                rationale="Urgent symptom descriptions should trigger immediate follow-up.",
            )
            suggestions.insert(0, urgent_task)

        for suggestion in suggestions:
            key = suggestion.title.lower()
            if key in seen_titles:
                continue
            seen_titles.add(key)
            deduped.append(suggestion)
        return deduped[:4]


def create_default_care_advisor() -> PetCareAdvisor:
    """Load the seed dataset and knowledge base from local project files."""
    examples = load_symptom_examples()
    documents = load_knowledge_documents()
    return PetCareAdvisor(
        classifier=SymptomClassifier(examples),
        knowledge_base=KnowledgeBase(documents),
    )
