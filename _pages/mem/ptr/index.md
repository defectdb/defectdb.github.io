---
title: "Pointers"
author: Maxim Menshikov
layout: defect
permalink: /mem/ptr
group:
   - mem
---

Defects in the pointers that reference memory, where the address held is not the valid object the code assumes. This covers dereferencing a pointer that may be null, holding a dangling pointer into storage that has already been freed or gone out of scope, and comparing pointers in ways that signal a misunderstanding. The shared theme is a pointer outliving — or never reaching — the validity of what it points to.
