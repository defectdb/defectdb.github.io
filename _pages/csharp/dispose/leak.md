---
title: "IDisposable not disposed"
author: Maxim Menshikov
layout: defect
permalink: /csharp/dispose/leak
arch:
   - native
vulnerability:
   - Medium
ddos:
   - Medium
group_full: csharp.dispose
group:
   - csharp
   - dispose
---
The resource is declared without `using`/`using var` and without a try-finally Dispose; the OS handle / connection / buffer leaks on early return or exception

# Impact

An `IDisposable` (a file handle, socket, `SqlConnection`, `HttpResponseMessage`, `Stream`, registry key, native buffer, OS sync object, etc.) is created but never deterministically released: there is no `using`/`using var` and no `try`/`finally` that calls `Dispose`. On the happy path the object may eventually be collected, but on an **early return** or an **exception** between creation and any manual `Dispose`, the resource is abandoned. It is freed only if and when the GC runs a finalizer — and only if the type *has* one.

Concrete consequences:

- **Handle / descriptor exhaustion.** Leaked file, socket, and pipe handles accumulate until the process hits its OS handle limit, after which every new `open`/`connect`/`accept` fails.
- **Connection-pool starvation.** ADO.NET and HTTP connections come from bounded pools. Undisposed `SqlConnection`/`DbConnection` objects keep pool slots checked out until a finalizer (if any) returns them, so the pool drains and callers block until the pool timeout, then throw `InvalidOperationException` ("Timeout expired ... pool"). The whole data tier appears hung.
- **Held locks / file locks.** A leaked `FileStream` keeps an exclusive OS lock, so other code or other processes cannot open or delete the file; a leaked mutex/semaphore can deadlock waiters.
- **Memory growth.** Undisposed objects (and any native memory they pin) stay alive at least until the next GC + finalization; for types with no finalizer the native resource is never reclaimed for the life of the process.

Because these are bounded, shared resources, a steady trickle of leaks degrades into a hard failure (DoS) under sustained load.

# Vulnerability potential

Resource leaks have genuine security weight (Medium for both ratings) because exhausting a bounded resource is a denial-of-service primitive, and the held resources can have confidentiality/integrity side effects.

1. **Resource-exhaustion DoS.** If an attacker can drive the leaky path — open many connections, send many requests that each leak a handle, trigger the exception branch repeatedly — leaked handles or pooled connections accumulate until the limit is hit. Then legitimate requests fail (handle limit, "connection pool timeout", inability to open files). A small, cheap request that leaks one descriptor each time is an amplified DoS.
2. **Lock-based DoS / deadlock.** A leaked exclusive file lock or unreleased mutex/semaphore blocks other operations or processes indefinitely, hanging functionality without crashing it.
3. **Stale state and information exposure.** Connections, transactions, and temp files left open past their intended scope can keep sensitive data resident, hold database transactions/locks open, or leave temp files on disk longer than expected. Undisposed crypto objects may keep key material in memory longer than necessary.

These map to CWE-401 (missing release of resource) and CWE-772 (missing release after effective lifetime). The realistic worst case is DoS; data-exposure outcomes are situational, which keeps this at Medium rather than High.

# Technical details

## Deterministic disposal vs the finalizer/GC

The .NET GC reclaims **managed memory**, but it knows nothing about OS handles, sockets, or unmanaged buffers, and it runs only under memory pressure — not when a handle limit is hit. `IDisposable.Dispose` is the deterministic release mechanism: it runs *now*, at a point you control, freeing the resource immediately. The whole `IDisposable` contract exists precisely because GC timing is the wrong signal for non-memory resources.

## The finalizer is a backstop, not a plan

Some disposable types (those wrapping native handles, typically via `SafeHandle`) also implement a **finalizer** so the OS resource is eventually freed even if you forget to `Dispose`. But:

- Finalization is **non-deterministic** and can lag far behind: objects go on the finalization queue at the first GC and are only finalized on a later pass by a single finalizer thread. Under load, leaked resources pile up faster than they are reclaimed.
- A finalizer that frees a pooled connection still leaves the slot checked out until that finalizer runs — by which time the pool may already be exhausted.
- **Not every disposable has a finalizer.** Many wrappers (and types holding *managed* disposables only) have none, so a missed `Dispose` is **never** compensated — the resource leaks for the entire process lifetime.

