---
title: "Language constructs"
author: Maxim Menshikov
layout: defect
permalink: /threading/lang
group:
   - threading
---

Defects in the language-level concurrency constructs that promise to run something exactly once or in a controlled way. Helpers such as Go's `sync.Once` carry strict usage rules — the guarded work must be idempotent-safe and the `Once` value must not be copied or reset — and breaking those rules quietly defeats the single-execution guarantee the construct exists to provide.
