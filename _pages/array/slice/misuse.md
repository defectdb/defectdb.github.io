---
title: "Slice misuse"
author: Maxim Menshikov
layout: defect
permalink: /array/slice/misuse
arch:
   - native
vulnerability:
   - Low
ddos:
   - None
group_full: array.slice
group:
   - array
   - slice
---
The slice might be used incorrectly

# Impact

A Go slice is a small header — pointer, length, and capacity — over a shared
backing array. Misusing it rarely crashes (the runtime bounds-checks every
index), but it produces *wrong results that compile cleanly*: data is silently
shared when a copy was intended, mutations bleed into unrelated slices, more
memory is retained than expected, or an out-of-range slice expression panics at
runtime. The damage is correctness and resource use rather than memory
corruption, but in a long-running service these aliasing bugs are notoriously
hard to track down.

# Vulnerability potential

Slice misuse in Go is mostly a correctness and resource concern; Go's runtime
bounds checking prevents the classic memory-corruption exploits.

1. A slice of a large buffer keeps the *entire* backing array alive as long as
   the sub-slice is referenced. Holding many such slices is a memory-retention
   bug that an attacker can amplify into a Denial-of-Service.
2. An out-of-range slice expression panics; if reachable from untrusted input
   and not recovered, it crashes the goroutine/process (DoS).
3. Unintended aliasing can let one request's data leak into another's response
   in a server that reuses buffers, which is an information-disclosure risk.

# Technical details

`s[low:high]` yields a new header sharing the same backing array; the elements
are not copied. The three-index form `s[low:high:max]` additionally caps
capacity at `max-low`, which is the tool for preventing later `append` from
reaching into shared storage.

## Length vs capacity

You may slice up to capacity, not just length: `s[:cap(s)]` is valid and exposes
elements beyond `len(s)`. Indexing past `len` panics, but *slicing* up to `cap`
does not — a common source of "stale" data appearing in a re-grown slice.

## Sub-slice retention

`small := big[0:1]` keeps all of `big`'s backing array reachable. To release the
rest, copy: `small := append([]T(nil), big[0:1]...)` or use `slices.Clone`.

## Out-of-range expressions

`s[2:10]` panics when `10 > cap(s)`. Slice bounds, unlike index bounds, are
checked against capacity, not length.

# Catching the issue

## go vet and analyzers

`go vet` plus `golangci-lint` (with `gocritic`, `staticcheck`) flag suspicious
slice patterns, including append-result-not-assigned and obviously bad bounds.

## Race detector

Run tests with `go test -race`; if a misused slice causes two goroutines to
touch the same backing array, the detector reports the conflicting access.

## Runtime

Slice-bounds and index panics are caught by the runtime with a clear message
(`slice bounds out of range`); run with representative inputs and fuzz with
`go test -fuzz` to surface them.

## Review

Use the three-index slice form when handing a sub-slice to code that may
`append`; use `copy`/`slices.Clone` when you need independence from the source.

# How to reproduce

Run the program; observe that writing through the sub-slice also changes the
original, because both share one backing array.

```go
package main

import "fmt"

func main() {
	original := []int{1, 2, 3, 4, 5}

	// sub shares the same backing array as original.
	sub := original[1:3] // {2, 3}
	sub[0] = 99          // intended to touch only sub...

	fmt.Println(sub)      // [99 3]
	fmt.Println(original) // [1 99 3 4 5]  <- original mutated too
}
```

