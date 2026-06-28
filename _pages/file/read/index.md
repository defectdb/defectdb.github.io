---
title: "Read"
author: Maxim Menshikov
layout: defect
permalink: /file/read
group:
   - file
---

Defects in read operations on files, typically where the requested length is
degenerate. Asking to read zero symbols performs no transfer yet still consumes
a call and its error handling, which almost always signals a miscalculated size
or an off-by-one in the surrounding logic rather than a deliberate no-op.

