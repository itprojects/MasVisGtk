'''
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

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw, Gtk, Gdk, GdkPixbuf, GLib, GObject, Gio, Pango

from .input import file_formats
from .params import understanding_graphs

import json
import logging

log = logging.getLogger(__package__)

class StringPath(GObject.GObject):

    name = GObject.Property(type=str)
    path = GObject.Property(type=str)

    def __init__(self, path, name, canvas=None, checked=None):
        super().__init__()
        self.path = path
        self.name = name
        self.canvas = canvas # canvas for comparison
        self.checked = checked # enabled/disabled state for comparison 

class FileDetails:

    def __init__(self, file_path, file_name, file_parent_folder, r128_unit):
        self.file_path = file_path
        self.file_name = file_name
        self.file_parent_folder = file_parent_folder
        self.file_r128_unit = r128_unit

class SpinBox(Gtk.Box):

    win = None

    str_counter = '<span font="FreeMono" size="large" weight="bold">  {} / {}  </span>'

    def __init__(self, win):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)

        self.win = win
        self.set_visible(False)
        self.set_name('spinng_box')
        self.spinner = Gtk.Spinner() # Used in headerbar.
        self.spinner.set_name('spinng_box_spinner')
        self.spin_counter = Gtk.Label(use_markup=True, hexpand=True)
        self.append(self.spin_counter)
        self.spin_file_label = Gtk.Label(hexpand=True, ellipsize=Pango.EllipsizeMode.END)
        self.spin_file_label.set_name('spinng_box_file_label')
        self.append(self.spin_file_label)

    def set_label(self, n_current, n_total, track):
        self.spin_counter.set_label(self.str_counter.format(n_current, n_total))
        self.spin_file_label.set_label(track)

    def start(self, n_current, n_total, track):
        self.set_label(n_current, n_total, track)
        self.spinner.start()
        self.set_visible(True)

    def stop(self, btn):
        if self.win.app.ops_cancellable != None:
            self.win.app.ops_cancellable.cancel()
            self.win.app.ops_cancellable = None
        self.spinner.stop()
        self.set_visible(False)

class PyPlotWindow(Adw.ApplicationWindow):

    app = None
    box = None
    tab_bar = None
    tab_view = None
    n_figures = 0 # each figue MUST have a different number, else drawn overlapping
    n_th_comparison = 0 # distinguish tab comparisons
    w_width = 1080 # default window width
    w_height = 720 # default window height

    save_formats = [
        ('*.png', 'Portable Network Graphics (*.png)'),
        ('*.jpeg', 'Joint Photographic Experts Group (*.jpeg)'),
        ('*.svg', 'Scalable Vector Graphics (*.svg)'),
        ('*.webp', 'WebP Image Format (*.webp)'),
        ('*.tiff', 'Tagged Image File Format (*.tiff)'),
        ('*.pdf', 'Portable Document Format (*.pdf)'),
        ('*.eps', 'Encapsultaed Postscript (*.eps)'),
    ]

    def __init__(self, title, *args, **kwargs):
        super(PyPlotWindow, self).__init__(*args, **kwargs)

        self.app = kwargs.get('application', None)

        self.set_title(self.app.app_name)

        self.set_default_size(self.w_width, self.w_height)

        # Prevent resizing lower to smaller width, height.
        self.set_size_request(self.w_width, self.w_height)

        # Disable window resizing.
        #self.set_resizable(False)

        header = Adw.HeaderBar()

        # Menu
        menu = Gio.Menu.new()
        submenu_general = Gio.Menu.new()
        submenu_general.append(_('File Information'), 'app.file_information_action')
        submenu_general.append(_('Go Compare'), 'app.go_compare_action')
        submenu_general.append(_('Save All'), 'app.save_all_action')
        menu.append_section(None, submenu_general)

        submenu_info = Gio.Menu.new()
        submenu_info.append(_('Preferences'), 'app.preferences_action')
        submenu_info.append(_('Formats'), 'app.formats_action')
        submenu_info.append(_('Keyboard Shortcuts'), 'app.shortcuts_action')
        submenu_info.append(_('Help'), 'app.help_action')
        submenu_info.append(_('About'), 'app.about_action')
        menu.append_section(None, submenu_info)

        popover = Gtk.PopoverMenu()
        popover.set_menu_model(menu)

        self.menu_button = Gtk.MenuButton()
        self.menu_button.set_popover(popover)
        self.menu_button.set_icon_name('open-menu-symbolic')

        header.pack_end(self.menu_button)

        # MasVis open files.
        self.btn_open_files = Gtk.Button(label=_('Open Files'), icon_name='folder-music-symbolic', tooltip_text=_('Open Files'))
        self.btn_open_files.connect('clicked', self.on_open_dialog, None, True)
        header.pack_start(self.btn_open_files)

        # MasVis advanced open, or overview.
        self.btn_open_folders = Gtk.Button(label=_('Advanced Open'), icon_name='folder-symbolic', tooltip_text=_('Advanced Open'))
        self.btn_open_folders.connect('clicked', self.on_open_advanced_dialog)
        header.pack_start(self.btn_open_folders)

        # MasVis save tab to image.
        self.btn_save = Gtk.Button(label=_('Save'), icon_name='document-save-symbolic', tooltip_text=_('Save Tab'))
        self.btn_save.connect('clicked', self.on_save_dialog)
        header.pack_end(self.btn_save)

        self.box = Gtk.Box()
        self.box.props.orientation = Gtk.Orientation.VERTICAL
        self.box.append(header)

        # Holds tabs.
        self.tab_bar = Adw.TabBar.new()
        self.tab_view = Adw.TabView.new()
        self.tab_bar.set_autohide(False) # Don't hide TabBar.
        self.tab_bar.set_view(self.tab_view)
        self.box.append(self.tab_bar)
        self.box.append(self.tab_view)

        self.set_content(self.box)

    def add_tab(self, a_file, overview_mode):
        tabbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        tabbox.a_file = a_file
        tabbox.overview_or_detailed = overview_mode

        tabbox.scrolled = Gtk.ScrolledWindow(vexpand=True)
        tabbox.scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        tabbox.append(tabbox.scrolled)

        page = self.tab_view.append(tabbox)

        # Required, otherwise risks low-resolution image.
        self.tab_view.set_selected_page(page)

        if overview_mode == 'dir':
            page.set_title(a_file.file_name)
            page.set_tooltip(a_file.file_path)
        elif overview_mode == 'flat':
            page.set_title('Overview')
        else:
            page.set_title(a_file.file_name)
            page.set_tooltip(a_file.file_name + '\n\n' + a_file.file_path)
        return page

    # Simple files open, or add to opening list.
    def on_open_dialog(self, btn_open, list_store_paths, files_or_folders):
        open_dialog = Gtk.FileDialog()
        open_dialog.set_modal(True)
        open_dialog.set_title(_('Open Files'))
        open_dialog.list_store_paths = list_store_paths
        open_dialog.files_or_folders = files_or_folders
        if files_or_folders:
            self.app.overview_mode = None
            open_dialog.set_title(_('Open Files'))
            open_dialog.open_multiple(self, None, self.app.on_open_dialog_cb)
        else:
            open_dialog.set_title(_('Open Folders'))
            open_dialog.select_multiple_folders(self, None, self.app.on_open_dialog_cb)

    # Advanced files and folders open dialog.
    def on_open_advanced_dialog(self, btn_open):
        dialog_advanced = Adw.Dialog()
        dialog_advanced.set_follows_content_size(True) # Adw size problems.
        dialog_advanced.set_title(_('Advanced Open'))

        list_store = Gio.ListStore.new(StringPath)

        headerbar = Adw.HeaderBar()

        add_files = Gtk.Button(label=_('Add Files'), icon_name='folder-music-symbolic', tooltip_text=_('Add Files'))
        add_files.connect('clicked', self.on_open_dialog, list_store, True)
        add_folders = Gtk.Button(label=_('Add Folders'), icon_name='folder-new-symbolic', tooltip_text=_('Add Folders'))
        add_folders.connect('clicked', self.on_open_dialog, list_store, False)

        headerbar.pack_start(add_files)
        headerbar.pack_start(add_folders)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.append(headerbar)

        # ListView for input paths.
        listview_inputs_selction = Gtk.SingleSelection.new(list_store)
        listview_inputs_selction.set_autoselect(False)
        listview_factory = Gtk.SignalListItemFactory()
        listview_factory.connect('setup', self.on_factory_setup_listview_item)
        listview_factory.connect('bind', self.on_factory_bind_listview_item)
        listview_inputs = Gtk.ListView.new(listview_inputs_selction, listview_factory)
        listview_inputs.set_name('transparency')
        listview_inputs.set_enable_rubberband(False)
        listview_inputs.store = list_store

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_name('dialog_advanced_cb_row')
        scrolled.set_size_request(-1, 200)
        scrolled.set_child(listview_inputs)
        box.append(scrolled)

        dialog_advanced.cb_r128_unit = Gtk.CheckButton.new_with_label(_('use LUFS units'))
        dialog_advanced.cb_r128_unit.set_name('dialog_advanced_cb_row')
        dialog_advanced.cb_r128_unit.set_active(True)
        box.append(dialog_advanced.cb_r128_unit)
        dialog_advanced.cb_recursive = Gtk.CheckButton.new_with_label(_('recursive (search sub-folders)'))
        dialog_advanced.cb_recursive.set_name('dialog_advanced_cb_row')
        dialog_advanced.cb_recursive.set_active(True)
        box.append(dialog_advanced.cb_recursive)
        box_layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box_layout.set_name('dialog_advanced_box_layout')
        dialog_advanced.cb_overview = Gtk.CheckButton.new_with_label(_('overview mode'))
        box_layout.append(dialog_advanced.cb_overview)
        dialog_advanced.cb_flat = Gtk.CheckButton.new_with_label('flat')
        dialog_advanced.cb_flat.set_name('dialog_advanced_cb_margin')
        dialog_advanced.cb_flat.set_active(True)
        dialog_advanced.cb_dir = Gtk.CheckButton.new_with_label('dir')
        dialog_advanced.cb_dir.set_name('dialog_advanced_cb_margin')
        dialog_advanced.cb_dir.set_group(dialog_advanced.cb_flat)
        box_layout.append(dialog_advanced.cb_flat)
        box_layout.append(dialog_advanced.cb_dir)
        open_advanced_start = Gtk.Button(label=_('Open'), tooltip_text=_('Open'), halign=Gtk.Align.END)
        open_advanced_start.connect('clicked', self.on_open_advanced_btn, list_store, dialog_advanced)
        box_layout.append(open_advanced_start)

        box.append(box_layout)

        dialog_advanced.set_child(box)
        dialog_advanced.present(self)

    # list_store -> ['path']
    def on_open_advanced_btn(self, btn, list_store, dialog_advanced):
        n = list_store.get_n_items()
        if n > 0:
            try:
                inputs = [list_store.get_item(i).path for i in range(0, n)]

                self.app.r128_unit = 'LUFS' if dialog_advanced.cb_r128_unit.get_active() else 'LU'
                self.app.recursive_scan = dialog_advanced.cb_recursive.get_active()
                self.app.overview_mode = None
                if dialog_advanced.cb_overview.get_active():
                    self.app.overview_mode = 'flat' if dialog_advanced.cb_flat.get_active() else 'dir'

                dialog_advanced.close() # dismiss, only after inputs
                self.app.open_async(inputs)
            except Exception as e:
                self.app.on_error_dialog(_('Failed Open'), e)

    def on_factory_setup_listview_item(self, factory, list_item):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.set_focus_on_click(True)
        box.set_size_request(-1, 30)
        btn_remove = Gtk.Button(icon_name='window-close-symbolic', halign=Gtk.Align.START, margin_start=5)
        btn_remove.connect('clicked', self.on_remove_list_item, list_item, factory)
        btn_remove.set_name('dialog_advanced_round_delete')
        box.append(btn_remove)
        label = Gtk.Label(ellipsize=Pango.EllipsizeMode.END, hexpand=True, halign=Gtk.Align.START, margin_start=5, margin_end=5)
        label.set_name('listview_item')
        box.append(label)
        list_item.set_child(box)

    def on_factory_bind_listview_item(self, factory, list_item):
        box = list_item.get_child()
        data_item = list_item.get_item()
        box.set_tooltip_text(data_item.path)
        box.get_last_child().set_text(data_item.name)

    def on_remove_list_item(self, btn, list_item, factory):
        listview = btn.get_parent().get_parent().get_parent()
        listview.store.remove(list_item.get_position())

    # Save headerbar button.
    def on_save_dialog(self, btn_save):
        if self.tab_view.get_n_pages() < 1:
            return
        save_dialog = Gtk.FileDialog()
        save_dialog.set_modal(True)
        save_dialog.set_accept_label(_('Save'))
        save_dialog.set_title(_('Save in Folder'))

        # Get file extension, use in suggested save name.
        file_ext = self.save_formats[self.app.pref_save_format][0][2:]

        initial_name = None
        if self.tab_view.get_selected_page().get_child().overview_or_detailed: # overview
            initial_name = 'overview-pymasvisgtk.' + file_ext
        else: # detailed
            initial_name = self.tab_view.get_selected_page().get_child().a_file.file_name + '-masvisgtk.' + file_ext

        self.on_make_filters(save_dialog)
        save_dialog.set_initial_folder(Gio.File.new_for_path('~'))
        save_dialog.set_initial_name(initial_name)
        save_dialog.save(self, None, self.app.on_save_one_dialog_cb) # creates UI
        self.select_format_widget(save_dialog)

    # Save All menu item.
    def on_save_multiple_dialog(self):
        save_dialog = Gtk.FileDialog()
        save_dialog.set_modal(True)
        save_dialog.set_accept_label(_('Save'))
        save_dialog.set_title(_('Save All in Folder'))
        self.on_make_filters(save_dialog)
        save_dialog.set_initial_folder(Gio.File.new_for_path('~'))
        save_dialog.select_folder(self, None, self.app.on_save_multiple_dialog_cb)
        self.select_format_widget(save_dialog)

    #################################################################################
    # Extracting selected FileFilter, used as format selection.                     #
    #                                                                               #
    # Gtk.FileDialog creates Gtk.FileChooserDialog, inside which is a Gtk.DropDown, #
    # located in a Gtk.ActionBar (bottom of the dialog).                            #
    # The Gtk.DropDown holds a FileFilter object, representing the image type,      #
    # that the user can select for image saving format.                             #
    # Press Ctrl+Shift+D to inspect a window/dialog, to find child widget.          #
    #################################################################################
    def select_format_widget(self, save_dialog):
        # Find the save UI dialog.
        top_level_windows = Gtk.Window.list_toplevels()
        dialog_found = None
        for window in top_level_windows:
            if isinstance(window, Gtk.Dialog):
                dialog_found = window
                break

        if dialog_found == None:
            save_dialog.filter_formats_widget = None
        else:
            save_dialog.filter_formats_widget = (
                dialog_found
                .get_first_child() # Gtk.Box
                .get_first_child() # Gtk.Box
                .get_first_child() # Gtk.FileChooserWidget
                .get_first_child() # Gtk.Box
                .get_last_child() # Gtk.ActionBar
                .get_first_child() # Gtk.Revealer
                .get_first_child() # Gtk.CenterBox
                .get_last_child() # Gtk.Box
                .get_first_child() # Gtk.Box
                .get_first_child() # Gtk.DropDown
            )

    # Create FileFilters, used as selection of the image format.
    def on_make_filters(self, save_dialog):
        filters_store = Gio.ListStore.new(Gtk.FileFilter)
        for tup in self.save_formats:
            file_filter = Gtk.FileFilter()
            file_filter.set_name(tup[1])
            file_filter.add_pattern(tup[0])
            filters_store.append(file_filter)
        save_dialog.set_filters(filters_store)
        save_dialog.set_default_filter(filters_store.get_item(self.app.pref_save_format))

    def on_file_information(self):
        page = self.tab_view.get_selected_page()
        if not page:
            return

        body = page.get_child().a_file.track

        dialog_information = Adw.MessageDialog(
            transient_for = self,
            heading = _('File Information'),
        )

        scrolled_textview = Gtk.ScrolledWindow()
        scrolled_textview.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        text_buffer = Gtk.TextBuffer()
        text_buffer.insert_markup(text_buffer.get_end_iter(), body, -1)
        text_view = Gtk.TextView(buffer=text_buffer, editable=False, justification=Gtk.Justification.FILL)
        text_view.set_name('text_view')
        text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        text_view.set_name('transparency')
        scrolled_textview.set_child(text_view)
        scrolled_textview.set_size_request(360, 480)
        dialog_information.set_extra_child(scrolled_textview)

        dialog_information.add_response('cancel',  _('Close'))
        dialog_information.present()

    # Prepare tab comparison.
    def on_go_compare_init(self):
        if self.tab_view.get_n_pages() < 2:
            self.app.on_error_dialog(_('Cannot Compare'), _('No tabs.'))
            return

        dialog_compare = Adw.Dialog()
        dialog_compare.set_size_request(480, 360)
        dialog_compare.set_follows_content_size(True) # Adw size problems.
        dialog_compare.set_title(_('Compare Tabs'))

        list_store = Gio.ListStore.new(StringPath)

        # Process the list of tabs.
        for tab in self.tab_view.get_pages():
            try:
                list_store.append(StringPath(
                        tab.get_child().a_file.file_path,
                        tab.get_child().a_file.file_name,
                        tab.get_child().scrolled.get_child().get_child().get_child() # canvas
                    )
                )
            except Exception as e:
                continue

        if list_store.get_n_items() < 2:
            self.app.on_error_dialog(_('Cannot Compare'), _('Too few tabs.'))
            return

        # ListView of tab canvas.
        listview_canvas_selction = Gtk.NoSelection.new(list_store)
        listview_factory = Gtk.SignalListItemFactory()
        listview_factory.connect('setup', self.on_factory_setup_listview_compare_item)
        listview_factory.connect('bind', self.on_factory_bind_listview_compare_item)
        listview_canvas = Gtk.ListView.new(listview_canvas_selction, listview_factory)
        listview_canvas.set_vexpand(True)
        listview_canvas.set_name('dialog_compare_listview')
        listview_canvas.set_enable_rubberband(False)

        btn_go = Gtk.Button(label=_('Go!'), tooltip_text=_('Go!'))
        btn_go.connect('clicked', self.on_go_compare, dialog_compare, listview_canvas_selction)

        headerbar = Adw.HeaderBar()
        headerbar.pack_start(btn_go)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.append(headerbar)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_name('dialog_compare_scrolled')
        scrolled.set_child(listview_canvas)
        box.append(scrolled)

        dialog_compare.set_child(box)
        dialog_compare.present(self)

    def on_factory_setup_listview_compare_item(self, factory, list_item):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        btn_check = Gtk.CheckButton(halign=Gtk.Align.START, margin_start=5, margin_end=5)
        box.append(btn_check)
        label = Gtk.Label(ellipsize=Pango.EllipsizeMode.END, hexpand=True, halign=Gtk.Align.START, margin_start=5, margin_end=5)
        box.append(label)
        list_item.set_child(box)

    def on_factory_bind_listview_compare_item(self, factory, list_item):
        box = list_item.get_child()
        data_item = list_item.get_item()
        box.set_tooltip_text(data_item.name + '\n\n' + data_item.path)
        box.get_first_child().connect('toggled', self.on_listview_compare_item_checked, data_item)
        box.get_last_child().set_text(data_item.name)

    # Handles Gtk.CheckButton to add item to comparison.
    def on_listview_compare_item_checked(self, button, data_item):
        if data_item.checked == None:
            data_item.checked = True
        else:
            data_item.checked = not data_item.checked

    # Start tabs' comparision.
    def on_go_compare(self, button, dialog_compare, listview_canvas_selction):
        # Create and check selection of data to compare.
        comparable_items = []
        for item in listview_canvas_selction.get_model():
            if item.checked:
                comparable_items.append(item)

        if len(comparable_items) < 2:
            self.app.on_error_dialog(_('Cannot Compare'), _('Too few tabs.'))
            return

        dialog_compare.close()

        self.n_th_comparison += 1

        # Comparison dialog.
        win = Adw.Window()
        win.set_title(_('Comparison #') + str(self.n_th_comparison))

        # Calculate initial window width.
        pic_section_width = self.app.pref_comparison_plot_width
        proposed_width = 2 * pic_section_width + 10

        scr_width = self.screen_width()
        if proposed_width > scr_width:
            win.set_size_request(self.w_width, self.w_height)
        else:
            win.set_size_request(proposed_width, self.w_height)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.append(Adw.HeaderBar())
        box_of_pictures = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box_of_pictures.set_homogeneous(False)

        for item in comparable_items:
            buff_w, buff_h = item.canvas.get_width_height()
            aspect_ratio = buff_w/buff_h
            pixbuf = GdkPixbuf.Pixbuf.new_from_data(
                item.canvas.buffer_rgba().tobytes(),
                GdkPixbuf.Colorspace.RGB,
                True,
                8,
                buff_w,
                buff_h,
                buff_w * 4, # rowstride (4 for RGBA, 3 for RGB)
                None
            )

            pixbuf = pixbuf.scale_simple(pic_section_width, pic_section_width//aspect_ratio, GdkPixbuf.InterpType.BILINEAR)
            texture = Gdk.Texture.new_for_pixbuf(pixbuf)
            pic = Gtk.Picture.new_for_paintable(texture)
            pic.set_size_request(pic_section_width, pic_section_width//aspect_ratio)
            pic.set_valign(Gtk.Align.START)
            pic.set_content_fit(Gtk.ContentFit.SCALE_DOWN)
            pic.set_tooltip_text(item.name + '\n\n' + item.path)
            box_holder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL) # prevent Gtk.Picture scaling
            box_holder.append(pic)
            box_of_pictures.append(box_holder)

        box_frame = Gtk.Box(hexpand=True, vexpand=True)
        box_frame.set_halign(Gtk.Align.CENTER)
        box_frame.append(box_of_pictures)

        scrolled_comparison = Gtk.ScrolledWindow()
        scrolled_comparison.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled_comparison.set_child(box_frame)
        box.append(scrolled_comparison)

        # F11 Fullscreen shortcut key.
        key_controller = Gtk.EventControllerKey.new()
        key_controller.connect("key-pressed", self.fullscreen_comparison_window, win)
        win.add_controller(key_controller)

        win.set_content(box)
        win.present()

    def fullscreen_comparison_window(self, event_controller_key, keyval, keycode, state, win):
        if keyval == Gdk.KEY_F11:
            if win.is_fullscreen():
                win.unfullscreen()
            else:
                win.fullscreen()
        elif keyval == Gdk.KEY_Escape:
            win.unfullscreen()

    # Get width of screen/display.
    def screen_width(self):
        try:
            return self.get_display().get_monitor_at_surface(self.get_surface()).get_geometry().width
        except:
            return -2

    def on_show_formats_dialog(self):
        if self.app.formats == None:
            self.app.formats = file_formats()
        n_formats = 0 if not self.app.formats else len(self.app.formats)
        dialog_formats= Adw.MessageDialog(
            transient_for = self,
            heading = _('FFMPEG Formats') + f'\n{n_formats}' if n_formats > 0 else _('No FFMPEG Formats'),
        )

        if n_formats > 0:
            scrolled_textview = Gtk.ScrolledWindow()
            scrolled_textview.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
            text_buffer = Gtk.TextBuffer()
            text_buffer.insert_markup(text_buffer.get_end_iter(), ',    '.join(self.app.formats), -1)
            text_view = Gtk.TextView(buffer=text_buffer, editable=False, justification=Gtk.Justification.FILL)
            text_view.set_name('text_view')
            text_view.set_wrap_mode(Gtk.WrapMode.WORD)
            scrolled_textview.set_child(text_view)
            scrolled_textview.set_size_request(640, 480)
            dialog_formats.set_extra_child(scrolled_textview)

        dialog_formats.add_response('cancel',  _('Close'))
        response = dialog_formats.present()

    def on_show_manual_dialog(self):
        builder = Gtk.Builder()
        obj = builder.new_from_resource('/io/github/itprojects/MasVisGtk/gtk/manual-overlay.ui')
        dialog_manual = obj.get_object('manual_overlay')
        text_buffer = obj.get_object('text_buffer')
        text_buffer.insert_markup(text_buffer.get_end_iter(), understanding_graphs, -1)
        dialog_manual.set_transient_for(self)
        response = dialog_manual.present()
        dialog_manual.add_response('cancel',  _('Close'))

    def on_open_menu(self):
        self.menu_button.popup()

    def on_show_shortcuts(self):
        builder = Gtk.Builder()
        obj = builder.new_from_resource('/io/github/itprojects/MasVisGtk/gtk/help-overlay.ui')
        shortcuts_window = obj.get_object('help_overlay')
        shortcuts_window.present()

    def on_show_about_dialog(self):
        about = Adw.AboutDialog()
        about.set_translator_credits('ITProjects')
        about.set_developers(['ITProjects (2024–)', 'Joakim Fors (2022)'])
        about.set_copyright('Copyright 2024 ITProjects\nCopyright 2022 Joakim Fors')
        about.set_license_type(Gtk.License.GPL_2_0)
        about.set_website('https://github.com/itprojects/MasVisGtk')
        about.set_version(self.app.VERSION)
        about.add_acknowledgement_section(_('Original PyMasVis module development.'), ['Joakim Fors'])
        about.set_application_name(self.app.app_name)
        about.set_comments(_('GTK application, originally based on PyMasVis commit #657196.'))
        about.set_application_icon('io.github.itprojects.MasVisGtk')
        about.present(self)
