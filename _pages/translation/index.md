---
title: "Translation"
author: Maxim Menshikov
layout: defect
permalink: /translation
---

Analyzer-internal diagnostics raised when code that parsed successfully cannot
be lowered into the tool's internal representation. Parsing recovers the syntax;
translation is the next stage, which converts that syntax tree into the
normalized form the analyses actually operate on — and when a construct cannot
be expressed in that form, the unit is dropped before any check runs.

A failure here reflects a gap in the analyzer rather than a fault in the
program: a language feature or construct the front end accepted but the
lowering stage does not yet model. The practical consequence is the same as a
parsing failure — that piece of code goes unanalysed.

