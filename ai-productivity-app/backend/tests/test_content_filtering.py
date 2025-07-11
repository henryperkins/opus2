"""Tests for content filtering functionality."""

import pytest
from app.services.content_filter import ContentFilter, content_filter


class TestContentFilter:
    """Test content filtering functionality."""

    def test_filter_chunk_with_secrets(self):
        """Test filtering chunks containing secrets."""

        chunk = {
            "content": "API_KEY = 'sk-1234567890abcdefghijklmnopqrstuvwxyz'\nprint('Hello World')",
            "metadata": {"file_path": "config.py"},
            "document_id": 1,
            "chunk_id": 1,
        }

        filtered_chunk = content_filter.filter_chunk(chunk)

        # Should have redacted the API key
        assert "[REDACTED API Key]" in filtered_chunk["content"]
        assert "Hello World" in filtered_chunk["content"]  # Safe content preserved

        # Should have added metadata
        assert filtered_chunk["metadata"]["content_filtered"] is True
        assert filtered_chunk["metadata"]["redacted_secrets"] == 1
        assert "API Key" in filtered_chunk["metadata"]["redaction_summary"]

    def test_filter_chunk_safe_content(self):
        """Test filtering chunks with no secrets."""

        chunk = {
            "content": "def hello_world():\n    print('Hello World')\n    return True",
            "metadata": {"file_path": "utils.py"},
            "document_id": 1,
            "chunk_id": 1,
        }

        filtered_chunk = content_filter.filter_chunk(chunk)

        # Should be unchanged
        assert filtered_chunk == chunk
        assert "content_filtered" not in filtered_chunk.get("metadata", {})

    def test_should_exclude_chunk_strict_mode(self):
        """Test chunk exclusion in strict mode."""

        high_severity_chunk = {
            "content": "-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA...",
            "metadata": {"file_path": "secrets.pem"},
        }

        # Should exclude in strict mode
        assert content_filter.should_exclude_chunk(
            high_severity_chunk, strict_mode=True
        )

        # Should not exclude in normal mode (would redact instead)
        assert not content_filter.should_exclude_chunk(
            high_severity_chunk, strict_mode=False
        )

    def test_should_exclude_chunk_high_redaction_ratio(self):
        """Test chunk exclusion when most content would be redacted."""

        mostly_secrets_chunk = {
            "content": "API_KEY='secret1'\nSECRET_KEY='secret2'\nDB_PASSWORD='secret3'\n# Small comment",
            "metadata": {"file_path": "config.py"},
        }

        # Should exclude when redaction ratio is too high
        assert content_filter.should_exclude_chunk(
            mostly_secrets_chunk, strict_mode=False
        )

    def test_filter_and_validate_chunks(self):
        """Test batch filtering and validation."""

        chunks = [
            {
                "content": "def safe_function():\n    return 'safe'",
                "metadata": {"file_path": "safe.py"},
            },
            {
                "content": "API_KEY = 'sk-secret123'\nprint('Using API')",
                "metadata": {"file_path": "config.py"},
            },
            {
                "content": "-----BEGIN PRIVATE KEY-----\nVERY_SECRET_KEY_DATA",
                "metadata": {"file_path": "secrets.pem"},
            },
        ]

        filtered_chunks, warnings = content_filter.filter_and_validate_chunks(
            chunks, strict_mode=True
        )

        # Should have 2 chunks (safe one + filtered one, private key excluded)
        assert len(filtered_chunks) == 2
        assert len(warnings) >= 2  # At least redaction warning + exclusion warning

        # Check that private key chunk was excluded
        assert not any(
            "PRIVATE KEY" in chunk.get("content", "") for chunk in filtered_chunks
        )

        # Check that API key was redacted
        config_chunk = next(
            (
                c
                for c in filtered_chunks
                if "config.py" in c.get("metadata", {}).get("file_path", "")
            ),
            None,
        )
        assert config_chunk is not None
        assert "[REDACTED API Key]" in config_chunk["content"]

    def test_is_content_safe(self):
        """Test content safety assessment."""

        safe_content = "def calculate_sum(a, b):\n    return a + b"
        is_safe, warnings = content_filter.is_content_safe(safe_content)

        assert is_safe is True
        assert len(warnings) == 0

        unsafe_content = "-----BEGIN PRIVATE KEY-----\nSECRET_DATA"
        is_safe, warnings = content_filter.is_content_safe(unsafe_content)

        assert is_safe is False
        assert len(warnings) > 0
        assert "high-severity secrets" in warnings[0]

    def test_get_safe_preview(self):
        """Test safe preview generation."""

        content_with_secret = (
            "API_KEY = 'sk-secret123'\n" + "def function():\n    pass\n" * 20
        )

        preview = content_filter.get_safe_preview(content_with_secret, max_length=100)

        # Should be redacted and truncated
        assert "[REDACTED API Key]" in preview
        assert len(preview) <= 103  # 100 + "..."
        assert preview.endswith("...")

    def test_multiple_secret_types(self):
        """Test detection of multiple secret types."""

        chunk = {
            "content": """
            API_KEY = 'sk-1234567890abcdefghijklmnopqrstuvwxyz'
            AWS_ACCESS_KEY = 'AKIAIOSFODNN7EXAMPLE'
            PASSWORD = 'super_secret_password123'
            """,
            "metadata": {"file_path": "config.py"},
        }

        filtered_chunk = content_filter.filter_chunk(chunk)

        # Should have redacted all three secrets
        assert "[REDACTED API Key]" in filtered_chunk["content"]
        assert "[REDACTED AWS Access Key]" in filtered_chunk["content"]
        assert "[REDACTED Password]" in filtered_chunk["content"]

        assert filtered_chunk["metadata"]["redacted_secrets"] == 3

    def test_jwt_token_detection(self):
        """Test JWT token detection and redaction."""

        chunk = {
            "content": "token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c'",
            "metadata": {"file_path": "auth.py"},
        }

        filtered_chunk = content_filter.filter_chunk(chunk)

        assert "[REDACTED JWT Token]" in filtered_chunk["content"]
        assert filtered_chunk["metadata"]["content_filtered"] is True

    def test_database_url_redaction(self):
        """Test database URL password redaction."""

        chunk = {
            "content": "DATABASE_URL = 'postgresql://user:secret_password@localhost:5432/mydb'",
            "metadata": {"file_path": "settings.py"},
        }

        filtered_chunk = content_filter.filter_chunk(chunk)

        assert "[REDACTED Database Password]" in filtered_chunk["content"]
        assert "postgresql://user" in filtered_chunk["content"]  # Safe parts preserved
        assert "secret_password" not in filtered_chunk["content"]

    def test_high_entropy_string_detection(self):
        """Test high entropy string detection."""

        # High entropy base64-like string
        chunk = {
            "content": "secret_token = 'aGVsbG93b3JsZGhlbGxvd29ybGRoZWxsb3dvcmxkaGVsbG93b3JsZA=='",
            "metadata": {"file_path": "tokens.py"},
        }

        filtered_chunk = content_filter.filter_chunk(chunk)

        # Should detect and redact high entropy string
        assert "[REDACTED High Entropy String]" in filtered_chunk["content"]
        assert filtered_chunk["metadata"]["content_filtered"] is True
