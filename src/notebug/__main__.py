"""Command line: python -m notebug program.py [-o out.html] [--lang ko] [--pet dog]"""
import argparse
import os
import sys

from .core import save_html


def main(argv=None):
    p = argparse.ArgumentParser(prog="python -m notebug",
                                description="Record a Python program and save the "
                                            "NoteBug debugger as an HTML page.")
    p.add_argument("file", help="the .py file to debug")
    p.add_argument("-o", "--output", help="output .html (default: <file>.debug.html)")
    p.add_argument("--lang", choices=["ko", "ja", "en"])
    p.add_argument("--pet")
    p.add_argument("--power", action="store_true", default=None)
    p.add_argument("--sound", action="store_true", default=None)
    p.add_argument("--max", type=int, dest="max_steps")
    p.add_argument("--theme", choices=["night", "light", "darcula", "contrast"])
    p.add_argument("--font", type=int, dest="font_size")
    a = p.parse_args(argv)
    with open(a.file, encoding="utf-8") as f:
        code = f.read()
    out = a.output or os.path.splitext(a.file)[0] + ".debug.html"
    save_html(code, out, lang=a.lang, pet=a.pet, power=a.power, sound=a.sound,
              max_steps=a.max_steps, theme=a.theme, font_size=a.font_size)
    print("saved:", out)


if __name__ == "__main__":
    sys.exit(main())
