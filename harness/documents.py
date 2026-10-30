"""Bounded, local text extraction with reproducible structural locators.

Extracted text is data, including any instructions it happens to contain. No
extractor executes document content, resolves external links, or installs tools.
"""
from __future__ import annotations

import codecs
import csv
from decimal import Decimal
import io
import json
import posixpath
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Iterator
from xml.etree import ElementTree as ET


SUPPORTED_EXTENSIONS = frozenset({
    ".txt", ".md", ".markdown", ".csv", ".tsv", ".json", ".jsonl",
    ".ndjson", ".pdf", ".docx", ".xlsx",
})
SEGMENT_CHARS = 4000
_XML_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


class ExtractionLimit(ValueError):
    """The format is understood, but a resource limit prevented extraction."""


def _record(text: str, locator: dict, limitations=(), status="ok") -> dict:
    return {"text": text, "locator": locator, "limitations": list(limitations),
            "extraction_status": status}


def _parts(text: str, locator: dict, limitations=(), status="ok") -> Iterator[dict]:
    for part, offset in enumerate(range(0, len(text), SEGMENT_CHARS), 1):
        yield _record(text[offset:offset + SEGMENT_CHARS],
                      {**locator, "part": part, "char_start": offset,
                       "char_end": min(offset + SEGMENT_CHARS, len(text))},
                      limitations, status)


def _encoding(path: Path, requested: str | None) -> tuple[str, list[str]]:
    if requested:
        codecs.lookup(requested)
        return requested, [f"Encoding explicitly selected: {requested}"]
    with path.open("rb") as source:
        sample = source.read(65536)
    if sample.startswith(codecs.BOM_UTF8):
        return "utf-8-sig", []
    if sample.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return "utf-16", []
    if b"\x00" in sample:
        raise ValueError("Binary or BOM-less UTF-16 content; specify a verified encoding")
    try:
        codecs.getincrementaldecoder("utf-8")().decode(sample, final=False)
        return "utf-8", []
    except UnicodeDecodeError:
        # Legacy Korean office exports are common. The fallback is visible and
        # remains strict: undecodable bytes never become replacement characters.
        codecs.getincrementaldecoder("cp949")().decode(sample, final=False)
        return "cp949", ["Encoding inferred as CP949 after UTF-8 decoding failed; verify source encoding"]


