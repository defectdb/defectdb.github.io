---
title: "Defer in loop"
author: Maxim Menshikov
layout: defect
permalink: /var/deinit/defer_in_loop
arch:
   - native
vulnerability:
   - Low
ddos:
   - Medium
group_full: var.deinit
group:
   - var
   - deinit
---
There might be too many deferred routines

# Impact

In Go a `defer` runs when the surrounding *function* returns, not when the loop
iteration ends. Placing `defer f.Close()` (or any cleanup) inside a loop means
every iteration stacks another deferred call that does not execute until the
whole function finishes. Over a long-running or large loop this keeps every
opened resource alive simultaneously: file descriptors, network connections,
database rows, mutex locks, or memory pinned by closures all accumulate. The
function eventually hits the open-file-descriptor limit, exhausts a connection
pool, or holds a lock far longer than intended — typically failing with
`too many open files` partway through, with the earlier work already done.

# Vulnerability potential

This issue has a real potential to contribute to denial of service.

1. If the loop count is driven by attacker-controlled input — number of files in
   an uploaded archive, rows in a request, entries in a paginated API response —
   an attacker can force the function to hold thousands of descriptors or
   connections at once, exhausting the per-process or system-wide limit and
   taking the service down or starving unrelated requests.
2. A deferred unlock inside a loop holds a mutex for the entire function,
   serializing or deadlocking other goroutines and stalling throughput.

It has little direct memory-safety relevance; Go's runtime prevents the
corruption-style issues, so the risk is resource exhaustion rather than code
execution.

# Technical details

`defer` pushes a call onto a per-goroutine stack that unwinds at function exit.
The deferred functions run in LIFO order *after* the `return` expression is
evaluated. Inside a loop this is almost always a misunderstanding: the developer
expects per-iteration cleanup but gets per-function cleanup, so resources are
released only once, all at the end.

## The fix: scope the defer to a function
Wrap the loop body in its own function (a closure called per iteration, or a
named helper) so the `defer` fires at the end of each iteration. Alternatively,
close explicitly at the end of the iteration and handle the error inline,
without `defer`.

## Note on loop-variable capture
A related historical hazard — a deferred closure capturing the loop variable —
was mitigated in Go 1.22, which gives each iteration a fresh variable. The
resource-accumulation problem described here is independent of that change and
still applies.

# Catching the issue

## Vet and linters
`go vet` does not flag this directly, but `golangci-lint` does via `revive`'s
`defer` rule and the `gocritic` `deferInLoop` check, which report a `defer`
inside a `for` loop. Enable these in CI.

## Runtime symptoms and limits
Watch for `too many open files` errors and rising descriptor counts
(`lsof`, `/proc/<pid>/fd`). Lower `ulimit -n` in tests to surface leaks early,
and use leak detectors (e.g. `go.uber.org/goleak`) to catch goroutines/resources
left open after a function returns.

# How to reproduce

Run against a directory with many files; the descriptors are not released until
`processAll` returns, so it can fail with "too many open files" before finishing.

```go
package main

import (
	"fmt"
	"os"
)

func processAll(paths []string) error {
	for _, p := range paths {
		f, err := os.Open(p)
		if err != nil {
			return err
		}
		defer f.Close() // BUG: runs only when processAll returns, not per iteration
		// ... use f ...
		_ = f
	}
	return nil // every file opened above is still open here
}

func main() {
	// Fix: move the body into a func so defer fires each iteration.
	fmt.Println("see processAll: descriptors accumulate across the loop")
}
```
