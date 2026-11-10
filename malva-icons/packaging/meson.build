project('malva-icons', version : '0.2.0', license : 'GPL-3.0-or-later', meson_version : '>= 0.60.0')

py = import('python').find_installation('python3')
icons_dir = get_option('datadir') / 'icons'

meson.add_install_script(
  py.full_path(),
  meson.current_source_dir() / '..' / 'tools' / 'icons' / 'install_theme.py',
  '--source', meson.current_source_dir() / '..' / 'assets' / 'icons' / 'Malva',
  '--dest', get_option('prefix') / icons_dir,
)
