#!/usr/bin/env python3
"""PlasmaForge development launcher."""

import os
import sys
from pathlib import Path

# Ensure root directory is on Python search path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from plasmaforge.main import main

if __name__ == "__main__":
    sys.exit(main())
