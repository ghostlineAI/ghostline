"""
Voice Metrics Service for strict numeric voice similarity.

Provides:
- Stylometry feature extraction (sentence length, vocabulary, punctuation, etc.)
- Numeric voice similarity computation (not LLM-judged)
- Embedding + stylometry combined scoring
- Voice profile calibration

This replaces the LLM-judged "score" with a deterministic, reproducible metric.
"""

import logging
import re
import statistics
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from app.services.embeddings import EmbeddingService, get_embedding_service

logger = logging.getLogger(__name__)


@dataclass
class StylometryFeatures:
    """
    Stylometry features extracted from text.
    
    These are numeric features that characterize writing style.
    """
    # Sentence-level
    avg_sentence_length: float = 0.0  # Words per sentence
    sentence_length_std: float = 0.0  # Variation in sentence length
    sentence_count: int = 0
    
    # Word-level
    avg_word_length: float = 0.0  # Characters per word
    vocabulary_complexity: float = 0.0  # Type-token ratio (unique words / total words)
    vocabulary_richness: float = 0.0  # Hapax legomena ratio (words appearing once / total unique)
    
    # Punctuation
    punctuation_density: float = 0.0  # Punctuation marks per 100 words
    question_ratio: float = 0.0  # Questions per sentence
    exclamation_ratio: float = 0.0  # Exclamations per sentence
    comma_density: float = 0.0  # Commas per 100 words
    semicolon_density: float = 0.0  # Semicolons per 100 words
    
    # Paragraph
    avg_paragraph_length: float = 0.0  # Sentences per paragraph
    paragraph_count: int = 0
    
    # Total metrics
    total_words: int = 0
    total_characters: int = 0
    
    def to_vector(self) -> list[float]:
        """Convert features to a normalized vector for comparison."""
        return [
            self.avg_sentence_length / 30.0,  # Normalize to ~0-1 range
            self.sentence_length_std / 15.0,
            self.avg_word_length / 10.0,
            self.vocabulary_complexity,  # Already 0-1
            self.vocabulary_richness,  # Already 0-1
            self.punctuation_density / 20.0,
            self.question_ratio,  # Already 0-1
            self.exclamation_ratio,  # Already 0-1
            self.comma_density / 10.0,
            self.semicolon_density / 2.0,
            min(self.avg_paragraph_length / 10.0, 1.0),
        ]


@dataclass
class VoiceSimilarityResult:
    """Result from voice similarity comparison."""
    # Combined score (0-1, higher is more similar)
    overall_score: float
    
    # Component scores
    embedding_similarity: float  # Cosine similarity of embeddings
    stylometry_similarity: float  # Stylometry vector similarity
    
    # Weights used
    embedding_weight: float
    stylometry_weight: float
    
    # Individual feature differences
    feature_differences: dict = field(default_factory=dict)
    
    # Diagnosis
    passes_threshold: bool = False
    threshold: float = 0.85
    
    def get_diagnosis(self) -> str:
        """Get a human-readable diagnosis of voice match."""
        if self.passes_threshold:
            return f"Voice match: {self.overall_score:.2%} (≥{self.threshold:.0%} threshold)"
        
        # Find the biggest mismatches
        issues = []
        for feature, diff in sorted(self.feature_differences.items(), key=lambda x: -x[1]):
            if diff > 0.2:
                issues.append(f"{feature} differs by {diff:.1%}")
        
        if issues:
            issue_str = ", ".join(issues[:3])
            return f"Voice mismatch: {self.overall_score:.2%} ({issue_str})"
        
        return f"Voice mismatch: {self.overall_score:.2%} (below {self.threshold:.0%} threshold)"


