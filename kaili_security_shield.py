import hashlib
import hmac
import json
import os
import re
import time
from collections import defaultdict, deque
from typing import Dict, List, Optional, Tuple

CREATOR = "LAVKUSH KUMAR"
GREETING = "Boss"


class RateLimiter:
    """Sliding-window rate limiter per client IP or session."""

    def __init__(self, max_requests: int = 30, window_seconds: int = 60) -> None:
        self.max_requests = max(1, int(max_requests))
        self.window_seconds = max(1, int(window_seconds))
        self._hits: Dict[str, deque] = defaultdict(deque)

    def allow(self, key: str, now: Optional[float] = None) -> Tuple[bool, Dict[str, int]]:
        ts = time.time() if now is None else now
        q = self._hits[key]
        cutoff = ts - self.window_seconds
        while q and q[0] <= cutoff:
            q.popleft()

        if len(q) >= self.max_requests:
            retry_after = max(1, int(q[0] + self.window_seconds - ts) + 1)
            return False, {"remaining": 0, "retry_after_sec": retry_after}

        q.append(ts)
        remaining = max(0, self.max_requests - len(q))
        return True, {"remaining": remaining, "retry_after_sec": 0}


DANGEROUS_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("command_chaining", re.compile(r"(;|\|\||&&|`|\$\()", re.IGNORECASE)),
    ("path_traversal", re.compile(r"(\.\./|\.\.\\|/etc/passwd|/proc/)", re.IGNORECASE)),
    ("script_injection", re.compile(r"(<\s*script|javascript:|onerror\s*=|onload\s*=)", re.IGNORECASE)),
    ("sql_tautology", re.compile(r"(\bunion\s+select\b|\bdrop\s+table\b|\bor\s+1\s*=\s*1\b)", re.IGNORECASE)),
]


def inspect_input_safety(text: str, max_len: int = 4000) -> Dict[str, object]:
    raw = text if isinstance(text, str) else ""
    if len(raw) > max_len:
        return {
            "safe": False,
            "risk_level": "HIGH",
            "reasons": [f"Input exceeds max length ({len(raw)} > {max_len})"],
        }

    reasons: List[str] = []
    for label, pattern in DANGEROUS_PATTERNS:
        if pattern.search(raw):
            reasons.append(label)

    if reasons:
        return {
            "safe": False,
            "risk_level": "HIGH",
            "reasons": reasons,
        }

    return {
        "safe": True,
        "risk_level": "LOW",
        "reasons": [],
    }


def resolve_safe_path(base_dir: str, relative_target: str) -> Tuple[bool, str]:
    """Prevent directory traversal outside base_dir."""
    abs_base = os.path.realpath(base_dir)
    clean_rel = relative_target.lstrip("/\\")
    candidate = os.path.realpath(os.path.join(abs_base, clean_rel))
    if candidate == abs_base or candidate.startswith(abs_base + os.sep):
        return True, candidate
    return False, "Blocked: path escapes base directory"


SECRET_PATTERNS: List[Tuple[str, re.Pattern]] = [
    ("openai_or_bearer_key", re.compile(r"\bsk-[A-Za-z0-9_\-]{12,}\b")),
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z\-_]{20,}\b")),
    ("github_token", re.compile(r"\b(ghp|gho|ghu|ghs|github_pat)_[A-Za-z0-9_]{12,}\b")),
    ("private_key_block", re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----")),
]


def scan_for_leaked_secrets(text: str) -> Dict[str, object]:
    findings: List[str] = []
    for name, pat in SECRET_PATTERNS:
        if pat.search(text):
            findings.append(name)
    return {
        "has_secrets": len(findings) > 0,
        "findings": findings,
    }


def sign_payload(secret_key: str, payload_str: str) -> str:
    mac = hmac.new(secret_key.encode("utf-8"), payload_str.encode("utf-8"), hashlib.sha256)
    return mac.hexdigest()


def verify_signature(secret_key: str, payload_str: str, provided_sig: str) -> bool:
    expected = sign_payload(secret_key, payload_str)
    return hmac.compare_digest(expected, provided_sig.strip())


def run_repo_security_audit(repo_dir: str = ".") -> Dict[str, object]:
    issues: List[str] = []
    checked_files = 0
    ignore_dirs = {".git", "__pycache__", "renders", "renders_4k", "renders_ultimate", "backups", "packages"}

    for root, dirs, files in os.walk(repo_dir):
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for fname in files:
            if fname.endswith((".py", ".json", ".env", ".sh", ".yml", ".yaml")):
                fpath = os.path.join(root, fname)
                checked_files += 1
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    sec = scan_for_leaked_secrets(content)
                    if sec["has_secrets"]:
                        issues.append(f"{fpath}: leaked secret pattern {sec['findings']}")
                except Exception as exc:
                    issues.append(f"{fpath}: unreadable ({exc})")

    gitignore_path = os.path.join(repo_dir, ".gitignore")
    has_env_ignore = False
    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r", encoding="utf-8", errors="ignore") as f:
            has_env_ignore = ".env" in f.read()
    if not has_env_ignore:
        issues.append(".gitignore missing '.env' rule")

    return {
        "ok": True,
        "creator": CREATOR,
        "greeting": GREETING,
        "checked_files": checked_files,
        "issues_found": len(issues),
        "issues": issues,
        "status": "HARDENED" if not issues else "ACTION_NEEDED",
    }


if __name__ == "__main__":
    limiter = RateLimiter(max_requests=5, window_seconds=60)
    print("Rate limit test:", [limiter.allow("ip_1")[0] for _ in range(6)])
    print("Safe input test:", inspect_input_safety("Boss, 3D video me voice kaise dale?"))
    print("Malicious pattern test:", inspect_input_safety("test; rm -rf / || cat /etc/passwd"))
    print("Path check:", resolve_safe_path("/data/data/com.termux/files/home/kaili-api", "../../etc/passwd"))
    sig = sign_payload("kaili-master-key", '{"action":"chat"}')
    print("HMAC valid:", verify_signature("kaili-master-key", '{"action":"chat"}', sig))
    print("Repo Security Audit:", json.dumps(run_repo_security_audit("."), ensure_ascii=False))
