---
title: "Locking"
author: Maxim Menshikov
layout: defect
permalink: /csharp/lock
group:
   - csharp
---

Defects in the choice of object passed to `lock`, where the monitor is taken on a reference that is not private to the protected region. Mutual exclusion only works when both the lock object and the data it guards are owned by the same code; sharing the lock object with the rest of the process breaks that guarantee.

Interned `string` literals, `typeof(X)` instances, and `this` are all visible to unrelated code that may lock on the very same reference, so two components that know nothing of each other can serialize against one another or deadlock. The remedy is a dedicated `private readonly object` whose only purpose is to be locked.

