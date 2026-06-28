---
title: "Slice modification might be incorrect"
author: Maxim Menshikov
layout: defect
permalink: /array/slice/modification
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
The slice after modification might have unexpected value

# Impact

Modifying a Go slice — especially via `append` — can have surprising effects
because the slice header and its backing array are decoupled. If there is spare
capacity, `append` writes *in place* and any other slice sharing that backing
array sees the change; if capacity is exhausted, `append` allocates a new array
and the original is left untouched. The same line of code therefore behaves
differently depending on runtime capacity, producing data that is sometimes
shared and sometimes not. The result is wrong values, lost or duplicated
elements, and aliasing bugs that pass tests on small inputs and fail on large
ones.

# Vulnerability potential

This is primarily a correctness defect; Go's memory safety prevents corruption.

1. In a server that reuses a backing buffer across requests, an in-place
   modification can cause one client's data to appear in another's response — an
   information-disclosure bug.
2. `append` that unexpectedly mutates shared state can break invariants relied
   on elsewhere, occasionally enabling logic-level security bypasses (e.g. a
   filtered slice that still aliases unfiltered data).
3. Misjudged growth can also cause excess allocation/retention, a mild
   resource-exhaustion concern.

# Technical details

`append(s, x)` returns a slice; you must assign the result back (`s = append(s,
x)`) because the header may change. Whether the underlying array changes depends
on `cap(s)`:

## In-place vs reallocating append

If `len(s) < cap(s)`, `append` stores into the existing array and returns a
header pointing at the same memory — visible to every alias. If `len(s) ==
cap(s)`, it allocates a larger array (growth is roughly geometric), copies, and
returns a header pointing at fresh memory, so aliases are decoupled.

## The classic aliasing trap

`b := a[:2]; b = append(b, x)` overwrites `a[2]` when `a` has capacity,
silently clobbering an element of `a`. Guard against it with the three-index
form `a[:2:2]`, which sets capacity to 2 so the next `append` is forced to
reallocate.

## Modifying while ranging

`for i := range s { s = append(s, ...) }` is evaluated against the original
length, but element writes through an aliased slice during iteration can produce
stale or duplicated reads.

# Catching the issue

## Tooling

`go vet` reports the common `x = append(y, ...)`-without-using-result and
`append`-result-not-assigned mistakes; `staticcheck`/`golangci-lint` add more
slice-aliasing diagnostics.

## Race detector

`go test -race` catches concurrent in-place modifications of a shared backing
array.

## Tests

Test with inputs that both fit and exceed initial capacity, since the bug only
appears in one regime. `go test -fuzz` is effective at hitting the boundary.

## Practice

Always assign `append`'s result; use `slices.Clone` or `copy` to get an
independent slice before modifying; use the three-index slice form when passing
a sub-slice that the callee might append to.

# How to reproduce

Run the program; observe that appending to a sub-slice overwrites an element of
the original because spare capacity lets `append` write in place.

```go
package main

import "fmt"

func main() {
	a := make([]int, 3, 5) // len 3, cap 5 — spare capacity
	a[0], a[1], a[2] = 1, 2, 3

	b := a[:2]            // shares backing array, cap is still 5
	b = append(b, 99)     // writes into a[2] in place (capacity available)

	fmt.Println(b) // [1 2 99]
	fmt.Println(a) // [1 2 99]  <- a[2] was 3, now clobbered
}
```

