"""Recording a program step by step, and replaying it for the console."""
import ast
import base64
import builtins
import io
import linecache
import random
import re
import sys
import textwrap
import time
import types
import uuid

from .encoding import Encoder, kind, short

SESSIONS = {}
MAX_SESSIONS = 30
MAX_FIGS = 30              # figures kept per run (PNG, embedded in the page)
TIME_BUDGET = 10.0         # seconds a run may continue after recording stopped (infinite-loop guard)
_PLOT_HINT = re.compile(r"matplotlib|seaborn|\bplt\b|\.plot\b|\.hist\(|\.boxplot\(|\.scatter\(|\bsns\b")
_NUMPY_HINT = re.compile(r"\bnumpy\b|\bpandas\b|\bnp\.|\bpd\.")
_DISPLAY_MODULES = ("IPython.display", "IPython.core.display_functions")


class _Stop(BaseException):
    """Used internally to abort traced execution."""


def _fig_png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=80, bbox_inches="tight")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _is_figure(v):
    return type(v).__name__ in ("Figure", "SubFigure") and hasattr(v, "savefig")


class Runner:
    def __init__(self, sess, mode, target=None, on_target=None, max_steps=3000):
        self.sess = sess
        self.fname = sess["fname"]
        self.mode = mode                  # "record" or "replay"
        self.target = target
        self.on_target = on_target
        self.max_steps = max_steps
        self.count = 0
        self.steps = []
        self.truncated = False            # stopped recording, but the program ran to the end
        self.aborted = False              # program stopped (probably an infinite loop)
        self.buf = io.StringIO()
        self.inputs = [] if mode == "record" else list(sess["inputs"])
        self.enc = Encoder("__main__") if mode == "record" else None
        self.base = sess["base"]
        self.figs = []                    # record: [{"o": text offset, "si": step index, "png": ...}]
        self.sink = None                  # replay: list collecting console figures (or None)
        self.plt = None
        self.fig_before = set()
        self.t0 = 0.0

    # --- builtins used by the student code ---------------------------------
    def _input(self, prompt=""):
        if self.mode == "record":
            val = self.sess["orig_input"](prompt)
            self.inputs.append(val)
        else:
            if not self.inputs:
                raise RuntimeError("replay: no recorded input left")
            val = self.inputs.pop(0)
        self.buf.write("%s%s\n" % (prompt, val))
        return val

    def _display(self, *objs, **kw):
        """Stand-in for IPython's display(): text goes to the output panel, figures become images."""
        for o in objs:
            if _is_figure(o):
                self.capture_fig(o)
            else:
                try:
                    self.buf.write(repr(o) + "\n")
                except BaseException as e:  # noqa
                    self.buf.write("<repr error: %s>\n" % type(e).__name__)

    def make_ns(self):
        ns = dict(self.base)
        bi = dict(builtins.__dict__)
        bi["input"] = self._input
        bi["breakpoint"] = lambda *a, **k: None
        bi["display"] = self._display
        ns["__builtins__"] = bi
        ns.setdefault("__name__", "__main__")
        return ns

    # --- figures -------------------------------------------------------------------
    def capture_fig(self, fig):
        if self.mode == "record":
            if len(self.figs) < MAX_FIGS:
                try:
                    self.figs.append({"o": self.buf.tell(), "si": len(self.steps), "png": _fig_png(fig)})
                except Exception as e:  # noqa
                    self.buf.write("<figure could not be drawn: %s>\n" % e)
            else:
                self.buf.write("<figure omitted: more than %d figures>\n" % MAX_FIGS)
        elif self.sink is not None:
            try:
                self.sink.append(_fig_png(fig))
            except Exception:  # noqa
                pass
        if self.plt is not None:
            self.plt.close(fig)

    def new_figs(self):
        if self.plt is None:
            return []
        return [self.plt.figure(n) for n in self.plt.get_fignums() if n not in self.fig_before]

    def _show(self, *a, **k):          # replaces plt.show()
        for fig in self.new_figs():
            self.capture_fig(fig)

    def _patch(self):
        self._undo = []
        if self.sess.get("plots"):
            try:
                import matplotlib.pyplot as plt
            except Exception:  # noqa - matplotlib missing: nothing to capture
                plt = None
            if plt is not None:
                self.plt = plt
                try:
                    plt._get_backend_mod()       # resolve the backend now, not in the middle of a run
                except Exception:  # noqa
                    pass
                self.fig_before = set(plt.get_fignums())
                self._undo.append((plt, "show", plt.show))
                runner = self

                def show(*args, **kwargs):     # a plain function: matplotlib sets attributes on it
                    runner._show()
                plt.show = show
        for name in _DISPLAY_MODULES:
            m = sys.modules.get(name)
            if m is not None and hasattr(m, "display"):
                self._undo.append((m, "display", m.display))
                m.display = self._display

    def _unpatch(self):
        for obj, attr, val in reversed(self._undo):
            setattr(obj, attr, val)
        if self.plt is not None:
            for fig in self.new_figs():
                self.plt.close(fig)

    # --- trace functions -------------------------------------------------------
    def t_global(self, frame, event, arg):
        code = frame.f_code
        if code.co_filename != self.fname:
            return None
        if code.co_name != "<module>":
            # Only follow calls made by the student's own code. Functions that a
            # library calls back (DataFrame.apply, np.vectorize, ...) run as one step.
            f = frame.f_back
            while f is not None and f.f_code.co_filename == self.fname and f.f_code.co_name != "<module>":
                f = f.f_back
            if f is None or f.f_code.co_filename != self.fname:
                return None
        return self.t_local

    def t_local(self, frame, event, arg):
        if event == "return" and frame.f_code.co_name == "<module>" and \
                (frame.f_back is None or frame.f_back.f_code.co_filename != self.fname):
            return self.t_local     # hide the module's own "return None"
        if event in ("line", "return", "exception"):
            i = self.count
            self.count += 1
            if self.mode == "record" and i < self.max_steps:
                self.snap(frame, event, arg)
            elif self.mode == "record":
                self.truncated = True
            elif i == self.target:
                self.on_target(self.user_frames(frame))
                raise _Stop()
            if i >= self.max_steps and (i & 4095) == 4095:
                if not self.t0:
                    self.t0 = time.monotonic()      # recording has stopped; start the clock
                elif time.monotonic() - self.t0 > TIME_BUDGET:
                    self.aborted = True
                    raise _Stop()
        return self.t_local

    def user_frames(self, frame):
        frames = []
        f = frame
        while f is not None and f.f_code.co_filename == self.fname:
            frames.append(f)
            f = f.f_back
        frames.reverse()
        return frames

    def frame_vars(self, fr, is_module):
        out = []
        if is_module:
            for k, v in list(fr.f_globals.items()):
                if k.startswith("__") and k.endswith("__"):
                    continue
                if k in self.base and self.base[k] is v:
                    continue
                if isinstance(v, types.ModuleType):
                    continue
                out.append([k, self.enc.encode(v), kind(v)])
        else:
            for k, v in list(fr.f_locals.items()):
                out.append([k, self.enc.encode(v), kind(v)])
        return out

    def snap(self, frame, event, arg):
        frames = self.user_frames(frame)
        stack = []
        for j, fr in enumerate(frames):
            is_mod = (j == 0 and fr.f_code.co_name == "<module>")
            stack.append({"fn": fr.f_code.co_name, "ln": fr.f_lineno,
                          "v": self.frame_vars(fr, is_mod)})
        st = {"e": {"line": "l", "return": "r", "exception": "x"}[event],
              "ln": frame.f_lineno, "d": len(stack), "s": stack,
              "o": self.buf.tell()}
        if event == "return":
            st["rv"] = self.enc.encode(arg)
        elif event == "exception":
            st["ex"] = short("%s: %s" % (arg[0].__name__, arg[1]), 200)
        self.steps.append(st)

    # --- run -------------------------------------------------------------------
    def show_value(self, val):
        """Like a notebook: the value of the last line is shown (df.head(), fig, ...)."""
        if val is None:
            return
        if _is_figure(val):
            self.capture_fig(val)
            return
        try:
            self.buf.write(repr(val) + "\n")
        except BaseException as e:  # noqa
            self.buf.write("<repr error: %s>\n" % type(e).__name__)

    def run(self, body, last=None, on_end=None):
        """Execute the program; `last` is the final expression (shown like Out[])."""
        ns = self.make_ns()
        old_out, old_err, old_hook = sys.stdout, sys.stderr, sys.breakpointhook
        exc, val = None, None
        self._patch()
        sys.stdout = sys.stderr = self.buf
        sys.breakpointhook = lambda *a, **k: None
        stopped = False
        sys.settrace(self.t_global)
        try:
            try:
                try:
                    exec(body, ns)
                    if last is not None:
                        val = eval(last, ns)
                finally:
                    sys.settrace(None)
                if last is not None:
                    self.show_value(val)
            except _Stop:
                stopped = True
            except BaseException as e:  # noqa - student errors, SystemExit, ...
                exc = e
            if not stopped:
                try:
                    self._show()              # figures a notebook would show at the end
                except Exception:  # noqa
                    pass
                if on_end is not None:
                    on_end(ns)                # console at the end (also after an error)
        finally:
            sys.stdout, sys.stderr, sys.breakpointhook = old_out, old_err, old_hook
            self._unpatch()
        return ns, exc


