---
title: "Unread channel"
author: Maxim Menshikov
layout: defect
permalink: /ipc/channel/unread
arch:
   - native
vulnerability:
   - None
ddos:
   - Low
group_full: ipc.channel
group:
   - ipc
   - channel
---
The channel is never read

# Impact

A channel is written to but no goroutine ever receives from it. On an
*unbuffered* channel the first send blocks forever, stalling the sender. On a
*buffered* channel, sends succeed until the buffer fills, after which every
further send blocks. In both cases the sending goroutines park permanently and
are never reclaimed, which is a goroutine (and memory) leak. Values placed in the
channel are never consumed, so the work they represent is silently dropped. The
program does not crash or error; it slowly accumulates blocked goroutines and the
objects they reference, degrading over time.

# Vulnerability potential

This issue has essentially no memory-safety relevance (Go is safe here) but a
modest denial-of-service angle.

1. If senders are spawned per request and their channel is never drained, each
   request leaks a blocked goroutine and its retained data; sustained traffic
   grows memory and goroutine count without bound until the process is killed.
2. Otherwise the consequence is dropped work and wasted resources rather than a
   security boundary being crossed.

# Technical details

Send and receive on an unbuffered channel rendezvous: a send completes only when
a matching receive is ready. With no receiver, the send's goroutine is parked on
the channel's send wait queue indefinitely. A buffered channel decouples sender
and receiver up to its capacity; once full it behaves like the unbuffered case.

## Buffered vs unbuffered

`make(chan T)` (capacity 0) blocks the very first send if unread.
`make(chan T, N)` absorbs N sends, then blocks. A buffer only delays, it does not
fix, a missing reader.

## Common sources

A producer goroutine launched but its consumer forgotten or removed in a
refactor; a results channel returned to a caller that ignores it; a `select`
that no longer has a receiving case. The fix is to ensure a receiver exists for
the channel's full lifetime, or to use a `select` with `default`/`ctx.Done()` so
the send cannot block indefinitely, or to not produce values nobody consumes.

# Catching the issue

## Goroutine leak detection

Use `go.uber.org/goleak` in tests to assert no goroutines are left blocked after
a test completes; an unread channel surfaces as a leaked goroutine parked in
`chansend`. Profile live processes with `/debug/pprof/goroutine` and watch
`runtime.NumGoroutine()` for monotonic growth.

## Static analysis and review

`staticcheck` and channel-direction typing help, but the strongest defense is a
review rule: every channel has a clearly owned receiver, and senders use a
bounded/cancelable send (`select` with `ctx.Done()`), so a vanished consumer
fails fast instead of leaking.

# How to reproduce

Observe a deadlock: the send on an unbuffered channel blocks forever because
nothing ever reads it.

```go
package main

import "fmt"

func main() {
	ch := make(chan int) // unbuffered, never read
	fmt.Println("sending...")
	ch <- 1 // blocks forever; runtime: all goroutines asleep - deadlock
	fmt.Println("unreachable")
}
```
