---
title: "IPC"
author: Maxim Menshikov
layout: defect
permalink: /ipc
---

Defects in inter-process and inter-goroutine communication — the mechanisms by which independent units of execution exchange data and coordinate. When the conduit itself is misused, the failure is not in either endpoint's logic but in the plumbing between them, producing deadlocks, lost messages, or panics that are hard to attribute to a single line of code.

The current focus is Go's channels, the language's primary synchronisation primitive, where the state of the channel — open, closed, nil, or pointed the wrong way — determines whether a send or receive proceeds, blocks forever, or crashes the program.
