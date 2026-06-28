---
title: "Concurrency"
author: Maxim Menshikov
layout: defect
permalink: /cpp/concurrency
group:
   - cpp
---

Synchronization defects in multithreaded C++, where the language hands you raw mutexes and trusts you to use them correctly. These entries concern the disciplines that locking demands but does not enforce: acquiring multiple mutexes in a consistent global order, and matching a lock's recursion semantics to how it is actually taken.

Both failure modes share a cause — a lock is held in a way the rest of the code does not expect. Inconsistent acquisition order across threads produces classic deadlock, while re-entering a non-recursive `std::mutex` on a thread that already owns it is undefined behavior. The standard offers tools that sidestep these — `std::scoped_lock` / `std::lock` for deadlock-free multi-acquire, `std::recursive_mutex` where re-entrancy is genuinely intended — but only if applied deliberately.
