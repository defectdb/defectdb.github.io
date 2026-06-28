---
title: "Unlock"
author: Maxim Menshikov
layout: defect
permalink: /std/unlock
group:
   - std
---

Defects in releasing a lock, where the unlock does not pair with a matching
acquisition by the current thread. Unlocking a mutex twice, or unlocking one
that was never locked or is held by another thread, is undefined behavior: it
can corrupt the mutex's internal state, wake the wrong waiter, or leave the
lock permanently broken. These slips typically come from tangled control flow
or error paths where the bookkeeping of acquire and release falls out of step.

