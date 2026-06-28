#!/usr/bin/env python3
"""
Validate DefectDB entries for structural consistency and uniformity.

Checks every page under _pages/ and the taxonomy in _data/group.yml:

  * frontmatter parses and carries the required keys
  * permalink matches the file's location on disk
  * leaf (defect) pages carry arch / vulnerability / ddos / group_full / group
    with valid severity values, the five standard sections, no leftover
    scaffold markers, and non-empty section bodies
  * group / group_full match the page's ancestry
  * every group.yml node has an index page and vice versa
  * every leaf's group_full points at a real taxonomy node
  * permalinks are unique

Exits non-zero (and prints a report) if anything is wrong. No third-party
dependency is required beyond PyYAML.

Usage:  python3 tools/validate_entries.py [repo_root]
"""
import os
import sys
import re

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required: pip install pyyaml")

ROOT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
PAGES = os.path.join(ROOT, "_pages")
GROUP_YML = os.path.join(ROOT, "_data", "group.yml")

SEVERITIES = {"None", "Low", "Medium", "High"}
SECTIONS = [
    "# Impact",
    "# Vulnerability potential",
    "# Technical details",
    "# Catching the issue",
    "# How to reproduce",
]

errors = []
warnings = []


def err(page, msg):
    errors.append(f"{page}: {msg}")


def warn(page, msg):
    warnings.append(f"{page}: {msg}")


def split_front_matter(text, page):
    """Return (frontmatter_dict, body) or (None, None) on failure."""
    if not text.startswith("---"):
        err(page, "missing YAML front matter (file must start with '---')")
        return None, None
    parts = text.split("---", 2)
    if len(parts) < 3:
        err(page, "front matter is not terminated by a second '---'")
        return None, None
    try:
        fm = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as e:
        err(page, f"front matter is not valid YAML: {e}")
        return None, None
    if not isinstance(fm, dict):
        err(page, "front matter is not a mapping")
        return None, None
    return fm, parts[2]


def as_scalar(v):
    """group/arch/vulnerability are written as single-item lists; normalize."""
    if isinstance(v, list):
        return v[0] if len(v) == 1 else v
    return v


def expected_permalink(rel):
    """rel is path under _pages. Map to the page's canonical permalink."""
    rel = rel[:-3]  # strip .md
    if rel.endswith("/index"):
        rel = rel[: -len("/index")]
    return "/" + rel


def validate_page(abspath):
    rel = os.path.relpath(abspath, PAGES)
    page = "_pages/" + rel
    text = open(abspath, encoding="utf-8").read()
    fm, body = split_front_matter(text, page)
    if fm is None:
        return

    is_index = os.path.basename(rel) == "index.md"

    # ---- common keys ----
    for key in ("title", "author", "layout"):
        if key not in fm:
            err(page, f"missing required front-matter key '{key}'")
    if fm.get("layout") != "defect":
        err(page, f"layout must be 'defect', got {fm.get('layout')!r}")

    # ---- permalink matches location ----
    want = expected_permalink(rel)
    have = fm.get("permalink")
    if have != want:
        err(page, f"permalink {have!r} does not match location (expected {want!r})")

    permalink = have if isinstance(have, str) else want
    segs = permalink.strip("/").split("/")
    ancestors = segs[:-1]

    # ---- group must list the ancestry ----
    if "group" in fm:
        grp = fm["group"]
        grp = grp if isinstance(grp, list) else [grp]
        if grp != ancestors:
            err(page, f"group {grp} does not match ancestry {ancestors}")
    elif not is_index and ancestors:
        err(page, "leaf page is missing 'group'")

    if is_index:
        return  # category landing pages need nothing further

    # ---- leaf (defect) page checks ----
    for key in ("arch", "vulnerability", "ddos", "group_full"):
        if key not in fm:
            err(page, f"defect page missing front-matter key '{key}'")

    for key in ("vulnerability", "ddos"):
        if key in fm:
            val = as_scalar(fm[key])
            if val not in SEVERITIES:
                err(page, f"{key} value {val!r} not in {sorted(SEVERITIES)}")

    if "group_full" in fm:
        want_gf = ".".join(ancestors)
        if fm["group_full"] != want_gf:
            err(page, f"group_full {fm['group_full']!r} != expected {want_gf!r}")

    # ---- body structure ----
    if "<!--CONTENT:" in body:
        err(page, "leftover scaffold marker '<!--CONTENT:...-->' in body")

    positions = []
    for sec in SECTIONS:
        m = re.search(r"^%s\s*$" % re.escape(sec), body, re.MULTILINE)
        if not m:
            err(page, f"missing section heading '{sec}'")
        else:
            positions.append((sec, m.start(), m.end()))

    # description line above the first section must be non-empty
    if positions:
        first_start = positions[0][1]
        intro = body[:first_start].strip()
        if not intro:
            err(page, "missing description text above the first section")

    # each section must have non-empty content
    if len(positions) == len(SECTIONS):
        for i, (sec, _s, e) in enumerate(positions):
            nxt = positions[i + 1][1] if i + 1 < len(positions) else len(body)
            content = body[e:nxt].strip()
            if not content:
                err(page, f"section '{sec}' has no content")
    return permalink, fm


