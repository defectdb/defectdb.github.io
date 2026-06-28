---
title: "Context"
author: Maxim Menshikov
layout: defect
permalink: /context
---

Defects that arise when code runs in an execution context it was not written
for: the assumptions a routine makes about what it may block on, who else is
running concurrently, and what it is allowed to do are violated by the
environment it actually executes in. The same line of code can be correct in
one context and a hazard in another.

The entries here divide along the two contexts that most often catch
developers out. Code reached from an interrupt handler must never sleep or
block, yet ordinary-looking calls quietly do; and code that runs on a thread
shares I/O and timing with everything else in the process, so operations that
are harmless in a single-threaded program — printing, scanning input — become
sources of interleaving, contention, and corrupted shared state.

