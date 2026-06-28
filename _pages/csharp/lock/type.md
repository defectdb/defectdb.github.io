---
title: "lock on typeof(X) is process-wide"
author: Maxim Menshikov
layout: defect
permalink: /csharp/lock/type
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
All instances and all callers share the same Type object as a monitor; use a private readonly instance field instead

# Impact

`lock(typeof(X))` synchronizes on the runtime `Type` object for `X`. A `Type` is a process-wide singleton: there is exactly one `Type` instance per type per load context, shared by every instance of the class, every caller, and every assembly in the process. Locking on it therefore creates a single global lock with a globally visible identity. The consequences:

- **Cross-component deadlock.** Any other code anywhere in the process that does `lock(typeof(X))` — or `lock(someXInstance.GetType())`, which yields the same object — contends on your monitor. Unrelated assemblies that never heard of each other now share a lock and can deadlock through order inversion.
- **Over-serialization.** Independent instances of `X` that should run concurrently are all funnelled through one monitor, destroying parallelism and creating a contention bottleneck.
- **Lock held hostage.** Foreign code can take and hold the type lock indefinitely, stalling every critical section in your class.

The fix is a private static lock object scoped to the class: `private static readonly object _lock = new();` and `lock(_lock)`.

# Vulnerability potential

The impact is on availability; there is no confidentiality or integrity vector.

1. **Process-wide deadlock by any cooperating or hostile code.** Because the `Type` object is reachable from anywhere via `typeof(X)` or `obj.GetType()`, untrusted plugins or unrelated libraries can acquire the same monitor and deadlock or starve every consumer of your synchronized code path. The attacker needs no reference to your objects — just the public type name.
2. **Amplified DoS surface.** A single global lock means one stuck thread can hang functionality across many otherwise-independent components, widening the blast radius of any hang triggered by attacker input.

No memory-safety, injection, or disclosure issue exists; the relevance is denial of service.

# Technical details

## Type objects have weak, shared identity

`lock(x)` is `Monitor.Enter(x)`, and the monitor is keyed on the object's identity (its header). `typeof(X)` returns the singleton `RuntimeType` for `X` in the current load context. Every `typeof(X)` and every `instanceOfX.GetType()` in the process returns *that same reference*, so all of them target one monitor. Historically (with multiple AppDomains and domain-neutral assemblies) the same `Type` could even be shared across AppDomains, making the lock cross even isolation boundaries.

This is the textbook "weak identity" problem: the object you are locking on has an identity that is visible and reachable far outside the code you control, so you cannot bound the set of threads that may contend for it.

## Why a private static field fixes it

`private static readonly object _lock = new()` allocates an ordinary object whose only reference lives in a private static field of your class. Its identity is not derivable from the type, an instance, or a literal, so no external code can name it. The lock is still shared across all instances of the class (correct for protecting static/shared state) but is invisible outside the class — a closed, auditable set of acquisition sites.

# Catching the issue

## CA2002

- **CA2002** — "Do not lock on objects with weak identity" — directly targets `lock` on a `Type` (along with strings, `MarshalByRefObject`, `MemberInfo`, `ExecutionEngineException`, `OutOfMemoryException`, and similar process- or domain-shared objects).

## SonarQube

- **S2445** — "Blocks should be synchronized on private fields" — flags locking on anything that is not a private field, including `typeof(...)`.

## CodeQL

- The C# weak-identity lock queries (**`cs/lock-on-weak-identity-object`** family) report monitor acquisition on `Type` objects.

## Code review

Reject any `lock(typeof(...))` or `lock(x.GetType())`. Require a `private static readonly object` dedicated to synchronization.

# How to reproduce

Unrelated code holding `lock(typeof(Service))` blocks the service's own critical section; the program deadlocks and never prints `done`.

```csharp
using System;
using System.Threading;

class Service
{
    public void Run()
    {
        lock (typeof(Service))      // bug: monitor is the process-wide Type object
        {
            Console.WriteLine("service running");
            Thread.Sleep(200);
        }
    }
}

class Program
{
    static void Main()
    {
        var s = new Service();

        // Any code in the process can take the very same monitor.
        lock (typeof(Service))
        {
            var t = new Thread(s.Run);
            t.Start();
            t.Join();               // deadlock: Run() waits for the same Type lock
        }

        Console.WriteLine("done");  // never reached
    }
}
```

