---
title: "Exceptions"
author: Maxim Menshikov
layout: defect
permalink: /csharp/exception
group:
   - csharp
---

Defects in how exceptions are thrown and caught, where the type or handling of a fault misrepresents what actually happened. The common thread is a mismatch between the exception's meaning and the program's intent — a placeholder thrown from a path that ships, or a catch so broad it erases the diagnosis.

Throwing `NotImplementedException` or `NotSupportedException` leaves a stub masquerading as a real method, while a bare `catch (Exception)` that does nothing turns every fault — including the ones that signal corruption you must not continue past — into silence. Catch narrowly, and let what you cannot handle propagate.

