---
title: "lock on string literal is deadlock-prone"
author: Maxim Menshikov
layout: defect
permalink: /csharp/lock/string
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
String literals are interned across the entire process; locking on one shares the monitor with every other site using the same literal

# Impact

`lock("literal")` synchronizes on a string literal. The CLR **interns** string literals: every identical literal anywhere in the process is folded to a single shared `String` object. Locking on it therefore acquires a monitor whose identity is shared by every other site in the process that uses the same literal text — including unrelated assemblies that coincidentally chose the same string. The consequences:

- **Action-at-a-distance deadlock.** A completely unrelated class that does `lock("lock")` (or any matching literal) contends on *your* monitor. Lock-order inversion between the two unrelated sites deadlocks, and nothing in either file hints at the connection.
- **Over-serialization.** Code paths that should be independent serialize against each other because they happen to share literal text, creating a hidden global bottleneck.
- **Extremely hard to diagnose.** The coupling is invisible at every call site and depends on interning, so the hang is intermittent and nearly impossible to reproduce or trace to its cause.

The fix is a dedicated private lock object: `private readonly object _lock = new();` (or `static` for shared state) and `lock(_lock)`.

# Vulnerability potential

The impact is availability; there is no confidentiality or integrity vector.

1. **Trivial, low-knowledge deadlock.** Of all the weak-identity lock targets, an interned string is the easiest for foreign code to collide with: an attacker controlling any code in the process (a plugin, an add-in) needs only to use the same literal text and can `lock` your monitor, holding it forever or inverting lock order to deadlock your synchronized paths.
2. **Accidental cross-library DoS.** Even without malice, two libraries that both lock on a common literal such as `"sync"` or `"lock"` introduce a non-reproducible hang the moment both run in the same process.

There is no information disclosure or code execution; rate as a denial-of-service concern.

# Technical details

## String interning

The C# compiler emits string literals via the `ldstr` IL instruction, and the CLR guarantees that `ldstr` for equal text returns a reference to a single interned `String` object held in the process-wide intern pool. So `"abc" == (object)"abc"` is reference-equal everywhere, across all assemblies loaded into the process. `lock(x)` is `Monitor.Enter(x)`, keyed on object identity; with an interned literal, that identity is global and reachable by anyone who writes the same characters.

This makes a string literal a *weak-identity* lock target, like `Type`: you cannot bound the set of contending threads because the lock object is implicitly shared across the whole process.

## Subtlety: only literals (and explicitly interned strings) collide

A string built at runtime (concatenation, `new string(...)`, formatting) is a distinct object and is *not* automatically interned, so `lock(someRuntimeString)` does not collide with literals — but it is still a poor, confusing lock target, and someone may pass an interned string in. The robust rule is never to lock on any `string`.

## The fix

`private readonly object _lock = new()` has an identity that no other code can name or reproduce, closing the set of acquisition sites to your own source. Use `static readonly` when the lock guards static/shared state.

# Catching the issue

## CA2002

- **CA2002** — "Do not lock on objects with weak identity" — lists `String` explicitly: interned strings have process-wide identity, so this is exactly the rule that fires on `lock("...")`.

## SonarQube

- **S2445** — "Blocks should be synchronized on private fields" — flags locking on a string literal because it is not a private field.

## CodeQL

- The C# weak-identity lock queries (**`cs/lock-on-weak-identity-object`** family) report monitor acquisition on strings.

## Code review

Treat any `lock` whose target is a `string` (literal or variable) as a defect. Require a `private readonly object` field used solely for locking.

# How to reproduce

Two unrelated components lock on the same literal text; they share one monitor and deadlock, so `done` is never printed.

```csharp
using System;
using System.Threading;

class ComponentA
{
    public void Work()
    {
        lock ("shared-lock")        // bug: interned literal, globally shared
        {
            Console.WriteLine("A running");
            Thread.Sleep(200);
        }
    }
}

class Program
{
    static void Main()
    {
        var a = new ComponentA();

        // Unrelated code uses the *same literal text* -> same interned object.
        lock ("shared-lock")
        {
            var t = new Thread(a.Work);
            t.Start();
            t.Join();               // deadlock: A.Work() waits on the same monitor
        }

        Console.WriteLine("done");  // never reached
    }
}
```

