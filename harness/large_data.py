"""Streaming structured data profiling and exact, disk-backed aggregation.

IDs and join keys use Unicode NFKC plus surrounding-whitespace removal,
case-sensitive. The first row which survives validation, join, and filters wins
across all files. Rows have one exclusion reason; seen = valid + excluded.
Date columns default to canonical YYYY-MM-DD; a mapping may explicitly supply
strptime format(s). Numeric sums use Decimal, never SQLite's floating SUM.
"""
from __future__ import annotations

import codecs
import csv
import hashlib
import json
import shutil
import sqlite3
import tempfile
import unicodedata
from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path
from typing import Any, Iterator


MAX_NUMBER_DIGITS = 10000
MEAN_PRECISION = 50
MAX_RECORD_CHARS = 1024 * 1024


def _bounded_lines(source):
    while line := source.readline(MAX_RECORD_CHARS + 1):
        if len(line) > MAX_RECORD_CHARS:
            raise ValueError('CSV physical line exceeds 1 MiB; split oversized records before analysis')
        yield line


def _hash(path: Path) -> str:
    try:
        from .sources import hash_file
    except ImportError:
        digest = hashlib.sha256()
        with path.open('rb') as source:
            for block in iter(lambda: source.read(1024 * 1024), b''):
                digest.update(block)
        return digest.hexdigest()
    return hash_file(path)


def _encoding(path: Path, encoding: str | None) -> str:
    if encoding:
        codecs.lookup(encoding)
        return encoding
    with path.open('rb') as source:
        prefix = source.read(4)
    if prefix.startswith(codecs.BOM_UTF8):
        return 'utf-8-sig'
    if prefix.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return 'utf-16'
    return 'utf-8'


