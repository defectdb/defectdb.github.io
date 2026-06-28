---
title: "Overloading of garbage collector"
author: Maxim Menshikov
layout: defect
permalink: /gc/misuse/overload
arch:
   - native
vulnerability:
   - Low
ddos:
   - Medium
group_full: gc.misuse
group:
   - gc
   - misuse
---
Overloading of garbage collector

# Impact

Code that allocates excessively — many short-lived objects in a hot loop, large
temporary slices/maps rebuilt each iteration, heavy use of boxing/interface
conversions, or per-call buffers that could be reused — drives the garbage
collector to run frequently and do a lot of work. In Go this shows up as high GC
CPU time, frequent GC cycles, rising "GC assist" where allocating goroutines are
forced to help collect, and increased tail latency from collector activity even
though the GC is concurrent. The program spends a growing fraction of CPU on
memory management instead of useful work; throughput drops and p99 latency
spikes. In the extreme, allocation outpaces collection and the live heap grows
until the process is OOM-killed.

# Vulnerability potential

This issue is principally a denial-of-service concern.

1. If the allocation rate is driven by request size or count (e.g. building a
   large temporary structure per request, or O(n^2) allocation on attacker-sized
   input), an attacker can force the GC into near-continuous operation,
   collapsing throughput and inflating latency for all users — an algorithmic /
   resource-exhaustion DoS.
2. Unbounded live-heap growth from retained allocations can trigger OOM and crash
   the process. There is no direct memory-corruption risk; Go remains
   memory-safe.

# Technical details

Go uses a concurrent, tri-color, mark-sweep collector. Its pacer triggers a cycle
based on heap growth relative to the live set (governed by `GOGC`, default 100,
i.e. collect when the heap doubles since the last collection). A high allocation
rate means cycles trigger often; if mutators allocate faster than the background
collector can keep up, they incur **GC assist** work, directly stealing CPU from
application logic.

## Sources of pressure

Allocating inside hot loops; returning new slices/maps instead of reusing
buffers; converting values to `interface{}` (which may box); appending without
preallocating capacity; excessive string concatenation; escaping locals forced to
the heap by the escape analyzer.

## Mitigations

Reuse buffers via `sync.Pool`; preallocate slices/maps with known capacity
(`make([]T, 0, n)`); avoid unnecessary interface boxing and pointer-heavy
structures; reduce escapes so values stay on the stack; tune `GOGC` or set a
`GOMEMLIMIT` as a guardrail. The goal is to cut the *allocation rate*, which is
what the GC ultimately responds to.

# Catching the issue

## Profiling

Use `pprof` heap and allocation profiles (`/debug/pprof/heap`,
`-memprofile`, `go test -benchmem`) to find allocation hot spots; `alloc_objects`
and `alloc_space` point straight at the offending call sites. The
`GODEBUG=gctrace=1` environment variable prints per-cycle GC stats (pause,
CPU%, heap sizes) so you can see the collector running too often.

## Escape analysis and benchmarks

`go build -gcflags=-m` reports which values escape to the heap. Benchmarks with
`-benchmem` show `allocs/op` and `B/op`; track these in CI so a regression that
multiplies allocations is caught before release. Runtime metrics
(`runtime.ReadMemStats`, `runtime/metrics`) expose GC CPU fraction for production
monitoring.

# How to reproduce

Observe high allocation count and GC activity: each iteration allocates a fresh
1 MiB slice that is immediately discarded. Run with `GODEBUG=gctrace=1` to see
frequent collections.

```go
package main

import "fmt"

func main() {
	var sink byte
	for i := 0; i < 100000; i++ {
		buf := make([]byte, 1<<20) // 1 MiB allocated and thrown away each loop
		buf[0] = byte(i)
		sink ^= buf[0]
	}
	fmt.Println(sink)
}
```
