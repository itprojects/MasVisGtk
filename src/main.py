#!/usr/bin/python3

'''
MasVisGtk UI Application

Audio Quality Analysis of files in folders.

Based on source code from https://github.com/joakimfors/PyMasVis
Based on source code commit: 657196232bcb88f3e335e4be853218329c770a1d

Copyright 2024 ITProjects

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import gi, os, sys, time, gc

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw, Gtk, Gdk, Gio, GLib, Pango, GObject

import locale
import logging
import traceback

from . import __version__
from .async_render import *
from .main_gtk_window import *
from .main_original import main_pymasvis # original module for cli
from .analysis import analyze
from .input import file_formats, load_file
from .output_gtk import list_styles, render, save_figure
from .utils import Steps, Timer

log = logging.getLogger('pymasvis')
lh = logging.StreamHandler(sys.stdout)
lh.setFormatter(logging.Formatter('%(message)s'))
log.addHandler(lh)
log.setLevel(logging.WARNING)

class MasVisGtk(Adw.Application):

    DEBUG = False
    VERSION = __version__

    app_name = _('MasVisGtk')
    win = None

    # Translations widget preferences.
    language_dict = {
        'Belarusian': 'be_BY.utf8', 'Bulgarian': 'bg_BG.utf8', 'Czech': 'cs_CZ.utf8', 'Danish': 'da_DK.utf8', 'German': 'de_DE.utf8', 'Greek': 'el_GR.utf8',
        'English (Canada)': 'en_CA.utf8', 'English (Britain)': 'en_GB.utf8', 'English (America)': 'en_US.utf8', 'Spanish': 'es_ES.utf8',
        'Estonian': 'et_EE.utf8', 'Farsi': 'fa_IR.utf8', 'Finnish': 'fi_FI.utf8', 'French': 'fr_FR.utf8',  'Hebrew': 'he_IL.utf8', 'Hindi': 'hi_IN.utf8',
        'Croatian': 'hr_HR.utf8', 'Hungarian': 'hu_HU.utf8', 'Icelandic': 'is_IS.utf8', 'Italian': 'it_IT.utf8', 'Japanese': 'ja_JP.utf8', 'Georgian': 'ka_GE.utf8',
        'Kazakh': 'kk_KZ.utf8', 'Korean': 'ko_KR.utf8', 'Lithuanian': 'lt_LT.utf8', 'Latvian': 'lv_LV.utf8', 'Norwegian (Bokmål)': 'nb_NO.utf8', 'Nepali': 'ne_NP.utf8',
        'Dutch': 'nl_NL.utf8', 'Polish': 'pl_PL.utf8', 'Portugues (Brazil)': 'pt_BR.utf8', 'Portugues': 'pt_PT.utf8',  'Romanian': 'ro_RO.utf8', 'Russian': 'ru_RU.utf8',
        'Slovakian': 'sk_SK.utf8', 'Slovenian': 'sl_SI.utf8', 'Serbian': 'sr_RS.utf8', 'Swedish': 'sv_SE.utf8', 'Turkish': 'tr_TR.utf8', 'Ukrainian': 'uk_UA.utf8',
        'Vietnamese': 'vi_VN.utf8', 'Chinese (Mainland)': 'zh_CN.utf8', 'Chinese (Taiwan)': 'zh_TW.utf8'
    }

    pref_language_locale = GObject.Property(type=str, default='en_GB.utf8')
    pref_app_style = GObject.Property(type=int, default=0) # follow system (0), light (1), dark (2)
    pref_matplotlib_style = GObject.Property(type=str, default='fast')
    pref_custom_background = GObject.Property(type=bool, default=False)
    pref_custom_background_value = GObject.Property(type=str, default='#FDF6E3')
    pref_custom_font = GObject.Property(type=bool, default=False)
    pref_custom_font_value = GObject.Property(type=str, default='FreeMono Bold 16')
    pref_save_format = GObject.Property(type=int, default=0) # 0=png, 1=jpeg, 2=svg, 3=webp, 4=tiff, 5=pdf, 6=eps
    pref_dpi_application = GObject.Property(type=int, default=100)
    pref_dpi_image = GObject.Property(type=int, default=200)

    settings = None # holds Gio.Settings for schema

    dialog_spinner = None
    spinbox = None # shows processing progress
    ops_cancellable = None # cancel processing

    infiles = None
    bad_inputs = None
    formats = None
    r128_unit = None
    overview_mode = None
    recursive_scan = False

    def __init__(self, VERSION, SETTINGS_in, *args, **kwargs):
        super().__init__(
            *args,
            application_id='io.github.itprojects.MasVisGtk',
            flags=Gio.ApplicationFlags.HANDLES_OPEN|Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
            **kwargs
        )

        # Override defaults with user preferences.
        if SETTINGS_in:
            self.settings = SETTINGS_in
            self.settings = Gio.Settings.new('io.github.itprojects.MasVisGtk')

            self.pref_language_locale = self.settings.get_string('language-locale')
            self.pref_custom_background = self.settings.get_boolean('custom-background')
            self.pref_custom_background_value = self.settings.get_string('custom-background-value')
            self.pref_app_style = self.settings.get_enum('app-style')
            self.pref_matplotlib_style = self.settings.get_string('matplotlib-style')
            self.pref_custom_font = self.settings.get_boolean('custom-font')
            self.pref_custom_font_value = self.settings.get_string('custom-font-value')
            self.pref_save_format = self.settings.get_enum('save-format')
            self.pref_dpi_application = self.settings.get_int('dpi-application')
            self.pref_dpi_image = self.settings.get_int('dpi-image')

            self.settings.bind('language-locale', self, 'pref_language_locale', Gio.SettingsBindFlags.DEFAULT)
            self.settings.bind('matplotlib-style', self, 'pref_matplotlib_style', Gio.SettingsBindFlags.DEFAULT)
            self.settings.bind('custom-background', self, 'pref_custom_background', Gio.SettingsBindFlags.DEFAULT)
            self.settings.bind('custom-background-value', self, 'pref_custom_background_value', Gio.SettingsBindFlags.DEFAULT)
            self.settings.bind('custom-font', self, 'pref_custom_font', Gio.SettingsBindFlags.DEFAULT)
            self.settings.bind('custom-font-value', self, 'pref_custom_font_value', Gio.SettingsBindFlags.DEFAULT)
            self.settings.bind('dpi-application', self, 'pref_dpi_application', Gio.SettingsBindFlags.DEFAULT)
            self.settings.bind('dpi-image', self, 'pref_dpi_image', Gio.SettingsBindFlags.DEFAULT)

            # Debug information.
            log.debug(f'schema language-locale: { self.pref_language_locale }')
            log.debug(f'schema custom-background: { self.pref_custom_background }')
            log.debug(f'schema custom-background-value: { self.pref_custom_background_value }')
            log.debug(f'schema app-style: { self.pref_app_style }')
            log.debug(f'schema matplotlib-style: { self.pref_matplotlib_style }')
            log.debug(f'schema custom-font: { self.pref_custom_font }')
            log.debug(f'schema custom-font-value: { self.pref_custom_font_value }')
            log.debug(f'schema save-format: { self.pref_save_format }')
            log.debug(f'schema dpi-application: { self.pref_dpi_application }')
            log.debug(f'schema dpi-image: { self.pref_dpi_image }')
        else:
            print(_('No gschema file for preferences. Using defaults.'))

        # Set custom application language/locale.
        try:
            locale.setlocale(locale.LC_ALL, self.pref_language_locale)
        except locale.Error as ll:
            # System package is required.
            log.warning(_('Cannot set locale ' + str(ll)) + ' ' + str(self.pref_language_locale))

        self.set_version(VERSION)
        self.set_option_context_parameter_string(_('FILES/FOLDERS'))
        self.set_option_context_summary(
            _('  FILE(S) and/or FOLDER(S) paths to process inside the application\n\n  MasVisGtk is an audio file analysis application.')
        )
        self.set_option_context_description(
            _('The original python module is also available with this package.\nThe command line options are different from the original.\nLarge file are always slow to render.')
        )

        # Command line options.
        self.add_main_option(
            'version',
            ord('v'),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            _('Version of MasVisGtk.'),
            None,
        )

        self.add_main_option(
            'verbose',
            ord('b'),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            _('Show Verbose Messages.'),
            None,
        )

        self.add_main_option(
            'debug',
            ord('d'),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            _('Show Debug Messages.'),
            None,
        )

        self.add_main_option(
            'formats',
            ord('f'),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            _('Show Supported [FFMPEG] Formats.'),
            None,
        )

        self.add_main_option(
            'LU',
            ord('l'),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            _('Use [LU], instead of [LUFS], when displaying R128 values, (default: LUFS).'),
            None,
        )

        self.add_main_option(
            'overview-mode',
            ord('o'),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.STRING,
            _('flat, generate one overview tab for all, or dir, for one tab for folders, (default: flat).'),
            None,
        )

        self.add_main_option(
            'recursive',
            ord('r'),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.NONE,
            _('If input is a folder, process subfolders, too.'),
            None,
        )

        self.add_main_option(
            GLib.OPTION_REMAINING,
            0,
            GLib.OptionFlags.NONE,
            GLib.OptionArg.STRING_ARRAY,
            _('FILE(S) or FOLDER(S)'),
            None,
        )

    def do_startup(self):
        Adw.Application.do_startup(self)

        #
        # Menu actions.
        #

        self.help_action = Gio.SimpleAction.new('help_action', None)
        self.help_action.connect('activate', self.on_action_start, 10)
        self.add_action(self.help_action)

        self.open_menu_action = Gio.SimpleAction.new('open_menu_action', None)
        self.open_menu_action.connect('activate', self.on_action_start, 20)
        self.add_action(self.open_menu_action)

        self.shortcuts_action = Gio.SimpleAction.new('shortcuts_action', None)
        self.shortcuts_action.connect('activate', self.on_action_start, 30)
        self.add_action(self.shortcuts_action)

        self.quit_action = Gio.SimpleAction.new('quit_action', None)
        self.quit_action.connect('activate', self.on_close_request)
        self.add_action(self.quit_action)

        self.simple_open_action = Gio.SimpleAction.new('simple_open_action', None)
        self.simple_open_action.connect('activate', self.on_action_start, 40)
        self.add_action(self.simple_open_action)

        self.advanced_open_action = Gio.SimpleAction.new('advanced_open_action', None)
        self.advanced_open_action.connect('activate', self.on_action_start, 50)
        self.add_action(self.advanced_open_action)

        self.save_action = Gio.SimpleAction.new('save_action', None)
        self.save_action.connect('activate', self.on_action_start, 60)
        self.add_action(self.save_action)

        self.save_all_action = Gio.SimpleAction.new('save_all_action', None)
        self.save_all_action.connect('activate', self.on_action_start, 70)
        self.add_action(self.save_all_action)

        self.preferences_action = Gio.SimpleAction.new('preferences_action', None)
        self.preferences_action.connect('activate', self.on_show_preferences)
        self.add_action(self.preferences_action)

        self.formats_action = Gio.SimpleAction.new('formats_action', None)
        self.formats_action.connect('activate', self.on_action_start, 80)
        self.add_action(self.formats_action)

        self.about_action = Gio.SimpleAction.new('about_action', None)
        self.about_action.connect('activate', self.on_action_start, 90)
        self.add_action(self.about_action)

        self.fullscreen_action = Gio.SimpleAction.new('fullscreen_action', None)
        self.fullscreen_action.connect('activate', self.on_action_start, 100)
        self.add_action(self.fullscreen_action)

        self.file_information_action = Gio.SimpleAction.new('file_information_action', None)
        self.file_information_action.connect('activate', self.on_action_start, 110)
        self.add_action(self.file_information_action)

        #
        # Shortcut keys.
        #

        self.set_accels_for_action('app.help_action',  ['F1'])
        self.set_accels_for_action('app.open_menu_action', ['F10'])
        self.set_accels_for_action('app.fullscreen_action', ['F11'])
        self.set_accels_for_action('app.shortcuts_action', ['<Control>question'])
        self.set_accels_for_action('app.quit_action', ['<Control>q'])
        self.set_accels_for_action('app.simple_open_action', ['<Control>o'])
        self.set_accels_for_action('app.advanced_open_action', ['<Shift>o'])
        self.set_accels_for_action('app.save_action', ['<Control>s'])
        self.set_accels_for_action('app.save_all_action', ['<Shift>s'])
        self.set_accels_for_action('app.file_information_action', ['<Control>i'])

    def on_change_app_style(self):
        match self.pref_app_style:
            case 1: # (1) light
                Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
            case 2: # (2) dark
                Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK)
            case _: # (0) follow system
                Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.DEFAULT)

    def do_activate(self):
        self.on_change_app_style()
        self.win = self.props.active_window
        if not self.win:
            self.win = PyPlotWindow(self.app_name, application=self)
            self.win.connect('close-request', self.on_close_request)
            css_provider = Gtk.CssProvider()
            css_provider.load_from_resource('/io/github/itprojects/MasVisGtk/style.css')
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(),
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        self.win.present()

    def do_command_line(self, command_line):
        options = command_line.get_options_dict()
        options = options.end().unpack()

        recursive_scan = False
        self.formats = None

        if 'version' in options:
            print(_('MasVisGtk Version ') + str(VERSION))
            return 0
        if 'verbose' in options:
            log.setLevel(logging.INFO)
        if 'debug' in options:
            self.DEBUG = True
            log.setLevel(logging.DEBUG)
        if 'formats' in options:
            self.formats = file_formats()
            print(_('FFMPEG Formats: ') + str(self.formats))
            return 0
        if 'LU' in options:
            self.r128_unit = 'LU'
        else:
            self.r128_unit = 'LUFS'
        if 'overview-mode' in options:
            mode = options['overview-mode']
            if mode == 'dir' or mode == 'flat':
                self.overview_mode = mode
            else:
                print(f'{mode}' + _('is not possible with option -o. Try dir or flat.'))
                return 0
        else:
            self.overview_mode = None
        if 'recursive' in options:
            self.recursive_scan = True

        # App must first show window, but matplotlib slows that.
        # Detect no window exists (app start) to create window.
        # Only then process audio.
        no_window_in_sight = self.win is None

        # Activate/create window, once.
        self.activate()

        # Check for inputs.
        inputs = None
        try:
            inputs = options[GLib.OPTION_REMAINING]
            self.open_async(inputs)
        except:
            log.debug(_('No input files or folders supplied.'))

        return 0

    def open_async(self, inputs):
        infiles = []
        bad_inputs = []
        if inputs:
            # Get command line file and/or folder inputs.
            try:
                for f in inputs:
                    if os.path.isfile(f):
                        # Check read permission.
                        if not os.access(f, os.R_OK):
                            log.warning(_(f'Bad permisions for file. ') + f'[{f}]')
                            continue
                        # Check audio, video mimetype.
                        list_file_mimetype = self.guess_mimetype(f)
                        if not list_file_mimetype:
                            continue
                        if not list_file_mimetype.lower().startswith('audio/'):
                            error = str(list_file_mimetype) + '\n' + _('This file is not an audio file.') + f'\n[{f}]'
                            log.warning(error)
                            self.on_error_dialog(_('Cannot process file.'), error)
                            continue
                        infiles.append(f)
                        continue
                    if os.path.isdir(f):
                        for root, dirs, files in os.walk(f):
                            for name in files:
                                if os.path.splitext(name)[1][1:] in self.formats:
                                    infiles.append(os.path.join(root, name))
                            if not self.recursive_scan:
                                del dirs[:]
                    else:
                        log.warning(_('Bad input: ') + f)
                        bad_inputs.append(f)
            except Exception as e:
                log.warning(_('Error processing files: ') + f'{e}\n {traceback.format_exc()}')

        self.infiles = infiles
        self.bad_inputs = bad_inputs

        # Pre-masvis check
        if self.bad_inputs and len(self.bad_inputs) > 0:
            log.warning(_('Bad input files: ') + f'{self.bad_inputs}')
            bad_inputs_ = '\n\n'.join(self.bad_inputs)
            self.on_error_dialog(_('Problem Files'), _('Ignoring bad input files:') + f'\n\n{bad_inputs_}')
            return
        n_infiles = len(self.infiles)
        if self.infiles == None or n_infiles < 1:
            error = _('No valid files found!')
            log.warning(error)
            self.on_error_dialog(_('No Files'), error)
            return

        # Begin processing audio. Plot asynchronously, not blocking UI.
        self.spinning_dialog()
        self.ops_cancellable = Gio.Cancellable()
        data = (self.infiles, n_infiles, self.overview_mode, self)
        async_worker = AsyncWorker(
            operation=self.masvis_process,
            operation_inputs=data,
            operation_callback=self.async_finished,
            cancellable=self.ops_cancellable
        )
        async_worker.start()

    # Blocking IO to find file mimetype consistently.
    def guess_mimetype(self, file_path):
        file = Gio.File.new_for_path(file_path)
        try:
            info = file.query_info('standard::content-type', Gio.FileQueryInfoFlags.NONE, None)
            mime_type = info.get_content_type()
            return mime_type
        except Exception as e:
            log.warning(_('Unknown mimetype: ') + f'{e}')
            self.on_error_dialog(_('Unknown Mimetype'), _('Skipping file: ') + f'{file_path}')
            return None

    # Starts spinning dialog.
    def spinning_dialog(self):
        self.dialog_spinner = Adw.Dialog()
        self.dialog_spinner.set_follows_content_size(True) # Adw size problems.
        self.dialog_spinner.set_title(_('Processing'))
        self.dialog_spinner.set_can_close(False)
        self.dialog_spinner.connect('close-attempt', self.spinning_dialog_response)

        headerbar = Adw.HeaderBar()
        box = Gtk.Box()
        box.props.orientation = Gtk.Orientation.VERTICAL
        box.append(headerbar)

        # Append spinning widget showing progress.
        self.spinbox = SpinBox(self.win)
        self.spinbox.dialog_spinner = self.dialog_spinner
        box.append(self.spinbox)
        headerbar.pack_start(self.spinbox.spinner)
        self.dialog_spinner.set_child(box)
        self.dialog_spinner.present(self.win)

    def spinning_dialog_response(self, dialog):
        if self.ops_cancellable != None:
            self.ops_cancellable.cancel()
        if self.spinbox != None:
            self.spinbox.stop(None)
            self.spinbox = None
        dialog.force_close()

    def check_cancellations(self):
        return self.ops_cancellable == None or self.ops_cancellable.is_cancelled()

    def async_finished(self, worker, gio_result, handler_data):
        if not self.check_cancellations():
            outcome = worker.return_value(gio_result)
            if outcome != None:
                self.on_error_dialog(_('AsyncWorkerError'), outcome['AsyncWorkerError'])
        if self.spinbox != None:
            self.spinbox.dialog_spinner.close()

    # Open/process selected files callback.
    def on_open_dialog_cb(self, dialog, response):
        try:
            list_returned = None
            # Simple files open.
            if dialog.list_store_paths == None:
                list_returned = dialog.open_multiple_finish(response)
                pylist_infiles = []
                if list_returned is not None:
                    for list_file in list_returned:
                        pylist_infiles.append(list_file.get_path())
                    self.open_async(pylist_infiles)
            else:
                # Pass the list, open later.
                if dialog.files_or_folders:
                    list_returned = dialog.open_multiple_finish(response)
                else:
                    list_returned = dialog.select_multiple_folders_finish(response)
                pylist_infiles = []
                if list_returned is not None:
                    for list_file in list_returned:
                        # Checking if path already exists.
                        for i in range(0, dialog.list_store_paths.get_n_items()):
                            if list_file == dialog.list_store_paths.get_item(i).path:
                                log.debug(_('Duplicate path: ') + f'{list_file}')
                                continue
                        dialog.list_store_paths.insert(0, StringPath(list_file.get_path(), list_file.get_basename()))
        except GLib.GError:
            pass # Ignore cancel: 'gtk-dialog-error-quark: Dismissed by user'
        except Exception as e:
            error = _('Error in Opening')
            log.warning(f'{error}: {e}')
            self.on_error_dialog(error, e)

    def on_save_one_init(self):
        # Check we tabs exist.
        if self.win.tab_view.get_n_pages() > 0:
            self.win.on_save_dialog(None)

    def on_save_one_dialog_cb(self, dialog, response):
        try:
            # 0=png, 1=jpeg, 2=svg, 3=webp, 4=tiff, 5=pdf, 6=eps
            save_format = 'PNG'
            if dialog.filter_formats_widget:
                save_format = self.on_parse_format(dialog.filter_formats_widget.get_selected())
            else:
                log.warning(_('Cannot detect save file format, defaulting to png.'))

            # GLocalFile of save location.
            save_file = dialog.save_finish(response)

            # Check path writeable.
            if not os.access(save_file.get_parent().get_path(), os.W_OK):
                error = f'{save_file.get_path()} ' + _('is not writeable.')
                log.warning(error)
                self.on_error_dialog(_('Permissions'), error)
                return

            pyplot_canvas = self.win.tab_view.get_selected_page().get_child().scrolled.get_child()
            if pyplot_canvas == None:
                return # Empty tab.

            # backend_gtk4agg.FigureCanvasGTK4Agg
            pyplot_canvas = pyplot_canvas.get_child().get_last_child()

            save_figure(pyplot_canvas.figure, save_file.get_path(), save_format, self.pref_dpi_image)
        except GLib.GError:
            pass # Ignore cancel: 'gtk-dialog-error-quark: Dismissed by user'

    def on_save_multiple_init(self):
        # Check we tabs exist.
        if self.win.tab_view.get_n_pages() < 1:
            return
        self.win.on_save_multiple_dialog()

    def on_save_multiple_dialog_cb(self, dialog, response):
        try:
            # 0=png, 1=jpeg, 2=svg, 3=webp, 4=tiff, 5=pdf, 6=eps
            save_format = 0
            if dialog.filter_formats_widget:
                save_format = dialog.filter_formats_widget.get_selected()
            else:
                log.warning(_('Cannot detect save file format, defaulting to png.'))

            # GLocalFile of save location.
            save_folder = dialog.select_folder_finish(response).get_path()

            # Check path writeable.
            if not os.access(save_folder, os.W_OK):
                error = f'{save_folder}'+ _(' is not writeable.')
                log.warning(error)
                self.on_error_dialog(_('Permissions'), error)
                return

            future_folder = save_folder + '/masvis'
            if os.path.exists(future_folder):
                n = 1
                while os.path.exists(future_folder + f' ({n})'):
                    n += 1
                future_folder = f'{future_folder} ({n})'

            # Create folder for images.
            os.makedirs(future_folder)

            # Begin saving plots asynchronously, not blocking UI.
            self.spinning_dialog()
            self.ops_cancellable = Gio.Cancellable()
            # Pass as list, avoiding conversion of chars to args!
            data = (future_folder, save_format)
            async_worker = AsyncWorker(
                operation=self.on_save_multiple_async,
                operation_inputs=data,
                operation_callback=self.async_finished,
                cancellable=self.ops_cancellable
            )
            async_worker.start()
        except GLib.GError:
            pass # Ignore cancel: 'gtk-dialog-error-quark: Dismissed by user'

    def on_save_multiple_async(self, future_folder, save_format_int, *args):
        # Get chosen format.
        save_format = self.on_parse_format(save_format_int)

        # Write files.
        n_th_file = 0
        n_tabs = self.win.tab_view.get_n_pages()
        for t in self.win.tab_view.get_pages():
            pyplot_canvas = t.get_child().scrolled.get_child()
            if pyplot_canvas == None:
                continue # Empty tab.

            # backend_gtk4agg.FigureCanvasGTK4Agg
            pyplot_canvas = pyplot_canvas.get_child().get_last_child()

            # Necessary to check width minimum.
            # If less than 1080, figure is broken.
            # Set plot page, and wait for plot to display.
            if pyplot_canvas.figure.get_figwidth() * self.pref_dpi_application < 1080:
                self.win.tab_view.set_selected_page(t)
                time.sleep(2.0)

            n_th_file += 1

            # Go up, to get tabbox a_file.
            a_file_name = t.get_child().scrolled.get_child().get_parent().get_parent().a_file.file_name
            save_file = f'{n_th_file}. {a_file_name}'

            if n_th_file == 1:
                GLib.idle_add(self.spinbox.start, n_th_file, n_tabs, a_file_name)
            else:
                if self.spinbox != None:
                    self.spinbox.set_label(n_th_file, n_tabs, a_file_name)

            save_figure(pyplot_canvas.figure, f'{future_folder}/{save_file}.{save_format}', save_format, self.pref_dpi_image)

    def on_parse_format(self, save_format_int):
        match save_format_int:
            case 0:
                return 'png'
            case 1:
                return 'jpeg'
            case 2:
                return 'svg'
            case 3:
                return 'webp'
            case 4:
                return 'tiff'
            case 5:
                return 'pdf'
            case 6:
                return 'eps'
            case _:
                return 'png' # default

    def on_show_preferences(self, action, param):
        builder = Gtk.Builder()
        obj = builder.new_from_resource('/io/github/itprojects/MasVisGtk/gtk/preferences-overlay.ui')
        shortcuts_window = obj.get_object('preferences_overlay')
        shortcuts_window.set_transient_for(self.win)
        shortcuts_window.present()

        # Set user schema valuess into Adw.PreferencesWindow.
        # Set callbacks, if the values are changed.

        # Get language.
        language_index = None
        for index, (k, v) in enumerate(self.language_dict.items()):
            if v == self.pref_language_locale:
                language_index = index
                break
        if language_index == None:
            language_index = 7 # en_GB.utf8

        # Set language.
        obj.get_object('dropdown_language').set_selected(language_index)
        obj.get_object('dropdown_language').connect('notify::selected', self.on_schema_changed_language_locale)

        obj.get_object('dropdown_app_style').set_selected(self.pref_app_style)
        obj.get_object('dropdown_app_style').connect('notify::selected', self.on_schema_changed_app_style)

        # Get Matplotlib styles.
        styles = list_styles()
        string_list = None
        if len(styles) > 0:
            string_list = Gtk.StringList()
            string_list.splice(0, 0, styles) # add array
            obj.get_object('dropdown_matplotlib_style').set_model(string_list)

        # Set Matplotlib style.
        if self.pref_matplotlib_style in styles:
            index = styles.index(self.pref_matplotlib_style)
            if index > -1:
                obj.get_object('dropdown_matplotlib_style').set_selected(index)

        # Set callback for Matplotlib style changes.
        obj.get_object('dropdown_matplotlib_style').connect('notify::selected', self.on_schema_changed_matplotlib_style)

        # Parse and set RGBA.
        clr = Gdk.RGBA()
        clr.parse(self.pref_custom_background_value)
        clr_dialog_btn = obj.get_object('background_button')
        clr_dialog_btn.set_rgba(clr)

        # Changed RGBA, update variables.
        clr_dialog_btn.connect('notify::rgba', self.on_schema_changed_custom_background_value)

        # Custom background off/on.
        obj.get_object('background_button_switch').set_active(self.pref_custom_background)
        obj.get_object('background_button_switch').connect('notify::active', self.on_schema_changed_custom_background)

        # Parse and set font.
        obj.get_object('font_button').set_font_desc(Pango.FontDescription.from_string(self.pref_custom_font_value))
        obj.get_object('font_button').connect('notify::font-desc', self.on_schema_changed_custom_font_value)

        obj.get_object('font_button_switch').set_active(self.pref_custom_font)
        obj.get_object('font_button_switch').connect('notify::active', self.on_schema_changed_custom_font)

        obj.get_object('dropdown_format').set_selected(self.pref_save_format)
        obj.get_object('dropdown_format').connect('notify::selected', self.on_schema_changed_save_format)

        obj.get_object('dpi_application').set_value(self.pref_dpi_application)
        obj.get_object('dpi_application').connect('changed', self.on_schema_changed_dpi_application)

        obj.get_object('dpi_image').set_value(self.pref_dpi_image)
        obj.get_object('dpi_image').connect('changed', self.on_schema_changed_dpi_image)

    def on_schema_changed_language_locale(self, gtk_dropdown, param):
        value = self.language_dict[gtk_dropdown.get_selected_item().get_string()]
        self.settings.set_string('language-locale', value)
        self.pref_language_locale = value

    def on_schema_changed_app_style(self, gtk_dropdown, param):
        value = gtk_dropdown.get_selected()
        self.settings.set_enum('app-style', value)
        self.pref_app_style = value
        self.on_change_app_style() # change style

    def on_schema_changed_matplotlib_style(self, gtk_dropdown, param):
        value = gtk_dropdown.get_model().get_item(gtk_dropdown.get_selected()).get_string()
        self.settings.set_string('matplotlib-style', value)
        self.pref_matplotlib_style = value

    def on_schema_changed_custom_background_value(self, gtk_color_dialog_button, rgba):
        value = self.rgba_to_text(gtk_color_dialog_button.get_rgba())
        self.settings.set_string('custom-background-value', value)
        self.pref_custom_background_value = value

    def on_schema_changed_custom_background(self, adw_switchrow, param):
        value = adw_switchrow.get_active()
        self.settings.set_boolean('custom-background', value)
        self.pref_custom_background = value

    def on_schema_changed_custom_font_value(self, gtk_font_dialog_btn, font_desc):
        value = gtk_font_dialog_btn.get_font_desc().to_string()
        self.settings.set_string('custom-font-value', value)
        self.pref_custom_font_value = value

    def on_schema_changed_custom_font(self, adw_switchrow, param):
        value = adw_switchrow.get_active()
        self.settings.set_boolean('custom-font', value)
        self.pref_custom_font = value

    def on_schema_changed_save_format(self, gtk_dropdown, param):
        value = gtk_dropdown.get_selected()
        self.settings.set_enum('save-format', value)
        self.pref_save_format = value

    def on_schema_changed_dpi_application(self, adw_spinrow):
        value = adw_spinrow.get_value()
        self.settings.set_int('dpi-application', value)
        self.pref_dpi_application = value

    def on_schema_changed_dpi_image(self, adw_spinrow):
        value = adw_spinrow.get_value()
        self.settings.set_int('dpi-image', value)
        self.pref_dpi_image = value

    def rgba_to_text(self, rgba):
        r = int(rgba.red * 255)
        g = int(rgba.green * 255)
        b = int(rgba.blue * 255)
        return f'#{r:02x}{g:02x}{b:02x}'.upper()

    # Handle app actions, located in window class.
    def on_action_start(self, action, param, param_value):
        if param_value != None:
            match param_value:
                case 10: # help
                    self.win.on_show_manual_dialog()
                case 20: # open menu
                    self.win.on_open_menu()
                case 30: # shortcuts window
                    self.win.on_show_shortcuts()
                case 40: # simple files open
                    self.win.on_open_dialog(None, None, True)
                case 50: # advanced open
                    self.win.on_open_advanced_dialog(None)
                case 60: # save current tab
                    self.on_save_one_init()
                case 70: # save all tabs
                    self.on_save_multiple_init()
                case 80: # formats
                    self.win.on_show_formats_dialog()
                case 90: # about
                    self.win.on_show_about_dialog()
                case 100: # fullscreen
                    if self.win.is_fullscreen():
                        self.win.unfullscreen()
                    else:
                        self.win.fullscreen()
                case 110: # file information
                    self.win.on_file_information()
                case _:
                    pass

    # Show error dialog on UI thread, without crash.
    def on_error_dialog(self, heading, body):
        GLib.idle_add(self.on_error_dialog_present, heading, body)

    def on_error_dialog_present(self, heading, body):
        dialog_err = Adw.MessageDialog(
            transient_for = self.win,
            heading = heading,
            body = f'{body}'
        )
        dialog_err.add_response('cancel',  _('Close'))
        dialog_err.present()

    def on_close_request(self, action, *args):
        self.quit()
        return True

    def masvis_process(self, infiles, n_infiles, overview_mode, app):
        try:
            dirs = []
            files = []

            # Prepare files for processing.
            for infile in self.infiles:
                files.append(FileDetails(infile, os.path.basename(infile), os.path.dirname(infile), self.r128_unit))

            if overview_mode == None or overview_mode == 'flat':
                # All-in-one dir.
                dirs.append(FileDetails('', '', '', self.r128_unit))
            else: # 'dir'
                # Collect unique dirs.
                dirs = [f.file_parent_folder for f in files]
                dirs = list(set(dirs))

            tab = None
            n_th_file = 0
            for dir in dirs:
                # Add new overview folder tab.
                if overview_mode == 'dir':
                    audio_folder = FileDetails(dir, os.path.basename(dir), '', self.r128_unit)
                    tab = self.win.add_tab(audio_folder, 'dir')
                elif overview_mode == 'flat' and tab == None:
                    audio_folder = FileDetails('', 'overview', '', self.r128_unit)
                    tab = self.win.add_tab(audio_folder, 'flat')

                # Start processing files.
                for audio_file in files:
                    if overview_mode == 'dir' and audio_file.file_parent_folder != dir:
                        # File is not in dir, but overview_mode is dir.
                        continue

                    n_th_file += 1

                    if self.check_cancellations():
                        return

                    if n_th_file == 1:
                        GLib.idle_add(self.spinbox.start, n_th_file, n_infiles, audio_file.file_name)
                    else:
                        GLib.idle_add(self.spinbox.set_label, n_th_file, n_infiles, audio_file.file_name)

                    # Add new detailed tab.
                    if overview_mode == None:
                        tab = self.win.add_tab(audio_file, None)
                    log.debug('Opening file %s', infile)
                    self.masvis_process_file(audio_file, self.r128_unit, overview_mode, tab)
        except Exception as e:
            trace = traceback.format_exc()
            error = f'{e}\n{infile}\n{trace}'
            log.warning(error)

            self.ops_cancellable.cancel()

            # Change spinning dialog for error.
            self.on_error_dialog(_('Opening File Error'), error)
            error_label = Gtk.Label(
                label='<span color="red" size="x-large" weight="bold">' + _('Errors in Processing!') + '</span>',
                use_markup=True, hexpand=True, halign=Gtk.Align.CENTER, margin_start=15, margin_end=15, margin_top=15, margin_bottom=15
            )
            box = self.dialog_spinner.get_child()
            box.append(error_label)

    def masvis_process_file(self, audio_file, r128_unit, overview_mode=False, tab=None):
        header = None
        loader = None
        loader_args = []

        if os.path.isfile(audio_file.file_path):
            log.debug('Selecting file loader')
            loader = load_file
            loader_args = [audio_file.file_path]
        else:
            log.warning(_('Unable to open input ') + audio_file.file_path)
            self.on_error_dialog(_('Cannot Open File'), audio_file.file_path)
            return
        track = loader(*loader_args)

        if type(track) is int:
            return

        # Minimum track duratio => 3 seconds.
        if track['duration'] < 3:
            err_duration = _('The minimum file duration is 3 seconds.') + f'\n[{audio_file.file_path}]'
            log.warning(_('Unable to open input '), audio_file.file_path)
            self.on_error_dialog(_('File Error'), err_duration)
            return

        # File output from FFMPEG.
        audio_file.track = track['raw_meta']

        if not header:
            header = '%s' % (track['metadata']['name'])

        with Timer('Running...', Steps.total, Steps.callback):
            with Timer('Analyzing...'):
                analysis = analyze(track, callback=Steps.callback)
            with Timer('Rendering...'):
                # Main rendering on canvas.
                render(
                    track,
                    analysis,
                    header,
                    r128_unit=r128_unit,
                    overview_mode=overview_mode,
                    callback=Steps.callback,
                    tab_page=tab, # Gtk.Widget for plotted figure
                    win=self.win,
                )
        Steps.report()
        gc.collect() # free RAM

def main(VERSION, SETTINGS_in):
    if len(sys.argv) > 1 and sys.argv[1] == '--pymasvis':
        # Remove redirection argument.
        sys.argv.remove(sys.argv[1])

        # Run original module.
        main_pymasvis()
    else:
        # Run Gtk UI app.
        app = MasVisGtk(VERSION, SETTINGS_in)
        app.run(sys.argv)

