desktop_file = i18n.merge_file(
        input: 'io.github.itprojects.MasVisGtk.desktop.in',
       output: 'io.github.itprojects.MasVisGtk.desktop',
         type: 'desktop',
       po_dir: '../po',
      install: true,
  install_dir: get_option('datadir') / 'applications'
)

desktop_utils = find_program('desktop-file-validate', required: false)
if desktop_utils.found()
  test('Validate desktop file', desktop_utils, args: [desktop_file])
endif

appstream_file = i18n.merge_file(
        input: 'io.github.itprojects.MasVisGtk.metainfo.xml.in',
       output: 'io.github.itprojects.MasVisGtk.metainfo.xml',
       po_dir: '../po',
      install: true,
  install_dir: get_option('datadir') / 'metainfo'
)

appstreamcli = find_program('appstreamcli', required: false)
test('Validate appstream file', appstreamcli,
     args: ['validate', '--no-net', '--explain', appstream_file])

gnome.compile_schemas(build_by_default: true)

test('Validate schema file',
     find_program('glib-compile-schemas', required: false),
     args: ['--strict', '--dry-run', meson.current_source_dir()])

install_data('io.github.itprojects.MasVisGtk.gschema.xml',
  install_dir: join_paths(get_option('datadir'), 'glib-2.0/schemas')
)

subdir('icons')