def _text(path: Path, encoding: str | None) -> Iterator[dict]:
    codec, notes = _encoding(path, encoding)
    section = ""
    line, offset = 1, 0
    with path.open(encoding=codec, errors="strict", newline="") as source:
        while chunk := source.readline(SEGMENT_CHARS):
            if offset == 0 and path.suffix.lower() in {".md", ".markdown"}:
                heading = re.match(r"^ {0,3}#{1,6}\s+(.+)", chunk)
                if heading:
                    section = heading.group(1).strip().rstrip("#").rstrip()
            if any(ord(c) < 32 and c not in "\t\r\n\f" for c in chunk):
                raise ValueError(f"Unexpected binary control characters at line {line}")
            locator = {"format": "text", "line": line, "column": offset + 1,
                       "part": offset // SEGMENT_CHARS + 1}
            if section:
                locator["section"] = section
            yield _record(chunk, locator, notes)
            offset += len(chunk)
            if chunk.endswith(("\n", "\r")):
                line += 1
                offset = 0


def _csv(path: Path, encoding: str | None) -> Iterator[dict]:
    codec, notes = _encoding(path, encoding)
    with path.open(encoding=codec, errors="strict", newline="") as source:
        reader = csv.reader(source, delimiter="\t" if path.suffix.lower() == ".tsv" else ",", strict=True)
        previous_line = 0
        for row_number, row in enumerate(reader, 1):
            # JSON encodes boundaries and embedded newlines without losing fields.
            text = json.dumps(row, ensure_ascii=False)
            yield from _parts(text, {"format": "csv", "row": row_number,
                                    "line_start": previous_line + 1,
                                    "line_end": reader.line_num}, notes)
            previous_line = reader.line_num


def _json_leaves(value, pointer="") -> Iterator[tuple[str, str]]:
    # Iterative traversal avoids a second recursion limit for deeply nested input.
    stack = [(pointer, value)]
    while stack:
        location, item = stack.pop()
        if isinstance(item, dict) and item:
            for key, child in reversed(list(item.items())):
                escaped = key.replace("~", "~0").replace("/", "~1")
                stack.append((f"{location}/{escaped}", child))
        elif isinstance(item, list) and item:
            for index in range(len(item) - 1, -1, -1):
                stack.append((f"{location}/{index}", item[index]))
        else:
            yield location, str(item) if isinstance(item, Decimal) else json.dumps(item, ensure_ascii=False)


def _json(path: Path, encoding: str | None, max_chars: int) -> Iterator[dict]:
    codec, notes = _encoding(path, encoding)
    notes = notes + ['JSON values are rendered by pointer, preserving decimal precision; this is not a raw-byte quotation']
    input_limit = min(32 * 1024 * 1024, max(65536, max_chars * 4))
    if path.suffix.lower() in {".jsonl", ".ndjson"}:
        with path.open(encoding=codec, errors="strict") as source:
            line = 0
            while raw := source.readline(input_limit + 1):
                line += 1
                if len(raw) > input_limit:
                    raise ExtractionLimit(f"JSONL line {line} exceeds bounded record limit ({input_limit} characters)")
                if not raw.strip():
                    continue
                try:
                    value = json.loads(raw, parse_float=Decimal)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSONL at line {line}: {exc.msg}") from exc
                for pointer, rendered in _json_leaves(value):
                    yield from _parts(f"{pointer or '/'}: {rendered}",
                                      {"format": "jsonl", "line": line,
                                       "pointer": pointer}, notes)
    else:
        if path.stat().st_size > input_limit:
            raise ExtractionLimit(f"JSON exceeds bounded input limit ({input_limit} bytes); split into JSONL for streaming extraction")
        with path.open(encoding=codec, errors="strict") as source:
            raw = source.read(input_limit + 1)
        if len(raw) > input_limit:
            raise ExtractionLimit("Decoded JSON exceeds bounded input limit")
        value = json.loads(raw, parse_float=Decimal)
        for pointer, rendered in _json_leaves(value):
            yield from _parts(f"{pointer or '/'}: {rendered}",
                              {"format": "json", "pointer": pointer}, notes)


def _check_zip(archive: zipfile.ZipFile, max_chars: int) -> None:
    limit = min(256 * 1024 * 1024, max(64 * 1024 * 1024, max_chars * 16))
    if sum(info.file_size for info in archive.infolist()) > limit:
        raise ExtractionLimit(f"OOXML archive exceeds uncompressed size limit ({limit} bytes)")
    if len(archive.infolist()) > 20000:
        raise ExtractionLimit("OOXML archive exceeds 20000 entries")


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _word_text(element) -> str:
    pieces = []
    for child in element.iter():
        name = _local(child.tag)
        if name in {"t", "delText"} and child.text:
            pieces.append(child.text)
        elif name == "tab":
            pieces.append("\t")
        elif name in {"br", "cr"}:
            pieces.append("\n")
    return "".join(pieces)


def _docx(path: Path, max_chars: int) -> Iterator[dict]:
    notes = ["DOCX body text extraction may omit headers, footers, comments, drawing text and layout"]
    with zipfile.ZipFile(path) as archive:
        _check_zip(archive, max_chars)
        if any(name.startswith("word/media/") for name in archive.namelist()):
            notes.append("Embedded images are not OCRed or extracted")
        paragraph, table, section = 0, 0, 1
        tables = []
        paragraphs = []
        heading = ""
        with archive.open("word/document.xml") as source:
            for event, element in ET.iterparse(source, events=("start", "end")):
                name = _local(element.tag)
                if event == "start":
                    if name == "tbl":
                        table += 1
                        tables.append({"table": table, "row": 0, "cell": 0})
                    elif name == "tr" and tables:
                        tables[-1]["row"] += 1
                        tables[-1]["cell"] = 0
                    elif name == "tc" and tables:
                        tables[-1]["cell"] += 1
                    elif name == "p":
                        paragraph += 1
                        paragraphs.append({"format": "docx", "section": section,
                                           "paragraph": paragraph,
                                           **(tables[-1] if tables else {})})
                    elif name in {"ins", "del", "moveFrom", "moveTo"}:
                        warning = "Tracked changes are present; extracted text includes available inserted/deleted text without revision resolution"
                        if warning not in notes:
                            notes.append(warning)
                else:
                    if name == "p":
                        locator = paragraphs.pop()
                        text = _word_text(element)
                        styles = [child for child in element.iter() if _local(child.tag) == "pStyle"]
                        if any("heading" in str(list(style.attrib.values())).lower() for style in styles):
                            heading = text
                        if heading:
                            locator["heading"] = heading
                        if text:
                            yield from _parts(text, locator, notes)
                        element.clear()
                    elif name == "tbl":
                        tables.pop()
                        element.clear()
                    elif name == "sectPr":
                        section += 1
                    elif name in {"tr", "tc"}:
                        element.clear()
        # A final structural note retains warnings discovered after the last text.
        yield _record("", {"format": "docx", "summary": True}, notes)


def _bounded_xml(archive: zipfile.ZipFile, name: str, limit=2 * 1024 * 1024):
    if archive.getinfo(name).file_size > limit:
        raise ExtractionLimit(f"OOXML metadata {name} exceeds {limit} bytes")
    with archive.open(name) as source:
        return ET.parse(source).getroot()


def _xlsx(path: Path, max_chars: int) -> Iterator[dict]:
    notes = ["XLSX extraction uses stored cell values; formatting, charts, images and macros are not evaluated"]
    with zipfile.ZipFile(path) as archive:
        _check_zip(archive, max_chars)
        shared = []
        shared_complete = True
        shared_limit = min(16 * 1024 * 1024, max(65536, max_chars * 2))
        shared_chars = 0
        if "xl/sharedStrings.xml" in archive.namelist():
            with archive.open("xl/sharedStrings.xml") as source:
                for _, element in ET.iterparse(source, events=("end",)):
                    if _local(element.tag) == "si":
                        text = "".join(child.text or "" for child in element.iter() if _local(child.tag) == "t")
                        if shared_chars + len(text) > shared_limit or len(shared) >= 100000:
                            shared_complete = False
                            break
                        shared.append(text)
                        shared_chars += len(text)
                        element.clear()
            if not shared_complete:
                notes.append("Shared strings exceeded bounded cache; cells referencing uncached strings are omitted explicitly")
        workbook = _bounded_xml(archive, "xl/workbook.xml")
        relations = _bounded_xml(archive, "xl/_rels/workbook.xml.rels")
        targets = {}
        for relation in relations:
            if relation.attrib.get("TargetMode") == "External":
                continue
            target = relation.attrib.get("Target", "")
            target = target.lstrip("/") if target.startswith("/") else posixpath.normpath(posixpath.join("xl", target))
            if target.startswith("xl/"):
                targets[relation.attrib.get("Id")] = target
        for sheet in workbook.iter(f"{{{_XML_NS}}}sheet"):
            sheet_name = sheet.attrib.get("name", "")
            relation_id = next((value for key, value in sheet.attrib.items() if key.endswith("}id")), None)
            target = targets.get(relation_id)
            if not target:
                yield _record("", {"format": "xlsx", "sheet": sheet_name},
                              ["Worksheet relationship missing or external"], "partial")
                continue
            row = 0
            with archive.open(target) as source:
                for event, element in ET.iterparse(source, events=("start", "end")):
                    name = _local(element.tag)
                    if event == "start" and name == "row":
                        row = int(element.attrib.get("r", row + 1))
                    elif event == "end" and name == "c":
                        address = element.attrib.get("r", "")
                        locator = {"format": "xlsx", "sheet": sheet_name,
                                   "row": row, "cell": address}
                        cell_notes = list(notes)
                        value = element.find(f"{{{_XML_NS}}}v")
                        formula = element.find(f"{{{_XML_NS}}}f")
                        kind = element.attrib.get("t", "n")
                        text = value.text or "" if value is not None else ""
                        status = "ok"
                        if kind == "s":
                            try:
                                index = int(text)
                                if index < 0:
                                    raise IndexError
                                text = shared[index]
                            except (ValueError, IndexError):
                                yield _record("", locator, cell_notes + ["Shared string reference unavailable"], "partial")
                                element.clear()
                                continue
                        elif kind == "inlineStr":
                            text = "".join(child.text or "" for child in element.iter() if _local(child.tag) == "t")
                        if kind == "e":
                            cell_notes.append("Cell contains a stored spreadsheet error")
                        if formula is not None:
                            cell_notes.append("Formula is not recalculated; cached value may be stale or absent")
                            formula_text = formula.text or ""
                            if formula.attrib.get("t") == "shared" and not formula_text:
                                cell_notes.append("Shared formula expression unavailable on this cell")
                            text = f"={formula_text}\nCached value: {text}" if text else f"={formula_text}"
                            if value is None or value.text is None:
                                status = "partial"
                                cell_notes.append("Formula has no cached value")
                        if text:
                            yield from _parts(text, locator, cell_notes, status)
                        element.clear()
                    elif event == "end" and name == "row":
                        element.clear()
        if not shared_complete:
            yield _record("", {"format": "xlsx", "summary": True}, notes, "partial")


def _pdf(path: Path) -> Iterator[dict]:
    command = shutil.which("pdftotext")
    if command is None:
        yield _record("", {"format": "pdf"}, ["Local pdftotext parser unavailable; install separately to extract text"], "unsupported")
        return
    notes = ["PDF text extraction can lose tables, columns, reading order and visual layout; verify the original page"]
    with tempfile.TemporaryDirectory(prefix="harness-pdf-") as directory:
        output = Path(directory) / "text.txt"
        with tempfile.TemporaryFile() as errors:
            try:
                result = subprocess.run([command, "-enc", "UTF-8", "-layout", str(path.resolve()), str(output)],
                                        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                                        stderr=errors, timeout=30, check=False)
            except subprocess.TimeoutExpired as exc:
                raise ExtractionLimit("PDF extraction exceeded 30 second timeout") from exc
            if result.returncode:
                errors.seek(0)
                detail = errors.read(2048).decode("utf-8", errors="replace").strip()
                raise ValueError(f"pdftotext exited {result.returncode}: {detail}")
        page, offset, had_text, pending_page = 1, 0, False, False
        with output.open(encoding="utf-8", errors="strict") as source:
            while chunk := source.read(SEGMENT_CHARS):
                pieces = chunk.split("\f")
                for index, text in enumerate(pieces):
                    if text:
                        pending_page = True
                        if text.strip():
                            had_text = True
                            yield _record(text, {"format": "pdf", "page": page,
                                                 "char_start": offset,
                                                 "char_end": offset + len(text)}, notes)
                        offset += len(text)
                    if index < len(pieces) - 1:
                        if not had_text:
                            yield _record("", {"format": "pdf", "page": page},
                                          ["Page has no searchable text; scanned/image-only content requires OCR"], "unsupported")
                        page += 1
                        offset, had_text, pending_page = 0, False, False
            if pending_page and not had_text or page == 1 and not pending_page:
                yield _record("", {"format": "pdf", "page": page},
                              ["Page has no searchable text; scanned/image-only content requires OCR"], "unsupported")


def iter_segments(path: Path, *, max_chars: int = 2_000_000,
                  encoding: str | None = None) -> Iterator[dict]:
    """Yield text/status records, bounded by characters and stable locators.

    ``max_chars`` bounds emitted document text, not source bytes. JSON input and
    OOXML expansion have separate guards. Exceptions become explicit records so
    a corpus cannot mistake an unreadable document for a successful empty file.
    """
    path = Path(path)
    if not isinstance(max_chars, int) or isinstance(max_chars, bool) or max_chars < 1:
        raise ValueError("max_chars must be a positive integer")
    extension = path.suffix.lower()
    raw = None
    count, emitted = 0, False
    try:
        if extension not in SUPPORTED_EXTENSIONS:
            yield _record("", {"format": extension.lstrip(".") or "unknown"},
                          [f"Unsupported document extension: {extension or '(none)'}"], "unsupported")
            return
        if extension in {".txt", ".md", ".markdown"}:
            raw = _text(path, encoding)
        elif extension in {".csv", ".tsv"}:
            raw = _csv(path, encoding)
        elif extension in {".json", ".jsonl", ".ndjson"}:
            raw = _json(path, encoding, max_chars)
        elif extension == ".pdf":
            raw = _pdf(path)
        elif extension == ".docx":
            raw = _docx(path, max_chars)
        else:
            raw = _xlsx(path, max_chars)
        for record in raw:
            text = record["text"]
            remaining = max_chars - count
            if text and remaining <= 0:
                yield _record("", {"format": extension.lstrip("."), "limit": max_chars},
                              [f"Document text truncated at max_chars={max_chars}"], "partial")
                return
            if len(text) > remaining:
                record = {**record, "text": text[:remaining],
                          "locator": {**record["locator"], "truncated_chars": remaining},
                          "limitations": record["limitations"] + [f"Document text truncated at max_chars={max_chars}"],
                          "extraction_status": "partial"}
                yield record
                yield _record("", {"format": extension.lstrip("."), "limit": max_chars},
                              [f"Document text truncated at max_chars={max_chars}"], "partial")
                return
            count += len(text)
            emitted = True
            yield record
        if not emitted:
            yield _record("", {"format": extension.lstrip(".")},
                          ["Document contains no extractable text"], "partial")
    except ExtractionLimit as exc:
        yield _record("", {"format": extension.lstrip(".")}, [str(exc)], "partial")
    except (OSError, ValueError, LookupError, csv.Error, zipfile.BadZipFile,
            KeyError, ET.ParseError, RecursionError, RuntimeError) as exc:
        yield _record("", {"format": extension.lstrip(".")},
                      [f"Extraction failed ({type(exc).__name__}): {exc}"], "error")
    finally:
        if raw is not None:
            raw.close()
