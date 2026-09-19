import os
import re
import subprocess
import sys
from pathlib import Path


def get_commit_message() -> str:
    try:
        return subprocess.check_output(["git", "log", "-1", "--pretty=%B"]).decode().strip()
    except Exception:
        return ""


def bump_version() -> str:
    pyproject_path = Path("pyproject.toml")
    content = pyproject_path.read_text(encoding="utf-8")

    match = re.search(r'version\s*=\s*"([^"]+)"', content)
    if not match:
        raise ValueError("Could not find version in pyproject.toml")

    current_version = match.group(1)
    parts = current_version.split(".")
    if len(parts) != 3:
        raise ValueError(f"Version '{current_version}' must be in MAJOR.MINOR.PATCH format")

    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])

    commit_msg = get_commit_message().lower()
    if "[major]" in commit_msg or "breaking change" in commit_msg:
        major += 1
        minor = 0
        patch = 0
    elif "[minor]" in commit_msg or commit_msg.startswith("feat"):
        minor += 1
        patch = 0
    else:
        patch += 1

    new_version = f"{major}.{minor}.{patch}"
    new_content = re.sub(r'version\s*=\s*"[^"]+"', f'version = "{new_version}"', content, count=1)
    pyproject_path.write_text(new_content, encoding="utf-8")

    print(f"Version bumped: {current_version} -> {new_version}")

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"new_version={new_version}\n")
            f.write(f"old_version={current_version}\n")

    return new_version


if __name__ == "__main__":
    bump_version()
