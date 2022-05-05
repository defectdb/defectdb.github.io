---
title: IR generation error
author: Maxim Menshikov
layout: defect
permalink: /translation/ir
arch:
   - native
vulnerability:
   - None
ddos:
   - None
group_full: translation
group:
   - translation
---

The tool failed to convert syntax structure to the intermediate representation.

It is possible that the tool will use a different name for this defect as the tool has more details about the issue.

# Impact
No impact except that the tool will not be able to proceed with the compilation or analysis.

# Vulnerability potential

None.

# Technical details

After the syntax structure is determined from the source code, most tools try to convert to the intermediate representation in order to analyze further. If there is no way the given syntax structure, the translator gives an intermediate representation generation error.
