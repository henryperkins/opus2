"""
Tests for PostgresVectorService._to_pgvector method.
"""

import numpy as np
import pytest

from app.services.postgres_vector_service import PostgresVectorService


class TestToPgvector:
    """Test the _to_pgvector method handles both lists and numpy arrays."""

    def test_to_pgvector_accepts_list(self):
        """Test that _to_pgvector handles plain Python lists."""
        expected = "[0.100000,0.200000,0.300000]"
        result = PostgresVectorService._to_pgvector([0.1, 0.2, 0.3])
        assert result == expected

    def test_to_pgvector_accepts_tuple(self):
        """Test that _to_pgvector handles tuples."""
        expected = "[0.100000,0.200000,0.300000]"
        result = PostgresVectorService._to_pgvector((0.1, 0.2, 0.3))
        assert result == expected

    def test_to_pgvector_accepts_numpy_array(self):
        """Test that _to_pgvector handles numpy arrays."""
        expected = "[0.100000,0.200000,0.300000]"
        result = PostgresVectorService._to_pgvector(np.array([0.1, 0.2, 0.3]))
        assert result == expected

    def test_to_pgvector_formatting_precision(self):
        """Test that _to_pgvector formats floats with correct precision."""
        expected = "[0.123456,0.654321]"
        result = PostgresVectorService._to_pgvector([0.123456789, 0.654321123])
        assert result == expected

    def test_to_pgvector_rejects_invalid_type(self):
        """Test that _to_pgvector raises TypeError for invalid input."""
        with pytest.raises(TypeError, match="Vector must be list/tuple/ndarray"):
            PostgresVectorService._to_pgvector("invalid")

    def test_to_pgvector_rejects_dict(self):
        """Test that _to_pgvector raises TypeError for dict input."""
        with pytest.raises(TypeError, match="Vector must be list/tuple/ndarray"):
            PostgresVectorService._to_pgvector({"x": 0.1, "y": 0.2})
