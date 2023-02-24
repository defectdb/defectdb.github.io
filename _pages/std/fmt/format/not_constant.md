---
title: Format string is not constant
author: Maxim Menshikov
layout: defect
permalink: /std/fmt/format/not_constant
arch:
   - native
vulnerability:
   - None
ddos:
   - None
group_full: std.fmt.format
group:
   - std
   - fmt
   - format
---

Non-constant format string might be used to corrupt memory. Consider using constant strings.
