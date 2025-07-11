"""Unit-tests for SecretScanner entropy calculation and pattern matching."""

import pytest

from app.chat.secret_scanner import SecretScanner


@pytest.fixture(scope="module")
def scanner():
    return SecretScanner()


def test_entropy_calculation_detects_random_strings(scanner):
    """A base64-looking high-entropy string should be reported."""

    high_entropy = "q3VhbmtyanVkZmhramRmZ2hramRocWprbGpoa2Znampr"  # random, > 40 chars

    findings = scanner.scan(high_entropy)

    assert any(
        f["category"] == "entropy" for f in findings
    ), "High entropy string not detected"


def test_entropy_low_string_not_flagged(scanner):
    """Common low-entropy text should not produce entropy findings."""

    text = "hello world this is not a secret"

    findings = scanner.scan(text)

    assert not any(f["category"] == "entropy" for f in findings)


@pytest.mark.parametrize(
    "secret_sample, expected_type",
    [
        ("AKIAABCDEFGHIJKLMNOPQRST", "AWS Access Key"),
        ("ghp_0123456789abcdef0123456789abcdef0123", "GitHub Personal Token"),
        ("api_key = '1234567890ABCDEFGHIJ'", "API Key"),
    ],
)
def test_known_secret_patterns(scanner, secret_sample, expected_type):
    findings = scanner.scan(secret_sample)

    # Ensure at least one finding of the right type exists
    assert any(f["type"] == expected_type for f in findings)
