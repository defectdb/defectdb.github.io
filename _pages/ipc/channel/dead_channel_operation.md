---
title: "Operation on closed channel"
author: Maxim Menshikov
layout: defect
permalink: /ipc/channel/dead_channel_operation
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
Operation on closed channel

# Impact

Certain operations on a closed Go channel cause a runtime panic that, if not
recovered, terminates the entire program:

- **Sending** to a closed channel (`ch <- v`) panics with "send on closed
  channel".
- **Closing** an already-closed channel (`close(ch)`) panics with "close of
  closed channel".
- **Closing a nil channel** panics with "close of nil channel".

Receiving from a closed channel does *not* panic — it returns immediately with
the element type's zero value and `ok == false` — which is by design, but a
receiver that ignores the `ok` flag will silently process an endless stream of
zero values (e.g. a busy `for range`-like loop reading zeros), spinning the CPU.
A single unrecovered panic on one goroutine crashes the whole process, so a
mis-timed close can take a server down.

# Vulnerability potential

This issue is principally a denial-of-service concern.

1. If the close/send ordering depends on external timing or input (e.g. a close
   driven by client disconnect racing with a send driven by a request), an
   attacker can provoke the "send on closed channel" panic and crash the process,
   denying service. Without `recover`, one panic ends the program.
2. A receiver that ignores `ok` after close can be driven into a tight loop
   consuming zero values, wasting CPU. The memory-safety impact is otherwise low
   since Go remains memory-safe.

# Technical details

A channel has a `closed` flag in its runtime `hchan`. `close` sets it and wakes
all blocked senders and receivers. The runtime then enforces:

- send checks `closed` and panics if set;
- `close` checks `closed`/nil and panics on double-close or nil;
- receive on a closed, drained channel returns `zero, false`.

## Ownership discipline

The idiomatic rule is that the **sole sender owns the close**: only the goroutine
(or coordinator) responsible for producing values closes the channel, and exactly
once. Multiple senders must never close directly; instead use a separate done
signal, a `sync.Once` around the close, or a dedicated closer that waits for all
senders to finish (e.g. via `sync.WaitGroup`).

## Receive idiom

Use `v, ok := <-ch` or `for v := range ch` (which stops on close) so closure is
handled explicitly rather than yielding a stream of zero values.

# Catching the issue

## Race detector

`go test -race` / `-race` builds catch the data race between a `close` and a
concurrent `send`/`close` that underlies most of these panics, reporting both
stacks before the panic occurs nondeterministically in production.

## Static analysis and review

`staticcheck` flags some closed-channel misuses. Review rules: a channel is
closed in exactly one place, by its owner, after all sends are done; senders
never close; nil channels are never closed; receivers always test `ok`.

## Defensive recovery

Where a send/close race cannot be fully designed out, wrapping the operation so a
panic is recovered (and logged) prevents a whole-process crash, though fixing the
ownership model is preferable.

# How to reproduce

Observe a panic "send on closed channel" that crashes the program.

```go
package main

func main() {
	ch := make(chan int, 1)
	close(ch)
	ch <- 1 // panic: send on closed channel
}
```
