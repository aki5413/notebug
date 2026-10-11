"""Public functions: config(), run(), run_file(), to_html(), save_html()."""
from . import tracer
from .render import PETS, render, standalone

_LANGS = ("ko", "ja", "en")
THEMES = ("night", "light", "darcula", "contrast")
_DEFAULTS = {
    "lang": None,          # "ko" | "ja" | "en"  (None: last choice in the browser, else Japanese)
    "pet": None,           # "cat" | "dog" | "hedgehog" | "penguin" | "turtle" | "dino" or any emoji
    "power": None,         # power mode (particles, combo)
    "sound": None,         # sound effects
    "achievements": True,  # 🏆 achievement pop-ups
    "theme": None,         # "night" | "light" | "darcula" | "contrast"  (None: last choice, else night)
    "font_size": None,     # code font size in px, 9-28 (everything scales with it; None: last choice, else 13)
    "colors": None,        # override single colours, e.g. {"bg": "#ffffff", "kw": "#d00000"}
    "max_steps": 3000,     # stop recording after this many steps (infinite-loop guard)
    "export": True,        # copy variables made by a %%notebug cell back into the notebook
}
_config = dict(_DEFAULTS)


def _check(k, v):
    if k not in _DEFAULTS:
        raise TypeError("unknown option %r (choose from %s)" % (k, ", ".join(_DEFAULTS)))
    if v is None:
        return
    if k == "lang" and v not in _LANGS:
        raise ValueError("lang must be one of %s" % (_LANGS,))
    if k == "theme" and v not in THEMES:
        raise ValueError("theme must be one of %s" % (THEMES,))
    if k == "font_size" and not 9 <= int(v) <= 28:
        raise ValueError("font_size must be between 9 and 28")
    if k == "colors" and not isinstance(v, dict):
        raise TypeError("colors must be a dict like {'bg': '#ffffff'}")


def config(**options):
    """Set notebook-wide defaults, e.g. ``notebug.config(lang="ko", theme="light")``.

    ``notebug.config()`` with no arguments returns the current settings.
    ``notebug.config(reset=True)`` restores the defaults.
    """
    if options.pop("reset", False):
        _config.clear()
        _config.update(_DEFAULTS)
    for k, v in options.items():
        _check(k, v)
    _config.update(options)
    if not options:
        return dict(_config)


def _options(overrides):
    for k, v in overrides.items():
        _check(k, v)
    opts = dict(_config)
    opts.update({k: v for k, v in overrides.items() if v is not None})
    return opts


def _ui_opts(o):
    return {"lang": o["lang"], "pet": PETS.get(o["pet"], o["pet"]),
            "power": o["power"], "sound": o["sound"],
            "achievements": o["achievements"], "theme": o["theme"],
            "font_size": o["font_size"], "colors": o["colors"]}


def _version():
    from . import __version__
    return __version__


def _export(ns, target):
    before = target.copy()
    for k, v in ns.items():
        if k.startswith("__") and k.endswith("__"):
            continue
        if k not in before or before[k] is not v:
            target[k] = v


def _build(code, namespace, overrides, source=None):
    o = _options(overrides)
    data, ns, _ = tracer.record(code.rstrip("\n"), namespace, o["max_steps"],
                                source=source.rstrip("\n") if source is not None else None)
    if o["export"] and ns is not None and namespace is not None:
        _export(ns, namespace)
    return render(data, _ui_opts(o), _version())


def to_html(code, *, lang=None, pet=None, power=None, sound=None, achievements=None,
            theme=None, font_size=None, colors=None, max_steps=None, namespace=None):
    """Record `code` and return the debugger widget as an HTML string."""
    return _build(code, namespace, dict(lang=lang, pet=pet, power=power, sound=sound,
                                        achievements=achievements, theme=theme,
                                        font_size=font_size, colors=colors,
                                        max_steps=max_steps, export=False))


def run(code, *, lang=None, pet=None, power=None, sound=None, achievements=None,
        theme=None, font_size=None, colors=None, max_steps=None, namespace=None, export=None):
    """Debug a string of Python code and show the debugger in the notebook.

    ``namespace`` is the dict the code can see (e.g. ``globals()``). When given,
    variables the code creates are copied back into it (unless ``export=False``).
    """
    from IPython.display import HTML, display
    html = _build(code, namespace, dict(lang=lang, pet=pet, power=power, sound=sound,
                                        achievements=achievements, theme=theme,
                                        font_size=font_size, colors=colors,
                                        max_steps=max_steps, export=export))
    display(HTML(html))


def run_file(path, **options):
    """Debug a .py file, e.g. ``notebug.run_file("homework1.py", lang="ko")``."""
    with open(path, encoding="utf-8") as f:
        run(f.read(), **options)


def save_html(code, path, **options):
    """Save the debugger as a standalone .html file (open it in any browser).

    Stepping, variables and breakpoints all work offline; only the >>> console
    needs a live Colab kernel.
    """
    with open(path, "w", encoding="utf-8") as f:
        f.write(standalone(to_html(code, **options)))
    return path
