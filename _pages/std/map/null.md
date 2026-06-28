---
title: "Null map"
author: Maxim Menshikov
layout: defect
permalink: /std/map/null
arch:
   - native
vulnerability:
   - Low
ddos:
   - Medium
group_full: std.map
group:
   - std
   - map
---
The map might be null

# Impact

In Go a map declared but never initialized has the value ``nil``. Reading from a
``nil`` map is safe — lookups return the element type's zero value and ``len`` is
``0`` — but **writing** to a ``nil`` map (``m[k] = v``) or deleting through it in
a way that mutates triggers a runtime panic: ``assignment to entry in nil map``.
The trap is that the read side works, so a ``nil`` map can pass through a lot of
code unnoticed until the first write, which then aborts the goroutine. If the
panic is not recovered it crashes the whole program. The defect typically comes
from declaring ``var m map[K]V`` (zero value ``nil``) instead of
``m := make(map[K]V)``, from a struct field whose map was never initialized in
the constructor, or from a function that returns a ``nil`` map on an error path
that callers then write into.

# Vulnerability potential

This is principally an availability defect.

1. A write to a ``nil`` map panics; an unrecovered panic terminates the process,
   so any code path where attacker-influenced input causes a previously-only-read
   map to be written becomes a denial-of-service trigger.
2. In a server using ``recover`` per request, the panic unwinds the current
   goroutine and may leave locks held or shared state half-updated, an indirect
   correctness/consistency risk.

There is no memory-corruption angle: Go detects the condition and panics
deterministically rather than performing an unsafe write.

# Technical details

A Go map value is a pointer to a runtime ``hmap`` header; the zero value of that
pointer is ``nil``. Lookups (``mapaccess``) special-case the ``nil`` header and
return the zero value, which is why reads never fail. Assignment goes through
``mapassign``, which must allocate a bucket and therefore needs a real ``hmap``;
on a ``nil`` map it cannot, so the runtime calls ``panic`` with
``assignment to entry in nil map``.

## nil map vs empty map

``var m map[string]int`` yields a ``nil`` map: readable, not writable.
``m := make(map[string]int)`` (or a map literal ``map[string]int{}``) yields an
initialized, empty, writable map. The two are indistinguishable on read, which is
exactly why the bug hides. ``m == nil`` is the explicit test.

## Common sources

Struct fields (``type S struct { cache map[K]V }``) default their map to ``nil``
unless the constructor calls ``make``; functions that return ``map[K]V`` should
return an initialized empty map rather than ``nil`` if callers will write to it.

# Catching the issue

## Tooling

``go vet`` does not flag this directly, but ``staticcheck`` and ``golangci-lint``
(with the ``nilness`` analyzer and others) detect writes to maps that may be
``nil`` along a path. The Go runtime's panic message names the file and line, so
a single test that exercises the write path surfaces it immediately.

## Design rules

Always initialize a map with ``make`` before writing; initialize map fields in
constructors; never return a ``nil`` map from a function whose contract allows
the caller to add entries. Guard uncertain maps with
``if m == nil { m = make(map[K]V) }`` before the first write.

# How to reproduce

Run the program; it panics with ``assignment to entry in nil map`` on the write,
even though the preceding read succeeded.

```go
package main

import "fmt"

func main() {
    var m map[string]int // nil map (zero value)

    fmt.Println("read ok:", m["missing"]) // reads return zero value: 0

    m["key"] = 1 // panic: assignment to entry in nil map
    fmt.Println(m)
}
```
