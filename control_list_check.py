#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml"]
# ///
"""Hold a vendor's security-control list to the sentences it quotes.

A rows file looks like this:

    checked: 2026-10-21
    sources:
      docs: https://vendor.example/security
    rows:
      - control: Single sign-on
        source: docs
        quote: "SAML 2.0 single sign-on"
        ours: The equivalent control in your own stack
      - control: Pen-test summary
        source: docs
        manual: true          # only a browser or a human can read it
        quote: "available on request"

Usage
  control_list_check.py rows.yaml            # human-readable
  control_list_check.py rows.yaml --json     # machine-readable
  control_list_check.py rows.yaml --quiet    # exit code only

Exit codes
  0  every non-manual quote was found
  1  at least one quote is gone from a page that loaded
  2  no quote missing, but at least one page could not be read (403, 404, timeout)

A missing quote is the useful signal. The vendor rewrote, renamed or withdrew
the claim, and the cell needs a fresh quote from the page it lives on.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"
)
SCRIPT_STYLE = re.compile(r"(?is)<(script|style)\b.*?</\1>")
TAG = re.compile(r"(?s)<[^>]+>")
SPACE = re.compile(r"\s+")
SMART = str.maketrans({"\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"', "\u00a0": " "})


def normalise(text: str) -> str:
    """Same text, before comparison: smart quotes flattened, whitespace collapsed."""
    return SPACE.sub(" ", text.translate(SMART)).strip().casefold()


def page_text(url: str, timeout: int = 45) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8", "ignore")
    return normalise(TAG.sub(" ", SCRIPT_STYLE.sub(" ", body)))


def check(rows_path: Path) -> dict:
    data = yaml.safe_load(rows_path.read_text(encoding="utf-8"))
    sources = data.get("sources") or {}
    cache: dict[str, str | None] = {}
    results = []

    for row in data.get("rows") or []:
        control = row.get("control") or "(unnamed)"
        quote = row.get("quote")
        if not quote:
            results.append({"control": control, "state": "no-quote"})
            continue
        if row.get("manual"):
            results.append({"control": control, "state": "manual"})
            continue
        name = row.get("source")
        url = sources.get(name) or name
        if not url:
            results.append({"control": control, "state": "no-source"})
            continue
        if name not in cache:
            try:
                cache[name] = page_text(url)
            except urllib.error.HTTPError as error:
                cache[name] = None
                results.append(
                    {"control": control, "state": "unreadable", "url": url,
                     "detail": f"HTTP {error.code}"})
                continue
            except Exception as error:  # noqa: BLE001 - any failure is unverified
                cache[name] = None
                results.append(
                    {"control": control, "state": "unreadable", "url": url,
                     "detail": str(error)})
                continue
        if cache[name] is not None and normalise(quote) in cache[name]:
            results.append({"control": control, "state": "held", "url": url})
        else:
            results.append({"control": control, "state": "missing", "url": url})

    counts: dict[str, int] = {}
    for item in results:
        counts[item["state"]] = counts.get(item["state"], 0) + 1
    missing = [r for r in results if r["state"] == "missing"]
    unreadable = [r for r in results if r["state"] == "unreadable"]
    return {
        "checked": data.get("checked"),
        "counts": counts,
        "results": results,
        "exit": 1 if missing else (2 if unreadable else 0),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("rows", type=Path, help="path to a rows.yaml file")
    parser.add_argument("--json", action="store_true", help="print the result as JSON")
    parser.add_argument("--quiet", action="store_true", help="print nothing, exit with the result")
    args = parser.parse_args()

    report = check(args.rows)
    if args.json:
        print(json.dumps(report, indent=2))
    elif not args.quiet:
        for item in report["results"]:
            line = f"{item['state']:<10} {item['control']}"
            if item.get("url"):
                line += f" -> {item['url']}"
            if item.get("detail"):
                line += f" ({item['detail']})"
            print(line)
        print()
        print(json.dumps(report["counts"]))
        for item in report["results"]:
            if item["state"] == "missing":
                print(f"lost: {item['control']} -> copy its sentence from {item['url']}")
    return report["exit"]


if __name__ == "__main__":
    sys.exit(main())
