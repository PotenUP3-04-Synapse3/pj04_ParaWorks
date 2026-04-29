"""HWP/HWPX parser using rhwp CLI (https://github.com/edwardkim/rhwp)."""
from __future__ import annotations

import logging
import re
import subprocess
import tempfile
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

# rhwp dump output pattern: lines like `Para N: "text content"`
_PARA_PATTERN = re.compile(r'^(?:\s*)Para \d+:\s*"(.*)"$')
_CELL_PATTERN = re.compile(r'^(?:\s*)Cell\(\d+,\d+\):\s*"(.*)"$')


def extract_text_from_hwp(file_path: str | Path, timeout: int = 30) -> str:
    """
    Extract plain text from an HWP/HWPX file using the rhwp CLI.

    Uses `rhwp dump <file>` which outputs an IR dump containing all paragraphs.
    Falls back gracefully if rhwp is not available or the file is corrupt.
    """
    bin_path = settings.RHWP_BIN
    file_path = str(file_path)

    try:
        result = subprocess.run(
            [bin_path, 'dump', file_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        logger.error('rhwp binary not found at %s. Install from https://github.com/edwardkim/rhwp', bin_path)
        raise RuntimeError(f'rhwp binary not found at {bin_path}')
    except subprocess.TimeoutExpired:
        logger.error('rhwp dump timed out for file: %s', file_path)
        raise RuntimeError(f'HWP parsing timed out after {timeout}s')

    if result.returncode != 0:
        logger.warning('rhwp dump exited with code %d: %s', result.returncode, result.stderr)

    return _parse_ir_dump(result.stdout)


def _parse_ir_dump(dump_output: str) -> str:
    """Extract readable text lines from rhwp IR dump output."""
    text_lines = []

    for line in dump_output.splitlines():
        # Match paragraph text
        m = _PARA_PATTERN.match(line)
        if m:
            content = m.group(1).strip()
            if content:
                text_lines.append(content)
            continue

        # Match table cell text
        m = _CELL_PATTERN.match(line)
        if m:
            content = m.group(1).strip()
            if content:
                text_lines.append(f'[표] {content}')
            continue

    return '\n'.join(text_lines)


def extract_text_from_hwp_bytes(data: bytes, suffix: str = '.hwp', timeout: int = 30) -> str:
    """Extract text from HWP file bytes by writing to a temp file."""
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
        f.write(data)
        tmp_path = f.name
    try:
        return extract_text_from_hwp(tmp_path, timeout=timeout)
    finally:
        Path(tmp_path).unlink(missing_ok=True)
