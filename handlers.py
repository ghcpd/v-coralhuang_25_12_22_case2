# Minimal patch: switch the package-level handler bindings to the
# optimized implementation. This single-line change is the patch a reviewer
# would apply in a real repo to adopt the faster codepath.
from handlers_optimized import *
