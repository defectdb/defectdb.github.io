---
title: "NotSupportedException thrown"
author: Maxim Menshikov
layout: defect
permalink: /csharp/exception/not_supported
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
Constructing NotSupportedException indicates an unsupported code path

# Impact

`NotSupportedException` signals that a member exists by contract but the concrete type or current configuration cannot perform it. The classic case is a read-only or fixed-size collection whose mutating members (`Add`, `Remove`, `Clear`, the indexer setter) throw because the interface forces them to exist even though the implementation refuses them. It also appears for unsupported stream operations (`Write` on a read-only stream, `Seek` on a non-seekable one), unsupported type conversions, and unsupported configurations or runtime modes.

Unlike a code smell, the impact is a hard runtime abort whenever the path is reached: the operation throws instead of completing. When the throwing member is reachable from external input — a request that selects an unsupported format, an upload to a read-only sink, an option that is not implemented on the current platform — the request fails. If the throw is unexpected by the caller (the caller assumed the collection was mutable, or the stream was writable), it surfaces as an unhandled exception, partially applied state, or an aborted batch where earlier items succeeded and the remainder never ran.

# Vulnerability potential

`NotSupportedException` is usually a designed-in contract boundary, so its direct security weight is low. The realistic concern is availability, with a narrow misuse angle.

1. **Reachable crash / DoS.** If input chooses an unsupported path — an algorithm name, encoding, serializer mode, or feature flag the code does not implement — every such request throws. Without a top-level handler this can fault a worker or, worse, feed a retry loop that hammers the same unsupported request indefinitely.
2. **Unexpected mutation faults.** Code that receives an `IList<T>` or `Stream` and assumes it is mutable/writable will throw when handed a read-only instance. If that throw lands inside a half-completed transaction or partially written output, it can leave inconsistent persisted state.
3. **Error-message leakage.** As with any unhandled exception, a `NotSupportedException` reaching a verbose error page can disclose method names and stack frames.

There is no memory-safety or injection dimension here; the type is a refusal, not a parsing or trust-boundary primitive. Both ratings are kept low: a triggerable abort is plausible, a true vulnerability is not the common case.

# Technical details

## Intent: contract refusal, not unfinished code

`System.NotSupportedException` means the operation is deliberately unavailable for this type or state, and that is permanent. It is the opposite of `NotImplementedException`, which marks a body that is simply not written yet and should never ship. The .NET BCL itself throws `NotSupportedException` from `Array`-backed and `ReadOnlyCollection<T>` mutators, from `Stream` members the concrete stream cannot perform, and from `TypeConverter`/`Convert` when a conversion is undefined. Using it correctly is fine; the defect is when a reachable, input-driven path lands on one of these throws unexpectedly.

## Why interfaces force these throws

Interfaces such as `ICollection<T>` and `IList<T>` declare mutating members that every implementer must provide, even read-only ones. The fixed-size or immutable implementation satisfies the type system by implementing the member as `throw new NotSupportedException()` and exposes `IsReadOnly`/`CanWrite` so callers can check first. The hazard is callers that ignore the capability flag and call the member directly.

## Runtime behaviour

The throw is an ordinary unchecked exception that unwinds the stack to the nearest handler. The capability properties (`IsReadOnly`, `CanWrite`, `CanSeek`) exist precisely so well-written code can branch before reaching the throw rather than catching it.

# Catching the issue

## Static analysis

The same SonarAnalyzer rule that tracks `NotImplementedException`, **S3717** (`Track uses of "NotImplementedException" and "NotSupportedException"`), flags constructions of `NotSupportedException` so each one is reviewed rather than left silent. SonarQube/SonarCloud carry the rule across the project. CodeQL can match object-creation expressions of type `System.NotSupportedException`. Note the goal is not to forbid the type — it is legitimate — but to confirm every throw is intentional and that callers guard against it.

## Capability checks instead of catch

The preventable cases are the ones where a caller invokes a mutator/writer without checking. Code review should require a guard on `IsReadOnly`, `CanWrite`, or `CanSeek` before the corresponding operation, rather than wrapping the call in a `try`/`catch (NotSupportedException)`. Roslyn analyzer **CA2208** (instantiate argument exceptions correctly) and general nullability/capability review catch some of these; a custom analyzer or CodeQL query can flag mutating calls on values whose declared type is known to include read-only implementations.

## Tests

Add tests that pass a read-only collection or non-writable/non-seekable stream into the consuming code to prove it degrades gracefully (or branches) instead of throwing. For input-selected features, test the "unsupported option" request and assert a controlled, handled response rather than an unhandled fault.

# How to reproduce

The helper assumes a mutable list; passing a read-only one aborts with `NotSupportedException`.

```csharp
using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;

class Program
{
    // Caller assumes the list can be mutated.
    static void AppendDefault(IList<int> items) => items.Add(0);

    static void Main()
    {
        IList<int> mutable = new List<int> { 1, 2 };
        AppendDefault(mutable); // fine

        IList<int> readOnly = new ReadOnlyCollection<int>(new[] { 1, 2 });
        AppendDefault(readOnly); // throws NotSupportedException: Collection is read-only
    }
}
```

