#!/usr/bin/env python3
import os
import runpy

service=os.environ.get("COALICION_SERVICE","api").strip().lower()
if service == "api":
    runpy.run_path("api.py", run_name="__main__")
elif service == "telegram":
    runpy.run_module("src.telegram_bot", run_name="__main__")
elif service == "cli":
    runpy.run_path("coalicion.py", run_name="__main__")
else:
    raise SystemExit(f"BLOCKED: unknown COALICION_SERVICE={service!r}")
