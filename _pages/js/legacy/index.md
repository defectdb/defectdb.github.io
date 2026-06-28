---
title: "Legacy"
author: Maxim Menshikov
layout: defect
permalink: /js/legacy
group:
   - js
---

Constructs the language has outgrown but still accepts. The `with` statement is the emblematic case: it makes name resolution depend on an object's runtime contents, defeating the engine's scope analysis, and is forbidden in strict mode for exactly that reason. Such forms produce ambiguous, hard-to-optimize code and should give way to their modern replacements.
