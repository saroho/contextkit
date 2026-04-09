"""Allow running contextkit as a module: python -m contextkit"""

import sys
from .cli import main

sys.exit(main())
