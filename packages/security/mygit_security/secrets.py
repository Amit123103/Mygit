import math
import re
from typing import List


class SecretWarning:
    def __init__(self, path: str, pattern_name: str, line_number: int, snippet: str):
        self.path = path
        self.pattern_name = pattern_name
        self.line_number = line_number
        self.snippet = snippet

    def to_summary(self) -> str:
        return f"Potential secret detected ({self.pattern_name}) in '{self.path}' at line {self.line_number}: {self.snippet}"


SECRET_PATTERNS = [
    (r"BEGIN (EC|RSA|OPENSSH|DSA|PGP) PRIVATE KEY", "Private Key"),
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key"),
    (r"ghp_[a-zA-Z0-9]{36}", "GitHub Personal Access Token"),
    (r"glpat-[a-zA-Z0-9\-]{20}", "GitLab Personal Access Token"),
    (r"hf_[a-zA-Z0-9]{34}", "Hugging Face User Token"),
    (r"(?i)(password|passwd|secret|api_key|token)\s*[:=]\s*['\"]([^'\"]{8,})['\"]", "Hardcoded Secret/Password"),
]


def calculate_entropy(data: str) -> float:
    """Calculate Shannon entropy of string to detect random secret keys."""
    if not data:
        return 0.0
    entropy = 0.0
    for x in set(data):
        p_x = float(data.count(x)) / len(data)
        entropy -= p_x * math.log(p_x, 2)
    return entropy


class SecretScanner:
    """Scans content for credentials, tokens, and private keys before committing."""

    @staticmethod
    def scan_file_content(rel_path: str, content: str) -> List[SecretWarning]:
        warnings = []
        lines = content.splitlines()

        for idx, line in enumerate(lines, 1):
            # Check Regex Patterns
            for pattern, name in SECRET_PATTERNS:
                match = re.search(pattern, line)
                if match:
                    snippet = line[:60] + "..." if len(line) > 60 else line
                    warnings.append(SecretWarning(rel_path, name, idx, snippet))

            # High Entropy Token Detection for long words
            for word in line.split():
                clean_word = word.strip("'\"=:,;")
                if len(clean_word) >= 24 and calculate_entropy(clean_word) > 4.5:
                    if not any(w.line_number == idx for w in warnings):
                        snippet = clean_word[:15] + "..."
                        warnings.append(SecretWarning(rel_path, "High Entropy Token", idx, snippet))

        return warnings
