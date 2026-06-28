---
title: "NotImplementedException thrown"
author: Maxim Menshikov
layout: defect
permalink: /csharp/exception/not_implemented
arch:
   - native
vulnerability:
   - Low
ddos:
   - Low
group_full: csharp.exception
group:
   - csharp
   - exception
---
Constructing NotImplementedException indicates unfinished code

# Impact

`NotImplementedException` is a placeholder thrown from a method body that was never finished. Tools like the IDE "Implement interface" or "Generate method stub" commands emit `throw new NotImplementedException();` automatically, and the expectation is that a developer replaces it before shipping. When that does not happen, the stub survives into production as a live failure: the first time control reaches that path, the operation aborts with an uncaught exception instead of doing useful work.

The practical consequences are correctness and completeness failures. A feature that appears wired up does nothing but throw; a callback, override, or interface member that the framework invokes blows up mid-operation; a rarely exercised branch (an error path, an edge-case format, an admin action) is the one left unimplemented, so the defect hides until exactly the wrong moment. Because the exception type carries no domain meaning, callers cannot handle it sensibly, and any partial work performed before the throw is left half-applied.

# Vulnerability potential

A `NotImplementedException` is rarely a vulnerability by itself, but an unfinished path that is reachable from input is a denial-of-service surface and, occasionally, more.

1. **Reachable crash / DoS.** If an attacker can steer execution into the unimplemented branch (an unhandled message type, an optional protocol feature, an unusual content type), every such request throws. If the surrounding code lacks a top-level handler, this can crash a worker, tear down a request pipeline, or take down a background processor that retries the same poison input forever.
2. **Fail-open security stubs.** A security control left as a stub is dangerous in the opposite way: a `Validate()`, `CheckPermission()`, or `VerifySignature()` method that still throws `NotImplementedException` may be wrapped in a `catch` that treats "no exception thrown by the check" as success, or the stub may have been temporarily replaced with a permissive return. An unfinished authorization path can therefore degrade into an auth bypass.
3. **Information disclosure.** An unhandled `NotImplementedException` that reaches a default error page can leak the method name, stack trace, and assembly internals when verbose errors are enabled.

For most occurrences the realistic risk is a triggerable crash, which is why both ratings are kept modest rather than high.

# Technical details

## What the type means

`System.NotImplementedException` lives in the framework specifically to mark "this member exists but its body is not written yet." It is distinct from `NotSupportedException`, which means "this operation is deliberately and permanently not available here." Confusing the two hides intent: `NotImplementedException` is a temporary marker that should never ship; `NotSupportedException` is a designed-in contract.

## Why it survives to production

The throw compiles cleanly and passes type checking — nothing about an unwritten method is a compile error, because `throw new NotImplementedException();` is a perfectly valid statement that also satisfies definite-assignment and return-path analysis. A method that must return `int` compiles fine if its only statement is this throw. The defect is therefore invisible to the compiler and only manifests dynamically, when the path executes. Code coverage gaps make this worse: the unimplemented branch is usually the least-tested one, so it sails through CI.

## Runtime behaviour

When hit, the exception propagates like any other unchecked exception, unwinding the stack until a matching handler is found or the thread terminates. There is no special framework treatment; the only signal is the type name in the stack trace.

# Catching the issue

## Static analysis

Roslyn analyzers ship a dedicated rule: **S3717** in SonarAnalyzer (`Track uses of "NotImplementedException"`) flags every construction so they cannot be forgotten. SonarQube/SonarCloud surface the same rule across the project. CodeQL can be expressed as a query for object-creation expressions of type `System.NotImplementedException`. A simple banned-API approach also works: add `M:System.NotImplementedException.#ctor` to a Roslyn banned-symbols list (analyzer **RS0030** via `BannedApiAnalyzers`) so any reference fails the build.

## Build gating

Treat the SonarAnalyzer warning as an error in release builds (`<WarningsAsErrors>` or ruleset severity `error`) so a stub cannot pass CI. Pair this with a grep/CI guard for the literal `NotImplementedException` in changed files.

## Code review and tests

Require that every generated stub is either implemented or has an explicit, justified decision before merge. Add tests that exercise the previously empty branch — a test that drives the method end-to-end converts the silent gap into a visible failing test. For interface members the framework will call, write at least one happy-path integration test per implementation.

# How to reproduce

The discount path compiles and looks complete, but any premium order crashes at runtime.

```csharp
using System;

class Order
{
    public decimal Total(string customerTier) => customerTier switch
    {
        "standard" => 100m,
        "premium"  => ApplyPremiumDiscount(100m), // stub was never finished
        _          => 100m,
    };

    // Generated stub, forgotten before shipping.
    private decimal ApplyPremiumDiscount(decimal amount) =>
        throw new NotImplementedException();
}

class Program
{
    static void Main()
    {
        var order = new Order();
        Console.WriteLine(order.Total("standard")); // 100 — fine
        Console.WriteLine(order.Total("premium"));   // throws NotImplementedException
    }
}
```

