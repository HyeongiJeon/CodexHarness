"""Local provenance and read-only resource observations. Never reads credentials."""
import hashlib
import os
from pathlib import Path
import resource
import shutil


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def resources(path: Path = Path('.')) -> dict:
    usage = shutil.disk_usage(path)
    result = {'cpu_count': os.cpu_count(), 'disk_free_bytes': usage.free,
              'disk_total_bytes': usage.total, 'hard_limits_known': False}
    if hasattr(os, 'sched_getaffinity'):
        result['cpu_affinity_count'] = len(os.sched_getaffinity(0))
    info = Path('/proc/meminfo')
    if info.exists():
        values = dict(line.split(':', 1) for line in info.read_text().splitlines())
        result['host_available_memory_bytes'] = int(values['MemAvailable'].split()[0]) * 1024
    for name, file in [('cgroup_memory_bytes', '/sys/fs/cgroup/memory.max'), ('cgroup_cpu_quota', '/sys/fs/cgroup/cpu.max')]:
        p = Path(file)
        result[name] = p.read_text().strip() if p.exists() else None
    result['address_space_rlimit'] = list(resource.getrlimit(resource.RLIMIT_AS))
    result['limitations'] = ['Host observations may exceed container limits; unavailable cgroup limits are unknown.',
                             'SQLite disk spill uses an 8 MiB cache; no host setting is changed.']
    return result
