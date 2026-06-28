---
title: "Null channel"
author: Maxim Menshikov
layout: defect
permalink: /ipc/channel/null
arch:
   - native
vulnerability:
   - Low
ddos:
   - Medium
group_full: ipc.channel
group:
   - ipc
   - channel
---
The channel used in this communication might be null

# Impact

In Go a channel variable that was never created with `make` holds its zero value,
`nil`. Unlike a nil map or nil pointer, operating on a nil channel does not
panic: a send to a nil channel and a receive from a nil channel both block
**forever**. A `select` case whose channel is nil is simply never selected. The
practical effect is a silently stuck goroutine. If the goroutine holds a request,
a connection, or a lock, that resource is leaked indefinitely; if `main` itself
blocks, the program hangs. Because nothing crashes and no error is returned, the
defect is easy to miss in testing and only manifests as a hang or steadily
growing goroutine count under specific conditions.

# Vulnerability potential

This issue is mainly a denial-of-service and liveness concern.

1. A goroutine permanently blocked on a nil channel never releases its stack,
   any held mutexes, or referenced objects. If the nil-channel path is reachable
   from request handling, an attacker who triggers it repeatedly leaks goroutines
   and memory until the service degrades or is killed (OOM), a denial of service.
2. A hang on a nil channel can deadlock a pipeline stage and stall all upstream
   producers, amplifying a single stuck path into a full outage. Direct
   memory-safety impact is negligible because Go is memory-safe here.

# Technical details

A channel value is internally a pointer to a runtime `hchan` structure. The zero
value of any channel type is `nil` (no `hchan`). The Go runtime defines the
blocking-forever behaviour deliberately so that nil channels can be used to
*disable* a `select` case dynamically (a useful idiom). The danger is the
*unintended* nil: a struct field channel that was never initialized, a channel
returned from a function on an error path, or a channel zeroed by a `var`
declaration without a following `make`.

## Why it does not panic

Sends/receives on closed channels panic or return immediately, but the runtime
special-cases nil to park the goroutine on a wait that is never woken. Combined
with `select`, a nil channel case is unreachable, so a `select` consisting only
of nil cases (and no `default`) blocks forever too.

## Common sources

Forgetting `make(chan T)`; returning the zero value of a named return on an
error path; resetting a channel field to `nil` and using it again.

# Catching the issue

## Static analysis

`go vet` does not flag nil-channel blocking directly, but `staticcheck` (SA
checks) and `nilness`-style analyzers can detect channels used before
initialization. Review rule: every channel field/variable must be initialized
with `make` before first use unless nil is deliberately used to disable a select
case (and that intent is commented).

## Runtime detection

The Go runtime's deadlock detector prints "all goroutines are asleep -
deadlock!" only when *every* goroutine is blocked; a single leaked goroutine is
not caught. Instead, monitor `runtime.NumGoroutine()`, take goroutine profiles
(`go tool pprof`, `/debug/pprof/goroutine`), and add timeouts (`context`,
`time.After` in `select`) so a stuck channel op fails loudly instead of hanging.

# How to reproduce

Observe that the program prints nothing and the runtime reports a deadlock,
because the receive is on a nil channel that is never made.

```go
package main

import "fmt"

func main() {
	var ch chan int // nil: never created with make
	fmt.Println("waiting...")
	<-ch // blocks forever; runtime: all goroutines asleep - deadlock
	fmt.Println("unreachable")
}
```