def _format(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {'.jsonl', '.ndjson'}:
        return 'jsonl'
    if suffix in {'.csv', '.tsv'}:
        return suffix[1:]
    raise ValueError(f'unsupported structured format: {suffix}; use CSV, TSV or JSONL')


def _rows(path: Path, encoding: str) -> Iterator[tuple[dict[str, Any] | None, str | None]]:
    kind = _format(path)
    with path.open('r', encoding=encoding, newline='') as source:
        if kind == 'jsonl':
            while line := source.readline(MAX_RECORD_CHARS + 1):
                if len(line) > MAX_RECORD_CHARS:
                    while line and not line.endswith('\n'):
                        line = source.readline(MAX_RECORD_CHARS + 1)
                    yield None, 'record_too_large'
                    continue
                try:
                    row = json.loads(line, parse_float=Decimal)
                except (ValueError, InvalidOperation):
                    yield None, 'malformed_json'
                    continue
                if not isinstance(row, dict):
                    yield None, 'non_object_json'
                else:
                    yield row, None
        else:
            reader = csv.DictReader(_bounded_lines(source), delimiter='\t' if kind == 'tsv' else ',', strict=True)
            if reader.fieldnames is None:
                raise ValueError(f'CSV must include a header: {path}')
            names = [name.strip() for name in reader.fieldnames]
            if any(not name for name in names) or len(set(names)) != len(names):
                raise ValueError(f'CSV header contains empty or duplicate columns: {path}')
            reader.fieldnames = names
            try:
                for row in reader:
                    yield (None, 'extra_columns') if None in row else (row, None)
            except csv.Error as exc:
                raise ValueError(f'malformed CSV at line {reader.line_num}: {path}: {exc}') from exc


def _missing(value: Any) -> bool:
    return value is None or isinstance(value, str) and not value.strip()


def _text(value: Any) -> str:
    if isinstance(value, (dict, list)):
        raise ValueError('structured values are not scalar')
    return str(value).strip()


def _key(value: Any) -> str:
    return unicodedata.normalize('NFKC', _text(value)).strip()


def _number(value: Any) -> Decimal:
    if isinstance(value, bool) or isinstance(value, (dict, list)):
        raise ValueError('not a finite number')
    try:
        result = Decimal(str(value).strip())
    except (ValueError, InvalidOperation) as exc:
        raise ValueError('not a finite number') from exc
    if not result.is_finite() or len(result.as_tuple().digits) > MAX_NUMBER_DIGITS or abs(result.as_tuple().exponent) > MAX_NUMBER_DIGITS:
        raise ValueError('not a finite supported number')
    return result


def _decimal_text(value: Decimal) -> str:
    return format(value, 'f')


def _add(a: Decimal, b: Decimal) -> Decimal:
    with localcontext() as ctx:
        ctx.prec = max(a.adjusted(), b.adjusted(), 0) - min(a.as_tuple().exponent, b.as_tuple().exponent, 0) + 2
        return a + b


def _multiply(a: Decimal, b: Decimal) -> Decimal:
    with localcontext() as ctx:
        ctx.prec = len(a.as_tuple().digits) + len(b.as_tuple().digits) + 2
        return a * b


def _type(value: Any) -> str:
    if _missing(value):
        return 'null'
    if isinstance(value, bool):
        return 'boolean'
    if isinstance(value, (dict, list)):
        return 'object' if isinstance(value, dict) else 'array'
    try:
        number = _number(value)
        return 'integer' if number == number.to_integral_value() else 'decimal'
    except ValueError:
        return 'string'


def profile_file(path: Path | str, sample_rows: int = 1000, encoding: str | None = None) -> dict:
    """Profile a bounded prefix; SHA-256 covers the entire source file.

    Counts and inferred types describe the sample only, never exact file totals.
    Returned sample records are capped at five and scalar strings at 500 chars.
    """
    if not isinstance(sample_rows, int) or not 0 <= sample_rows <= 100000:
        raise ValueError('sample_rows must be between 0 and 100000')
    path = Path(path)
    resolved_encoding = _encoding(path, encoding)
    schema: dict[str, Counter] = {}
    sample: list[dict] = []
    sampled = 0
    schema_truncated = False
    if _format(path) in {'csv', 'tsv'}:
        with path.open(encoding=resolved_encoding, newline='') as header_source:
            header = next(csv.reader(_bounded_lines(header_source), delimiter='\t' if path.suffix.lower() == '.tsv' else ','), [])
        schema = {name.strip(): Counter() for name in header[:256]}
        schema_truncated = len(header) > 256
    issues: Counter = Counter()
    iterator = _rows(path, resolved_encoding)
    try:
        for _ in range(sample_rows):
            try:
                row, issue = next(iterator)
            except StopIteration:
                break
            sampled += 1
            if issue:
                issues[issue] += 1
                continue
            assert row is not None
            for name, item in row.items():
                if name not in schema and len(schema) >= 256:
                    schema_truncated = True
                    continue
                schema.setdefault(name, Counter())[_type(item)] += 1
            if len(sample) < 5:
                sample.append({name: str(item)[:500] if item is not None else None for name, item in list(row.items())[:50]})
    finally:
        iterator.close()
    valid_sampled = sampled - sum(issues.values())
    fields = []
    for name, counts in sorted(schema.items()):
        missing = counts.get('null', 0) + valid_sampled - sum(counts.values())
        fields.append({'name': name, 'types': sorted(k for k in counts if k != 'null'),
                       'type_counts': dict(sorted(counts.items())), 'nonempty': valid_sampled - missing, 'missing': missing})
    return {'path': str(path.resolve()), 'format': _format(path), 'size_bytes': path.stat().st_size,
            'encoding': resolved_encoding, 'sha256': _hash(path), 'sampled_rows': sampled,
            'sample_limit': sample_rows, 'counts_scope': 'sample', 'schema': fields,
            'sample': sample, 'sample_issues': dict(sorted(issues.items())),
            'schema_truncated': schema_truncated, 'schema_limit': 256, 'sample_column_limit': 50}


def _date_formats(date_columns: list[str] | dict | None) -> dict[str, list[str]]:
    if not date_columns:
        return {}
    if isinstance(date_columns, list):
        return {name: ['%Y-%m-%d'] for name in date_columns}
    if not isinstance(date_columns, dict):
        raise ValueError('date_columns must be a list or mapping of explicit formats')
    result = {}
    for name, formats in date_columns.items():
        formats = [formats] if isinstance(formats, str) else formats
        if not isinstance(formats, list) or not formats or not all(isinstance(f, str) and f for f in formats):
            raise ValueError('date formats must be nonempty strings')
        result[name] = formats
    return result


def _normalize_date(value: Any, formats: list[str]) -> str:
    value = _text(value)
    for date_format in formats:
        try:
            parsed = datetime.strptime(value, date_format)
            # Enforce explicit formatting, including zero padding; do not guess.
            if parsed.strftime(date_format) == value:
                return parsed.date().isoformat()
        except ValueError:
            pass
    raise ValueError('date does not match an explicit format')


def _filters(row: dict, where: dict) -> bool:
    for column, condition in where.items():
        actual = row.get(column)
        if isinstance(condition, list):
            if actual not in condition and str(actual) not in [str(x) for x in condition]:
                return False
        elif isinstance(condition, dict):
            for operator, expected in condition.items():
                if operator in {'gt', 'gte', 'lt', 'lte'}:
                    try:
                        left, right = _number(actual), _number(expected)
                    except ValueError:
                        try:
                            left = datetime.strptime(str(actual), '%Y-%m-%d').date()
                            right = datetime.strptime(str(expected), '%Y-%m-%d').date()
                            if left.isoformat() != str(actual) or right.isoformat() != str(expected):
                                return False
                        except ValueError:
                            return False
                    passed = {'gt': left > right, 'gte': left >= right, 'lt': left < right, 'lte': left <= right}[operator]
                elif operator == 'eq':
                    passed = str(actual) == str(expected)
                elif operator == 'ne':
                    passed = str(actual) != str(expected)
                elif operator == 'in':
                    passed = str(actual) in [str(x) for x in expected]
                else:
                    raise ValueError(f'unsupported filter operator: {operator}')
                if not passed:
                    return False
        elif str(actual) != str(condition):
            return False
    return True


def _stats(row: tuple) -> dict:
    count, total, low, high = row
    with localcontext() as ctx:
        ctx.prec = MEAN_PRECISION
        mean = _decimal_text(Decimal(total) / count) if count else None
    return {'count': count, 'sum': total, 'min': low, 'max': high, 'mean': mean,
            'mean_fraction': {'numerator': total, 'denominator': count}, 'mean_precision': MEAN_PRECISION}


def aggregate_files(paths: list[Path | str], *, group_by: list[str], value: str,
                    id_column: str | None = None, required: list[str] | None = None,
                    encoding: str | None = None, where: dict | None = None,
                    date_columns: list[str] | dict | None = None, units: dict | None = None,
                    join: dict | None = None, work_dir: Path | None = None,
                    max_groups: int = 1000) -> dict:
    """Aggregate CSV/JSONL using disk-backed IDs, dimension keys and groups.

    ``where`` maps columns to equality, membership lists, or operator maps with
    eq/ne/in/gt/gte/lt/lte. ``units`` maps numeric columns to a fixed scale or
    {scale: '0.01', unit: 'USD'}; source units must already be homogeneous.
    Join columns must not overwrite fact columns. Joins are many-to-one only.
    ``date_columns`` may map columns to explicit strptime format(s).
    """
    paths = [Path(path) for path in paths]
    if not paths:
        raise ValueError('at least one input path is required')
    if not isinstance(max_groups, int) or max_groups < 0:
        raise ValueError('max_groups must be a nonnegative integer')
    if not value or not all(isinstance(name, str) and name for name in group_by) or len(set(group_by)) != len(group_by):
        raise ValueError('value and group_by must contain valid column names')
    where = where or {}
    for condition in where.values():
        if isinstance(condition, dict):
            for operator, operand in condition.items():
                if operator not in {'eq', 'ne', 'in', 'gt', 'gte', 'lt', 'lte'}:
                    raise ValueError(f'unsupported filter operator: {operator}')
                if operator == 'in' and not isinstance(operand, list):
                    raise ValueError('in filter requires a list')
    dates = _date_formats(date_columns)
    scales = {}
    unit_checks = {}
    for column, spec in (units or {}).items():
        scales[column] = _number(spec.get('scale', 1) if isinstance(spec, dict) else spec)
        if isinstance(spec, dict) and spec.get('unit_column'):
            if not isinstance(spec.get('unit'), str) or not spec['unit']:
                raise ValueError('unit_column requires an explicit expected unit')
            unit_checks[spec['unit_column']] = spec['unit']
    required_columns = list(dict.fromkeys((required or []) + group_by + [value] + ([id_column] if id_column else []) + list(dates) + list(scales)))
    join_stats = {'enabled': bool(join), 'dimension_rows': 0, 'matched': 0, 'missing_matches': 0, 'how': None}
    if join:
        if not all(join.get(key) for key in ('path', 'left_key', 'right_key')):
            raise ValueError('join requires path, left_key and right_key')
        if join.get('how', 'left') not in {'left', 'inner'}:
            raise ValueError('join how must be left or inner')
        if not isinstance(join.get('columns', []), list) or len(set(join.get('columns', []))) != len(join.get('columns', [])):
            raise ValueError('join columns must be a unique list')
        join_stats['how'] = join.get('how', 'left')
    sources = [{'path': str(path.resolve()), 'size_bytes': path.stat().st_size,
                'sha256': _hash(path), 'encoding': _encoding(path, encoding), 'role': 'fact'} for path in paths]
    if join:
        dimension = Path(join['path'])
        sources.append({'path': str(dimension.resolve()), 'size_bytes': dimension.stat().st_size,
                        'sha256': _hash(dimension), 'encoding': _encoding(dimension, encoding), 'role': 'dimension'})
    if work_dir:
        work_dir = Path(work_dir)
        work_dir.mkdir(parents=True, exist_ok=True)
    root = Path(work_dir or tempfile.gettempdir())
    free = shutil.disk_usage(root).free
    reserve = 4 * 1024 * 1024
    if free <= reserve + 1024 * 1024:
        raise ValueError('insufficient free disk space for SQLite spill (5 MiB minimum)')
    reasons: Counter = Counter()
    exclusion_examples: list[dict] = []

    def exclude(reason: str, path: Path, record: int) -> None:
        reasons[reason] += 1
        if len(exclusion_examples) < 20:
            exclusion_examples.append({'source_path': str(path.resolve()), 'record': record, 'reason': reason})

    seen = valid = 0
    with tempfile.TemporaryDirectory(prefix='harness-aggregate-', dir=work_dir) as temporary:
        db_path = Path(temporary) / 'aggregate.sqlite3'
        connection = sqlite3.connect(db_path)
        try:
            connection.execute('PRAGMA journal_mode=OFF')
            connection.execute('PRAGMA synchronous=OFF')
            connection.execute('PRAGMA temp_store=FILE')
            connection.execute('PRAGMA cache_size=-8192')
            connection.execute(f'PRAGMA max_page_count={(free - reserve) // 4096}')
            connection.create_function('dadd', 2, lambda a, b: _decimal_text(_add(Decimal(a), Decimal(b))))
            connection.create_function('dmin', 2, lambda a, b: a if Decimal(a) <= Decimal(b) else b)
            connection.create_function('dmax', 2, lambda a, b: a if Decimal(a) >= Decimal(b) else b)
            connection.executescript('CREATE TABLE ids (id TEXT PRIMARY KEY) WITHOUT ROWID; CREATE TABLE dimensions (id TEXT PRIMARY KEY, payload TEXT NOT NULL) WITHOUT ROWID; CREATE TABLE groups (key TEXT PRIMARY KEY, n INTEGER NOT NULL, total TEXT NOT NULL, low TEXT NOT NULL, high TEXT NOT NULL) WITHOUT ROWID; CREATE TABLE totals (n INTEGER, total TEXT, low TEXT, high TEXT); INSERT INTO totals VALUES (0, "0", NULL, NULL);')
            if join:
                columns = join.get('columns', [])
                for row, issue in _rows(dimension, sources[-1]['encoding']):
                    if issue or row is None:
                        raise ValueError(f'invalid dimension row: {issue}')
                    if _missing(row.get(join['right_key'])) or any(column not in row for column in columns):
                        raise ValueError('dimension row missing join key or selected column')
                    try:
                        key = _key(row[join['right_key']])
                        payload = json.dumps({column: row[column] for column in columns}, default=str, ensure_ascii=False)
                        connection.execute('INSERT INTO dimensions VALUES (?, ?)', (key, payload))
                    except sqlite3.IntegrityError as exc:
                        raise ValueError(f'duplicate dimension key; many-to-many join rejected: {key}') from exc
                    join_stats['dimension_rows'] += 1
                    if join_stats['dimension_rows'] % 1000 == 0:
                        connection.commit()
            upsert = 'INSERT INTO groups VALUES (?, 1, ?, ?, ?) ON CONFLICT(key) DO UPDATE SET n=n+1,total=dadd(total,excluded.total),low=dmin(low,excluded.low),high=dmax(high,excluded.high)'
            for path, metadata in zip(paths, sources):
                for record, (row, issue) in enumerate(_rows(path, metadata['encoding']), start=1):
                    seen += 1
                    if issue or row is None:
                        exclude(issue or 'invalid_row', path, record)
                        continue
                    row = {column: item.strip() if isinstance(item, str) else item for column, item in row.items()}
                    if join:
                        if any(column in row for column in join.get('columns', [])):
                            raise ValueError('join columns would overwrite fact columns; select distinct names')
                        raw_key = row.get(join['left_key'])
                        try:
                            match = connection.execute('SELECT payload FROM dimensions WHERE id=?', (_key(raw_key),)).fetchone() if not _missing(raw_key) else None
                        except ValueError:
                            exclude('invalid_join_key', path, record)
                            continue
                        if match:
                            join_stats['matched'] += 1
                            row.update(json.loads(match[0]))
                        else:
                            join_stats['missing_matches'] += 1
                            if join_stats['how'] == 'inner':
                                exclude('join_missing', path, record)
                                continue
                            row.update({column: None for column in join.get('columns', [])})
                    if any(_missing(row.get(column)) for column in required_columns):
                        exclude('missing_value', path, record)
                        continue
                    if any(row.get(column) != expected for column, expected in unit_checks.items()):
                        exclude('unit_mismatch', path, record)
                        continue
                    try:
                        for column, formats in dates.items():
                            row[column] = _normalize_date(row[column], formats)
                    except (ValueError, TypeError):
                        exclude('invalid_date', path, record)
                        continue
                    try:
                        for column, scale in scales.items():
                            row[column] = _decimal_text(_multiply(_number(row[column]), scale))
                        amount = _number(row[value])
                    except (ValueError, InvalidOperation):
                        exclude('invalid_number', path, record)
                        continue
                    if not _filters(row, where):
                        exclude('filtered', path, record)
                        continue
                    try:
                        key = json.dumps([_text(row[column]) for column in group_by], ensure_ascii=False, separators=(',', ':'))
                        identity = _key(row[id_column]) if id_column else None
                    except ValueError:
                        exclude('invalid_scalar', path, record)
                        continue
                    if identity is not None:
                        cursor = connection.execute('INSERT OR IGNORE INTO ids VALUES (?)', (identity,))
                        if cursor.rowcount == 0:
                            exclude('duplicate_id', path, record)
                            continue
                    amount_text = _decimal_text(amount)
                    connection.execute(upsert, (key, amount_text, amount_text, amount_text))
                    connection.execute('UPDATE totals SET n=n+1,total=dadd(total,?),low=CASE WHEN low IS NULL THEN ? ELSE dmin(low,?) END,high=CASE WHEN high IS NULL THEN ? ELSE dmax(high,?) END', (amount_text,) * 5)
                    valid += 1
                    if seen % 1000 == 0:
                        connection.commit()
            connection.commit()
            groups_total = connection.execute('SELECT COUNT(*) FROM groups').fetchone()[0]
            groups = []
            for key, count, total, low, high in connection.execute('SELECT key,n,total,low,high FROM groups ORDER BY key LIMIT ?', (max_groups,)):
                groups.append({'key': dict(zip(group_by, json.loads(key))), **_stats((count, total, low, high))})
            totals = _stats(connection.execute('SELECT n,total,low,high FROM totals').fetchone())
            disk_bytes = db_path.stat().st_size
        except sqlite3.OperationalError as exc:
            raise ValueError(f'SQLite aggregation failed (check available disk space): {exc}') from exc
        finally:
            connection.close()
    for source in sources:
        if _hash(Path(source['path'])) != source['sha256']:
            raise ValueError(f"source changed during aggregation: {source['path']}")
    return {'sources': sources, 'rows_seen': seen, 'valid': valid, 'excluded': seen - valid,
            'exclusion_reasons': dict(sorted(reasons.items())), 'exclusion_examples': exclusion_examples, 'duplicates': reasons['duplicate_id'],
            'filtered': reasons['filtered'], 'join': join_stats, 'totals': totals,
            'groups': groups, 'groups_total': groups_total, 'groups_truncated': groups_total > max_groups,
            'group_by': group_by, 'value': value, 'units': units or {},
            'policies': {'id_normalization': 'NFKC, trim, case-sensitive; first valid row wins',
                         'exclusion': 'one first reason per row', 'dates': dates,
                         'missing': 'null or whitespace-only; numeric zero is valid',
                         'unit_scope': 'fixed scale per column; verify optional unit_column, otherwise caller declares homogeneous source units'},
            'spill': {'engine': 'sqlite', 'disk_backed': True, 'database_bytes': disk_bytes,
                      'cache_limit_kib': 8192, 'temporary_database_removed': True}}
