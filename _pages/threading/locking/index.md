---
title: "Locking"
author: Maxim Menshikov
layout: defect
permalink: /threading/locking
group:
   - threading
---

Defects in how locks guard shared state — cases where the locking discipline is incomplete or inconsistent rather than absent in principle. A mutex only protects data if every access takes it; when one path locks and another does not, or different sites acquire locks in conflicting ways, the result is a data race or deadlock that surfaces only under the right interleaving.
