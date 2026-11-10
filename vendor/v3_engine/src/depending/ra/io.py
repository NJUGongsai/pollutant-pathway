"""Deterministic I/O helpers: stable JSON, sha256 manifests, atomic writes."""
import hashlib
import json
import os


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: str) -> str:
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def stable_json_text(obj) -> str:
    """Serialise to a canonical, deterministic JSON string."""
    return json.dumps(
        obj,
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def stable_json_dump(obj, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(stable_json_text(obj))
        fh.write("\n")


def stable_json_lines(records, path: str) -> None:
    """Write one canonical JSON object per line (deterministic order in caller)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(stable_json_text(rec))
            fh.write("\n")


def read_json_lines(path: str):
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def manifest_write(directory: str, relpaths) -> str:
    """Write MANIFEST.sha256 in sha256sum format over the given relative paths."""
    manifest_path = os.path.join(directory, "MANIFEST.sha256")
    lines = []
    for rel in sorted(relpaths):
        lines.append(f"{sha256_file(os.path.join(directory, rel))}  {rel}")
    with open(manifest_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return manifest_path