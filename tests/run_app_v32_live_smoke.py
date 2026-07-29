from __future__ import annotations

from streamlit.testing.v1 import AppTest


app = AppTest.from_file("app_v32.py")
app.run(timeout=300)
if app.exception:
    details = "\n\n".join(str(item.value) for item in app.exception)
    raise AssertionError(f"Live V3.2 app smoke test failed:\n{details}")
print("Live V3.2 app smoke test passed")
