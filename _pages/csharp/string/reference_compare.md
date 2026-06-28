---
title: "string == may compare references"
author: Maxim Menshikov
layout: defect
permalink: /csharp/string/reference_compare
arch:
   - native
vulnerability:
   - Low
ddos:
   - None
group_full: csharp.string
group:
   - csharp
   - string
---
Use string.Equals with StringComparison.Ordinal/OrdinalIgnoreCase for explicit, locale-independent comparison

# Impact

Two strings that are character-for-character equal can compare as **unequal**, or two values that differ only by case/culture can compare as **equal**, depending on how the comparison is written. The most common failures are:

- A value comparison is accidentally turned into a **reference** comparison. When at least one operand is statically typed as `object` (an explicit `(object)` cast, a generic `T` constrained to a class, or `object.ReferenceEquals`), the `==` operator binds to `object.operator==`, which compares references, not contents. Two equal strings built at runtime live at different addresses, so the test returns `false` even though the text matches.
- A comparison is left **culture-sensitive** by default. `String.Equals(a, b)` and `string.CompareOrdinal`-free overloads of `Compare`/`StartsWith`/`IndexOf` use the current culture unless told otherwise, so results change with the machine locale. Under the Turkish (`tr-TR`) culture, `"FILE".ToLower()` is `"fıle"` (dotless i) and `"I".Equals("i", currentCulture, ignoreCase)` behaves differently than under invariant culture.

Concrete consequences: equality checks that silently break when the same logical string arrives as a fresh instance (parsed input, deserialized data, `string.Copy`, `new string(...)`), branch logic that flips when the process runs under a different OS locale, and dictionary/set lookups that miss because the comparer disagrees with the equality test the developer expected.

# Vulnerability potential

The security relevance is real but situational, so the rating is Low.

1. **Culture-sensitive comparison of security tokens.** Validating an API key, password hash string, role name, header value, or file-extension allow-list with a culture-aware comparison can make two different byte sequences compare as equal (the classic Turkish-I problem: `"file".Equals(input, StringComparison.CurrentCultureIgnoreCase)` matching unexpected casings). For any value with a security meaning, comparison must be **ordinal**. Note that culture-aware comparison can match values you did not intend; it does not generally let an attacker bypass an exact ordinal check.

2. **Reference comparison rejecting a valid value.** The mirror image: `(object)token == (object)expected` returns `false` for two equal strings that are distinct instances, which can turn a valid credential or signature into a spurious failure (availability/usability bug) rather than a bypass.

Outside token handling this defect is mostly a correctness bug, not an exploitable hole.

# Technical details

## What `==` actually binds to

`string` overloads `operator ==` to call `String.Equals(a, b)`, which performs an **ordinal** value comparison. So for two operands both statically typed `string`, `a == b` is the correct, locale-independent thing. The trap is operator overload resolution: overloads are chosen by **static** type at compile time, not runtime type. The moment one operand's static type is `object` (cast, generic without a `string` constraint, assignment to an `object` field), the compiler picks `object.operator==`, i.e. `ReferenceEquals`. The text is identical but the references differ, so the result is `false`.

## Interning is not a guarantee

String literals and compile-time constants are interned, so `"abc" == (object)"abc"` may happen to be `true` because both refer to the same interned instance. Strings produced at runtime are **not** interned unless you call `string.Intern`, so any reference comparison that "works" in a unit test with literals can fail in production with computed values. Never rely on interning for correctness.

## Culture vs ordinal

The no-`StringComparison` overloads of `Equals`, `Compare`, `StartsWith`, `EndsWith`, and `IndexOf` use `CurrentCulture` (the `IndexOf(char)` overloads are ordinal — another inconsistency). `StringComparison.Ordinal` compares UTF-16 code units directly; `OrdinalIgnoreCase` applies a simple invariant case fold. These are fast, deterministic, and independent of `CultureInfo.CurrentCulture`, which is exactly what equality and security checks want. Reserve culture-aware comparison for user-facing sorting and display.

# Catching the issue

## Roslyn / .NET analyzers

- **CA1309 (Use ordinal StringComparison)** flags culture-sensitive comparisons that should be ordinal.
- **CA1307 / CA1310** flag `Equals`, `Compare`, `StartsWith`, `IndexOf` calls that omit an explicit `StringComparison`, forcing a deliberate choice.
- **CA2249** suggests `string.Contains` over `IndexOf >= 0` patterns, removing one more place to forget the comparison kind.
- Enable these as warnings-as-errors in `.editorconfig` so missing `StringComparison` cannot merge silently.

## SonarQube / CodeQL

SonarQube rule **S4423**-family and **S1698** ("Objects should not be compared with `==`" / reference vs value equality) catch reference comparisons of strings, including the `(object)` cast pattern. CodeQL has queries for culture-dependent string comparison in security contexts.

## Code review and design

- Treat any `(object)`/`ReferenceEquals` on strings, or a generic `==` over an unconstrained `T`, as a smell — prefer `EqualityComparer<T>.Default.Equals`.
- Build dictionaries and sets of strings with an explicit comparer, e.g. `new Dictionary<string,V>(StringComparer.Ordinal)`, so the lookup matches the equality you intend.
- Make ordinal comparison the house style for all non-display strings; reserve `CurrentCulture` for sorting human-readable text.

# How to reproduce

Observe that two equal strings compare unequal once the comparison is forced to reference equality, and that a culture-aware ignore-case compare can disagree with ordinal.

```csharp
using System;
using System.Globalization;
using System.Threading;

class Program
{
    static void Main()
    {
        // Build an equal string at runtime so it is NOT interned.
        string a = "secret";
        string b = new string("secret".ToCharArray());

        Console.WriteLine(a == b);                 // True  (string == is ordinal value equality)
        Console.WriteLine((object)a == (object)b); // False (operator resolves to ReferenceEquals)
        Console.WriteLine(ReferenceEquals(a, b));  // False (distinct instances)

        // Culture-sensitive ignore-case can match values an ordinal check would reject.
        Thread.CurrentThread.CurrentCulture = new CultureInfo("tr-TR");
        Console.WriteLine("FILE".Equals("fıle", StringComparison.CurrentCultureIgnoreCase)); // True under tr-TR
        Console.WriteLine("FILE".Equals("fıle", StringComparison.OrdinalIgnoreCase));        // False
    }
}
```

