---
title: "blocking wait on Task"
author: Maxim Menshikov
layout: defect
permalink: /csharp/task/sync_wait
arch:
   - native
vulnerability:
   - Low
ddos:
   - Medium
group_full: csharp.task
group:
   - csharp
   - task
---
Task.Wait() / Task.Result block the current thread; combined with a captured SynchronizationContext (UI/ASP.NET) this deadlocks. Use await instead

# Impact

Blocking on a `Task` with `.Wait()`, `.Result`, or `.GetAwaiter().GetResult()` turns asynchronous code back into synchronous code, and does so in the most dangerous way possible.

Two distinct failure modes follow:

- **Deadlock.** On a single-threaded `SynchronizationContext` — classic ASP.NET (`AspNetSynchronizationContext`) or a WinForms/WPF UI thread — the thread that blocks on the task is the only thread that can run the task's continuation. The continuation cannot start until the thread is free, and the thread will not be free until the continuation completes. Both sides wait forever; the request hangs or the UI freezes.
- **Thread-pool starvation.** Even without a captured context, every blocked thread is a thread-pool thread parked doing nothing while it waits. Under load, many concurrent blocking waits consume all available pool threads. The pool grows only slowly (roughly one new thread per 500 ms by default), so throughput collapses and the process appears hung even though no single call has deadlocked.

A secondary consequence: `.Wait()` and `.Result` wrap any thrown exception in an `AggregateException`, so the original exception type is no longer caught by an ordinary `catch (SpecificException)` and stack traces become harder to read. (`GetAwaiter().GetResult()` unwraps to the original exception but still blocks.)

# Vulnerability potential

This is primarily an availability defect, not a memory-safety one. The security relevance is denial of service:

1. **Deadlock as a DoS primitive.** On a single-threaded context, an attacker who can trigger a code path that blocks on an async call can hang a request thread permanently. In classic ASP.NET this also pins the request to its context; a handful of such requests can wedge the application.
2. **Thread-pool starvation as a DoS amplifier.** An endpoint that blocks on async I/O lets a modest request rate exhaust the thread pool. Legitimate traffic then stalls behind the slow pool-growth heuristic — a low-effort availability attack with no memory corruption required.

There is no direct path to memory corruption, RCE, or information disclosure. The `AggregateException` wrapping can cause exceptions to go uncaught and surface as crashes, but that is a robustness issue rather than an exploitable one. Overall vulnerability potential is low; the DoS potential is real and is captured by the `ddos` rating.

# Technical details

## SynchronizationContext capture

When code reaches an `await` on an incomplete task, the awaiter captures the current `SynchronizationContext` (or, if none, the current `TaskScheduler`). When the awaited operation completes, the continuation is `Post`ed back to that captured context so the rest of the method runs on the "right" thread (the UI thread, or an ASP.NET request context).

A single-threaded context dispatches all posted work through one thread. If that thread is sitting inside `task.Wait()` / `task.Result`, it is blocked and cannot pump the message queue. The continuation that would complete `task` is queued to a thread that will never pick it up:

```
UI thread: ... ── task.Wait() ──► blocked, holding the context
                                     ▲
continuation needs to Post here ─────┘   (never runs)
```

This is the classic *sync-over-async* deadlock. `ConfigureAwait(false)` inside the awaited method avoids capturing the context, which is why it sidesteps the deadlock — but it does not fix thread-pool starvation, and you cannot rely on every transitive callee using it.

## Thread-pool semantics

A blocking wait on the thread pool parks a worker thread in a kernel wait. The pool treats sustained saturation conservatively, injecting additional threads slowly. With N concurrent blocking waits and fewer than N available threads, new work queues behind the starved pool. Because the threads are blocked rather than running, CPU looks idle while latency climbs — the hallmark of starvation.

## Exception wrapping

`Task.Wait()` and `Task.Result` throw `AggregateException` wrapping the real exception in `InnerExceptions`. `GetAwaiter().GetResult()` rethrows the original exception (preserving its type and stack via `ExceptionDispatchInfo`) but is just as blocking. The correct fix in all cases is to `await` the task; if a synchronous result is genuinely unavoidable, the entire call chain should be restructured to be synchronous rather than bridged.

# Catching the issue

## Roslyn analyzers

Several analyzers flag the pattern directly. The Microsoft.VisualStudio.Threading.Analyzers package emits `VSTHRD002` ("avoid problematic synchronous waits") on `.Wait()`, `.Result`, and `GetAwaiter().GetResult()`, and `VSTHRD103` when an async alternative exists. Related rule `CA2007` (ConfigureAwait) points at the context-capture half of the problem. Treat these as build-breaking warnings in library code.

## SonarQube / CodeQL

SonarQube rule `S6966` and similar flag synchronous blocking of async APIs and recommend the `await` form. CodeQL queries can be written to find member accesses to `Task.Result` / calls to `Task.Wait()` reachable from request handlers.

## Code review and banned APIs

Add `Task.Wait`, `Task<T>.Result`, and `GetAwaiter().GetResult()` to a banned-API list (e.g. `BannedSymbols.txt` consumed by `Microsoft.CodeAnalysis.BannedApiAnalyzers`) for any code that runs under a UI or request `SynchronizationContext`. In review, treat any `.Result`/`.Wait()` on a non-already-completed task as a defect and ask for the async signature instead. Load-test endpoints to expose starvation that does not reproduce at low concurrency.

# How to reproduce

Run under a single-threaded `SynchronizationContext`; the program hangs forever at `.Result` instead of printing `done`.

```csharp
using System;
using System.Threading;
using System.Threading.Tasks;

class SingleThreadContext : SynchronizationContext
{
    readonly System.Collections.Concurrent.BlockingCollection<(SendOrPostCallback, object?)> _q = new();
    public void Run() { foreach (var (cb, st) in _q.GetConsumingEnumerable()) cb(st); }
    public override void Post(SendOrPostCallback d, object? state) => _q.Add((d, state));
}

class Program
{
    static async Task<int> GetValueAsync()
    {
        await Task.Delay(100);   // captures the context; continuation must Post back here
        return 42;
    }

    static void Main()
    {
        var ctx = new SingleThreadContext();
        SynchronizationContext.SetSynchronizationContext(ctx);

        // The only thread that can run the continuation is now blocked here -> deadlock.
        int value = GetValueAsync().Result;

        Console.WriteLine($"done: {value}");   // never reached
    }
}
```

