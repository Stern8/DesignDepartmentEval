"""Reference submission: passes prism + furnace; deliberately has no caustic renderer."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from designbench.render_engine import reference  # noqa: E402

task, out = sys.argv[1], sys.argv[2]
{"prism": reference.render_prism, "furnace": reference.render_furnace}[task](out)
