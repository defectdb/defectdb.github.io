---
title: "Capacity of the object is too big"
author: Maxim Menshikov
layout: defect
permalink: /var/size/too_big_capacity
arch:
   - native
vulnerability:
   - None
ddos:
   - Low
group_full: var.size
group:
   - var
   - size
---
Overbuffered object

# Impact

Allocating a slice, map, or buffer with a capacity far larger than what is
actually used wastes memory for the lifetime of the object. A single
over-allocation is harmless, but the pattern multiplied across many objects, or
inside a hot loop, inflates the working set, increases garbage-collector
pressure, and hurts cache locality. A subtler effect is *retention*: a small
slice that re-slices a much larger backing array (`big[:1]`) keeps the entire
backing array alive, so a tiny visible length pins megabytes that the GC cannot
reclaim. The program is correct but uses far more memory than it needs.

# Vulnerability potential

There is no memory-safety or information-disclosure angle here — over-allocation
does not corrupt state or cross a trust boundary. The only security-adjacent
concern is denial of service: if the capacity is derived from
attacker-controlled input (a length prefix, a `Content-Length`, a count field),
an attacker can request a huge `make([]T, 0, n)` and force the process to
reserve large amounts of memory per request, exhausting RAM. That is a
pre-allocation/untrusted-size problem; bounded, validated sizes remove it.

# Technical details

In Go, `make([]T, len, cap)` reserves `cap` elements immediately. Capacity that
greatly exceeds the eventual length is pure overhead. Two common sources:

## Over-eager pre-sizing
Guessing a large capacity "to be safe" when the typical fill is small. `append`
grows slices automatically and amortizes reallocation, so over-reserving rarely
pays off unless the final size is known and large.

## Backing-array retention via re-slicing
`small := big[:n]` shares `big`'s backing array; `cap(small)` is still the full
length of `big`, so the whole array stays reachable as long as `small` lives.
Returning such a sub-slice from a function that read a large buffer is a classic
hidden leak. The fix is to copy the needed part into a right-sized slice
(`append([]T(nil), big[:n]...)`).

## Untrusted sizes
`make([]byte, 0, n)` with `n` from the network lets a client dictate allocation
size; always cap `n` against a sane limit before allocating.

# Catching the issue

## Profiling
`pprof` heap profiles (`go tool pprof`) and `runtime.ReadMemStats` reveal
objects whose capacity dwarfs their length and backing arrays kept alive longer
than expected. Benchmark with `-benchmem` to see allocations per operation.

## Linters and review
`golangci-lint` (`prealloc` for the opposite case, `gocritic`) and code review
catch obviously oversized `make` calls and re-slicing that retains large
backings. As a rule, validate any externally supplied size before using it as a
capacity, and copy out small results from large temporary buffers.

# How to reproduce

Run with memory stats; the returned 4-byte slice pins the entire 10 MB backing
array because re-slicing preserves capacity.

```go
package main

import (
	"fmt"
	"runtime"
)

func firstFour() []byte {
	big := make([]byte, 10<<20) // 10 MB scratch buffer
	// ... fill big ...
	return big[:4] // BUG: keeps all 10 MB alive via the shared backing array
}

func main() {
	s := firstFour()
	runtime.GC()
	var m runtime.MemStats
	runtime.ReadMemStats(&m)
	fmt.Printf("len=%d cap=%d heap=%d KB\n", len(s), cap(s), m.HeapAlloc/1024)
	// Fix: out := append([]byte(nil), big[:4]...); return out
}
```
