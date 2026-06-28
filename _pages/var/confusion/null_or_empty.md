---
title: "Misuse of null/empty variables"
author: Maxim Menshikov
layout: defect
permalink: /var/confusion/null_or_empty
arch:
   - native
vulnerability:
   - Low
ddos:
   - Low
group_full: var.confusion
group:
   - var
   - confusion
---
Null/empty variables might be used incorrectly

# Impact

In Go a `nil` slice or map and an empty-but-allocated one are *almost* but not
quite interchangeable, and conflating the two leads to subtle bugs. Ranging over,
reading from, or taking `len()` of a nil slice or map works fine, which lulls
developers into treating `nil` and empty as the same — until a `nil` map is
*written to*, which panics, or until serialization, equality, or "was this field
provided?" logic needs to tell them apart. The result is intermittent panics on
write, JSON that emits `null` where `[]` was expected (breaking clients), and
business logic that cannot distinguish "no value supplied" from "explicitly
empty".

# Vulnerability potential

Direct security impact is limited. The main concern is availability:

1. Writing to a `nil` map (`m[k] = v` when `m == nil`) panics with `assignment
   to entry in nil map`; if such a path is reachable from request handling it
   becomes a crash-on-demand denial-of-service primitive.
2. Logic that conflates nil with empty can misclassify input — for example
   treating a missing list as an empty allow/deny set — which, depending on the
   surrounding code, may relax a check; the flaw there is the ambiguous
   semantics, not memory safety.

# Technical details

A `nil` slice has no backing array but `len` and `cap` of 0 and is fully usable
for reads, `append` (which allocates), and `range`. A `nil` map supports reads
(returning the zero value) and `len`, but **panics on assignment** because there
is no hash table to insert into. This asymmetry is the crux of the defect.

## nil vs empty are observably different
- JSON: a `nil` slice marshals to `null`; an empty non-nil slice (`[]T{}`)
  marshals to `[]`. Clients and schemas often care.
- Equality / presence: only `nil` answers "field never set"; `[]T{}` answers
  "set, but empty". Collapsing them loses that distinction.
- `reflect.DeepEqual(nilSlice, emptySlice)` is `false`.

## Strings and pointers
Go strings cannot be nil; the empty string `""` is the zero value, so "nil vs
empty" for strings is really "empty vs non-empty" — but pointer-to-string or
interface fields reintroduce the nil/empty/absent three-way distinction.

# Catching the issue

## Static analysis
`staticcheck` flags writes to potentially-nil maps and some nil-related mistakes;
`golangci-lint` with `nilness` helps. There is no single check that proves
intent, so the discipline matters more than the tool.

## Conventions
Always initialize a map with `make(map[K]V)` (or a literal) before writing.
Decide per type whether your API treats nil and empty alike, and document it; for
JSON responses pick `[]T{}` when clients expect an array. When presence matters
(PATCH semantics, optional fields), use pointers or a dedicated "set" flag rather
than overloading empty.

# How to reproduce

Run the program; reads from the nil map are fine, but the write panics with
"assignment to entry in nil map".

```go
package main

import "fmt"

func main() {
	var counts map[string]int // nil map (not made)

	fmt.Println(len(counts))      // 0 — fine
	fmt.Println(counts["x"])      // 0 — read of missing key is fine
	for range counts {            // ranging a nil map is fine
	}

	counts["x"]++ // panic: assignment to entry in nil map
}
```
