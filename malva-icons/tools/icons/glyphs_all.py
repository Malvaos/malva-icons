"""Imports every glyph module so that glyphkit.GLYPHS holds the whole set."""
import glyphs_status      # noqa: F401
import glyphs_status2     # noqa: F401
import glyphs_actions     # noqa: F401
import glyphs_devices     # noqa: F401
import glyphs_extra      # noqa: F401
import glyphs_alias      # noqa: F401  (last: merges repeated drawings into aliases)

import kitshift                                   # noqa: E402  (after every glyph: puts off-centre drawings on the middle of the grid)
kitshift.apply()
