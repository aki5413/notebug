"""NoteBug - a PyCharm-style breakpoint debugger for teaching Python in Colab / Jupyter.

Quick start (in a notebook)::

    import notebug
    notebug.config(lang="ko")          # optional: defaults for the whole notebook

    %%notebug --pet dog
    total = 0
    for i in range(5):
        total += i      # bp        <- "# bp" or breakpoint() presets a breakpoint
    print(total)

Other ways to use it::

    notebug.run(code_string)                    # debug a string of code
    notebug.run_file("homework.py")             # debug a .py file
    notebug.save_html(code_string, "demo.html") # standalone page for any browser
    python -m notebug homework.py -o demo.html  # the same from a terminal
"""
from .core import config, run, run_file, save_html, to_html
from .ipython import load_ipython_extension

__version__ = "0.5.0"
__all__ = ["config", "run", "run_file", "save_html", "to_html",
           "load_ipython_extension", "__version__"]

from .ipython import auto_register as _auto_register

_auto_register()     # `import notebug` inside a notebook enables %%notebug
del _auto_register
