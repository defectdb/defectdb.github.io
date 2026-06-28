---
title: "Threads"
author: Maxim Menshikov
layout: defect
permalink: /context/thread
group:
   - context
---

Defects that surface when code runs on a thread and shares process-wide
resources with concurrent execution. Operations that look local — writing to
standard output, reading input from a shared stream — actually touch global
state, so their effects interleave unpredictably with other threads, producing
scrambled output, lost or stolen input, and timing-dependent behaviour that is
hard to reproduce.

