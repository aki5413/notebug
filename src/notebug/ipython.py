"""IPython / Colab integration: the %%notebug cell magic and the console callback."""
import argparse
import shlex

from . import tracer
from .core import _build

CALLBACK_NAME = "notebug.eval"


def _parser():
    p = argparse.ArgumentParser(prog="%%notebug", add_help=False)
    p.add_argument("--lang", choices=["ko", "ja", "en"])
    p.add_argument("--pet")
    p.add_argument("--max", type=int, dest="max_steps")
    p.add_argument("--theme", choices=["night", "light", "darcula", "contrast"])
    p.add_argument("--font", type=int, dest="font_size")
    for name in ("power", "sound", "achievements"):
        p.add_argument("--" + name, dest=name, action="store_const", const=True)
        p.add_argument("--no-" + name, dest=name, action="store_const", const=False)
    p.add_argument("--no-export", dest="export", action="store_const", const=False)
    return p


def notebug_magic(line, cell):
    """%%notebug [--lang ko|ja|en] [--theme night|light|darcula|contrast] [--font 16]
    [--pet NAME] [--power] [--sound] [--max N] [--no-achievements] [--no-export]"""
    from IPython import get_ipython
    from IPython.display import HTML, display
    try:
        args = vars(_parser().parse_args(shlex.split(line)))
    except SystemExit:
        print(notebug_magic.__doc__)
        return
    code = cell
    try:   # %matplotlib inline, !pip ... -> Python (the UI still shows the original cell)
        from IPython.core.inputtransformer2 import TransformerManager
        code = TransformerManager().transform_cell(cell)
    except Exception:  # noqa
        pass
    try:
        html = _build(code, get_ipython().user_ns, args, source=cell)
    except (TypeError, ValueError) as e:
        print("%%notebug:", e)
        return
    display(HTML(html))


def _colab_callback(sid, step, level, history, expr):
    from IPython.display import JSON
    try:
        res = tracer.eval_at(sid, int(step), int(level), list(history or []), str(expr))
    except BaseException as e:  # noqa - report anything to the console
        res = {"ok": False, "err": "%s: %s" % (type(e).__name__, e)}
    return JSON(res)


def load_ipython_extension(ip):
    """Called by ``import notebug`` or ``%load_ext notebug``."""
    ip.register_magic_function(notebug_magic, "cell", "notebug")
    try:
        from google.colab import output
    except ImportError:
        return
    output.register_callback(CALLBACK_NAME, _colab_callback)


def auto_register():
    try:
        from IPython import get_ipython
    except ImportError:
        return
    ip = get_ipython()
    if ip is not None:
        load_ipython_extension(ip)
