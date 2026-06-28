---
title: "Threading"
author: Maxim Menshikov
layout: defect
permalink: /threading
---

Defects in concurrent execution — the bugs that appear when multiple threads, lightweight processes, or goroutines run against shared state. These are among the hardest defects to diagnose because they depend on timing: the same code passes a thousand runs and corrupts data on the next, and a debugger's presence can make the symptom disappear entirely.

The section spans the layers at which concurrency goes wrong: the synchronisation primitives and one-shot constructs a language provides, the discipline of locking shared data consistently and not omitting it, and the management of the threads or lightweight processes themselves. The unifying theme is that correctness now depends on order of execution, and any gap in that ordering is a latent race.
