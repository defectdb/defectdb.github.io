---
title: "Threads"
author: Maxim Menshikov
layout: defect
permalink: /threading/thread
group:
   - threading
---

Defects in the management of threads and lightweight processes themselves, as opposed to the data they share. Spawning far more threads than the workload or hardware can support inverts the intended benefit: scheduling overhead, context switching, and memory per stack overwhelm the gains from parallelism, leaving a system that is slower and less stable than a smaller pool would be.
