---
title: "Wrong channel direction"
author: Maxim Menshikov
layout: defect
permalink: /ipc/channel/wrong_direction
arch:
   - native
vulnerability:
   - None
ddos:
   - None
group_full: ipc.channel
group:
   - ipc
   - channel
---
Send on a receive-only channel, or receive from a send-only channel

# Impact

Go channel types carry an optional direction: `chan<- T` is send-only and
`<-chan T` is receive-only. Attempting the wrong operation — sending on a
receive-only channel, receiving from a send-only channel, or closing a
receive-only channel — is a **compile-time type error**. The program does not
build, so there is no runtime impact. The practical consequence is a failed
build and the developer time spent diagnosing it; the directional types are in
fact a safety feature catching a real mistake (a goroutine using a channel for
the wrong half of the protocol) before it can run. The defect signals confusion
about which side of a channel a given function is supposed to drive.

# Vulnerability potential

This defect has no security relevance. It is rejected by the compiler, so no
faulty binary is produced; there is nothing to exploit at runtime. It is a
correctness/clarity issue caught at build time.

# Technical details

A bidirectional channel value (`chan T`) is implicitly convertible to either
directional type, but not the reverse, and the directional types restrict the
permitted operations:

- `chan<- T` (send-only): only `ch <- v` and `close(ch)` are allowed; receiving
  is a type error.
- `<-chan T` (receive-only): only `<-ch` is allowed; sending and `close(ch)` are
  type errors.

## Why directions exist

Function signatures use directional channel parameters to document and enforce
roles: a producer takes a `chan<- T`, a consumer takes a `<-chan T`. This lets
the compiler guarantee, for example, that a consumer cannot accidentally send or
close the shared channel. The "wrong direction" defect is the compiler refusing
an operation the role forbids.

## Typical messages

The compiler emits errors such as "invalid operation: cannot receive from
send-only channel" or "invalid operation: cannot send to receive-only channel",
or "cannot close receive-only channel".

# Catching the issue

## The compiler

`go build`/`go vet` catch this unconditionally — it cannot reach a running
binary. No sanitizer or runtime check is needed.

## Design and review

Prefer directional channel types in every function signature that takes a
channel; this both documents intent and lets the compiler reject misuse at the
boundary. In review, confirm producers receive `chan<- T` and consumers receive
`<-chan T`, and that `close` happens only on the (sole) sending side.

# How to reproduce

Observe that this does not compile: "invalid operation: cannot send to
receive-only channel ch".

```go
package main

func send(ch <-chan int) { // receive-only parameter
	ch <- 1 // compile error: cannot send to receive-only channel
}

func main() {
	ch := make(chan int, 1)
	send(ch)
}
```
