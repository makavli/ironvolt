"""Start IRONVOLT: python run.py"""
import faulthandler
import sys

from ironvolt.app import main

if __name__ == "__main__":
    if sys.stderr:                       # a windowed exe has no stderr; elsewhere a hard crash prints its Python stack
        faulthandler.enable()
    main()
