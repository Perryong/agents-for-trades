"""Shared utility for extracting vol_note from analyst LLM output."""
import re
from typing import Optional


_VOL_NOTE_PATTERNS = [
    r"\*\*Vol Note:\*\*\s*(.+)",           # **Vol Note:** sentence
    r"\*\*Volatility Note:\*\*\s*(.+)",    # **Volatility Note:** sentence
    r"(?i)vol[_-]note:\s*(.+)",            # vol_note: / vol-note:
    r"(?i)volatility note:\s*(.+)",        # Volatility note: sentence
]


def extract_vol_note(content: Optional[str]) -> Optional[str]:
    """Extract vol_note from analyst LLM output using multi-pattern fallback.

    Returns the first matched sentence stripped of leading/trailing whitespace.
    Returns None if no pattern matches or if content is None/empty.
    Never raises — all failures return None.
    """
    if not content:
        return None
    for pattern in _VOL_NOTE_PATTERNS:
        match = re.search(pattern, content)
        if match:
            return match.group(1).strip()
    return None
