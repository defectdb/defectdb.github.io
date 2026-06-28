---
title: "Unwritten channel"
author: Maxim Menshikov
layout: defect
permalink: /ipc/channel/unwritten
arch:
   - native
vulnerability:
   - None
ddos:
   - Medium
group_full: ipc.channel
group:
   - ipc
   - channel
---
Nothing ever writes to a channel

# Impact

A channel is read from, but no goroutine ever sends to it and it is never closed.
The receiving goroutine blocks forever on `<-ch`. Any goroutine waiting on that
receive is leaked, along with everything it references; if the blocked receive is
on the path to producing output or releasing a resource, that work never
completes. When the receiver is `main` (or the only remaining runnable
goroutine), the Go runtime detects the global stall and aborts with "all
goroutines are asleep - deadlock!". When other goroutines remain runnable, there
is no crash — just a silently stuck reader and a resource leak.

# Vulnerability potential

This issue is a liveness / denial-of-service concern with no direct
memory-safety impact.

1. A reader permanently blocked on a never-written channel holds its goroutine,
   stack, and any captured objects forever. If such readers are created per
   request/connection, repeated triggering leaks goroutines and memory until the
   service is starved or OOM-killed.
2. A stalled receive in a pipeline blocks the consumer stage and can cascade into
   a full hang of dependent work, turning one missing producer into a
   service-wide outage.

# Technical details

A receive on a channel completes when either a value is sent or the channel is
closed (closing wakes all blocked receivers, which then read the zero value).
With no sender and no close, neither event occurs, so the receiver stays parked
on the channel's receive wait queue indefinitely.

## Missing close as the usual cause

Idiomatic Go signals "no more values" by *closing* the channel; a `for v := range
ch` loop ends only on close. Forgetting to close — or forgetting to start the
producer at all, or the producer returning early on an error path before sending —
leaves the reader hanging. A `select` whose only viable case reads such a channel
is likewise stuck unless it has a `default` or a timeout/cancellation case.

## Distinguishing from a nil channel

Here the channel is a real, made channel; it simply has no writer. The blocking
mechanism is the empty receive queue, not the nil special case, but the
observable hang is the same.

# Catching the issue

## Deadlock detector and timeouts

The runtime's all-goroutines-asleep detector catches the case where the stuck
reader is the last runnable goroutine. For partial stalls, add a timeout or
cancellation:
`select { case v := <-ch: ...; case <-ctx.Done(): ...; case <-time.After(d): ... }`
so a missing producer turns into a handled error rather than an infinite wait.

## Leak detection and review

Use `go.uber.org/goleak` in tests and goroutine profiles in production to spot
readers parked in `chanrecv`. Review rule: every channel has an identified
producer that always either sends the expected values or closes the channel
(typically via `defer close(ch)` in the producer), guaranteeing every receiver
eventually unblocks.

# How to reproduce

Observe a deadlock: the receive blocks forever because nothing sends to or closes
the channel.

```go
package main

import "fmt"

func main() {
	ch := make(chan int) // made, but no writer and never closed
	fmt.Println("receiving...")
	v := <-ch // blocks forever; runtime: all goroutines asleep - deadlock
	fmt.Println("got", v)
}
```
