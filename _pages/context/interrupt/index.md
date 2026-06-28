---
title: "Interrupts"
author: Maxim Menshikov
layout: defect
permalink: /context/interrupt
group:
   - context
---

Defects in code that executes in interrupt context, where the cardinal rule is
that the handler must run to completion quickly and must never block. Calling
into anything that can sleep — a delay, a mutex that may contend, an allocation
that can wait on reclaim — stalls or deadlocks the handler and, with it, the
part of the system the interrupt was meant to service.

