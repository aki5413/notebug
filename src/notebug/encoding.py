"""Turning Python values into small JSON nodes for the UI."""
import json
import reprlib
import sys
import types

MAX_CHILDREN = 30

_rp = reprlib.Repr()
_rp.maxstring = 80
_rp.maxother = 100
_rp.maxlist = _rp.maxtuple = _rp.maxset = _rp.maxfrozenset = 20
_rp.maxdict = 12
_rp.maxlevel = 3

_SKIP_TYPES = (types.FunctionType, types.BuiltinFunctionType, types.MethodType,
               types.ModuleType, type)


def short(s, n):
    return s if len(s) <= n else s[: n - 1] + "…"


def _user_class(v, module):
    return (type(v).__module__ == module and hasattr(v, "__dict__")
            and not isinstance(v, _SKIP_TYPES))


def _np_scalar(v):
    np = sys.modules.get("numpy")
    return np is not None and isinstance(v, np.generic)


def _cell(x):
    """Short text for one table cell / array item (numpy scalars shown as plain numbers)."""
    if _np_scalar(x):
        x = x.item()
    if isinstance(x, float):
        return "%.6g" % x
    return short(str(x), 18)


def _safe_repr(v, module="__main__"):
    try:
        if _np_scalar(v):
            return _rp.repr(v.item())          # np.float64(1.5) -> 1.5
        if _user_class(v, module) and type(v).__repr__ is object.__repr__:
            inner = ", ".join("%s=%s" % (k, _rp.repr(x))
                              for k, x in list(vars(v).items())[:8])
            return "%s(%s)" % (type(v).__name__, inner)
        return _rp.repr(v)
    except BaseException as e:  # noqa
        return "<repr error: %s>" % type(e).__name__


class Encoder:
    """Turns Python values into small JSON nodes, de-duplicated in a table."""

    def __init__(self, module):
        self.module = module
        self.table = {}
        self.vals = []
        self.oids = {}

    def intern(self, node):
        key = json.dumps(node, ensure_ascii=False, sort_keys=True)
        idx = self.table.get(key)
        if idx is None:
            idx = len(self.vals)
            self.table[key] = idx
            self.vals.append(node)
        return idx

    def oid(self, v):
        k = id(v)
        if k not in self.oids:
            self.oids[k] = len(self.oids) + 1
        return self.oids[k]

    # --- numpy / pandas -------------------------------------------------------
    def _special(self, v, depth):
        """DataFrame / Series / ndarray: shape + dtype, a preview, and a content hash
        so that the UI can tell when they changed. Returns None for other values."""
        pd = sys.modules.get("pandas")
        np = sys.modules.get("numpy")
        if pd is not None and isinstance(v, pd.DataFrame):
            r, c = v.shape
            cols = [short(str(x), 18) for x in v.columns[:8]]
            head = v.iloc[:8, :8]
            node = {"t": "DataFrame", "sh": "%d×%d" % (r, c),
                    "r": short("%d rows × %d columns: %s%s" % (r, c, ", ".join(cols), ", …" if c > 8 else ""), 160),
                    "tbl": {"c": cols, "i": [short(str(x), 16) for x in head.index],
                            "v": [[_cell(x) for x in row] for row in head.itertuples(index=False, name=None)],
                            "n": r, "m": c},
                    "o": self.oid(v)}
            if r <= 2000:
                try:
                    node["h"] = int(pd.util.hash_pandas_object(v, index=True).sum()) & 0xFFFFFFFF
                except Exception:  # noqa - unhashable cells
                    pass
            return self.intern(node)
        if pd is not None and isinstance(v, pd.Series):
            n = len(v)
            node = {"t": "Series", "sh": "(%d,) %s" % (n, v.dtype),
                    "r": short(", ".join("%s: %s" % (k, _cell(x)) for k, x in v.iloc[:10].items())
                               + (", …" if n > 10 else ""), 160),
                    "o": self.oid(v)}
            if v.name is not None:
                node["r"] = short("%s | %s" % (v.name, node["r"]), 160)
            if depth < 2 and n:
                node["k"] = [[short(str(k), 30), self.encode(x, depth + 1)]
                             for k, x in v.iloc[:MAX_CHILDREN].items()]
            if n <= 2000:
                try:
                    node["h"] = int(pd.util.hash_pandas_object(v, index=True).sum()) & 0xFFFFFFFF
                except Exception:  # noqa
                    pass
            return self.intern(node)
        if np is not None and isinstance(v, np.ndarray):
            try:
                txt = np.array2string(v, threshold=40, edgeitems=3, max_line_width=160, separator=", ")
            except Exception:  # noqa
                txt = "…"
            node = {"t": "ndarray", "sh": "%s %s" % (v.shape, v.dtype),
                    "r": short(" ".join(txt.split()), 160), "o": self.oid(v)}
            if depth < 2 and v.ndim >= 1 and v.shape[0]:
                node["k"] = [[str(i), self.encode(v[i], depth + 1)] for i in range(min(len(v), MAX_CHILDREN))]
            if v.size <= 100000:
                try:
                    node["h"] = hash(v.tobytes()) & 0xFFFFFFFF
                except Exception:  # noqa
                    pass
            return self.intern(node)
        return None

    def encode(self, v, depth=0):
        try:
            special = self._special(v, depth)
        except Exception:  # noqa - never let a preview break the recording
            special = None
        if special is not None:
            return special
        node = {"t": type(v).__name__, "r": short(_safe_repr(v, self.module), 160)}
        items = None
        try:
            if isinstance(v, (list, tuple)):
                items = [(str(i), x) for i, x in enumerate(v[:MAX_CHILDREN])]
                node["n"] = len(v)
            elif isinstance(v, (set, frozenset)):
                items = [("·", x) for x in list(v)[:MAX_CHILDREN]]
                node["n"] = len(v)
            elif isinstance(v, dict):
                items = [(short(_safe_repr(k), 40), x)
                         for k, x in list(v.items())[:MAX_CHILDREN]]
                node["n"] = len(v)
            elif isinstance(v, str):
                node["n"] = len(v)
            elif _user_class(v, self.module):
                d = vars(v)
                items = [(k, x) for k, x in list(d.items())[:MAX_CHILDREN]]
        except BaseException:  # noqa
            items = None
        if isinstance(v, (list, dict, set)) or _user_class(v, self.module):
            node["o"] = self.oid(v)
        if items and depth < 2:
            node["k"] = [[lbl, self.encode(x, depth + 1)] for lbl, x in items]
        return self.intern(node)


def kind(v):
    if isinstance(v, (types.FunctionType, types.BuiltinFunctionType, types.MethodType)):
        return "f"
    if isinstance(v, type):
        return "c"
    return ""
