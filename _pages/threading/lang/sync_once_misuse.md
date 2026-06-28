---
title: "Misuse of sync.Once"
author: Maxim Menshikov
layout: defect
permalink: /threading/lang/sync_once_misuse
arch:
   - native
vulnerability:
   - Low
ddos:
   - Low
group_full: threading.lang
group:
   - threading
   - lang
---
sync.Once is used incorrectly

# Impact

Go's `sync.Once` guarantees that the function passed to its `Do` method runs
exactly once, even under concurrent calls, and that all callers observe its
side effects before `Do` returns. Misusing it breaks initialization in subtle,
timing-dependent ways. Common misuses and their consequences:

- Copying a `sync.Once` value (passing it by value, or copying a struct that
  embeds one) produces an independent zero-valued `Once`, so the action runs
  again. The "single" initialization happens more than once.
- Calling `once.Do` recursively from inside the very function it is running
  deadlocks: `Do` blocks waiting for the in-progress call to finish, which is the
  current goroutine.
- Using a different `Once` instance per call (e.g. a local variable, or a new
  `Once` each iteration) defeats the purpose entirely; the guard is meaningless.
- Expecting `Do` to retry on failure: if the function panics or fails, `Once`
  still records it as done, so the resource is never initialized and every later
  caller proceeds with a nil/zero value, often causing a nil dereference far
  from the real fault.

# Vulnerability potential

This issue has limited security relevance.

1. A recursive or self-referential `Do` deadlocks the calling goroutine; if that
   goroutine holds a request, repeated triggering can exhaust a worker pool and
   deny service.
2. If `Once` is meant to perform a one-time security setup (load keys, seed a
   RNG, build an allowlist) and a copy or wrong instance causes it to be skipped
   or repeated, the program may run with uninitialized or re-initialized
   security state. The direct memory-safety impact is otherwise negligible.

# Technical details

`sync.Once` contains a `done` flag (accessed atomically) and an internal
`Mutex`. The first caller to win takes the mutex, double-checks `done`, runs the
function, then sets `done`. The `done` flag is set in a deferred statement, so it
is marked done even if the function panics — this is intentional and means
`Once` is not a retry primitive.

## Non-copyability

Because `Once` holds a `Mutex`, it must not be copied after first use; `go vet`'s
`copylocks` pass reports this. A copied `Once` has its own zero state and will
re-run.

## Correct usage patterns

Store the `Once` as a field of a long-lived struct (or a package-level variable)
and always call `Do` on the *same* instance through a pointer. For
initialization that can fail and should be retried, use a custom guard or the
`sync.OnceValue`/`sync.OnceFunc` helpers (Go 1.21+) only where one-shot
semantics are actually desired; for retry-on-error, do not use `Once` at all.

# Catching the issue

## go vet

`go vet` runs the `copylocks` analyzer, which flags any copy of a value
containing a `sync.Once` (or any lock), catching the most common misuse.

## Race detector

Build and test with `-race`. While it does not directly understand `Once`
semantics, it surfaces the concurrent unsynchronized access that results when a
copied or wrong `Once` fails to establish the intended happens-before edge.

## Linters and review

`staticcheck` reports several `Once` antipatterns. In review, require that each
`Once` is a stable field/global referenced by pointer, that `Do` is never called
from within its own function, and that the action is idempotent and does not rely
on `Once` for retry.

# How to reproduce

Observe a self-deadlock: calling `once.Do` recursively blocks forever (the Go
runtime reports "all goroutines are asleep - deadlock").

```go
package main

import "sync"

var once sync.Once

func initX() {
	// BUG: re-entering Do on the same Once deadlocks.
	once.Do(initX)
}

func main() {
	once.Do(initX)
}
```
