---
title: "lock(this) is deadlock-prone"
author: Maxim Menshikov
layout: defect
permalink: /csharp/lock/this
arch:
   - native
vulnerability:
   - Low
ddos:
   - Medium
group_full: csharp.lock
group:
   - csharp
   - lock
---
Any external caller holding a reference to this instance can lock against the same monitor; use a private readonly object instead

# Impact

`lock(this)` takes the monitor on the instance itself. Because the instance reference is handed to any caller that constructs or receives the object, the synchronization lock is effectively public. The consequences:

- **Deadlock.** Any external code that holds a reference to the object can `lock` on it for its own reasons. If that code holds the instance lock while waiting on something your synchronized method needs (or simply in the opposite order to your internal locks), the two paths deadlock. You did not write the conflicting code and may not even know it exists.
- **Lock held hostage / starvation.** External code can take `lock(instance)` and hold it indefinitely, blocking every one of your internal critical sections that synchronize on `this`. Your object's progress now depends on code you do not control.
- **Broken encapsulation.** The lock object is part of the type's public surface by accident. You cannot reason locally about who can acquire it, which defeats the purpose of the lock.

The fix is a dedicated, non-public lock that nothing outside the class can reach: `private readonly object _lock = new();` and `lock(_lock)`.

# Vulnerability potential

The security relevance is availability (denial of service); there is no direct confidentiality or integrity impact.

1. **Deliberate deadlock by untrusted code.** In a process that loads plugins, add-ins, or other partially trusted assemblies, hostile code holding a reference to your object can acquire `lock(instance)` and either hold it forever or take locks in a conflicting order, deadlocking the threads that use your synchronized methods. Because the lock is publicly reachable, the attacker needs only the reference, not access to your source.
2. **Accidental DoS from third-party libraries.** Even without malice, an unrelated library that also does `lock(someObject)` on an object that happens to be your instance (e.g. exposed via an event args or a shared collection) can introduce a non-reproducible hang.

There is no information-disclosure or code-execution vector here; rate accordingly.

# Technical details

## What the lock actually locks

`lock(x)` compiles to `Monitor.Enter(x, ref lockTaken)` / `Monitor.Exit(x)`. The argument is an object reference, and the monitor is associated with the *object identity*, stored in the object header (sync block index). Two `lock` statements serialize against each other if and only if they pass references to the *same object*. With `lock(this)`, that object is the instance, and its identity is visible to every holder of a reference.

## Why publicly reachable lock objects are dangerous

Correct locking requires that you can enumerate every site that acquires a given monitor, so you can guarantee a consistent acquisition order and bounded hold times. When the lock object is reachable from outside the class, that set is open-ended: callers, derived classes, and unrelated libraries can all `Monitor.Enter` the same header. You lose the ability to prove the absence of lock-order inversions, which is the necessary condition for deadlock freedom.

A `private readonly object _lock = new()` has no reference path out of the class, so the set of acquiring sites is exactly the sites in your own source — closed, auditable, and safe.

# Catching the issue

## SonarQube

- **S2445** — "Blocks should be synchronized on private fields" — fires on `lock(this)`, `lock` on a parameter, or `lock` on any non-private/accessible field.

## Roslyn analyzers

- **CA2002** — "Do not lock on objects with weak identity" — covers `this` when the type can cross AppDomain boundaries (e.g. `MarshalByRefObject`), as well as `Type`, strings, and other weak-identity objects.

## CodeQL

- The C# query **`cs/lock-on-this`** (and the related "lock on locally created object / weak identity" queries) flags monitor acquisition on `this`.

## Code review

Ban `lock(this)`, `lock(typeof(...))`, and `lock("...")` outright. Require every monitor target to be a `private readonly object` field created with `new()` and used for nothing else.

# How to reproduce

External code locking the instance blocks the object's own synchronized method; the program deadlocks and never prints `done`.

```csharp
using System;
using System.Threading;

class Worker
{
    public void DoWork()
    {
        lock (this)             // bug: monitor is publicly reachable
        {
            Console.WriteLine("work running");
            Thread.Sleep(200);
        }
    }
}

class Program
{
    static void Main()
    {
        var w = new Worker();

        // Hostile/unaware external code grabs the same monitor and holds it.
        lock (w)
        {
            var t = new Thread(w.DoWork);
            t.Start();
            t.Join();           // deadlock: DoWork waits for lock(this) == lock(w)
        }

        Console.WriteLine("done");   // never reached
    }
}
```

