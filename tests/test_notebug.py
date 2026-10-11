"""Run with:  python -m pytest tests"""
import builtins

import notebug
from notebug import tracer

CODE = '''def fact(n):
    if n <= 1:
        return 1
    return n * fact(n - 1)

nums = [3, 1, 2]
alias = nums
total = 0
for x in nums:
    total += x   # bp
r = fact(3)
name = input("name? ")
print("hi", name, total, r)
print(1/0)'''


def _rec(monkeypatch, code=CODE, **kw):
    monkeypatch.setattr(builtins, "input", lambda p="": "Kim")
    return tracer.record(code, **kw)


def test_record_basic(monkeypatch):
    data, ns, _ = _rec(monkeypatch)
    assert data["bps"] == [10]
    assert data["out"] == "name? Kim\nhi Kim 6 6\n"
    end = data["steps"][-1]
    assert end["e"] == "end" and end["eln"] == 14 and "ZeroDivisionError" in end["ex"]
    # nums and alias are the same object -> same object number
    first = next(s for s in data["steps"] if s["e"] == "l" and s["ln"] == 10)
    oid = {v[0]: data["vals"][v[1]].get("o") for v in first["s"][0]["v"]}
    assert oid["nums"] == oid["alias"] is not None


def test_console_eval_in_function_frame(monkeypatch):
    data, _, _ = _rec(monkeypatch)
    i = next(k for k, s in enumerate(data["steps"]) if s["e"] == "r" and s["d"] == 4)
    assert tracer.eval_at(data["sid"], i, 3, [], "n")["val"] == "1"
    assert tracer.eval_at(data["sid"], i, 0, ["z = total * 10"], "z + 1")["val"] == "61"
    assert tracer.eval_at(data["sid"], i, 0, [], 'print("a")')["out"] == "a\n"
    assert not tracer.eval_at(data["sid"], i, 0, [], "nope")["ok"]
    assert tracer.eval_at(data["sid"], -1, 0, [], "name")["val"] == "'Kim'"


def test_infinite_loop_is_cut(monkeypatch):
    monkeypatch.setattr(tracer, "TIME_BUDGET", 0.5)
    data, _, _ = _rec(monkeypatch, "while True:\n    pass", max_steps=100)
    assert data["trunc"] and data["hard"] and len(data["steps"]) == 101


def test_long_loop_runs_to_the_end(monkeypatch):
    data, ns, _ = _rec(monkeypatch, "t = 0\nfor i in range(5000):\n    t += i\nprint(t)", max_steps=100)
    assert data["trunc"] and not data["hard"] and data["out"] == "12497500\n" and ns["t"] == 12497500


def test_syntax_error(monkeypatch):
    data, _, _ = _rec(monkeypatch, "x = (\n")
    assert data["syntax"]["ln"] == 1


def test_html_is_self_contained(monkeypatch):
    monkeypatch.setattr(builtins, "input", lambda p="": "Kim")
    html = notebug.to_html('s = "</script>"\nprint(s)', lang="ko", pet="dog")
    assert '<script type="application/json"' not in html
    assert html.count("</script>") == 1          # only our own closing tag
    assert "__DATA__" not in html and "/*__I18N__*/" not in html
    assert '"pet": "🐕"' in html and '"lang": "ko"' in html


def test_config(monkeypatch):
    notebug.config(lang="en", achievements=False)
    try:
        html = notebug.to_html("a = 1")
        assert '"lang": "en"' in html and '"achievements": false' in html
    finally:
        notebug.config(reset=True)


def test_console_multiline(monkeypatch):
    data, _, _ = _rec(monkeypatch)
    i = next(k for k, s in enumerate(data["steps"]) if s["e"] == "l" and s["ln"] == 10)
    sid = data["sid"]
    # for-loop with print, then the value of the last expression
    r = tracer.eval_at(sid, i, 0, [], "s = 0\nfor v in nums:\n    if v > 1:\n        print(v)\n        s += v\ns")
    assert r["ok"] and r["out"] == "3\n2\n" and r["val"] == "5"
    # statements only -> no value, but state is kept through the history
    r = tracer.eval_at(sid, i, 0, [], "for v in nums:\n    total += v")
    assert r["ok"] and "val" not in r
    assert tracer.eval_at(sid, i, 0, ["for v in nums:\n    total += v"], "total")["val"] == "6"
    # indented paste and syntax errors
    assert tracer.eval_at(sid, i, 0, [], "    a = 2\n    a * 3")["val"] == "6"
    assert "SyntaxError" in tracer.eval_at(sid, i, 0, [], "for v in nums\n    pass")["err"]
    # inside a function frame
    j = next(k for k, s in enumerate(data["steps"]) if s["e"] == "r" and s["d"] == 4)
    assert tracer.eval_at(sid, j, 3, [], "acc = []\nfor q in range(n + 2):\n    acc.append(q)\nacc")["val"] == "[0, 1, 2]"


def test_theme_font_colors(monkeypatch):
    import pytest
    html = notebug.to_html("a = 1", theme="light", font_size=18, colors={"bg": "#fff"})
    assert '"theme": "light"' in html and '"font_size": 18' in html and '"colors": {"bg": "#fff"}' in html
    with pytest.raises(ValueError):
        notebug.to_html("a = 1", theme="pink")
    with pytest.raises(ValueError):
        notebug.config(font_size=40)


def test_data_analysis(monkeypatch):
    import pytest
    pytest.importorskip("pandas")
    pytest.importorskip("matplotlib")
    code = """import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
np.random.seed(0)
df = pd.DataFrame({"s": np.random.randint(50, 100, 300)})
df["ok"] = df["s"].apply(lambda v: v >= 60)
m = df["s"].mean()
plt.hist(df["s"])
plt.show()
df.head(2)"""
    data, ns, _ = _rec(monkeypatch, code)
    lines = [s["ln"] for s in data["steps"] if s["e"] == "l"]
    assert lines.count(6) == 1                      # the lambda called by apply is not stepped into
    assert len(data["figs"]) == 1 and data["figs"][0]["si"] == lines.index(9) + 1
    assert "ok" in data["out"] and data["steps"][-1].get("ex") is None
    vals = {n: data["vals"][i] for n, i, k in data["steps"][-1]["s"][0]["v"]}
    assert vals["df"]["t"] == "DataFrame" and vals["df"]["sh"] == "300×2" and len(vals["df"]["tbl"]["v"]) == 8
    assert vals["m"]["r"] == repr(float(ns["m"]))   # numpy scalar shown as a plain number
    i = lines.index(8)
    r = tracer.eval_at(data["sid"], i, 0, [], "plt.plot([1, 2, 3])")
    assert r["ok"] and len(r.get("imgs", [])) == 1
    assert tracer.eval_at(data["sid"], i, 0, [], "int(df.ok.sum()) > 0")["val"] == "True"
    import matplotlib.pyplot as plt
    assert plt.get_fignums() == []                   # nothing leaks into the notebook
