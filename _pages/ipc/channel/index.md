---
title: "Channels"
author: Maxim Menshikov
layout: defect
permalink: /ipc/channel
group:
   - ipc
---

Defects in the use of Go channels, where the channel's state or direction makes an operation block forever, panic, or silently do nothing. A send or receive behaves entirely differently depending on whether the channel is nil, has been closed, or is constrained to one direction — and getting that state wrong is the dominant source of goroutine leaks and channel panics.

The entries here span the recurring failure modes: operating on a `nil` channel, which blocks the goroutine indefinitely; sending on a closed channel, which panics; channels that are never drained or never fed, stranding the goroutines waiting on them; and values pushed against a channel's declared direction.
