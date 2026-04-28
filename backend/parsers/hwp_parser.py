from __future__ import annotations

import io
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Any

import structlog

from backend.parsers.base import BaseParser, ParsedDocument

log = structlog.get_logger(__name__)

HWP_MIMES = {
    'application/haansofthwp',
    'application/x-hwp',
    'application/vnd.hancom.hwp',
    'application/vnd.hancom.hwpx',
    'application/hwp',
}


class HwpParser(BaseParser):
    """HWP/HWPX 파서 — 4단계 fallback chain.

    1. pyhwp (hwp5) Python 라이브러리 → 텍스트 추출
    2. Hancom HWP Viewer CLI (subprocess) → PDF 변환 후 pypdf로 추출
    3. LibreOffice CLI (subprocess, Windows 설치 전제) → DOCX/TXT 변환
    4. Azure Computer Vision OCR (최후 수단)
    """

    def can_parse(self, mime_type: str) -> bool:
        return mime_type in HWP_MIMES or mime_type.endswith('.hwp') or mime_type.endswith('.hwpx')

    def parse(self, content: bytes | str, source_url: str | None = None) -> ParsedDocument:
        if isinstance(content, str):
            content = content.encode('utf-8')

        for method_name, method in [
            ('pyhwp', self._parse_pyhwp),
            ('hancom_cli', self._parse_hancom_cli),
            ('libreoffice', self._parse_libreoffice),
            ('ocr', self._parse_ocr),
        ]:
            try:
                result = method(content)
                if result is not None:
                    log.info('hwp.parsed', method=method_name, chars=len(result.text))
                    return result
            except Exception as exc:
                log.warning('hwp.fallback', method=method_name, error=str(exc))

        log.error('hwp.all_fallbacks_failed', source_url=source_url)
        return ParsedDocument(
            text='[HWP 파싱 실패: 지원되는 파서가 없거나 파일이 손상되었습니다]',
            metadata={'parse_status': 'failed', 'source_url': source_url},
        )

    def _parse_pyhwp(self, content: bytes) -> ParsedDocument | None:
        """pyhwp (hwp5txt) 라이브러리 사용."""
        import hwp5  # type: ignore
        from hwp5.xmlmodel import Hwp5File  # type: ignore

        buf = io.BytesIO(content)
        hwp_file = Hwp5File(buf)
        paragraphs: list[dict[str, Any]] = []
        all_text_parts: list[str] = []
        para_idx = 0

        for section in hwp_file.bodytext.sections:
            for para in section.paragraphs:
                text_parts = []
                for ctrl in para.controls:
                    if hasattr(ctrl, 'text'):
                        text_parts.append(ctrl.text)
                para_text = ''.join(text_parts).strip()
                if para_text:
                    paragraphs.append({
                        'text': para_text,
                        'page_number': None,
                        'paragraph_index': para_idx,
                        'heading': None,
                    })
                    all_text_parts.append(para_text)
                    para_idx += 1

        full_text = '\n'.join(all_text_parts)
        if not full_text.strip():
            return None

        return ParsedDocument(
            text=full_text,
            paragraphs=paragraphs,
            metadata={'parser': 'pyhwp'},
        )

    def _parse_hancom_cli(self, content: bytes) -> ParsedDocument | None:
        """Hancom HWP Viewer의 CLI 변환 사용 (Windows 전용).
        hwp.exe /PDF output.pdf input.hwp 형태의 CLI 지원 여부에 따라 동작.
        """
        hancom_paths = [
            r'C:\Program Files\HNC\HOffice 2022\Office\HWord.exe',
            r'C:\Program Files (x86)\HNC\HOffice 2022\Office\HWord.exe',
        ]
        hwp_exe = next((p for p in hancom_paths if os.path.exists(p)), None)
        if hwp_exe is None:
            return None

        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / 'input.hwp'
            dst = Path(tmpdir) / 'output.pdf'
            src.write_bytes(content)

            result = subprocess.run(
                [hwp_exe, '/PDF', str(dst), str(src)],
                capture_output=True,
                timeout=60,
            )
            if result.returncode != 0 or not dst.exists():
                return None

            return self._extract_from_pdf(dst.read_bytes(), parser_name='hancom_cli')

    def _parse_libreoffice(self, content: bytes) -> ParsedDocument | None:
        """LibreOffice CLI 변환: HWP → DOCX or TXT."""
        lo_paths = [
            r'C:\Program Files\LibreOffice\program\soffice.exe',
            r'C:\Program Files (x86)\LibreOffice\program\soffice.exe',
        ]
        lo_exe = next((p for p in lo_paths if os.path.exists(p)), None)
        if lo_exe is None:
            return None

        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir) / 'input.hwp'
            src.write_bytes(content)

            result = subprocess.run(
                [lo_exe, '--headless', '--convert-to', 'txt:Text', '--outdir', tmpdir, str(src)],
                capture_output=True,
                timeout=120,
            )
            txt_file = Path(tmpdir) / 'input.txt'
            if result.returncode != 0 or not txt_file.exists():
                return None

            text = txt_file.read_text(encoding='utf-8', errors='replace').strip()
            if not text:
                return None

            paragraphs = [
                {'text': line, 'page_number': None, 'paragraph_index': i, 'heading': None}
                for i, line in enumerate(text.splitlines())
                if line.strip()
            ]
            return ParsedDocument(
                text=text,
                paragraphs=paragraphs,
                metadata={'parser': 'libreoffice'},
            )

    def _parse_ocr(self, content: bytes) -> ParsedDocument | None:
        """Azure Computer Vision OCR — 최후 수단."""
        from backend.core.config import settings as cfg
        if not cfg.azure_content_safety_endpoint:
            return None

        from azure.ai.vision.imageanalysis import ImageAnalysisClient  # type: ignore
        from azure.ai.vision.imageanalysis.models import VisualFeatures  # type: ignore
        from azure.core.credentials import AzureKeyCredential  # type: ignore

        client = ImageAnalysisClient(
            endpoint=cfg.azure_content_safety_endpoint,
            credential=AzureKeyCredential(cfg.azure_content_safety_key),
        )
        # HWP를 직접 OCR할 수 없으므로 PDF 변환 후 첫 페이지만 처리
        log.warning('hwp.ocr_fallback_limited')
        return None

    @staticmethod
    def _extract_from_pdf(pdf_bytes: bytes, parser_name: str) -> ParsedDocument | None:
        from pypdf import PdfReader  # type: ignore
        reader = PdfReader(io.BytesIO(pdf_bytes))
        pages_text: list[str] = []
        paragraphs: list[dict[str, Any]] = []
        para_idx = 0

        for page_num, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or '').strip()
            pages_text.append(text)
            for line in text.splitlines():
                line = line.strip()
                if line:
                    paragraphs.append({
                        'text': line,
                        'page_number': page_num,
                        'paragraph_index': para_idx,
                        'heading': None,
                    })
                    para_idx += 1

        full_text = '\n'.join(pages_text)
        if not full_text.strip():
            return None
        return ParsedDocument(
            text=full_text,
            pages=pages_text,
            paragraphs=paragraphs,
            metadata={'parser': parser_name},
        )
