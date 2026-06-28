---
title: "Environment.FailFast called"
author: Maxim Menshikov
layout: defect
permalink: /csharp/process/failfast
arch:
   - native
vulnerability:
   - Low
ddos:
   - Medium
group_full: csharp.process
group:
   - csharp
   - process
---
Environment.FailFast aborts the process without running finalizers

# Impact

`Environment.FailFast` terminates the current process immediately and unconditionally. Unlike a thrown exception, it cannot be caught: no `catch` clause runs, no `finally` block runs, and no finalizers execute. The runtime takes the fastest path out of the process.

Concrete consequences:

- Any work in `finally` blocks higher on the stack is skipped. Locks released in `finally`, temp files deleted in `finally`, transactions rolled back in `finally` — none of that happens.
- Finalizers (`~T()` / `Object.Finalize`) and `SafeHandle` releases do not run. The OS reclaims handles on process death, but any flush-on-finalize logic (for example buffered writers that flush in a finalizer) loses its buffered data.
- Buffered standard output / standard error may be lost because the normal managed shutdown that flushes streams does not run.
- On .NET, `FailFast` reports the failure to Watson / Windows Error Reporting, writes an entry to the Application event log, and (depending on configuration) produces a crash dump. This is comparatively expensive and pollutes crash telemetry with a self-inflicted "crash" that is indistinguishable, at a glance, from a real fault.
- If a `FailFast` message and/or exception are supplied, they are included in the error report, which can leak diagnostic state into logs and dumps.

The practical effect is a hard, non-recoverable abort of the whole application from a single library call.

# Vulnerability potential

`FailFast` is not a memory-safety or injection primitive, so its direct security exposure is limited. The realistic concerns are availability and, secondarily, information disclosure:

1. Availability / denial of service. If the call site can be driven by attacker-controllable input — for example a `FailFast` placed in an "impossible" branch of a request handler that an attacker can actually reach — a single crafted request kills the entire process and every in-flight request with it. In a single-process service this is a one-shot DoS; with auto-restart it becomes a crash loop the attacker can keep triggering.
2. Information disclosure. The failure message and any attached exception are written to the event log, Watson reports, and crash dumps. If sensitive data (paths, tokens, internal state) is passed as the message, it ends up in diagnostic artifacts that may be readable by lower-privileged accounts or shipped to external telemetry.
3. Loss of integrity guarantees. Because `finally` blocks and finalizers are skipped, a `FailFast` mid-operation can leave on-disk or external state half-written (no rollback, no flush), which can be a precondition for later corruption-driven bugs.

Note that `FailFast` is also the *correct* tool for a few security-sensitive situations (detected heap corruption, a broken invariant where continuing is more dangerous than crashing). The defect is using it as ordinary error handling, not its existence.

# Technical details

## What FailFast actually does

`Environment.FailFast(string)` and its overloads (`FailFast(string, Exception)`, `FailFast(string, Exception, string)`) call into the runtime's fail-fast path. On CoreCLR / .NET this routes through `EEPolicy::HandleFatalError`, which is the same machinery the runtime uses for unrecoverable internal errors. The process is brought down via a fatal-error exit rather than a normal managed shutdown.

Key semantic differences from other ways of ending a program:

| Mechanism | `finally` runs | Finalizers run | Catchable | Crash dump / Watson |
|---|---|---|---|---|
| Throw uncaught exception | yes (during unwind) | yes (normal shutdown) | yes | yes (unhandled) |
| `Environment.Exit(code)` | no (no unwind) | yes (ProcessExit, finalizer pass) | n/a | no |
| `Environment.FailFast(...)` | no | no | no | yes |

`Environment.Exit` still performs a managed shutdown: it raises `AppDomain.ProcessExit`, runs the finalizer queue, and flushes. `FailFast` deliberately skips all of that to avoid running any more managed code, on the theory that the process state is already untrustworthy.

## Why finally/finalizers are skipped

A normal exception drives stack unwinding, and unwinding is what executes `finally` blocks. `FailFast` does not unwind the stack and does not return control to managed code; it transfers directly to the runtime's fatal-error handler. There is no unwind, therefore no `finally`, and the finalizer thread is never given the chance to drain.

## The Watson / event-log side effect

On Windows .NET, the fatal-error path reports to Windows Error Reporting (Watson). This generates an Application event-log entry (typically a .NET Runtime error) and, when WER or `createDump` settings allow, a crash dump file. The supplied message and exception are embedded so that post-mortem tooling can show why the process self-terminated. This reporting cost is part of why `FailFast` is more "violent" and more visible than `Environment.Exit`.

# Catching the issue

## Code review

Treat any `Environment.FailFast` in non-test library or service code as requiring justification. Legitimate uses are narrow: detected state corruption where continuing is unsafe, or a violated invariant that genuinely cannot be recovered. Ordinary "this shouldn't happen" branches should throw a normal exception instead, so callers and `finally`/finalizer logic still run.

## Static analysis

- Roslyn / CodeQL: a custom analyzer or CodeQL query matching invocations of `System.Environment.FailFast` is straightforward and reliable, because the symbol is fully qualified and rarely aliased. Flag every call and require a suppression with rationale.
- SonarQube: there is no single dedicated FailFast rule equivalent to the `Environment.Exit` rule (S1147), so a custom rule (or the generic "review uses of this API" mechanism) is the practical option. Group it with the same policy you apply to `Environment.Exit` (S1147), `Process.Kill`, and similar process-ending calls.
- Banned-API list: add `System.Environment.FailFast` to a `BannedApiAnalyzers` (`BannedSymbols.txt`) entry so that any use produces a build warning/error and must be explicitly allow-listed.

## Operational detection

After the fact, a self-inflicted `FailFast` shows up as a .NET Runtime error in the Application event log and as a WER report. Alerting on these helps catch a `FailFast` that escaped review and is now firing in production.

# How to reproduce

Observe that neither the `finally` block nor the finalizer prints, and the process exits with a fatal error (plus an event-log/Watson entry on Windows) even though `FailFast` is invoked inside a `try`/`catch`.

```csharp
using System;

class Resource
{
    ~Resource() => Console.WriteLine("finalizer ran"); // never prints
}

class Program
{
    static void Main()
    {
        var r = new Resource();
        try
        {
            try
            {
                Console.WriteLine("before FailFast");
                Environment.FailFast("invariant violated");
            }
            finally
            {
                Console.WriteLine("finally ran"); // never prints
            }
        }
        catch (Exception)
        {
            Console.WriteLine("caught"); // never prints — FailFast is uncatchable
        }

        GC.KeepAlive(r);
        Console.WriteLine("after"); // never reached
    }
}
```

