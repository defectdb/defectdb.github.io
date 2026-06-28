---
title: "C#"
author: Maxim Menshikov
layout: defect
permalink: /csharp
---

Defects rooted in C# and the .NET runtime — the places where idiomatic-looking code collides with how the CLR actually schedules work, manages object lifetimes, and surfaces failure. Many of these bugs compile cleanly and pass a casual test, then misbehave under concurrency, on a background thread, or when an unmanaged resource or interop boundary is involved.

The groups here trace the runtime's main hazard areas: the `async`/`await` and `Task` machinery and the deadlocks and unobserved exceptions it invites; `IDisposable` lifetimes and `Marshal`-based interop with native memory; monitor `lock` patterns that escalate to process-wide contention; exception and null-handling conventions that swallow or misreport faults; and process-control and string operations whose defaults differ from what the call site assumes.

