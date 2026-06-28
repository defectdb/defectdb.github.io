---
title: "Debug.Assert(false) reached"
author: Maxim Menshikov
layout: defect
permalink: /csharp/debug/assert
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
Debug.Assert with a always-false condition aborts at runtime

# Impact

`Debug.Assert(condition)` with a condition that evaluates to `false` signals a broken invariant at the point of the call. What happens next depends entirely on the build configuration, and that split is the heart of the defect:

- In a Debug build (the `DEBUG` compilation symbol is defined), a failed assertion is reported through `System.Diagnostics.Trace`. With the default listener on Windows desktop, it pops a modal Abort/Retry/Ignore dialog; under other listeners or non-interactive hosts it writes the failure (including a stack trace) to the trace output, and a `DefaultTraceListener` configured to fail can call `Environment.FailFast`-style termination. Either way the program stops or stalls at that point.
- In a Release build, the `DEBUG` symbol is normally not defined, so the entire `Debug.Assert` call — argument evaluation included — is removed by the compiler. The check simply does not exist in shipped code.

The damaging consequence is the asymmetry. The assertion gives developers confidence that a condition is being enforced, but in production that enforcement is gone. A genuinely invalid state that would have been caught loudly in Debug slips through silently in Release, so execution continues on bad data instead of failing fast. The "always-false" case here just makes the failure unconditional and therefore obvious in Debug while still vanishing in Release.

# Vulnerability potential

`Debug.Assert` is not itself a memory-safety, injection, or escalation primitive, so its direct security relevance is low. The security concern is indirect and stems from the Debug/Release asymmetry:

1. Disappearing validation. If a `Debug.Assert` is mistakenly used as the *only* guard for a security-relevant precondition (a bounds check, a non-null/authorization invariant, "input was already sanitized"), that guard is compiled out in Release. The attacker-facing build then runs with no check at all, which can turn a would-be assertion failure into a real out-of-bounds access, null dereference, or logic bypass downstream.
2. Debug-build information disclosure. The assertion failure output includes a stack trace and the textual condition/message. A Debug build accidentally shipped, or one reachable on a test endpoint, can leak internal structure to an attacker who can trigger the failure.

The `ddos` rating is `None` because in Release the call does nothing, and in Debug the dialog/abort is a development-time behavior that should never be on a production attack surface. The residual risk is entirely "assert was the only check," which is a design mistake rather than a property of the API.

# Technical details

## The `[Conditional("DEBUG")]` mechanism

All `Debug.Assert` overloads are decorated with `[Conditional("DEBUG")]`. `ConditionalAttribute` is a compile-time directive: if the named symbol (`DEBUG`) is *not* defined at the call site's compilation, the C# compiler omits the entire call, including evaluation of every argument. This is different from `#if DEBUG`, but the visible effect is the same — the call vanishes from the IL.

Two consequences follow:

- Because arguments are not evaluated when the call is elided, any side effect placed inside the assert expression (for example `Debug.Assert(Initialize())`) also disappears in Release. Asserts must be side-effect free for exactly this reason.
- The default Visual Studio Release configuration defines `TRACE` but not `DEBUG`, so the elision happens automatically without any explicit `#if`.

## What "fails" means in Debug

When `DEBUG` is defined and the condition is `false`, `Debug.Assert` calls into `TraceInternal`/`Trace.Listeners`. The `DefaultTraceListener` writes the message plus a captured stack trace and, in an interactive Windows session with `AssertUiEnabled`, shows the Abort / Retry / Ignore message box. Abort terminates, Retry breaks into the debugger, Ignore continues. In a non-interactive process (service, container, CI), there is no UI, so behavior depends on the configured listeners — commonly the failure is written to the trace output and execution may continue, which is itself a trap because a "failed" assertion can pass unnoticed in headless Debug runs.

## Debug.Assert vs Trace.Assert

`Trace.Assert` is the non-conditional sibling: it is gated on `TRACE`, not `DEBUG`, so it survives into Release builds. Code that genuinely needs a runtime invariant check in production should throw an exception (or use `Trace.Assert`), never rely on `Debug.Assert`.

# Catching the issue

## Code review

The rule is simple: `Debug.Assert` is a developer-time sanity check, never a substitute for real input or precondition validation. In review, flag any `Debug.Assert` that guards a security- or correctness-critical condition reachable from external input, and require a real `throw` (for example `ArgumentNullException`, `ArgumentOutOfRangeException`, or a domain exception) instead. Also flag any assert whose argument has a side effect.

## Static analysis

- SonarQube: rule S3923 and related "all branches are identical" / "useless assertion" checks can catch trivially-constant assertions; more usefully, S112/S3868-style rules and review gates help spot validation that should be an exception. A custom rule banning `Debug.Assert` outside test projects is often added for production libraries.
- Roslyn analyzers / CodeQL: a query matching `System.Diagnostics.Debug.Assert` invocations whose condition is a literal `false` (or a constant-foldable false) flags the always-fail case directly. CodeQL can also be used to find asserts whose argument expression has side effects.
- `BannedApiAnalyzers`: adding `System.Diagnostics.Debug.Assert` to `BannedSymbols.txt` in code paths where it must not appear forces explicit justification.

## Compiler and build configuration

There is no compiler warning for a `Debug.Assert(false)` because it is legal and intentional in many test/dead-branch scenarios. The most reliable safety net is process: run a Debug build with assertions enabled in CI (so failing asserts surface as test failures via a trace listener that throws), and never rely on assert behavior being present in the shipped Release binary.

# How to reproduce

Observe that the assertion fires (dialog/trace/abort) when built with `DEBUG` defined, but the program prints `reached end` and exits cleanly when built in Release — the check has silently disappeared.

```csharp
using System;
using System.Diagnostics;

class Program
{
    static int Divide(int a, int b)
    {
        // Intended as the guard against b == 0, but compiled out in Release:
        Debug.Assert(b != 0, "b must not be zero");
        return a / b; // throws DivideByZeroException in Release instead of asserting
    }

    static void Main()
    {
        Debug.Assert(false, "this assertion is always false"); // fires only in Debug

        try
        {
            Console.WriteLine(Divide(10, 0));
        }
        catch (DivideByZeroException)
        {
            Console.WriteLine("release path: no assert, just a runtime exception");
        }

        Console.WriteLine("reached end");
    }
}
```

