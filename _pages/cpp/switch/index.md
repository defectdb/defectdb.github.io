---
title: "Switch"
author: Maxim Menshikov
layout: defect
permalink: /cpp/switch
group:
   - cpp
---

Defects from the C-inherited semantics of `switch`, where control flow runs from one `case` into the next unless a `break` stops it. An unintended fall-through executes the following case's code as well, usually because a `break` was forgotten — a silent logic error that the `[[fallthrough]]` attribute lets you mark when the behavior is genuinely intended.
