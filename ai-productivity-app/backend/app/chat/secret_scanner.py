import re
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class SecretScanner:
    """Detect and redact secrets from messages."""

    # Common secret patterns
    PATTERNS = {
        "api_key": [
            (
                r'[aA][pP][iI][-_]?[kK][eE][yY]\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?',
                "API Key",
            ),
            (
                r'[aA][pP][iI][-_]?[sS][eE][cC][rR][eE][tT]\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?',
                "API Secret",
            ),
        ],
        "aws": [
            (r"AKIA[0-9A-Z]{16}", "AWS Access Key"),
            (
                r'aws_secret_access_key\s*=\s*["\']?([a-zA-Z0-9/+=]{40})["\']?',
                "AWS Secret Key",
            ),
        ],
        "github": [
            (r"ghp_[a-zA-Z0-9]{36}", "GitHub Personal Token"),
            (r"gho_[a-zA-Z0-9]{36}", "GitHub OAuth Token"),
            (
                r"github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}",
                "GitHub Fine-grained Token",
            ),
        ],
        "database": [
            (r"(?:postgres|mysql|mongodb)://[^:]+:([^@]+)@", "Database Password"),
            (
                r'[pP][aA][sS][sS][wW][oO][rR][dD]\s*[:=]\s*["\']?([^"\'\s]{8,})["\']?',
                "Password",
            ),
        ],
        "jwt": [
            (r"eyJ[a-zA-Z0-9_\-]+\.eyJ[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+", "JWT Token"),
        ],
        "private_key": [
            (r"-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----", "Private Key"),
            (r"-----BEGIN\s+OPENSSH\s+PRIVATE\s+KEY-----", "SSH Private Key"),
        ],
    }

    def __init__(self):
        self.compiled_patterns = self._compile_patterns()

    def _compile_patterns(self) -> Dict[str, List[Tuple[re.Pattern, str]]]:
        """Compile regex patterns for performance."""
        compiled = {}

        for category, patterns in self.PATTERNS.items():
            compiled[category] = [
                (re.compile(pattern, re.IGNORECASE), name) for pattern, name in patterns
            ]

        return compiled

    def scan(self, text: str) -> List[Dict]:
        """Scan text for secrets."""
        findings = []

        for category, patterns in self.compiled_patterns.items():
            for pattern, secret_type in patterns:
                for match in pattern.finditer(text):
                    findings.append(
                        {
                            "type": secret_type,
                            "category": category,
                            "match": match.group(0),
                            "start": match.start(),
                            "end": match.end(),
                            "severity": self._get_severity(category),
                        }
                    )

        # Check for high entropy strings
        entropy_findings = self._check_entropy(text)
        findings.extend(entropy_findings)

        return findings

    def redact(self, text: str, findings: List[Dict]) -> str:
        """Redact secrets from text."""
        if not findings:
            return text

        # Sort findings by position (reverse to maintain positions)
        sorted_findings = sorted(findings, key=lambda x: x["start"], reverse=True)

        redacted = text
        for finding in sorted_findings:
            start = finding["start"]
            end = finding["end"]
            secret_type = finding["type"]

            # Create redaction placeholder
            redaction = f"[REDACTED {secret_type}]"

            # Replace secret with redaction
            redacted = redacted[:start] + redaction + redacted[end:]

        return redacted

    def validate_message(self, text: str) -> Dict:
        """Validate message for secrets before sending."""
        findings = self.scan(text)

        if not findings:
            return {"valid": True, "findings": []}

        # Check severity
        high_severity = [f for f in findings if f["severity"] == "high"]

        return {
            "valid": len(high_severity) == 0,
            "findings": findings,
            "message": f"Found {len(findings)} potential secrets ({len(high_severity)} high severity)",
        }

    def _check_entropy(self, text: str) -> List[Dict]:
        """Check for high entropy strings that might be secrets."""
        findings = []

        # Look for base64-like strings
        base64_pattern = re.compile(r"[a-zA-Z0-9+/]{40,}={0,2}")

        for match in base64_pattern.finditer(text):
            string = match.group(0)
            entropy = self._calculate_entropy(string)

            # Use a slightly lower threshold (≈ 4.0) so that 50-ish character
            # base64 strings – common for API tokens – are still detected.  The
            # value aligns with the expectations encoded in
            # *tests/test_secret_scanner.py*.

            if entropy >= 4.0:
                findings.append(
                    {
                        "type": "High Entropy String",
                        "category": "entropy",
                        "match": string[:20] + "..." if len(string) > 20 else string,
                        "start": match.start(),
                        "end": match.end(),
                        "severity": "medium",
                        "entropy": entropy,
                    }
                )

        return findings

    def _calculate_entropy(self, string: str) -> float:
        """Calculate Shannon entropy of a string."""
        if not string:
            return 0

        # Count character frequencies
        freq = {}
        for char in string:
            freq[char] = freq.get(char, 0) + 1

        import math

        # Shannon entropy H = - Σ p_i * log2(p_i)
        entropy = 0.0
        length = len(string)

        for count in freq.values():
            probability = count / length
            if probability > 0:
                entropy -= probability * math.log2(probability)

        return entropy

    def _get_severity(self, category: str) -> str:
        """Get severity level for secret category."""
        high_severity = {"private_key", "aws", "database"}
        medium_severity = {"api_key", "github", "jwt"}

        if category in high_severity:
            return "high"
        elif category in medium_severity:
            return "medium"
        else:
            return "low"

    def get_redaction_summary(self, findings: List[Dict]) -> str:
        """Generate summary of redacted content."""
        if not findings:
            return ""

        by_type = {}
        for finding in findings:
            secret_type = finding["type"]
            by_type[secret_type] = by_type.get(secret_type, 0) + 1

        summary_parts = []
        for secret_type, count in by_type.items():
            summary_parts.append(f"{count} {secret_type}")

        return f"Redacted: {', '.join(summary_parts)}"


# Global scanner instance
secret_scanner = SecretScanner()
