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

import gi, os
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Adw, Gtk, Gdk, GdkPixbuf, GLib, GObject, Gio, Pango

from PIL import Image

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
        self.canvas = canvas # canvas
        self.checked = checked # enabled/disabled state

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
        self.spinner = Gtk.Spinner()
        self.spinner.set_name('spinng_box_spinner')
        self.spin_counter = Gtk.Label(
            use_markup=True,
            hexpand=True
        )
        self.append(self.spin_counter)
        self.spin_file_label = Gtk.Label(
            hexpand=True,
            ellipsize=Pango.EllipsizeMode.END
        )
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

    # Zoom widgets.
    box_view_buttons = None
    int_zoom_scale = 1080 # lower 1080, upper 4096, step 100 px
    btn_zoom_out = None
    btn_zoom_original = None
    btn_zoom_indicator = None
    btn_zoom_best_fit = None
    btn_zoom_in = None

    popover_zoom_indicator = None
    spin_zoom = None

    btn_dr = None
    n_figures = 0 # each figue MUST have a different number, else drawn overlapping
    n_th_animation = 0 # distinguish tab animations
    n_th_comparison = 0 # distinguish tab comparisons
    w_width = 1080 # default window width
    w_height = 720 # default window height

    animated_pil_images = [] # animated gif PIL images

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
        submenu_general.append(_('Animate Tabs'), 'app.animate_tabs_action')
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
        self.btn_open_files = Gtk.Button(
            icon_name='io.github.itprojects.MasVisGtk-symbolic',
            tooltip_text=_('Open Files')
        )
        self.btn_open_files.set_name('btn_open_files')
        self.btn_open_files.connect('clicked', self.on_open_dialog, None, True)
        header.pack_start(self.btn_open_files)

        # MasVis advanced open, or overview.
        self.btn_open_folders = Gtk.Button(
            icon_name='advanced-open-symbolic',
            tooltip_text=_('Advanced Open')
        )
        self.btn_open_folders.connect('clicked', self.on_open_advanced_dialog)
        header.pack_start(self.btn_open_folders)

        # MasVis save tab to image.
        self.btn_save = Gtk.Button(
            label=_('Save'),
            icon_name='document-save-symbolic',
            tooltip_text=_('Save Tab')
        )
        self.btn_save.connect('clicked', self.on_save_dialog)
        header.pack_start(self.btn_save)

        # Dynamic Range indicator widget.
        self.btn_dr = Gtk.Button(
            label='00.0',
            tooltip_text=_('Dynamic Range')
        )
        self.btn_dr.set_name('btn_dr_dark')
        self.btn_dr.set_halign(Gtk.Align.START)
        self.btn_dr.set_valign(Gtk.Align.CENTER)
        self.btn_dr.set_hexpand(True)
        self.btn_dr.connect('clicked', self.on_show_dynamic_range_channels)
        self.btn_dr.last_class = ''
        self.dr_change_css('dr_style00')
        header.pack_end(self.btn_dr)

        btn_dr_chart = Gtk.Button(
            icon_name='info',
            tooltip_text=_('Dynamic Range Chart')
        )
        btn_dr_chart.connect('clicked', self.on_show_dynamic_range_chart)
        header.pack_end(btn_dr_chart)

        self.box_view_buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.box_view_buttons.set_name('box_view_buttons')
        self.box_view_buttons.set_hexpand(False)
        self.box_view_buttons.set_vexpand(False)
        self.box_view_buttons.set_halign(Gtk.Align.CENTER)
        self.box_view_buttons.set_valign(Gtk.Align.END)
        self.box_view_buttons.set_visible(False)

        # Less zoom.
        self.btn_zoom_out = Gtk.Button(
            icon_name='zoom-out-symbolic',
            tooltip_text=_('Zoom in')
        )
        self.btn_zoom_out.connect('clicked', self.on_scale_to_value, -1)
        self.box_view_buttons.append(self.btn_zoom_out)

        # Original zoom.
        self.btn_zoom_original = Gtk.Button(
            icon_name='zoom-original-symbolic',
            tooltip_text=_('Restore original dimensions')
        )
        self.btn_zoom_original.connect('clicked', self.on_scale_to_value, 1080)
        self.box_view_buttons.append(self.btn_zoom_original)

        # Indicator of zoom.
        self.btn_zoom_indicator = Gtk.MenuButton(label='1080')
        self.btn_zoom_indicator.set_always_show_arrow(False)
        self.btn_zoom_indicator.set_direction(Gtk.ArrowType.NONE)
        self.box_view_buttons.append(self.btn_zoom_indicator)

        # Resize button to scale canvas to window width.
        self.btn_zoom_best_fit = Gtk.Button(
            icon_name='zoom-fit-best-symbolic',
            tooltip_text=_('Scale to Window Width')
        )
        self.btn_zoom_best_fit.connect('clicked', self.on_scale_to_value, 66)
        self.box_view_buttons.append(self.btn_zoom_best_fit)

        # More zoom.
        self.btn_zoom_in = Gtk.Button(
            icon_name='zoom-in-symbolic',
            tooltip_text=_('Zoom out')
        )
        self.btn_zoom_in.connect('clicked', self.on_scale_to_value, 1)
        self.box_view_buttons.append(self.btn_zoom_in)

        # Gtk.SpinButton to zoom-in/re-scale the canvas size.
        self.spin_zoom = Gtk.SpinButton.new_with_range(1080, 4096, 500) # lower, upper, step
        self.spin_zoom.set_valign(Gtk.Align.CENTER)
        self.spin_zoom.set_tooltip_text(_('Zoom Level [px]'))
        self.spin_zoom.set_digits(0)
        self.spin_zoom.connect('value-changed', self.on_spin_zoom_value_changed)

        # Gtk.Popover for manual entry of zoom level in [px].
        self.popover_zoom_indicator = Gtk.Popover.new()
        self.popover_zoom_indicator.set_autohide(True)
        self.popover_zoom_indicator.set_has_arrow(True)
        self.popover_zoom_indicator.set_child(self.spin_zoom)
        self.popover_zoom_indicator.set_default_widget(self.spin_zoom)
        self.popover_zoom_indicator.set_position(Gtk.PositionType.TOP)
        self.btn_zoom_indicator.set_popover(self.popover_zoom_indicator)

        # Set initial app style to buttons.
        self.dark_light_css(Adw.StyleManager.get_for_display(Gdk.Display.get_default()).get_dark())

        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.box.append(header)

        # Holds tabs.
        box_tabs = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.tab_bar = Adw.TabBar.new()
        self.tab_bar.set_autohide(True) # Hide TabBar.

        self.tab_view = Adw.TabView.new()
        self.tab_bar.set_view(self.tab_view)

        # Called after changes in selected pages,
        # to show or hide DR Meter and zoom widgets.
        self.tab_view.connect("notify::selected-page", self.on_tab_changed)

        box_tabs.append(self.tab_bar)
        box_tabs.append(self.tab_view)

        # Overlay for zoom controls.
        overlay = Gtk.Overlay()
        overlay.set_vexpand(True)
        overlay.set_child(box_tabs)
        overlay.add_overlay(self.box_view_buttons)

        self.box.append(overlay)
        self.set_content(self.box)

    def add_tab(self, a_file, overview_mode):
        tabbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        tabbox.a_file = a_file
        tabbox.overview_or_detailed = overview_mode
        tabbox.scrolled = Gtk.ScrolledWindow(vexpand=True)
        tabbox.scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        tabbox.append(tabbox.scrolled)

        page = self.tab_view.append(tabbox)
        page.tabbox = tabbox

        if overview_mode == 'dir':
            page.set_title(a_file.file_name)
            page.set_tooltip(a_file.file_path)
        elif overview_mode == 'flat':
            page.set_title(_('Overview'))
        else:
            page.set_title(a_file.file_name)
            page.set_tooltip(a_file.file_name + '\n\n' + a_file.file_path)

        return page

    # Change highlighting of new tabs.
    def on_attention_changed(self, tab_view, selected_page):
        page = tab_view.get_selected_page()
        if page:
            if page.get_needs_attention():
                page.set_needs_attention(False)

    def on_tab_changed(self, tab_view, item):
        tabbox = tab_view.get_selected_page().get_child()

        # Change DR Meter.
        self.dr_change(tabbox)

        # Change canvas scale indicator.
        if hasattr(tabbox, 'canvas_width'):
            self.int_zoom_scale = tabbox.canvas_width
            self.btn_zoom_indicator.set_label(str(self.int_zoom_scale))

    # Set style light or dark.
    def dark_light_css(self, dark_or_light):
        if dark_or_light:
            self.btn_dr.set_name('btn_dr_dark')
            self.btn_zoom_out.set_name('btn_zoom_out_dark')
            self.btn_zoom_original.set_name('btn_zoom_original_dark')
            self.btn_zoom_indicator.set_name('btn_zoom_indicator_dark')
            self.btn_zoom_best_fit.set_name('btn_zoom_best_fit_dark')
            self.btn_zoom_in.set_name('btn_zoom_in_dark')
        else:
            self.btn_dr.set_name('btn_dr_light')
            self.btn_zoom_out.set_name('btn_zoom_out_light')
            self.btn_zoom_original.set_name('btn_zoom_original_light')
            self.btn_zoom_indicator.set_name('btn_zoom_indicator_light')
            self.btn_zoom_best_fit.set_name('btn_zoom_best_fit_light')
            self.btn_zoom_in.set_name('btn_zoom_in_light')

    def dr_change_css(self, str_style):
        if str_style == self.btn_dr.last_class:
            return

        if len(self.btn_dr.last_class) > 0:
            self.btn_dr.remove_css_class(self.btn_dr.last_class)

        self.btn_dr.last_class = str_style
        self.btn_dr.add_css_class(str_style)

    # Changes DR Meter button.
    def dr_change(self, tabbox):
        if hasattr(tabbox, 'dr_val'):
            if not self.btn_dr.get_visible():
                self.btn_dr.set_visible(True)

            if not self.box_view_buttons.get_visible():
                self.box_view_buttons.set_visible(True)
        else:
            # overview or empty
            if self.btn_dr.get_visible():
                self.btn_dr.set_visible(False)

            if self.box_view_buttons.get_visible():
                self.box_view_buttons.set_visible(False)
            return

        self.btn_dr.set_label(str(tabbox.dr_val))
        if tabbox.int_dr == -1:
            self.btn_dr.set_tooltip_text(_('Unknown Dynamic Range'))
            self.dr_change_css('dr_style00')
        else:
            self.btn_dr.set_tooltip_text(_('Dynamic Range'))
            match tabbox.int_dr:
                case 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7:
                    self.dr_change_css('dr_style07')
                case 8:
                    self.dr_change_css('dr_style08')
                case 9:
                    self.dr_change_css('dr_style09')
                case 10:
                    self.dr_change_css('dr_style10')
                case 11:
                    self.dr_change_css('dr_style11')
                case 12:
                    self.dr_change_css('dr_style12')
                case 13:
                    self.dr_change_css('dr_style13')
                case _:
                    if tabbox.int_dr > 13:
                        self.dr_change_css('dr_style14')

    def on_scroll_over_canvas(self, event):
        page = self.tab_view.get_selected_page()
        if page != None:
            tabbox = page.get_child()
            if tabbox:
                v = tabbox.scrolled.get_vadjustment()
                step = 50
                if event.button == 'down':
                    v.set_value(max(v.get_value() - step, 0))
                else:
                    v.set_value(min(v.get_value() + step, v.get_upper() - v.get_page_size()))

    def on_spin_zoom_value_changed(self, btn):
        self.on_scale_to_value(None, 99)

    # Set new canvas size. [1080 px, 4096 px]
    # Maximum width is artificially set to 4096 px (4K).
    # Scale font sizes, using width.
    def on_scale_to_value(self, btn, which_option):
        page = self.tab_view.get_selected_page()
        if page != None:
            tabbox = page.get_child()
            if tabbox and not tabbox.overview_or_detailed:
                # Direct towards specific option.
                new_canvas_width = None
                if which_option == 66: # Best fit zoom.
                    new_canvas_width = self.get_allocated_width()
                elif which_option == -1: # Less zoom.
                    new_canvas_width = self.int_zoom_scale - 100
                elif which_option == 1: # More zoom.
                    new_canvas_width = self.int_zoom_scale + 100
                elif which_option == 99:
                    new_canvas_width = int(self.spin_zoom.get_value())
                else: # Original zoom. 1080
                    new_canvas_width = 1080

                # Check value is new.
                if new_canvas_width == self.int_zoom_scale:
                    return

                # Check value is possible.
                if new_canvas_width <= 1080: # minimum
                    self.int_zoom_scale = 1080
                elif new_canvas_width >= 4096: # maximum
                    self.int_zoom_scale = 4096

                # Assign and keep value.
                self.int_zoom_scale = new_canvas_width
                self.btn_zoom_indicator.set_label(str(self.int_zoom_scale))
                tabbox.canvas_width = new_canvas_width

                # Set new canvas dimensions.
                tabbox.canvas.set_size_request(
                    new_canvas_width,
                    new_canvas_width//tabbox.aspect_ratio
                )

                # Change font sizes of axes texts.
                scale_factor = new_canvas_width / 1080
                for k, v in tabbox.canvas.figure.dict_fontsizes.items():
                    if v[2] == 'text':
                        v[0].set_fontsize(round(v[1] * scale_factor))

                # Change font sizes of axis ticks.
                for ax in tabbox.canvas.figure.get_axes():

                    xticklabels_ = ax.get_xticklabels()
                    for xt in xticklabels_:
                        xt.set_fontsize(round(10.0 * scale_factor))

                    yticklabels_ = ax.get_yticklabels()
                    for yt in yticklabels_:
                        yt.set_fontsize(round(10.0 * scale_factor))

    def on_show_dynamic_range_chart(self, btn):
        dialog = Adw.Dialog()
        dialog.set_follows_content_size(True) # Adw size problems.
        dialog.set_title(_('Dynamic Range Chart'))
        dialog.set_size_request(320, 500)

        headerbar = Adw.HeaderBar()
        picture_dr_chart = Gtk.Picture.new_for_resource('/io/github/itprojects/MasVisGtk/dynamic-range-chart.svg')
        picture_dr_chart.set_content_fit(Gtk.ContentFit.SCALE_DOWN)
        picture_dr_chart.set_name('picture_dr_chart')

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.append(headerbar)
        box.append(picture_dr_chart)

        dialog.set_child(box)
        dialog.present(self)

    def on_show_dynamic_range_channels(self, btn):
        page = self.tab_view.get_selected_page()
        if page != None:
            tabbox = page.get_child()
            if not tabbox.overview_or_detailed:
                if hasattr(tabbox, 'dr_channels'):
                    dialog = Adw.Dialog()
                    dialog.set_follows_content_size(True) # Adw size problems.
                    dialog.set_title(_('Dynamic Range of Channels'))

                    headerbar = Adw.HeaderBar()

                    text = tabbox.c_layout if tabbox.c_layout else ''
                    text = text.title()
                    for i in range(len(tabbox.dr_channels)):
                        text += '\n' + _('Channel #') + f'{i+1} ' + str(tabbox.dr_channels[i])

                    label_channels = Gtk.Label(label='test')
                    label_channels.set_name('label_channels')
                    label_channels.set_justify(Gtk.Justification.CENTER)
                    label_channels.set_text(text)

                    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
                    box.append(headerbar)
                    box.append(label_channels)

                    dialog.set_child(box)
                    dialog.present(self)

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

        add_files = Gtk.Button(
            label=_('Add Files'),
            icon_name='io.github.itprojects.MasVisGtk-symbolic',
            tooltip_text=_('Add files for processing')
        )
        add_files.connect('clicked', self.on_open_dialog, list_store, True)
        add_folders = Gtk.Button(
            label=_('Add Folders'),
            icon_name='folder-new-symbolic',
            tooltip_text=_('Add folders for processing')
        )
        add_folders.connect('clicked', self.on_open_dialog, list_store, False)

        headerbar.pack_start(add_files)
        headerbar.pack_start(add_folders)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.append(headerbar)

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
        box.append(box_layout)

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

        load_advanced_start = Gtk.Button(
            label=_('Start'),
            tooltip_text=_('Begin audio analysis'),
            halign=Gtk.Align.CENTER
        )
        load_advanced_start.connect('clicked', self.on_open_advanced_btn, list_store, dialog_advanced)
        load_advanced_start.set_name('dialog_advanced_load')

        box.append(load_advanced_start)

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
        btn_remove = Gtk.Button(
            icon_name='window-close-symbolic',
            halign=Gtk.Align.START,
            margin_start=5
        )
        btn_remove.connect('clicked', self.on_remove_list_item, list_item, factory)
        btn_remove.set_name('dialog_advanced_round_delete')
        box.append(btn_remove)
        label = Gtk.Label(
            ellipsize=Pango.EllipsizeMode.END,
            hexpand=True,
            halign=Gtk.Align.START,
            margin_start=5,
            margin_end=5
        )
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
            initial_name = 'overview-masvisgtk.' + file_ext
        else: # detailed
            initial_name = self.tab_view.get_selected_page().get_child().a_file.file_name + '-masvisgtk.' + file_ext

        self.on_make_filters(save_dialog)
        save_dialog.set_initial_folder(Gio.File.new_for_path(os.path.expanduser('~')))
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
        save_dialog.set_initial_folder(Gio.File.new_for_path(os.path.expanduser('~')))
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

    # Save gif animation dialog.
    def on_save_animation_dialog(self, btn_save, dialog_animation_save):
        dialog_animation_save.close() # close previous dialog

        save_dialog = Gtk.FileDialog()
        save_dialog.set_modal(True)
        save_dialog.set_accept_label(_('Save'))
        save_dialog.set_title(_('Save Animation'))

        save_dialog.set_initial_folder(Gio.File.new_for_path(os.path.expanduser('~')))
        save_dialog.set_initial_name('animation.gif')
        save_dialog.save(self, None, self.app.on_save_animation_dialog_cb) # creates UI

    def on_file_information(self):
        page = self.tab_view.get_selected_page()
        if not page:
            return

        body = page.get_child().a_file.track

        dialog_information = Adw.AlertDialog()
        dialog_information.set_heading(_('File Information'))

        scrolled_textview = Gtk.ScrolledWindow()
        scrolled_textview.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        text_buffer = Gtk.TextBuffer()
        text_buffer.insert_markup(text_buffer.get_end_iter(), body, -1)
        text_view = Gtk.TextView(
            buffer=text_buffer,
            editable=False,
            justification=Gtk.Justification.FILL
        )
        text_view.set_name('text_view')
        text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        text_view.set_name('transparency')
        scrolled_textview.set_child(text_view)
        scrolled_textview.set_size_request(360, 480)
        dialog_information.set_extra_child(scrolled_textview)

        dialog_information.add_response('cancel',  _('Close'))
        dialog_information.present(self)

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

        btn_go = Gtk.Button(
            label=_('Go!'),
            tooltip_text=_('Compare tabs in separate window')
        )
        btn_go.connect('clicked', self.on_go_compare, dialog_compare, listview_canvas_selction, False)
        btn_go.set_name('btn_rounded')

        btn_go_all = Gtk.Button(
            label=_('☑ All!'),
            tooltip_text=_('Compare ALL tabs in separate window')
        )
        btn_go_all.connect('clicked', self.on_go_compare, dialog_compare, listview_canvas_selction, True)
        btn_go_all.set_name('btn_rounded')

        headerbar = Adw.HeaderBar()
        headerbar.pack_start(btn_go)
        headerbar.pack_end(btn_go_all)
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
        btn_check = Gtk.CheckButton(
            halign=Gtk.Align.START,
            margin_start=5,
            margin_end=5
        )
        box.append(btn_check)
        label = Gtk.Label(
            ellipsize=Pango.EllipsizeMode.END,
            hexpand=True,
            halign=Gtk.Align.START,
            margin_start=5,
            margin_end=5
        )
        box.append(label)
        list_item.set_child(box)

    def on_factory_bind_listview_compare_item(self, factory, list_item):
        box = list_item.get_child()
        data_item = list_item.get_item()
        box.set_tooltip_text(data_item.name + '\n\n' + data_item.path)
        box.get_first_child().connect('toggled', self.on_listview_compare_item_checked, data_item)
        box.get_last_child().set_text(data_item.name)

    # Handles Gtk.CheckButton to add item to comparison.
    def on_listview_compare_item_checked(self, btn, data_item):
        if data_item.checked == None:
            data_item.checked = True
        else:
            data_item.checked = not data_item.checked

    # Start tabs' comparision.
    def on_go_compare(self, btn, dialog_compare, listview_canvas_selction, all):
        # Create and check selection of data to compare.
        comparable_items = []
        if all:
            for item in listview_canvas_selction.get_model():
                comparable_items.append(item)
        else:
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

        # Shortcut key actions, F11, ESC.
        key_controller = Gtk.EventControllerKey.new()
        key_controller.connect('key-pressed', self.fullscreen_comparison_window, win)
        win.add_controller(key_controller)

        win.set_content(box)
        win.present()

    def on_animate_tabs_init(self):
        if self.tab_view.get_n_pages() < 2:
            self.app.on_error_dialog(_('Cannot Animate'), _('Too few tabs.'))
            return

        dialog_animate = Adw.Dialog()
        dialog_animate.set_size_request(480, 360)
        dialog_animate.set_follows_content_size(True) # Adw size problems.
        dialog_animate.set_title(_('Animate Tabs'))

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
            self.app.on_error_dialog(_('Cannot Animate'), _('Too few tabs.'))
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

        btn_animate = Gtk.Button(
            label=_('Animate'),
            tooltip_text=_('Animate tabs in separate window')
        )
        btn_animate.connect('clicked', self.on_animate_tabs, dialog_animate, listview_canvas_selction, False)
        btn_animate.set_name('btn_rounded')

        btn_animate_all = Gtk.Button(
            label=_('☑ All!'),
            tooltip_text=_('Animate ALL tabs in separate window')
        )
        btn_animate_all.connect('clicked', self.on_animate_tabs, dialog_animate, listview_canvas_selction, True)
        btn_animate_all.set_name('btn_rounded')

        headerbar = Adw.HeaderBar()
        headerbar.pack_start(btn_animate)
        headerbar.pack_end(btn_animate_all)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.append(headerbar)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_name('dialog_compare_scrolled')
        scrolled.set_child(listview_canvas)
        box.append(scrolled)

        dialog_animate.set_child(box)
        dialog_animate.present(self)

    def on_animate_tabs(self, btn, dialog_animate, listview_canvas_selction, all):
        # Create and check selection of data to compare.
        comparable_items = []
        if all:
            for item in listview_canvas_selction.get_model():
                comparable_items.append(item)
        else:
            for item in listview_canvas_selction.get_model():
                if item.checked:
                    comparable_items.append(item)

        if len(comparable_items) < 2:
            self.app.on_error_dialog(_('Cannot Animate'), _('Too few tabs.'))
            return

        dialog_animate.close()

        self.n_th_animation += 1

        # Comparison dialog.
        dialog_animation_save = Adw.Dialog()
        dialog_animation_save.set_follows_content_size(True) # Adw size problems.
        dialog_animation_save.set_title(_('Animation #' ) + str(self.n_th_animation))

        # Calculate initial window width.
        pic_section_width = 1080
        proposed_width = 2 * pic_section_width + 10

        scr_width = self.screen_width()
        if proposed_width > scr_width:
            dialog_animation_save.set_size_request(240, 120)
        else:
            dialog_animation_save.set_size_request(proposed_width, self.w_height)

        dialog_animation_save.spinner_animate_save = Gtk.Spinner()
        dialog_animation_save.spinner_animate_save.set_name('spinng_box_spinner')

        btn_animate_save = Gtk.Button(label='Save', tooltip_text=_('Save tabs to animated gif image'))
        btn_animate_save.connect('clicked', self.on_save_animation_dialog, dialog_animation_save)
        btn_animate_save.set_name('btn_animate_save')
        btn_animate_save.set_halign(Gtk.Align.CENTER)
        btn_animate_save.set_valign(Gtk.Align.CENTER)
        btn_animate_save.set_sensitive(False)

        dialog_animation_save.btn_animate_save = btn_animate_save

        label_animation_status = Gtk.Label(hexpand=True, ellipsize=Pango.EllipsizeMode.END)
        label_animation_status.set_name('label_animation_status')

        headerbar = Adw.HeaderBar()
        headerbar.pack_start(dialog_animation_save.spinner_animate_save)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.append(headerbar)

        box_status_info = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            hexpand=True,
            vexpand=True
        )
        box_status_info.set_halign(Gtk.Align.CENTER)
        box_status_info.append(label_animation_status)
        box_status_info.append(btn_animate_save)

        box.append(box_status_info)

        # Shortcut key actions, ESC.
        key_controller = Gtk.EventControllerKey.new()
        key_controller.connect('key-pressed', self.close_dialog_animation_save, dialog_animation_save)
        dialog_animation_save.add_controller(key_controller)

        dialog_animation_save.comparable_items = comparable_items
        dialog_animation_save.label_animation_status = label_animation_status

        dialog_animation_save.set_child(box)
        dialog_animation_save.present(self)

        dialog_animation_save.spinner_animate_save.start()

        # Indirect call, protecting UI.
        GLib.idle_add(self.on_animate_tabs_process, dialog_animation_save)

    # Convert canvas into RGBA Image array.
    def on_animate_tabs_process(self, dialog_animation_save):
        dialog_animation_save.label_animation_status.set_label(_('Processing images.'))
        try:
            self.animated_pil_images = []
            for item in dialog_animation_save.comparable_items:
                buff_w, buff_h = item.canvas.get_width_height()
                aspect_ratio = buff_w/buff_h
                self.animated_pil_images.append(Image.frombytes('RGBA', (buff_w, buff_h), item.canvas.buffer_rgba().tobytes()))
                dialog_animation_save.label_animation_status.set_label(_('Animated image ready for saving.'))
        except Exception as e:
            self.app.on_error_dialog(
                _('Animation Error'),
                _('Cannot create animation.\nPlotting canvas cannot be made into image.\n')
                + str(e)
            )
        dialog_animation_save.spinner_animate_save.stop()
        dialog_animation_save.btn_animate_save.set_sensitive(True)

    def close_dialog_animation_save(self, event_controller_key, keyval, keycode, state, dialog):
        if keyval == Gdk.KEY_Escape:
            dialog.close()

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

    def on_show_formats_dialog(self, formats):
        dialog_formats = Adw.AlertDialog()
        dialog_formats.set_heading(_('Supported Formats'))
        dialog_formats.set_body(self.app.formats)
        dialog_formats.add_response('cancel', _('Close'))
        response = dialog_formats.present(self)

    def on_show_manual_dialog(self):
        builder = Gtk.Builder()
        obj = builder.new_from_resource('/io/github/itprojects/MasVisGtk/gtk/manual-overlay.ui')
        dialog_manual = obj.get_object('manual_overlay')
        text_buffer = obj.get_object('text_buffer')
        text_buffer.insert_markup(text_buffer.get_end_iter(), understanding_graphs, -1)
        response = dialog_manual.present(self)
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
        about.set_translator_credits('ITProjects, John Peter SA')
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