def compile_program(code, fname):
    """Compile like a notebook cell: (body, last_expression_or_None). Raises SyntaxError."""
    tree = ast.parse(code, fname, "exec")
    last = None
    if tree.body and isinstance(tree.body[-1], ast.Expr):
        expr = tree.body.pop()
        last = compile(ast.Expression(expr.value), fname, "eval")
    return compile(tree, fname, "exec"), last


def format_exc(exc, fname, lines):
    tb = exc.__traceback__
    parts, last = [], None
    while tb is not None:
        f = tb.tb_frame
        if f.f_code.co_filename == fname:
            ln = tb.tb_lineno
            src = lines[ln - 1].strip() if 0 < ln <= len(lines) else ""
            parts.append("  line %d, in %s\n    %s" % (ln, f.f_code.co_name, src))
            last = ln
        tb = tb.tb_next
    head = "Traceback (most recent call last):\n" if parts else ""
    return head + "\n".join(parts) + ("\n" if parts else "") + \
        "%s: %s" % (type(exc).__name__, exc), last


def in_colab():
    try:
        import google.colab  # noqa
        return True
    except ImportError:
        return False


def record(code, base=None, max_steps=3000, source=None):
    """Run `code` and record every step. `source` is the text shown in the UI
    (e.g. the cell before IPython turned %magics into Python); it must have the
    same number of lines as `code`, otherwise `code` is shown."""
    sid = uuid.uuid4().hex[:10]
    fname = "<notebug-%s>" % sid
    shown = source if source is not None and source.count("\n") == code.count("\n") else code
    lines = shown.split("\n")
    linecache.cache[fname] = (len(code), None, [l + "\n" for l in code.split("\n")], fname)
    if _NUMPY_HINT.search(code) and "numpy" not in sys.modules:
        try:
            import numpy  # noqa - so its random state can be saved for the console replay
        except ImportError:
            pass
    sess = {"sid": sid, "fname": fname, "code": code, "lines": lines,
            "base": dict(base or {"__name__": "__main__"}),
            "orig_input": builtins.input, "inputs": [],
            "rand": random.getstate(), "np": None,
            "plots": bool(_PLOT_HINT.search(code)) or "matplotlib.pyplot" in sys.modules,
            "max_steps": max_steps}
    np = sys.modules.get("numpy")
    if np is not None:
        try:
            sess["np"] = np.random.get_state()
        except Exception:  # noqa
            pass
    sess["base"].pop("__builtins__", None)

    bps = [i + 1 for i, l in enumerate(lines)
           if "breakpoint()" in l.replace(" ", "") or _is_bp_comment(l)]
    data = {"sid": sid, "code": shown, "bps": bps, "steps": [], "vals": [], "figs": [],
            "out": "", "trunc": False, "hard": False, "max": max_steps, "syntax": None,
            "colab": in_colab()}
    try:
        body, last = compile_program(code, fname)
    except SyntaxError as e:
        data["syntax"] = {"ln": e.lineno or 1,
                          "msg": "%s: %s" % (type(e).__name__, e.msg)}
        return data, None, sess

    r = Runner(sess, "record", max_steps=max_steps)
    ns, exc = r.run(body, last)
    sess["inputs"] = r.inputs
    end = {"e": "end", "ln": None, "d": 1, "o": r.buf.tell(),
           "s": [{"fn": "<module>", "ln": None,
                  "v": r.frame_vars(types.SimpleNamespace(f_globals=ns), True)}]}
    if exc is not None:
        end["ex"], end["eln"] = format_exc(exc, fname, lines)
    r.steps.append(end)
    data.update(steps=r.steps, vals=r.enc.vals, out=r.buf.getvalue(), figs=r.figs,
                trunc=r.truncated, hard=r.aborted)

    SESSIONS[sid] = sess
    while len(SESSIONS) > MAX_SESSIONS:
        SESSIONS.pop(next(iter(SESSIONS)))
    return data, ns, sess