class VoiceMetricsService:
    """
    Service for computing strict numeric voice similarity.
    
    Uses a combination of:
    1. Embedding similarity (semantic style)
    2. Stylometry features (structural style)
    
    This provides a reproducible, calibrated metric instead of LLM-judged scores.
    """
    
    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        default_embedding_weight: float = 0.4,
    ):
        self.embeddings = embedding_service or get_embedding_service()
        self.default_embedding_weight = default_embedding_weight
    
    def extract_features(self, text: str) -> StylometryFeatures:
        """
        Extract stylometry features from text.
        
        Args:
            text: The text to analyze
            
        Returns:
            StylometryFeatures with computed metrics
        """
        if not text or not text.strip():
            return StylometryFeatures()
        
        # Split into paragraphs
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        if not paragraphs:
            paragraphs = [text]
        
        # Split into sentences (simple heuristic)
        sentence_pattern = r'[.!?]+[\s\n]+'
        sentences = re.split(sentence_pattern, text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            sentences = [text]
        
        # Split into words
        word_pattern = r'\b\w+\b'
        words = re.findall(word_pattern, text.lower())
        
        if not words:
            return StylometryFeatures()
        
        # Compute features
        features = StylometryFeatures()
        features.total_words = len(words)
        features.total_characters = len(text)
        features.sentence_count = len(sentences)
        features.paragraph_count = len(paragraphs)
        
        # Sentence-level
        sentence_lengths = [len(re.findall(word_pattern, s)) for s in sentences]
        sentence_lengths = [l for l in sentence_lengths if l > 0]
        
        if sentence_lengths:
            features.avg_sentence_length = statistics.mean(sentence_lengths)
            if len(sentence_lengths) > 1:
                features.sentence_length_std = statistics.stdev(sentence_lengths)
        
        # Word-level
        word_lengths = [len(w) for w in words]
        features.avg_word_length = statistics.mean(word_lengths) if word_lengths else 0
        
        unique_words = set(words)
        features.vocabulary_complexity = len(unique_words) / len(words) if words else 0
        
        # Hapax legomena (words appearing exactly once)
        word_counts = {}
        for w in words:
            word_counts[w] = word_counts.get(w, 0) + 1
        hapax = sum(1 for count in word_counts.values() if count == 1)
        features.vocabulary_richness = hapax / len(unique_words) if unique_words else 0
        
        # Punctuation
        punctuation_count = len(re.findall(r'[.,;:!?"\'\-]', text))
        features.punctuation_density = (punctuation_count / len(words)) * 100 if words else 0
        
        question_count = text.count('?')
        exclamation_count = text.count('!')
        features.question_ratio = question_count / len(sentences) if sentences else 0
        features.exclamation_ratio = exclamation_count / len(sentences) if sentences else 0
        
        comma_count = text.count(',')
        semicolon_count = text.count(';')
        features.comma_density = (comma_count / len(words)) * 100 if words else 0
        features.semicolon_density = (semicolon_count / len(words)) * 100 if words else 0
        
        # Paragraph
        sentences_per_paragraph = len(sentences) / len(paragraphs) if paragraphs else 0
        features.avg_paragraph_length = sentences_per_paragraph
        
        return features
    
    def compute_stylometry_similarity(
        self,
        features1: StylometryFeatures,
        features2: StylometryFeatures,
    ) -> tuple[float, dict]:
        """
        Compute similarity between two stylometry feature sets.
        
        Returns:
            Tuple of (similarity_score, feature_differences)
        """
        vec1 = np.array(features1.to_vector())
        vec2 = np.array(features2.to_vector())
        
        # Compute per-feature differences
        differences = np.abs(vec1 - vec2)
        
        feature_names = [
            "sentence_length", "sentence_variation", "word_length",
            "vocabulary_complexity", "vocabulary_richness",
            "punctuation_density", "question_ratio", "exclamation_ratio",
            "comma_density", "semicolon_density", "paragraph_length"
        ]
        
        feature_diffs = {name: float(diff) for name, diff in zip(feature_names, differences)}
        
        # Compute similarity (1 - average absolute difference)
        # Weighted to emphasize certain features
        weights = np.array([2.0, 1.0, 1.5, 2.0, 1.5, 1.0, 1.0, 1.0, 0.5, 0.5, 0.5])
        weighted_diff = np.average(differences, weights=weights)
        
        similarity = max(0.0, 1.0 - weighted_diff)
        
        return similarity, feature_diffs
    
    def compute_similarity(
        self,
        text1: str,
        text2: str,
        embedding_weight: Optional[float] = None,
        threshold: float = 0.85,
    ) -> VoiceSimilarityResult:
        """
        Compute voice similarity between two texts.
        
        Args:
            text1: First text (typically the reference/profile)
            text2: Second text (typically the generated content)
            embedding_weight: Weight for embedding similarity (0-1)
            threshold: Minimum score to pass
            
        Returns:
            VoiceSimilarityResult with detailed scores
        """
        embedding_weight = embedding_weight or self.default_embedding_weight
        stylometry_weight = 1.0 - embedding_weight
        
        # Extract stylometry features
        features1 = self.extract_features(text1)
        features2 = self.extract_features(text2)
        
        # Compute stylometry similarity
        stylometry_sim, feature_diffs = self.compute_stylometry_similarity(features1, features2)
        
        # Compute embedding similarity
        emb1 = self.embeddings.embed_text(text1)
        emb2 = self.embeddings.embed_text(text2)
        embedding_sim = self.embeddings.similarity(emb1.embedding, emb2.embedding)
        
        # Combine scores
        overall_score = (
            embedding_weight * embedding_sim +
            stylometry_weight * stylometry_sim
        )
        
        return VoiceSimilarityResult(
            overall_score=overall_score,
            embedding_similarity=embedding_sim,
            stylometry_similarity=stylometry_sim,
            embedding_weight=embedding_weight,
            stylometry_weight=stylometry_weight,
            feature_differences=feature_diffs,
            passes_threshold=overall_score >= threshold,
            threshold=threshold,
        )
    
    def compute_similarity_to_profile(
        self,
        profile_embedding: list[float],
        profile_features: StylometryFeatures,
        content: str,
        embedding_weight: Optional[float] = None,
        threshold: float = 0.85,
    ) -> VoiceSimilarityResult:
        """
        Compute similarity between content and a pre-computed voice profile.
        
        This is more efficient when comparing multiple texts to the same profile.
        """
        embedding_weight = embedding_weight or self.default_embedding_weight
        stylometry_weight = 1.0 - embedding_weight
        
        # Extract features from content
        content_features = self.extract_features(content)
        
        # Compute stylometry similarity
        stylometry_sim, feature_diffs = self.compute_stylometry_similarity(
            profile_features, content_features
        )
        
        # Compute embedding similarity
        content_emb = self.embeddings.embed_text(content)
        embedding_sim = self.embeddings.similarity(profile_embedding, content_emb.embedding)
        
        # Combine scores
        overall_score = (
            embedding_weight * embedding_sim +
            stylometry_weight * stylometry_sim
        )
        
        return VoiceSimilarityResult(
            overall_score=overall_score,
            embedding_similarity=embedding_sim,
            stylometry_similarity=stylometry_sim,
            embedding_weight=embedding_weight,
            stylometry_weight=stylometry_weight,
            feature_differences=feature_diffs,
            passes_threshold=overall_score >= threshold,
            threshold=threshold,
        )


# Global singleton
_voice_metrics_service: Optional[VoiceMetricsService] = None


def get_voice_metrics_service() -> VoiceMetricsService:
    """Get the global voice metrics service instance."""
    global _voice_metrics_service
    if _voice_metrics_service is None:
        _voice_metrics_service = VoiceMetricsService()
    return _voice_metrics_service


def reset_voice_metrics_service():
    """Reset the global service (for testing)."""
    global _voice_metrics_service
    _voice_metrics_service = None

