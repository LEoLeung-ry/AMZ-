from __future__ import annotations

from streamlit.testing.v1 import AppTest


app = AppTest.from_file("app_v32_parallel.py")
app.run(timeout=180)
if app.exception:
    details = "\n\n".join(str(item.value) for item in app.exception)
    raise AssertionError(f"Live optimized V3.2 app smoke test failed:\n{details}")
print("Live parallel optimized V3.2 app smoke test passed")
