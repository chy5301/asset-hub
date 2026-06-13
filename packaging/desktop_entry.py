"""PyInstaller 入口：桌面便携版。"""

import multiprocessing
import sys

from asset_hub.desktop.launcher import main

if __name__ == "__main__":
    multiprocessing.freeze_support()
    sys.exit(main())
