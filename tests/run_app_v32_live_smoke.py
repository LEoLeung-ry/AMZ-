from __future__ import annotations

from streamlit.testing.v1 import AppTest


app = AppTest.from_file("dashboard.py")
app.run(timeout=120)
if app.exception:
    details = "\n\n".join(str(item.value) for item in app.exception)
    raise AssertionError(f"Live responsive V3.2 app smoke test failed:\n{details}")
print("Live responsive V3.2 dashboard smoke test passed")
