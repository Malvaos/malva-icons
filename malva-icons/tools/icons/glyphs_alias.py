"""Names that share one drawing. A drawing is stored once, under its canonical name; the theme installs the other names
as aliases (symlinks or copies, see install_theme.py). check_glyphs.py rejects two different names for one drawing
unless they are listed here."""
from glyphkit import GLYPHS

MERGES = {
    'dialog-question': ('system-help', 'help-browser', 'help-faq'),
    'dialog-information': ('help-about',),
    'non-starred': ('star-new',),
    'printer': ('document-print',),
    'document-save': ('media-floppy',),
    'document-properties': ('text-editor', 'accessories-text-editor', 'document-page-setup'),
    'edit-undo': ('document-revert',),
    'edit-find': ('preferences-system-search',),
    'action-unavailable': ('emblem-unreadable',),
    'view-refresh': ('emblem-synchronizing',),
    'view-grid': ('preferences-desktop-apps',),
    'sliders': ('preferences-other',),
    'send-to': ('preferences-system-sharing', 'emblem-shared'),
    'insert-image': ('preferences-desktop-wallpaper', 'emblem-photos'),
    'font-select': ('preferences-desktop-font',),
    'camera-video': ('emblem-videos',),
    # the standard names for one drawing: values and flags, legacy battery names, the emoji picker
    'object-select': ('edit-select',),
    'list-add': ('value-increase',),
    'list-remove': ('value-decrease',),
    'insert-text': ('format-text-plaintext',),
    'flag': ('emoji-flags',),
    'document-open-recent': ('emoji-recent',),
    'bluetooth-disconnected': ('bluetooth-acquiring',),
    'view-conceal': ('user-not-tracked',),
    'input-gaming': ('applications-games',),
    'preferences-system': ('applications-system',),
    'applications-utilities': ('applications-accessories',),
    'view-more-horizontal': ('applications-other',),
    'battery-level-0': ('battery-empty',),
    'battery-level-0-charging': ('battery-empty-charging',),
    'battery-level-10-charging': ('battery-caution-charging',),
    'battery-level-20': ('battery-low',),
    'battery-level-20-charging': ('battery-low-charging',),
    'battery-level-70': ('gnome-power-manager',),
    'battery-level-70-charging': ('battery-good-charging',),
    'battery-level-100': ('battery-full',),
    'battery-level-100-charged': ('battery-full-charged', 'battery-full-charging'),
}

for _canon, _names in MERGES.items():
    # a name is listed once: the file that draws a glyph may already name some of these
    GLYPHS[_canon].alias = tuple(dict.fromkeys(tuple(GLYPHS[_canon].alias) + _names))
