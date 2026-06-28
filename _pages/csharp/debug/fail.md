---
title: "Debug.Fail called"
author: Maxim Menshikov
layout: defect
permalink: /csharp/debug/fail
arch:
   - native
vulnerability:
   - Low
ddos:
   - None
group_full: csharp.debug
group:
   - csharp
   - debug
---
Debug.Fail unconditionally aborts at runtime

# Impact

`Debug.Fail(message)` (and the `Debug.Fail(message, detailMessage)` overload) is an unconditional assertion failure — it is equivalent to `Debug.Assert(false, message)`. Reaching it means control flow arrived at a point the author declared unreachable or invalid.

As with `Debug.Assert`, behavior is split by build configuration:

- In a Debug build (`DEBUG` defined), the call reports through `System.Diagnostics.Trace`. The default Windows listener shows an Abort/Retry/Ignore dialog; headless hosts write the message and a stack trace to the trace output, and a fail-configured listener can terminate the process.
- In a Release build (`DEBUG` not defined), the whole call is removed by the compiler. Nothing happens; execution falls through to the code after the `Debug.Fail`.

The concrete risk is the same false confidence as `Debug.Assert`: a branch the developer marked "can't happen / must not happen" is loudly flagged during development but silently allowed to continue in production. If `Debug.Fail` is sitting in, say, the `default` of a `switch` that classifies untrusted input, the Release build will fall straight through that branch with no error, running whatever code follows on an unhandled case.

# Vulnerability potential

`Debug.Fail` carries no direct memory-safety or injection exposure; its security relevance is indirect and identical in shape to `Debug.Assert`:

1. Disappearing guard. If a `Debug.Fail` is used as the *only* rejection for an invalid or unauthorized case (an "unreachable" `default` branch, a "this input is impossible" path), Release builds drop it. The supposedly-rejected case then executes the fall-through code with no error, which can become a logic bypass, an unhandled state, or a downstream null/bounds fault.
2. Debug-build information disclosure. The failure message, detail message, and a stack trace are emitted by the Debug listener. A Debug build reachable by an attacker leaks internal structure and the developer's own description of the "impossible" state.

The `ddos` rating is `None`: in Release the call is absent, and in Debug the abort/dialog is development-time behavior that does not belong on a production attack surface. The residual risk is the design error of treating a compiled-out debug aid as a real runtime check.

# Technical details

## `[Conditional("DEBUG")]` again

`Debug.Fail` is decorated with `[Conditional("DEBUG")]`, exactly like `Debug.Assert`. If `DEBUG` is not defined at the call site's compilation, the C# compiler omits the entire call and the evaluation of its arguments. Standard Release configurations define `TRACE` but not `DEBUG`, so the elision is automatic. Because arguments are not evaluated when elided, building a `Debug.Fail` message via a method with side effects means those side effects also vanish in Release.

## What happens in Debug

`Debug.Fail` calls into the same `TraceInternal` / `Trace.Listeners` path as a failed `Debug.Assert`. The `DefaultTraceListener` writes the message and detail plus a captured stack trace; in an interactive Windows session with assert UI enabled, it shows the Abort / Retry / Ignore message box (Abort terminates, Retry breaks into the debugger, Ignore continues). In a non-interactive process (service, container, CI agent) there is no dialog, so the outcome depends on the configured listeners — frequently the message is just written to trace output and execution continues, meaning a `Debug.Fail` can pass unnoticed even in a headless Debug run.

## Relationship to Debug.Assert and Trace.Fail

`Debug.Fail(message)` is semantically `Debug.Assert(false, message)`; both are gated on `DEBUG`. `Trace.Fail` is the non-conditional sibling gated on `TRACE`, so it survives into Release. Code that must signal an unrecoverable invariant violation in production should `throw` an exception (for example `InvalidOperationException` or `UnreachableException` on .NET 7+) rather than rely on `Debug.Fail`.

# Catching the issue

## Code review

Treat `Debug.Fail` as a development-time marker only. In review, reject any `Debug.Fail` that is the sole handler for an invalid input, an unauthorized case, or an "unreachable" branch reachable from external data — replace it with a `throw`. On .NET 7+, `throw new UnreachableException()` expresses genuinely-impossible branches and survives into Release; for invalid runtime states use a domain or argument exception.

## Static analysis

- Roslyn analyzers / CodeQL: a query matching invocations of `System.Diagnostics.Debug.Fail` is exact and easy to write, since the symbol is rarely aliased. Flag every occurrence in non-test code for review, and specifically flag a `Debug.Fail` as the body/`default` of a branch that handles untrusted input.
- SonarQube: there is no dedicated `Debug.Fail` rule, so a custom rule (or grouping with the "review uses of this API" mechanism) is appropriate; pair it with the rules that push real validation toward exceptions.
- `BannedApiAnalyzers`: add `System.Diagnostics.Debug.Fail` to `BannedSymbols.txt` for production code paths so any use forces an explicit, justified suppression.

## Build configuration

No compiler warning fires for `Debug.Fail`, because it is a legitimate construct. The dependable safeguard is process: run Debug builds with assertions wired to a throwing trace listener in CI so a reached `Debug.Fail` becomes a test failure, and never depend on its behavior being present in the shipped Release binary.

# How to reproduce

Observe that the `default` branch aborts/reports in a Debug build but falls through silently in Release, printing `handled: 0` for an input the code claimed was impossible.

```csharp
using System;
using System.Diagnostics;

class Program
{
    static int Classify(int code)
    {
        switch (code)
        {
            case 1: return 10;
            case 2: return 20;
            default:
                Debug.Fail($"unexpected code {code}"); // fires only in Debug
                return 0; // Release falls straight through to here
        }
    }

    static void Main()
    {
        // 99 is "impossible" per the author, but nothing stops it in Release:
        Console.WriteLine($"handled: {Classify(99)}");
        Console.WriteLine("reached end");
    }
}
```