def _is_bp_comment(line):
    i = line.find("#")
    return i >= 0 and line[i + 1:].strip().lower().startswith("bp") and \
        line[i + 1:].strip()[2:3] in ("", " ", ":")


def _exec_one(src, g, l):
    """Run console input like the Python REPL.

    A single expression is evaluated. Several lines / statements are executed;
    if the last one is an expression, its value is returned (so a for-loop
    followed by ``total`` shows the total). Returns (has_value, value).
    """
    src = textwrap.dedent(src).strip("\n")
    try:
        co = compile(src, "<console>", "eval")
    except SyntaxError:
        co = None
    if co is not None:
        return True, eval(co, g, l)
    tree = ast.parse(src, "<console>", "exec")
    last = None
    if tree.body and isinstance(tree.body[-1], ast.Expr):
        last = ast.Expression(tree.body.pop().value)
    if tree.body:
        exec(compile(tree, "<console>", "exec"), g, l)
    if last is not None:
        return True, eval(compile(last, "<console>", "eval"), g, l)
    return False, None


def eval_at(sid, step, level, history, expr):
    """Re-run the program up to `step`, then run console code in that frame."""
    sess = SESSIONS.get(sid)
    if sess is None:
        return {"ok": False, "err": "Session expired. Please run the cell again."}
    result = {"ok": False, "err": "Replay did not reach this step."}
    wants_plot = bool(_PLOT_HINT.search(expr)) or bool(re.search(r"\bfig\b|\bax\b|\baxes\b", expr))
    runner = None

    def evaluate(g, l):
        for h in history:
            try:
                _exec_one(h, g, l)
            except BaseException:  # noqa
                pass
        buf = io.StringIO()
        old = sys.stdout, sys.stderr
        sys.stdout = sys.stderr = buf
        imgs = []
        runner.sink = imgs
        try:
            is_expr, val = _exec_one(expr, g, l)
            result.clear()
            result["ok"] = True
            if is_expr and val is not None:
                if _is_figure(val):
                    runner.capture_fig(val)
                else:
                    try:
                        result["val"] = short(repr(val), 3000)
                    except BaseException as e:  # noqa
                        result["val"] = "<repr error: %s>" % type(e).__name__
            if wants_plot:
                runner._show()              # draw what the console code plotted
        except BaseException as e:  # noqa
            result.clear()
            result.update(ok=False, err="%s: %s" % (type(e).__name__, e))
        finally:
            sys.stdout, sys.stderr = old
            runner.sink = None
        result["out"] = buf.getvalue()
        if imgs:
            result["imgs"] = imgs

    def on_target(frames):
        fr = frames[level] if 0 <= level < len(frames) else frames[-1]
        g = fr.f_globals
        l = g if fr.f_code.co_name == "<module>" and fr is frames[0] else fr.f_locals
        evaluate(g, l)

    body, last = compile_program(sess["code"], sess["fname"])
    saved = random.getstate()
    np = sys.modules.get("numpy")
    np_saved = None
    random.setstate(sess["rand"])
    if np is not None and sess["np"] is not None:
        np_saved = np.random.get_state()
        np.random.set_state(sess["np"])
    try:
        if step < 0:   # end of program
            runner = Runner(sess, "replay", target=-1, max_steps=sess["max_steps"])
            runner.run(body, last, on_end=lambda ns: evaluate(ns, ns))
        else:
            runner = Runner(sess, "replay", target=step, on_target=on_target,
                            max_steps=sess["max_steps"])
            runner.run(body, last)
    finally:
        random.setstate(saved)
        if np_saved is not None:
            np.random.set_state(np_saved)
    return result
