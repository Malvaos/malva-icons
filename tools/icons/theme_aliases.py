"""Standard icon names that are served by another icon's drawing.

The theme stores every drawing once, under one canonical name. Toolkits ask for names from the freedesktop naming
list (GNOME, Qt and Slint apps all do), and several of those names mean the same picture: an SSD and a hard disk are
both "a drive", a CD, a DVD and a Blu-ray are all "a disc". install_theme.py links each alias to its canonical file;
build_theme.py writes the same table into the manifest. The map is checked against the files by check_theme.py.
"""

# standard name -> object id (coloured file and one-colour cut both follow)
OBJECT_ALIASES = {
    "inode-directory": "folder",
    "folder-visiting": "folder-open",
    "drive-harddisk-system": "drive-internal",
    "drive-harddisk-solidstate": "drive-internal",
    "drive-multidisk": "drive-internal",
    "drive-optical": "optical-disc",
    "media-optical-bd": "optical-disc",
    "media-optical-cd": "optical-disc",
    "media-optical-cd-audio": "optical-disc",
    "media-optical-dvd": "optical-disc",
    "drive-removable-media": "usb-stick",
    "media-removable": "usb-stick",
}

# standard name -> app id
APP_ALIASES = {
    "start-here": "launcher",
}


def alias_names():
    return set(OBJECT_ALIASES) | set(APP_ALIASES)
