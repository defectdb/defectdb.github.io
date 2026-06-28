---
title: "Parsing"
author: Maxim Menshikov
layout: defect
permalink: /parsing
---

Analyzer-internal diagnostics raised when the tool cannot turn source into a
structure it can analyse. These are not defects in the examined program as such
but signals that an earlier stage of the pipeline failed: the input could not
be parsed into a syntax tree, so nothing downstream can run against it.

The entries distinguish where the breakdown occurs. A parsing failure is the
analyzer's own front end rejecting the input — malformed, unsupported, or
beyond what its grammar accepts — while an external tool error reports that a
helper invoked during parsing exited abnormally. In both cases the result is
the same: no usable representation, and analysis of that unit is abandoned.

