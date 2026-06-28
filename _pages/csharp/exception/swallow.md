---
title: "catch (Exception) swallows the error"
author: Maxim Menshikov
layout: defect
permalink: /csharp/exception/swallow
arch:
   - native
vulnerability:
   - Medium
ddos:
   - Low
group_full: csharp.exception
group:
   - csharp
   - exception
---
An empty catch on the base Exception type silently drops every failure; at minimum log the exception, ideally narrow the type or rethrow

# Impact

`catch (Exception) { }` — an empty catch on the base `Exception` type — silently discards every failure that occurs inside the guarded block. The program continues as if nothing happened, but the work the block was supposed to do did not complete. There is no log entry, no rethrow, no signal of any kind; the only evidence is downstream corruption when later code relies on state the failed block never produced.

The concrete consequences compound:

- **Silent data corruption.** A write that half-completed, a parse that failed, or a transaction that never committed leaves the system in an inconsistent state that is then treated as valid.
- **Lost diagnosability.** Bugs become unreproducible because the originating exception — type, message, stack trace — was thrown away. Incidents take far longer to diagnose because the first failure is invisible.
- **Masked control failures.** Because the catch is on `Exception`, it also eats failures from security and integrity checks (described in the next section), turning a hard failure into a silent success.
- **Swallowed framework-critical signals.** Catching `Exception` also catches `OperationCanceledException` (breaking cooperative cancellation and graceful shutdown) and severe conditions like `OutOfMemoryException`, `StackOverflowException` semantics, and thread aborts — conditions the code cannot actually handle but now pretends it did.

# Vulnerability potential

Swallowing exceptions is genuinely security-relevant because many security controls signal denial by *throwing*. An empty `catch (Exception)` converts those throws into silent success — the textbook fail-open pattern.

1. **Authentication / authorization bypass.** A permission or authentication check that throws on failure (an invalid token, an expired session, a missing claim) is neutralised if the throw is swallowed and execution falls through to the protected operation. The system fails open instead of fail-closed.
2. **Broken signature / certificate / integrity validation.** Code that verifies a digital signature, validates a TLS certificate, or checks an HMAC/hash typically throws when verification fails. Swallowing that exception means tampered or forged data is accepted as authentic. This is a classic root cause of CWE-295 (improper certificate validation) and CWE-347 (improper verification of cryptographic signature).
3. **Masking active attacks.** Injection probes, deserialization failures, path-traversal attempts, and malformed-input attacks often surface first as exceptions. An empty catch erases the evidence, so intrusion detection, alerting, and forensic logging see nothing while the attacker iterates.
4. **State corruption as a primitive.** Silently continuing after a failed write or partial update can leave invariants violated; subsequent code operating on that corrupted state can be steered into unexpected behaviour.

The unifying weakness is **CWE-390: detection of error condition without action** (and CWE-391, unchecked error condition). Because the realistic worst case is a fail-open security control rather than direct memory corruption, the vulnerability rating is Medium. The DoS angle is smaller — swallowing tends to *hide* crashes rather than cause them — but masking a failure can keep a degraded or looping component alive in a broken state, hence ddos Low.

# Technical details

## Two defects in one

The pattern combines two distinct mistakes. First, **catching too broadly**: `catch (Exception)` matches the root of the exception hierarchy, so it captures not only the specific failure the author had in mind but also unrelated, severe, and framework-meaningful exceptions the code has no ability to handle. Second, **handling with nothing**: the empty body means the caught exception is neither logged, translated, nor rethrown — the information is destroyed. Either mistake alone is bad; together they guarantee invisible failure.

## What `catch (Exception)` also catches

Because every exception derives from `System.Exception`, the clause swallows:

- `OperationCanceledException` / `TaskCanceledException` — cooperative cancellation tokens stop working; shutdown and timeout logic silently break.
- `OutOfMemoryException`, `StackOverflowException` (where catchable), and other corrupted-state conditions the process cannot meaningfully recover from. Historically the runtime treated some of these as Corrupted State Exceptions that `catch (Exception)` would not catch unless `HandleProcessCorruptedStateExceptions`/`legacyCorruptedStateExceptionsPolicy` was enabled; the safe assumption is that a broad catch reaches things you must not suppress.

## The fail-closed principle

Security and integrity code should fail closed: if a check cannot complete, the operation must be refused, not allowed. An exception *is* the refusal signal. Swallowing it inverts the default to fail-open. The corrected forms are: catch the narrowest type you can actually handle; if you catch, log with the full exception (preserving the stack trace, e.g. `_logger.LogError(ex, ...)`); and rethrow with a bare `throw;` (not `throw ex;`, which resets the stack trace) when you cannot truly recover. Never swallow without at least logging.

# Catching the issue

## Roslyn / .NET analyzers

`CA1031: Do not catch general exception types` flags `catch (Exception)` (and `catch` without a type). Enable it as a warning-or-error in the `.editorconfig`/ruleset. The empty body specifically is caught by `S2486` and `S108` below; pairing CA1031 with those covers both "too broad" and "does nothing."

## SonarQube / SonarAnalyzer.CSharp

- **S2486** — *Generic exceptions should not be ignored* (an exception is caught but the handler does nothing).
- **S108** — *Nested blocks of code should not be left empty* (catches the empty `{ }` body generally).
- **S2737** — *"catch" clauses should do more than rethrow* (the opposite anti-pattern, useful in the same review pass).
- **S3445 / S2221** — broad-catch and rethrow hygiene around `catch (Exception)`.

## CodeQL

The C# query pack ships `cs/empty-catch-block` (empty catch clause) and `cs/catch-of-all-exceptions` (catching `System.Exception`/`SystemException`). Run both in CI to fail the build on new occurrences.

## Code-review rules and banned patterns

- Reject any `catch (Exception)` or untyped `catch` whose body does not log, translate, or rethrow.
- Require a bare `throw;` (never `throw ex;`) when re-raising.
- Require that security/integrity verification paths have no surrounding broad catch at all, or that the catch re-throws to a fail-closed default.
- A lint/grep guard for `catch (Exception` and `catch {` over changed files is a cheap backstop. Forbid swallowing of `OperationCanceledException` — either let it propagate or filter it explicitly with `catch (Exception ex) when (ex is not OperationCanceledException)`.

# How to reproduce

The forged token is rejected by the verifier, but the empty catch swallows the failure and the request is treated as authenticated.

```csharp
using System;

class Program
{
    // Throws when the signature does not verify.
    static void VerifySignature(string token)
    {
        if (token != "valid-signature")
            throw new InvalidOperationException("Signature verification failed");
    }

    static bool IsAuthenticated(string token)
    {
        try
        {
            VerifySignature(token);
            return true;
        }
        catch (Exception)
        {
            // Empty catch: the verification failure vanishes...
        }
        return true; // ...and the method falls through to "authenticated".
    }

    static void Main()
    {
        // Forged token is accepted — fail-open. Prints: True
        Console.WriteLine(IsAuthenticated("forged"));
    }
}
```

