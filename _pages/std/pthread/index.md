---
title: "Pthread"
author: Maxim Menshikov
layout: defect
permalink: /std/pthread
group:
   - std
---

Defects in the use of the POSIX threads API, where the library's contracts
around thread lifetime and resource ownership are subtle and easy to violate.
The grouped problems concern how a thread terminates and what it leaves behind:
unwinding past the point that frees thread-local resources, or exiting in a way
that strands memory or synchronization state.

