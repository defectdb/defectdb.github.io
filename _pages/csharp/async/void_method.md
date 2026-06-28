---
title: "async void method"
author: Maxim Menshikov
layout: defect
permalink: /csharp/async/void_method
arch:
   - native
vulnerability:
   - Low
ddos:
   - Medium
group_full: csharp.async
group:
   - csharp
   - async
---
async void cannot be awaited and crashes the process on unhandled exceptions; use async Task instead (except for event handlers)

# Impact

An `async void` method returns `void` instead of `Task`, so the compiler-generated state machine has nothing to hand back to the caller. The caller cannot `await` it, cannot know when it finishes, and cannot observe whether it succeeded. This produces three concrete failures:

- **Process crash on unhandled exception.** When an exception escapes an `async void` method, there is no `Task` to carry it. The runtime rethrows it on the captured `SynchronizationContext` (or, with no context, on a thread-pool thread) as an unobserved exception. No `try`/`catch` around the *call site* can catch it, because the call returned long before the exception was raised. The result is an unhandled exception that tears down the process.
- **Fire-and-forget races.** Because completion is invisible, subsequent code runs while the `async void` work is still in flight, producing ordering bugs, use of half-initialized state, and disposal of objects still in use.
- **Untestable.** A test cannot `await` the method, so it has no reliable way to wait for completion or to assert on thrown exceptions.

The only legitimate use is an event handler whose delegate signature requires `void` (e.g. `EventHandler`).

# Vulnerability potential

The dominant risk is availability rather than confidentiality or integrity.

1. **Denial of service via forced crash.** If an `async void` method can throw on attacker-influenced input (a malformed request, an oversized payload, a parse failure), the attacker can reliably crash the hosting process. Unlike a faulting request handler that returns `500`, this exception bypasses the normal exception pipeline and terminates the process, taking down all in-flight requests with it. Repeated triggering is a cheap, reliable DoS.
2. **Swallowed security-relevant failures.** Fire-and-forget `async void` work (audit logging, token revocation, cache invalidation) can fail silently because nobody observes its result, leaving the system in a state the caller assumes was reached.

There is no direct memory-safety or injection angle; the security relevance is confined to availability and silent failure of background work.

# Technical details

## Why the exception escapes

For an `async Task` method, the compiler builds a state machine driven by `AsyncTaskMethodBuilder`. When the body throws, the builder calls `SetException`, which stores the exception on the returned `Task`. The exception is dormant until someone `await`s, calls `.Result`/`.Wait()`, or the `Task` is finalized — at which point it surfaces in a controlled way.

An `async void` method is instead driven by `AsyncVoidMethodBuilder`. There is no `Task`, so `SetException` cannot park the exception anywhere observable. Its implementation captures the `SynchronizationContext` present when the method started and posts the exception to it via `Post`, which rethrows on that context. If there is no context (typical for console apps, thread-pool callbacks, and most server frameworks), it is rethrown directly on a thread-pool thread. Either way it becomes an unhandled exception on a thread that the original caller does not control, so `AppDomain.UnhandledException` fires and the CLR terminates the process.

## Completion is unobservable

`AsyncVoidMethodBuilder` exposes no awaitable. The caller's stack unwinds at the first incomplete `await` inside the method, returning control immediately while the continuation is still scheduled. There is no handle to join on, which is the root of both the race conditions and the untestability.

The fix is simply to return `Task` (or `Task<T>`): `async Task DoWorkAsync()`. The caller can then `await` it, exceptions land on the `Task`, and tests can synchronize on completion.

# Catching the issue

## Roslyn / analyzers

- **VSTHRD100** (`Microsoft.VisualStudio.Threading.Analyzers`) — "Avoid `async void` methods" — flags every `async void` that is not an event handler.
- **VSTHRD101** — warns about `async void` lambdas, a common hidden form.
- The .NET SDK analyzer **CA2007**/**AsyncFixer** family and **AsyncFixer03** ("Fire-and-forget async void methods") also report it.

## SonarQube

- **S3168** — "`async` methods should not return `void`" — exactly this rule, with the event-handler exception built in.

## Code review

Grep for `async void`. Allow it only where the signature is mandated by a delegate type (event handlers, `EventHandler`/`EventHandler<T>`). In those handlers, wrap the entire body in `try`/`catch` so no exception escapes, since the handler itself is still an `async void`. Everywhere else require `async Task`.

# How to reproduce

The `try`/`catch` at the call site does not catch the exception; the process terminates with an unhandled exception.

```csharp
using System;
using System.Threading.Tasks;

class Program
{
    static async void FireAndForget()
    {
        await Task.Delay(100);
        throw new InvalidOperationException("boom");
    }

    static async Task Main()
    {
        try
        {
            FireAndForget();        // returns immediately; nothing to await
        }
        catch (Exception ex)
        {
            // Never reached: the method already returned before throwing.
            Console.WriteLine($"caught: {ex.Message}");
        }

        await Task.Delay(500);      // give the async void time to throw
        Console.WriteLine("still alive?");   // never printed: process crashed
    }
}
```