def walk_pages():
    permalinks = {}
    index_permalinks = set()
    leaf_group_fulls = {}
    for dirpath, _dirs, files in os.walk(PAGES):
        for f in sorted(files):
            if not f.endswith(".md"):
                continue
            abspath = os.path.join(dirpath, f)
            rel = os.path.relpath(abspath, PAGES)
            result = validate_page(abspath)
            page = "_pages/" + rel
            pl = expected_permalink(rel)
            if pl in permalinks:
                err(page, f"duplicate permalink {pl!r} (also {permalinks[pl]})")
            permalinks[pl] = page
            if os.path.basename(rel) == "index.md":
                index_permalinks.add(pl)
            elif isinstance(result, tuple) and len(result) == 2:
                _pl, fm = result
                if "group_full" in fm:
                    leaf_group_fulls[fm["group_full"]] = page
    return permalinks, index_permalinks, leaf_group_fulls


def walk_group_yml(index_permalinks):
    data = yaml.safe_load(open(GROUP_YML, encoding="utf-8"))
    node_fulls = set()

    def visit(node, path_segs):
        name = node.get("name")
        full = node.get("full")
        permalink = node.get("permalink")
        segs = path_segs + [name]
        exp_full = ".".join(segs)
        exp_perma = "/" + "/".join(segs)
        loc = f"group.yml:{exp_full}"
        if not name:
            err(loc, "node missing 'name'")
        if "title" not in node:
            err(loc, "node missing 'title'")
        if full != exp_full:
            err(loc, f"full {full!r} != expected {exp_full!r}")
        if permalink != exp_perma:
            err(loc, f"permalink {permalink!r} != expected {exp_perma!r}")
        node_fulls.add(exp_full)
        if exp_perma not in index_permalinks:
            err(loc, f"no index page for taxonomy node (expected _pages{exp_perma}/index.md)")
        for child in node.get("group", []) or []:
            visit(child, segs)

    for top in data:
        visit(top, [])
    return node_fulls


def main():
    if not os.path.isdir(PAGES):
        sys.exit(f"_pages not found under {ROOT}")
    if not os.path.isfile(GROUP_YML):
        sys.exit(f"{GROUP_YML} not found")

    permalinks, index_permalinks, leaf_group_fulls = walk_pages()
    node_fulls = walk_group_yml(index_permalinks)

    # every index page must correspond to a taxonomy node
    for pl in sorted(index_permalinks):
        full = pl.strip("/").replace("/", ".")
        if full not in node_fulls:
            err(f"_pages{pl}/index.md", "index page has no matching node in _data/group.yml")

    # every leaf's group_full must be a real taxonomy node
    for gf, page in sorted(leaf_group_fulls.items()):
        if gf not in node_fulls:
            err(page, f"group_full {gf!r} is not a node in _data/group.yml")

    n_leaf = len(permalinks) - len(index_permalinks)
    print(f"Scanned {len(permalinks)} pages "
          f"({n_leaf} defects, {len(index_permalinks)} categories), "
          f"{len(node_fulls)} taxonomy nodes.")

    if warnings:
        print(f"\n{len(warnings)} warning(s):")
        for w in warnings:
            print("  WARN ", w)

    if errors:
        print(f"\n{len(errors)} error(s):", file=sys.stderr)
        for e in errors:
            print("  ERROR", e, file=sys.stderr)
        sys.exit(1)

    print("\nAll entries valid.")


if __name__ == "__main__":
    main()
