---
title: "Deinitialization"
author: Maxim Menshikov
layout: defect
permalink: /var/deinit
group:
   - var
---

Defects in releasing a variable's resources — closing handles, freeing memory, running cleanup — where the teardown happens at the wrong time or not at all. A common case is deferring cleanup inside a loop body when the intent was a single release at function exit, so resources pile up across iterations and are not reclaimed until far later than expected.

