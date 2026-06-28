#!/usr/bin/env python3
"""
Dependency-free internal link checker for the built Jekyll site.

Walks every .html file under _site/, extracts href= / src= targets, and verifies
that each *internal* link resolves to a file that actually exists in the build.
External links (http/https/protocol-relative/mailto/tel/data), fragments and
empty hrefs are skipped — this guards against broken on-site navigation only,
which is what we control.

GitHub Pages serves `<path>.html` at the extensionless URL `<path>`, so an
internal link to `/a/b/c` is considered satisfied by `_site/a/b/c.html`.

Usage:  python3 tools/check_links.py [site_dir]
"""
import os
import re
import sys
from urllib.parse import urldefrag, urlparse

SITE = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "_site")

LINK_RE = re.compile(r'(?:href|src)\s*=\s*"([^"]*)"', re.IGNORECASE)
SKIP_PREFIX = ("http://", "https://", "//", "mailto:", "tel:", "data:",
               "javascript:", "#")


def resolve(target, page_dir):
    """Map a URL path to a candidate file path under SITE, or None to skip."""
    target, _frag = urldefrag(target)
    target = target.split("?", 1)[0]
    if not target:
        return None
    if target.startswith("/"):
        base = SITE + target
    else:
        base = os.path.normpath(os.path.join(page_dir, target))
    # directory link -> index.html
    if target.endswith("/"):
        return [os.path.join(base, "index.html")]
    last = os.path.basename(base)
    if "." in last:
        return [base]
    # extensionless: GitHub Pages style pretty URL
    return [base + ".html", os.path.join(base, "index.html")]


def main():
    if not os.path.isdir(SITE):
        sys.exit(f"site dir not found: {SITE} (run `jekyll build` first)")

    broken = []
    n_files = 0
    n_links = 0
    for dirpath, _dirs, files in os.walk(SITE):
        for f in files:
            if not f.endswith(".html"):
                continue
            n_files += 1
            abspath = os.path.join(dirpath, f)
            page = os.path.relpath(abspath, SITE)
            html = open(abspath, encoding="utf-8", errors="replace").read()
            for raw in LINK_RE.findall(html):
                raw = raw.strip()
                if not raw or raw.lower().startswith(SKIP_PREFIX):
                    continue
                # ignore absolute URLs with a scheme that slipped through
                if urlparse(raw).scheme:
                    continue
                cands = resolve(raw, dirpath)
                if cands is None:
                    continue
                n_links += 1
                if not any(os.path.exists(c) for c in cands):
                    broken.append((page, raw))

    print(f"Checked {n_links} internal links across {n_files} HTML files.")
    if broken:
        print(f"\n{len(broken)} broken internal link(s):", file=sys.stderr)
        for page, raw in broken:
            print(f"  ERROR {page} -> {raw}", file=sys.stderr)
        sys.exit(1)
    print("All internal links resolve.")


if __name__ == "__main__":
    main()
