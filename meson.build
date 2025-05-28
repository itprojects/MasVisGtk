project('masvisgtk',
    version: '4.0.2',
    license: ['GPL-2.0'],
    meson_version: '>= 0.62.0',
    default_options: [ 'warning_level=2', 'werror=false', ],
)

python = import('python')
py_installation = python.find_installation('python3')
if not py_installation.found()
    error('No valid python3 binary found')
endif
if not py_installation.language_version().version_compare('>= 3.11')
    error('Python 3.11 or newer is required.')
endif

i18n = import('i18n')
gnome = import('gnome')
dependency('libadwaita-1', version: '>= 1.5')

subdir('data')
subdir('src')
subdir('po')

gnome.post_install(
    glib_compile_schemas: true,
    gtk_update_icon_cache: true,
    update_desktop_database: true,
)
