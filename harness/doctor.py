"""Read-only capability discovery, deliberately excluding credentials."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def command(args: list[str]) -> dict:
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=20)
        return {"exit_code": p.returncode, "stdout": p.stdout.strip(), "stderr": p.stderr.strip()[:500]}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"exit_code": None, "error": str(exc)}


def inspect() -> dict:
    result = {"python": sys.version.split()[0], "codex_path": shutil.which("codex"), "configuration_changed": False}
    if not result["codex_path"]:
        result["limitation"] = "Codex CLI absent: use supplied IDE tools or sequential role prompts; do not install/update exam Codex."
        return result
    result["version"] = command(["codex", "--version"])
    result["features"] = command(["codex", "features", "list"])
    result["exec_help"] = command(["codex", "exec", "--help"])
    # This cache contains public model metadata, never authentication. Cache is evidence
    # of discovery only: actual entitlement/routing still requires an execution probe.
    cache = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))) / "models_cache.json"
    result["models"] = []
    if cache.is_file():
        try:
            for model in json.loads(cache.read_text()).get("models", []):
                slug = model.get("slug", "")
                if slug and "astra" not in slug.lower():
                    result["models"].append({"id": slug, "efforts": [x["effort"] for x in model.get("supported_reasoning_levels", [])]})
        except (ValueError, KeyError, OSError) as exc:
            result["catalog_error"] = str(exc)
    result["model_evidence"] = "local cache; availability and effective routing NOT proven"
    result["next"] = "Check supplied UI /model or codex debug models --help if available; run native smoke. Never change managed restrictions."
    return result
