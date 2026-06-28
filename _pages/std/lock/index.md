---
title: "Locking"
author: Maxim Menshikov
layout: defect
permalink: /std/lock
group:
   - std
---

Defects in acquiring a lock, chiefly taking a mutex that the current thread
already holds. With a non-recursive mutex a double lock is undefined behavior
and typically deadlocks the thread against itself; even where it is detected,
it signals confusion about which locks are held along a code path. The root
cause is usually a function that locks and then calls, directly or indirectly,
another function that locks the same mutex.

