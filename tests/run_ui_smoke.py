from __future__ import annotations

from streamlit.testing.v1 import AppTest


app = AppTest.from_file("tests/ui_smoke_app.py")
app.run(timeout=120)
if app.exception:
    details = "\n\n".join(str(item.value) for item in app.exception)
    raise AssertionError(f"Streamlit UI smoke test failed:\n{details}")
print("Streamlit UI smoke test passed")
