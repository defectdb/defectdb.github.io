---
title: "Exit"
author: Maxim Menshikov
layout: defect
permalink: /std/pthread/exit
group:
   - std
   - pthread
---

Defects in how a thread terminates with `pthread_exit`. Unlike returning from
the thread function, calling `pthread_exit` ends the thread at an arbitrary
point in the call stack: automatic objects between that point and the thread's
entry are not destroyed in the way a normal return would arrange, so heap
allocations and other resources owned by intervening frames can leak.

