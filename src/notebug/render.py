"""Building the debugger page (HTML + CSS + JS) from the files in assets/."""
import json
from functools import lru_cache
from importlib import resources

PETS = {"cat": "🐈", "dog": "🐕", "hedgehog": "🦔", "penguin": "🐧",
        "turtle": "🐢", "dino": "🦖"}


@lru_cache(maxsize=None)
def _asset(name):
    return resources.files(__package__).joinpath("assets", name).read_text(encoding="utf-8")


def _js_literal(obj):
    """JSON that is also safe to put inside a <script> element."""
    return (json.dumps(obj, ensure_ascii=False)
            .replace("<", "\\u003c")
            .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def render(data, opts, version):
    """Return the widget HTML for one recorded run.

    The data is embedded directly in the executable script, because Colab
    strips <script type="application/json"> elements from outputs.
    """
    sid = data["sid"]
    data = dict(data, opts=opts)
    js = (_asset("ui.js")
          .replace("__SID__", sid)
          .replace("/*__I18N__*/", _asset("i18n.js"))
          .replace("__DATA__", _js_literal(data)))   # user data last
    html = _asset("ui.html").replace("__SID__", sid).replace("__VER__", version)
    return "<style>\n%s</style>\n%s<script>\n%s</script>\n" % (_asset("ui.css"), html, js)


def standalone(widget_html, title="NoteBug"):
    """Wrap the widget in a full HTML document (for saving to a file)."""
    return ("<!doctype html>\n<html><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            "<title>%s</title></head>\n<body style=\"margin:0;padding:16px;background:#0f1019\">\n"
            "%s</body></html>\n" % (title, widget_html))
