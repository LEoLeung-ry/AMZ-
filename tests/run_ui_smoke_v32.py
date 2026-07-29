from __future__ import annotations

from streamlit.testing.v1 import AppTest


app = AppTest.from_file("tests/ui_smoke_v32_app.py")
app.run(timeout=180)
if app.exception:
    details = "\n\n".join(str(item.value) for item in app.exception)
    raise AssertionError(f"V3.2 Streamlit UI smoke test failed:\n{details}")
print("V3.2 Streamlit UI smoke test passed")
