---
title: "Garbage Collector"
author: Maxim Menshikov
layout: defect
permalink: /gc
---

Defects in how code cooperates with an automatic garbage collector — chiefly Go's. The collector reclaims unreachable memory transparently, but the program still controls how much garbage it produces and how hard the collector must work, and those decisions leak into latency, throughput, and tail behaviour.

The problems here are rarely outright bugs; they are patterns that are correct but expensive. Hot paths that allocate gratuitously, retained references that defeat reclamation, and tuning that fights the runtime all manifest as GC pressure: rising pause times, CPU spent in collection rather than work, and memory footprints that grow until the collector dominates the profile.
