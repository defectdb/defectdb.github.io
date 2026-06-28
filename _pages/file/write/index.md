---
title: "Write"
author: Maxim Menshikov
layout: defect
permalink: /file/write
group:
   - file
---

Defects in write operations on files, typically where the requested length is
degenerate. Writing zero symbols flushes nothing while still issuing the call,
which usually points to a miscalculated buffer length or a control-flow mistake
upstream rather than an intentional empty write.

