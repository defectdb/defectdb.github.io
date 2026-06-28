---
title: "Debugging"
author: Maxim Menshikov
layout: defect
permalink: /csharp/debug
group:
   - csharp
---

Defects where a diagnostic assertion encodes a condition the author believed unreachable, and execution reaches it anyway. These calls are compiled only into `Debug` builds, so the contract they express vanishes in `Release` — the violated invariant then passes silently instead of failing loudly.

Whether through `Debug.Assert(false)` or `Debug.Fail`, hitting one of these marks a state the code was never meant to enter. Treat it as a logic error that has already occurred, not merely a place that pops an assertion dialog under the debugger.

