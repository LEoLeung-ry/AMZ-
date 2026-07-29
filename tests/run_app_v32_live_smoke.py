from __future__ import annotations

from streamlit.testing.v1 import AppTest


app = AppTest.from_file("dashboard.py")
for attempt in (1, 2):
    app.run(timeout=180)
    if app.exception:
        details = "\n\n".join(str(item.value) for item in app.exception)
        raise AssertionError(
            f"Responsive dashboard run {attempt} failed:\n{details}"
        )
    if len(app.sidebar.radio) == 0:
        raise AssertionError(
            f"Responsive dashboard run {attempt} rendered no sidebar navigation; "
            "this reproduces the blank-page-on-refresh failure."
        )
    if len(app.markdown) == 0:
        raise AssertionError(
            f"Responsive dashboard run {attempt} rendered no main content."
        )

print("Responsive V3.2 dashboard rendered successfully on two consecutive runs")
