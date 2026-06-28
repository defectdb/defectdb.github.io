---
title: "Equals(null) throws on null receiver"
author: Maxim Menshikov
layout: defect
permalink: /csharp/null/equals_null
arch:
   - native
vulnerability:
   - Low
ddos:
   - Low
group_full: csharp.null
group:
   - csharp
   - null
---
x.Equals(null) crashes when x is null; use `x is null` (or `x == null`) for null checks

# Impact

Writing `x.Equals(null)` to test whether `x` is null is self-defeating: if `x` is in fact null, the call dereferences a null receiver and throws `NullReferenceException` **before** `Equals` ever runs. The check that was meant to handle the null case is precisely the line that crashes on it. When `x` is non-null the call works but is redundant — `Equals(null)` simply returns `false` for any well-behaved type.

Concrete consequences:

- An unhandled `NullReferenceException` on a reachable path, aborting the current request/operation and unwinding the stack. In a server this fails one request; in a background loop or startup path it can bring down the worker or process.
- The failure surfaces at the guard clause itself, so the stack trace points at the defensive code rather than the real source of the null, making diagnosis confusing.
- The same mistake appears as `if (!x.Equals(null))` and in generic code (`item.Equals(null)` over `T`), where the crash depends on runtime data and may slip past testing.

The intent — "is this reference null?" — should be expressed with `x is null`, `x == null`, `ReferenceEquals(x, null)`, or the static `object.Equals(x, null)`, none of which dereference `x`.

# Vulnerability potential

The security impact is modest (Low). The defect is a crash, not a memory-safety or logic bypass, but a reliably reachable `NullReferenceException` has denial-of-service relevance:

1. **Availability / DoS.** If `x` can be null as a result of attacker-influenced input (a missing field, an unmatched lookup, a deserialized object with a null member), an attacker can deterministically trigger the exception on demand. Repeated requests crash operations or, on an unguarded background/host path, the process — a low-effort DoS. This is why ddos is rated Low rather than None.
2. **Error-path information leak.** An uncaught NRE can surface a stack trace to the client if exception details are not suppressed, leaking internal type and method names. This is configuration-dependent and minor.

There is no privilege escalation or data-integrity angle here; the realistic risk is a crash on a reachable null.

# Technical details

## Why the receiver throws

`x.Equals(null)` is an **instance** method call. The CLR must dispatch on the object `x` refers to, which for a reference type means dereferencing it (a `callvirt` that loads the method table). If `x` is null there is nothing to dispatch on, so the runtime raises `NullReferenceException` at the call site — the `null` argument is irrelevant because the crash happens before any argument is examined. Contrast this with `null` as the *argument* of a static method (`object.Equals(x, null)`), which never touches `x` unsafely.

## Why `is null` is the preferred check

- `x is null` lowers to a direct reference comparison against null. It is a language construct, not an operator call, and **cannot be overloaded** — it always means "is this reference null," regardless of the type.
- `x == null` usually does the same, but `==` *can* be overloaded by the type. A custom `operator ==` could do extra work, behave unexpectedly for null, or (rarely) itself dereference, so `==` is not guaranteed to be a pure null check the way `is null` is.
- `ReferenceEquals(x, null)` and `object.Equals(x, null)` are also null-safe: both are static, neither dereferences `x`, and `ReferenceEquals` bypasses any overloaded operator entirely.
- For value types the question rarely arises (a non-nullable struct is never null), and on `Nullable<T>` use `x.HasValue` / `x is null`.

The guidance: use `x is null` / `x is not null` for null checks; reserve `Equals` for *value* comparison between two known-non-null operands, or call it statically as `Equals(a, b)`.

# Catching the issue

## Nullable reference types

Enabling `<Nullable>enable</Nullable>` is the strongest defense. If `x` is typed `T?`, the compiler issues **CS8602 (dereference of a possibly null reference)** on `x.Equals(...)`, pointing straight at the unsafe receiver and forcing either a real null check or a non-null annotation. This catches the bug at compile time before it can run.

## Roslyn / IDE analyzers

- **CA1508** and the flow analysis behind it can flag the dead/contradictory condition when `x` is known nullable.
- **IDE0150 (Prefer `null` check over type check)** and the `is null` pattern suggestions steer the code toward `x is null`. Many teams enforce "use pattern matching for null checks" via `.editorconfig`.
- The compiler/IDE also surface a hint when an instance call is made on a possibly-null value under nullable context.

## SonarQube

Rule **S2259 ("Null pointers should not be dereferenced")** detects paths where a reference that may be null is dereferenced, including `x.Equals(...)` guarded incorrectly. SonarQube also flags `Equals` misuse patterns.

## Code review

Treat `x.Equals(null)` (and `!x.Equals(null)`) as an automatic rewrite to `x is null` / `x is not null`. Any "null check" expressed as an instance method call on the value being checked is a red flag.

# How to reproduce

Observe that the `Equals(null)` "null check" throws `NullReferenceException`, while `is null` correctly reports the null.

```csharp
using System;

class Program
{
    static void Main()
    {
        string x = null;

        // Intended as a null check, but crashes on the null receiver:
        try
        {
            if (x.Equals(null))            // throws NullReferenceException
                Console.WriteLine("x is null");
        }
        catch (NullReferenceException)
        {
            Console.WriteLine("NRE: the guard itself crashed on null x");
        }

        // Correct, null-safe checks:
        Console.WriteLine(x is null);            // True
        Console.WriteLine(x == null);            // True
        Console.WriteLine(ReferenceEquals(x, null)); // True
        Console.WriteLine(Equals(x, null));      // True (static object.Equals)
    }
}
```

