"""
Confidence scoring service for RAG operations.

This service calculates confidence scores for RAG responses based on:
- Similarity scores from vector search
- Source quality metrics
- Document recency
- User feedback history
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import statistics
import logging

logger = logging.getLogger(__name__)


class ConfidenceService:
    """Service for calculating RAG confidence scores."""

    def __init__(self):
        self.base_confidence_weights = {
            'similarity_score': 0.4,
            'source_quality': 0.3,
            'recency': 0.2,
            'user_feedback': 0.1
        }

    def calculate_rag_confidence(
        self, 
        knowledge_results: List[Dict[str, Any]], 
        user_feedback_history: Optional[List[Dict]] = None
    ) -> float:
        """
        Calculate overall confidence for RAG response.
        
        Args:
            knowledge_results: List of search results with scores and metadata
            user_feedback_history: Historical user feedback for similar queries
            
        Returns:
            Float between 0.0 and 1.0 representing confidence level
        """
        if not knowledge_results:
            return 0.0

        confidences = []
        total_weight = 0.0

        for result in knowledge_results:
            # Calculate individual result confidence
            result_confidence = self._calculate_result_confidence(result, user_feedback_history)
            
            # Weight by similarity score (higher similarity = more influence)
            weight = result.get('score', 0.5)
            confidences.append(result_confidence * weight)
            total_weight += weight

        # Weighted average confidence
        if total_weight > 0:
            avg_confidence = sum(confidences) / total_weight
        else:
            avg_confidence = 0.0

        # Apply diminishing returns for multiple sources
        source_count = len(knowledge_results)
        if source_count > 1:
            # Boost confidence slightly for multiple confirming sources
            diversity_boost = min(0.1, (source_count - 1) * 0.02)
            avg_confidence = min(1.0, avg_confidence + diversity_boost)

        return round(avg_confidence, 3)

    def _calculate_result_confidence(
        self, 
        result: Dict[str, Any], 
        user_feedback_history: Optional[List[Dict]] = None
    ) -> float:
        """Calculate confidence for a single search result."""
        
        # Base similarity confidence
        similarity_conf = min(result.get('score', 0), 1.0)
        
        # Source quality confidence
        source_conf = self._calculate_source_quality(result)
        
        # Recency confidence
        recency_conf = self._calculate_recency_confidence(result)
        
        # User feedback confidence
        feedback_conf = self._calculate_feedback_confidence(result, user_feedback_history)
        
        # Weighted combination
        confidence = (
            similarity_conf * self.base_confidence_weights['similarity_score'] +
            source_conf * self.base_confidence_weights['source_quality'] +
            recency_conf * self.base_confidence_weights['recency'] +
            feedback_conf * self.base_confidence_weights['user_feedback']
        )
        
        return min(confidence, 1.0)

    def _calculate_source_quality(self, result: Dict[str, Any]) -> float:
        """Calculate confidence based on source type and metadata."""
        # Try to get source_type from multiple places
        source_type = result.get('source_type')
        
        # Fallback 1: Check in metadata if not at top level
        if not source_type:
            metadata = result.get('metadata', {})
            if isinstance(metadata, dict):
                source_type = metadata.get('source_type')
        
        # Fallback 2: Infer from other fields if still missing
        if not source_type:
            source_type = self._infer_source_type(result)
        
        # Final fallback
        if not source_type:
            source_type = 'unknown'
        
        # Quality scores for different source types
        quality_scores = {
            'official_docs': 0.95,
            'code_with_tests': 0.90,
            'documentation': 0.85,
            'code_comments': 0.75,
            'readme_file': 0.70,
            'user_uploaded': 0.65,
            'auto_extracted': 0.60,
            'unknown': 0.50
        }
        
        base_quality = quality_scores.get(source_type.lower(), 0.50)
        
        # Adjust based on additional metadata
        metadata = result.get('metadata', {})
        
        # Boost for code with good structure
        if metadata.get('has_docstrings'):
            base_quality = min(1.0, base_quality + 0.05)
        
        if metadata.get('has_type_hints'):
            base_quality = min(1.0, base_quality + 0.05)
            
        # Penalize for potential issues
        if metadata.get('has_todos') or metadata.get('has_fixmes'):
            base_quality = max(0.0, base_quality - 0.1)
            
        return base_quality

    def _calculate_recency_confidence(self, result: Dict[str, Any]) -> float:
        """Calculate confidence based on document recency."""
        last_modified = result.get('last_modified')
        if not last_modified:
            return 0.6  # Neutral score for unknown dates
            
        try:
            if isinstance(last_modified, str):
                modified_date = datetime.fromisoformat(last_modified.replace('Z', '+00:00'))
            else:
                modified_date = last_modified
                
            days_old = (datetime.now() - modified_date.replace(tzinfo=None)).days
            
            # Confidence decreases with age
            if days_old <= 7:
                return 1.0  # Very recent
            elif days_old <= 30:
                return 0.9  # Recent
            elif days_old <= 90:
                return 0.8  # Somewhat recent
            elif days_old <= 365:
                return 0.6  # Older but reasonable
            else:
                return 0.4  # Very old
                
        except (ValueError, TypeError) as e:
            logger.warning(f"Error parsing date {last_modified}: {e}")
            return 0.6

    def _calculate_feedback_confidence(
        self, 
        result: Dict[str, Any], 
        feedback_history: Optional[List[Dict]] = None
    ) -> float:
        """Adjust confidence based on user feedback for similar results."""
        if not feedback_history:
            return 0.5  # Neutral score when no feedback available
            
        source_path = result.get('source_path', '')
        source_type = result.get('source_type', '')
        
        # Find relevant feedback
        relevant_feedback = []
        for feedback in feedback_history:
            # Exact match on source
            if feedback.get('source_path') == source_path:
                relevant_feedback.append(feedback)
            # Similar source type
            elif feedback.get('source_type') == source_type:
                relevant_feedback.append(feedback)
                
        if not relevant_feedback:
            return 0.5
            
        # Calculate positive feedback ratio
        helpful_count = sum(1 for f in relevant_feedback if f.get('helpful', False))
        total_count = len(relevant_feedback)
        
        if total_count == 0:
            return 0.5
            
        positive_ratio = helpful_count / total_count
        
        # Convert to confidence score with some smoothing
        if total_count < 3:
            # Less confident with little feedback data
            return 0.5 + (positive_ratio - 0.5) * 0.3
        else:
            # More confident with more feedback data
            return positive_ratio

    def _infer_source_type(self, result: Dict[str, Any]) -> str:
        """Infer source type from available result fields."""
        metadata = result.get('metadata', {})
        
        # Check for code-related fields
        if any(field in result for field in ['chunk_id', 'file_path', 'language']):
            return 'auto_extracted'
        
        # Check metadata for hints
        if isinstance(metadata, dict):
            if metadata.get('category'):
                category = metadata.get('category', '').lower()
                category_mapping = {
                    'documentation': 'documentation',
                    'code': 'auto_extracted',
                    'readme': 'readme_file',
                    'manual': 'user_uploaded',
                    'api_docs': 'official_docs',
                    'tutorial': 'documentation',
                    'notes': 'user_uploaded',
                }
                return category_mapping.get(category, 'unknown')
            
            if metadata.get('file_path'):
                file_path = metadata.get('file_path', '').lower()
                if 'readme' in file_path:
                    return 'readme_file'
                elif any(ext in file_path for ext in ['.md', '.rst', '.txt']):
                    return 'documentation'
        
        return 'unknown'

    def calculate_degradation_status(
        self, 
        confidence: float, 
        knowledge_results: List[Dict[str, Any]],
        error_message: Optional[str] = None
    ) -> str:
        """
        Determine RAG status based on confidence and results.
        
        Returns: 'active', 'degraded', 'poor', 'error', or 'standard'
        """
        if error_message:
            return 'error'
            
        if not knowledge_results:
            return 'standard'
            
        if confidence >= 0.8:
            return 'active'
        elif confidence >= 0.6:
            return 'degraded'
        elif confidence >= 0.3:
            return 'poor'
        else:
            return 'poor'

    def get_confidence_explanation(self, confidence: float) -> str:
        """Get human-readable explanation of confidence level."""
        if confidence >= 0.9:
            return "Very high confidence - multiple high-quality sources confirm this information"
        elif confidence >= 0.8:
            return "High confidence - reliable sources support this response"
        elif confidence >= 0.7:
            return "Good confidence - sources are relevant and reasonably reliable"
        elif confidence >= 0.6:
            return "Moderate confidence - some uncertainty in source quality or relevance"
        elif confidence >= 0.5:
            return "Low confidence - limited or less reliable source information"
        else:
            return "Very low confidence - sources may not be reliable or relevant"