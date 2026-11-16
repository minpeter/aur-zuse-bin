#!/usr/bin/env python3
"""Check for new opcodehq/zuse releases and update PKGBUILD."""

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

REPO = "opcodehq/zuse"
ASSETS = {
    "x86_64": "zuse-{version}-linux-x86_64.deb",
    "aarch64": "zuse-{version}-linux-aarch64.deb",
}


def api_get(url: str) -> dict:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "aur-zuse-bin-updater",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def get_latest_release() -> tuple[str, dict[str, str]]:
    release = api_get(f"https://api.github.com/repos/{REPO}/releases/latest")
    tag = release["tag_name"]
    version = tag[1:] if tag.startswith("v") else tag
    assets = {asset["name"]: asset["browser_download_url"] for asset in release["assets"]}
    return version, assets


def parse_pkgbuild(path: Path) -> tuple[str, int, str, str]:
    content = path.read_text(encoding="utf-8")

    def field(name: str) -> str:
        match = re.search(rf"^{name}=([^\s]+)", content, re.MULTILINE)
        if not match:
            raise ValueError(f"Could not parse {name} from PKGBUILD")
        return match.group(1)

    def sums(name: str) -> str:
        match = re.search(rf"^{name}=\(\s*'([^']+)'\s*\)", content, re.MULTILINE)
        if not match:
            raise ValueError(f"Could not parse {name} from PKGBUILD")
        return match.group(1)

    return field("pkgver"), int(field("pkgrel")), sums("sha256sums_x86_64"), sums("sha256sums_aarch64")


def compute_sha256(url: str) -> str:
    print(f"Downloading and calculating sha256: {url}...", file=sys.stderr)
    hasher = hashlib.sha256()
    request = urllib.request.Request(url, headers={"User-Agent": "curl/8.0.0"})
    with urllib.request.urlopen(request, timeout=300) as response:
        while chunk := response.read(1024 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest()


def update_pkgbuild(path: Path, version: str, pkgrel: int, sums: dict[str, str]) -> None:
    content = path.read_text(encoding="utf-8")
    content = re.sub(r"^pkgver=.*$", f"pkgver={version}", content, flags=re.MULTILINE)
    content = re.sub(r"^pkgrel=.*$", f"pkgrel={pkgrel}", content, flags=re.MULTILINE)
    for arch, digest in sums.items():
        content, count = re.subn(
            rf"^sha256sums_{arch}=\(\s*'[^']+'\s*\)",
            f"sha256sums_{arch}=('{digest}')",
            content,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise ValueError(f"Could not replace sha256sums_{arch} in PKGBUILD")
    path.write_text(content, encoding="utf-8")
    print(f"Updated {path} to {version}-{pkgrel}", file=sys.stderr)


def set_github_output(name: str, value: str) -> None:
    output_file = os.getenv("GITHUB_OUTPUT")
    if output_file:
        with open(output_file, "a", encoding="utf-8") as handle:
            handle.write(f"{name}={value}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pkgbuild", type=Path, default=Path("PKGBUILD"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    current_version, current_rel, current_x86, current_arm = parse_pkgbuild(args.pkgbuild)
    print(f"Current PKGBUILD: {current_version}-{current_rel}", file=sys.stderr)

    latest_version, assets = get_latest_release()
    print(f"Upstream release: {latest_version}", file=sys.stderr)

    if not args.force and current_version == latest_version:
        print("PKGBUILD is already up to date.", file=sys.stderr)
        set_github_output("updated", "false")
        return 0

    new_rel = 1 if latest_version != current_version else current_rel + 1
    set_github_output("updated", "true")
    set_github_output("new_version", f"{latest_version}-{new_rel}")

    if args.dry_run:
        print("Dry run requested; stopping before download.", file=sys.stderr)
        return 0

    sums = {}
    for arch, pattern in ASSETS.items():
        name = pattern.format(version=latest_version)
        if name not in assets:
            raise RuntimeError(f"Release v{latest_version} has no asset named {name}")
        sums[arch] = compute_sha256(assets[name])

    if latest_version == current_version and sums["x86_64"] == current_x86 and sums["aarch64"] == current_arm:
        print("Version and checksums are unchanged.", file=sys.stderr)
        set_github_output("updated", "false")
        return 0

    update_pkgbuild(args.pkgbuild, latest_version, new_rel, sums)
    return 0


if __name__ == "__main__":
    sys.exit(main())
