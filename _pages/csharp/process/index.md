---
title: "Process"
author: Maxim Menshikov
layout: defect
permalink: /csharp/process
group:
   - csharp
---

Defects in calls that control the operating-system process or spawn new ones, where a single statement reaches past the current method to affect the whole program or the shell. These APIs are blunt: they end the process or invoke external commands, and their consequences are not contained by the usual exception and scope boundaries.

`Environment.Exit` and `Environment.FailFast` terminate the process from deep in library code, bypassing `finally` blocks and cooperative shutdown, while `Process.Start` given a single command string defers argument parsing to the platform — an injection and quoting hazard that the explicit `ArgumentList` overload avoids.

