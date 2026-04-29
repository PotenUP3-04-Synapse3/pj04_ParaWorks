from app.parsers.document_parser import extract_text
from app.parsers.hwp_parser import extract_text_from_hwp, extract_text_from_hwp_bytes

__all__ = ['extract_text', 'extract_text_from_hwp', 'extract_text_from_hwp_bytes']