So relying on finalization is, at best, delaying the failure, and at worst, a permanent leak.

## using = try/finally

`using var s = Open();` (and the block form) compiles to a `try { ... } finally { s?.Dispose(); }`, guaranteeing `Dispose` runs on *every* exit — normal completion, early `return`, or exception. That is exactly what the leaky code omits. For fields, the **Dispose pattern** (`IDisposable` on the owning type, disposing owned members in its `Dispose`) carries the same guarantee up the ownership chain. For `IAsyncDisposable`, use `await using`.

# Catching the issue

## Roslyn / .NET analyzers

- **CA2000 (Dispose objects before losing scope)** is the primary rule: it flags a local `IDisposable` that can go out of scope without `Dispose` being called on all paths, including the exception path. This is the direct detector for this defect.
- **CA2213 (Disposable fields should be disposed)** catches the field-ownership variant: a type holds a disposable member but its own `Dispose` doesn't dispose it.
- **CA1816** is related to correct `Dispose` implementation (call `GC.SuppressFinalize(this)`), relevant when you write the owning type's `Dispose`.
- **IDE0063 / IDE0067 / IDE0068 / IDE0069** suggest `using` declarations and warn about disposable locals/fields not being disposed.
- Promote CA2000/CA2213 to warnings-as-errors in `.editorconfig` so a missing `using` cannot merge.

## SonarQube

Rule **S2930 ("`IDisposable`/`IAsyncDisposable` objects should be disposed")** and **S3881** (Dispose pattern correctness) flag undisposed locals and incorrect Dispose implementations.

## CodeQL

The `cs/local-not-disposed` (and resource-leak) queries trace data flow from a disposable allocation to all exits and report paths with no `Dispose`, including across early returns and exception edges.

## Nullable / review practices

- Make `using var` the default for any local that implements `IDisposable`; treat a bare `var x = new SomethingDisposable()` without a `using` as a review flag.
- Be careful **not** to dispose objects you don't own — notably the singleton `HttpClient`, or a `Stream`/connection handed in by a caller. Use the `leaveOpen` constructor arguments where applicable.
- Stress-test under load and watch process handle count and connection-pool counters; a monotonically rising handle count is the runtime signature of this bug.

# How to reproduce

Observe that the leaky method abandons the `FileStream` on the exception path (the file stays locked / the handle leaks), while the `using` version always releases it.

```csharp
using System;
using System.IO;

class Program
{
    // BUG: if Validate throws, 'fs' is never disposed -> handle + exclusive file lock leak.
    static void WriteLeaky(string path, byte[] data)
    {
        FileStream fs = File.Open(path, FileMode.Create, FileAccess.Write, FileShare.None);
        Validate(data);          // throws -> early exit, fs.Dispose() never reached
        fs.Write(data, 0, data.Length);
        fs.Dispose();            // only runs when nothing above threw
    }

    // FIX: using guarantees Dispose on every path (return, throw, normal).
    static void WriteSafe(string path, byte[] data)
    {
        using var fs = File.Open(path, FileMode.Create, FileAccess.Write, FileShare.None);
        Validate(data);
        fs.Write(data, 0, data.Length);
    }

    static void Validate(byte[] data)
    {
        if (data.Length == 0) throw new ArgumentException("empty");
    }

    static void Main()
    {
        try { WriteLeaky("leak.tmp", Array.Empty<byte>()); } catch { }
        // The handle from WriteLeaky is now leaked until a finalizer (if any) runs.
        // This open with FileShare.None can fail because the leaked stream still holds the lock.
        try
        {
            using var probe = File.Open("leak.tmp", FileMode.Open, FileAccess.Write, FileShare.None);
            Console.WriteLine("reopened OK");
        }
        catch (IOException ex)
        {
            Console.WriteLine($"still locked by leaked handle: {ex.Message}");
        }
    }
}
```

