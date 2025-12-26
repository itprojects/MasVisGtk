#!/usr/bin/python3

'''
AB Classifier compares two audio files.

Version 1.0

Copyright 2025 ITProjects

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

Usage:

python ab_classifier.py

python ab_classifier.py --theme dark

follow, light, dark

The user selects tracks which are of equal duration.

Application:

1. Sets audio files into pipeline
2. Calculates track loudness and gain offsets
3. Calculates true peaks of the two files
4. Plays audio files, applying gain and true peaks to match level
5. Shows statistics for playback A/B track preference

GStreamer file types supported.
Locally installed FFMPEG required for loudness detection.
'''

import gi, datetime, os, random, re, subprocess, sys, threading

gi.require_version('Adw', '1')
gi.require_version('Gtk', '4.0')
gi.require_version('Gst', '1.0')
gi.require_version('GstPbutils', '1.0')
from gi.repository import Adw, Gdk, Gtk, GLib, Gio, GObject, Gst, GstPbutils

#import os # debugging GStreamer
#os.environ['GST_DEBUG'] = 'rgvolume:DEBUG' # element type name

Gst.init(None) # init GStreamer

class ABClassifierWindow(Adw.ApplicationWindow):

    app = None

    level_match_target_lufs = -14.0

    text_a = '<span weight=\"bold\" size=\"100pt\">A</span>'
    text_b = '<span weight=\"bold\" size=\"100pt\">B</span>'
    text_x = '<span weight=\"bold\" size=\"100pt\">X</span>'
    text_y = '<span weight=\"bold\" size=\"100pt\">Y</span>'

    swapped_tracks = False # False A plays A, True A plays B

    total_picks_made = 0

    count_a_abs = 0
    count_b_abs = 0

    text_counts_a = '% {}  \\  {}'
    text_counts_b = '{}  /  {} %'

    last_selected_ab = -1 # -1 for not set, 0 for A, 1 for B

    label_count_a = None
    label_count_b = None

    popover_track_a = None
    label_popover_track_a = None

    popover_track_b = None
    label_popover_track_b = None

    def __init__(self, title, *args, **kwargs):
        super(ABClassifierWindow, self).__init__(*args, **kwargs)

        self.app = kwargs.get('application', None)

        self.set_title('AB Classifier')

        self.set_size_request(700, 484)

        header = Adw.HeaderBar()

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.append(header)

        btn_stop = Gtk.Button(label='Stop', icon_name='stop-large-symbolic', tooltip_text='Stop playback')
        btn_stop.add_css_class('circular')
        btn_stop.add_css_class('btn_top')
        btn_stop.connect('clicked', self.on_stop, False)
        btn_stop.add_css_class('btn_stop')
        header.pack_start(btn_stop)

        self.btn_play = Gtk.Button(label='Play', icon_name='play-large-symbolic', tooltip_text='Play audio tracks')
        self.btn_play.add_css_class('circular')
        self.btn_play.add_css_class('btn_play')
        self.btn_play.connect('clicked', self.on_play)
        self.btn_play.set_valign(Gtk.Align.CENTER)
        header.pack_start(self.btn_play)

        self.btn_pause = Gtk.Button(label='Pause', icon_name='pause-large-symbolic', tooltip_text='Pause playback')
        self.btn_pause.add_css_class('circular')
        self.btn_pause.add_css_class('btn_pause')
        self.btn_pause.connect('clicked', self.on_pause)
        self.btn_pause.set_valign(Gtk.Align.CENTER)
        header.pack_start(self.btn_pause)

        box_popover = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        btn_spin_level_match_reset = Gtk.Button(label='-14', tooltip_text='Set -14 LUFS target level')
        btn_spin_level_match_reset.connect('clicked', self.on_reset_levels)
        btn_spin_level_match_reset.set_margin_end(8)
        box_popover.append(btn_spin_level_match_reset)

        self.adjustment_level_lufs = Gtk.Adjustment.new(-14, -23, -5, 1.0, 1.0, 1.0)
        self.spin_level_lufs = Gtk.SpinButton.new(self.adjustment_level_lufs, 1.0, 1)
        self.spin_level_lufs.connect('value-changed', self.on_level_match_target)
        self.spin_level_lufs.add_css_class('spin_level_match_lufs')
        self.spin_level_lufs.set_tooltip_text('Custom LUFS target level (default -14 LUFS)')
        self.spin_level_lufs.set_margin_start(5)
        self.spin_level_lufs.set_margin_end(5)
        box_popover.append(self.spin_level_lufs)

        self.btn_enable_level_match = Gtk.CheckButton(tooltip_text='Enable matching audio levels with True Peak LUFS')
        self.btn_enable_level_match.set_active(True)
        self.btn_enable_level_match.connect('notify::active', self.on_enable_level_match)
        self.btn_enable_level_match.set_margin_start(5)
        box_popover.append(self.btn_enable_level_match)

        self.btn_level_match = Gtk.MenuButton(icon_name='preferences-other-symbolic', tooltip_text='Level Match with True Peak')
        self.btn_level_match.add_css_class('circular')

        popover = Gtk.Popover()
        popover.set_child(box_popover)
        popover.set_default_widget(self.btn_enable_level_match)
        self.btn_level_match.set_popover(popover)
        header.pack_start(self.btn_level_match)

        self.btn_blind = Gtk.ToggleButton(label='Blind', icon_name='eye-open-negative-filled-symbolic', tooltip_text='Blind Mode OFF')
        self.btn_blind.add_css_class('circular')
        self.btn_blind.add_css_class('btn_blind')
        self.btn_blind.connect('clicked', self.on_blind)
        header.pack_start(self.btn_blind)

        # Changes application style
        btn_style = Gtk.MenuButton(icon_name='display-brightness-symbolic', tooltip_text='Change application style')
        btn_style.set_valign(Gtk.Align.CENTER)
        btn_style.add_css_class('circular')
        btn_style.add_css_class('btn_style')
        menu_style = Gio.Menu.new()
        menu_item_reset_1 = Gio.MenuItem.new('System', 'app.radio_group_style::system')
        menu_item_reset_2 = Gio.MenuItem.new('Light', 'app.radio_group_style::light')
        menu_item_reset_3 = Gio.MenuItem.new('Dark', 'app.radio_group_style::dark')
        menu_style.append_item(menu_item_reset_1)
        menu_style.append_item(menu_item_reset_2)
        menu_style.append_item(menu_item_reset_3)
        btn_style.set_popover(Gtk.PopoverMenu.new_from_model(menu_style))
        self.app.radio_action_style.connect('notify::state', self.on_style_change)
        header.pack_end(btn_style)

        btn_clear = Gtk.Button(label='Clear', icon_name='user-trash-symbolic', tooltip_text='Clear and reset')
        btn_clear.connect('clicked', self.on_clear)
        btn_clear.add_css_class('circular')
        btn_clear.add_css_class('btn_clear')
        header.pack_end(btn_clear)

        self.btn_reset_stats = Gtk.Button(icon_name='view-refresh-symbolic', tooltip_text='Reset counting statistics')
        self.btn_reset_stats.connect('clicked', self.on_reset_stats)
        self.btn_reset_stats.add_css_class('circular')
        self.btn_reset_stats.add_css_class('btn_reset_stats')
        self.btn_reset_stats.set_halign(Gtk.Align.CENTER)
        header.pack_end(self.btn_reset_stats)

        box_layout = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box_layout.set_halign(Gtk.Align.CENTER)
        box_layout.set_valign(Gtk.Align.CENTER)
        box_layout.set_hexpand(True)
        box_layout.set_vexpand(True)

        #######################################################################

        box_big_buttons = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box_big_buttons.set_margin_top(15)
        box_big_buttons.set_halign(Gtk.Align.CENTER)
        box_big_buttons.set_valign(Gtk.Align.CENTER)
        box_big_buttons.set_hexpand(True)
        box_big_buttons.set_vexpand(True)

        box_big_buttons_inner_top = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box_big_buttons_inner_top_ = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        self.label_a = Gtk.Label()
        self.label_a.set_use_markup(True)
        self.label_a.set_markup(self.text_a)
        self.btn_a = Gtk.Button()
        self.btn_a.connect('clicked', self.on_ab_click)
        self.btn_a.add_css_class('circular')
        self.btn_a.add_css_class('btn_a')
        self.btn_a.set_size_request(260, 260)
        self.btn_a.set_valign(Gtk.Align.CENTER)
        self.btn_a.set_child(self.label_a)
        box_big_buttons_inner_top_.append(self.btn_a)

        self.label_separator1 = Gtk.Label()
        self.label_separator1.set_text('\u2E3B')
        box_big_buttons_inner_top_.append(self.label_separator1)

        self.btn_pick = Gtk.Button(label='PICK')
        self.btn_pick.connect('clicked', self.on_pick)
        self.btn_pick.add_css_class('circular')
        self.btn_pick.add_css_class('btn_pick')
        self.btn_pick.set_size_request(60, 60)
        self.btn_pick.set_halign(Gtk.Align.CENTER)
        self.btn_pick.set_valign(Gtk.Align.CENTER)
        box_big_buttons_inner_top_.append(self.btn_pick)

        self.label_separator2 = Gtk.Label()
        self.label_separator2.set_text('\u2E3B')
        box_big_buttons_inner_top_.append(self.label_separator2)

        self.label_b = Gtk.Label()
        self.label_b.set_use_markup(True)
        self.label_b.set_markup(self.text_b)
        self.btn_b = Gtk.Button()
        self.btn_b.connect('clicked', self.on_ab_click)
        self.btn_b.add_css_class('circular')
        self.btn_b.add_css_class('btn_b')
        self.btn_b.set_size_request(260, 260)
        self.btn_a.set_valign(Gtk.Align.CENTER)
        self.btn_b.set_child(self.label_b)
        box_big_buttons_inner_top_.append(self.btn_b)

        self.box_big_buttons_inner_bottom = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.box_big_buttons_inner_bottom.set_hexpand(True)

        box_big_buttons_inner_top.append(box_big_buttons_inner_top_)

        #######################################################################

        self.track_progress = Gtk.ProgressBar()
        self.track_progress.set_tooltip_text('Seek playing track')
        self.track_progress.set_margin_top(15)
        self.track_progress.add_css_class('progressbar_track')
        box_big_buttons_inner_top.append(self.track_progress)

        gesture_click_progress = Gtk.GestureClick.new() # changes play location
        gesture_click_progress.connect('released', self.on_gesture_click_track)
        gesture_click_progress.set_button(1) # capture left-click events
        self.track_progress.add_controller(gesture_click_progress)

        #######################################################################

        box_big_buttons_inner_bottom_ = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box_big_buttons_inner_bottom_.set_hexpand(True)

        self.entry_a = Gtk.Entry()
        self.entry_a.set_halign(Gtk.Align.START)
        self.entry_a.set_placeholder_text('Track Label A')
        self.entry_a.set_alignment(0.5)
        self.entry_a.add_css_class('entry_track_label')
        self.entry_a.set_size_request(260, -1)
        self.entry_a.set_icon_sensitive(Gtk.EntryIconPosition.SECONDARY, True)
        self.entry_a.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY, 'user-trash-symbolic')
        self.entry_a.set_icon_tooltip_text(Gtk.EntryIconPosition.SECONDARY, 'Delete track A label')
        self.entry_a.set_margin_top(15)
        self.entry_a.set_hexpand(True)
        self.entry_a.connect('icon-press', self.on_clear_entry)
        evk_a = Gtk.EventControllerKey.new() # change focus if Esc key pressed
        evk_a.connect('key-pressed', lambda evk, keyval, keycode, state: self.set_focus(None) if keyval == Gdk.KEY_Escape else False)
        self.entry_a.add_controller(evk_a)
        box_big_buttons_inner_bottom_.append(self.entry_a)

        self.entry_b = Gtk.Entry()
        self.entry_b.set_halign(Gtk.Align.END)
        self.entry_b.set_placeholder_text('Track Label B')
        self.entry_b.set_alignment(0.5)
        self.entry_b.add_css_class('entry_track_label')
        self.entry_b.set_size_request(260, -1)
        self.entry_b.set_icon_sensitive(Gtk.EntryIconPosition.PRIMARY, True)
        self.entry_b.set_icon_from_icon_name(Gtk.EntryIconPosition.PRIMARY, 'user-trash-symbolic')
        self.entry_b.set_icon_tooltip_text(Gtk.EntryIconPosition.PRIMARY, 'Delete track B label')
        self.entry_b.set_margin_top(15)
        self.entry_b.set_hexpand(True)
        self.entry_b.connect('icon-press', self.on_clear_entry)
        evk_b = Gtk.EventControllerKey.new() # change focus if Esc key pressed
        evk_b.connect('key-pressed', lambda evk, keyval, keycode, state: self.set_focus(None) if keyval == Gdk.KEY_Escape else False)
        self.entry_b.add_controller(evk_b)
        box_big_buttons_inner_bottom_.append(self.entry_b)

        self.box_big_buttons_inner_bottom.append(box_big_buttons_inner_bottom_)

        box_big_buttons.append(box_big_buttons_inner_top)
        box_big_buttons.append(self.box_big_buttons_inner_bottom)

        box_layout.append(box_big_buttons)

        #######################################################################

        self.box_track_buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.box_track_buttons.set_hexpand(True)
        self.box_track_buttons.set_margin_top(15)
        self.box_track_buttons.set_margin_bottom(15)

        box_left_side_track_buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box_left_side_track_buttons.set_size_request(260, -1)

        self.label_count_a = Gtk.Label(tooltip_text='Track A counting statistics')
        self.label_count_a.add_css_class('label_count')
        self.label_count_a.set_text(self.text_counts_a.format(0, 0))
        self.label_count_a.set_halign(Gtk.Align.START)
        box_left_side_track_buttons.append(self.label_count_a)

        box_left_spacer = Gtk.Box()
        box_left_spacer.set_hexpand(True)
        box_left_side_track_buttons.append(box_left_spacer)

        self.img_left_track_status = Gtk.Image(icon_name='emblem-ok-symbolic')
        self.img_left_track_status.set_margin_end(5)
        self.img_left_track_status.set_visible(False)
        box_left_side_track_buttons.append(self.img_left_track_status)

        btn_left_track_info = Gtk.MenuButton(icon_name='dialog-information-symbolic', tooltip_text='Track A information')
        btn_left_track_info.set_direction(Gtk.ArrowType.UP)
        btn_left_track_info.add_css_class('btn_left_track_info')
        btn_left_track_info.connect('activate', self.on_show_track_info, True)
        box_left_side_track_buttons.append(btn_left_track_info)

        self.popover_track_a = Gtk.Popover.new()
        box_label_popover_a = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.label_popover_track_a = Gtk.Label.new()
        self.label_popover_track_a.add_css_class('label_popover_track')
        self.label_popover_track_a.set_text('No Track A')
        box_label_popover_a.append(self.label_popover_track_a)

        box_label_popover_a.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL, margin_top=10, margin_bottom=10))

        self.label_popover_track_a_path = Gtk.Label.new()
        self.label_popover_track_a_path.set_wrap(True)
        self.label_popover_track_a_path.set_wrap_mode(Gtk.WrapMode.CHAR)
        self.label_popover_track_a_path.set_max_width_chars(40) # required by wrap
        self.label_popover_track_a_path.set_visible(False)
        box_label_popover_a.append(self.label_popover_track_a_path)

        self.popover_track_a.set_child(box_label_popover_a)
        btn_left_track_info.set_popover(self.popover_track_a)

        self.btn_left_track_load = Gtk.Button(icon_name='emblem-music-symbolic', tooltip_text='Set track A')
        self.btn_left_track_load.add_css_class('btn_track_a_load')
        self.btn_left_track_load.connect('clicked', self.on_set_file_dialog, True)
        box_left_side_track_buttons.append(self.btn_left_track_load)

        self.btn_left_track_reset = Gtk.Button(icon_name='user-trash-symbolic', tooltip_text='Unset track A')
        self.btn_left_track_reset.add_css_class('btn_track_a_reset')
        self.btn_left_track_reset.connect('clicked', self.on_unset_file, True)
        box_left_side_track_buttons.append(self.btn_left_track_reset)

        self.box_track_buttons.append(box_left_side_track_buttons)

        #######################################################################

        box_spacer_middle = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box_spacer_middle.set_hexpand(True)
        box_spacer_middle.set_halign(Gtk.Align.CENTER)
        box_spacer_middle.set_size_request(140, -1)
        self.box_track_buttons.append(box_spacer_middle)

        #######################################################################

        box_right_side_track_buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box_right_side_track_buttons.set_size_request(260, -1)

        self.btn_right_track_reset = Gtk.Button(icon_name='user-trash-symbolic', tooltip_text='Unset track B')
        self.btn_right_track_reset.add_css_class('btn_track_b_reset')
        self.btn_right_track_reset.connect('clicked', self.on_unset_file, False)
        box_right_side_track_buttons.append(self.btn_right_track_reset)

        self.btn_right_track_load = Gtk.Button(icon_name='emblem-music-symbolic', tooltip_text='Set track B')
        self.btn_right_track_load.add_css_class('btn_track_b_load')
        self.btn_right_track_load.connect('clicked', self.on_set_file_dialog, False)
        box_right_side_track_buttons.append(self.btn_right_track_load)

        btn_right_track_info = Gtk.MenuButton(icon_name='dialog-information-symbolic', tooltip_text='Track B information')
        btn_right_track_info.set_direction(Gtk.ArrowType.UP)
        btn_right_track_info.add_css_class('btn_right_track_info')
        btn_right_track_info.connect('activate', self.on_show_track_info, False)
        box_right_side_track_buttons.append(btn_right_track_info)

        self.popover_track_b = Gtk.Popover.new()
        box_label_popover_b = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.label_popover_track_b = Gtk.Label()
        self.label_popover_track_b.add_css_class('label_popover_track')
        self.label_popover_track_b.set_text('No Track B')
        box_label_popover_b.append(self.label_popover_track_b)

        box_label_popover_b.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL, margin_top=10, margin_bottom=10))

        self.label_popover_track_b_path = Gtk.Label.new()
        self.label_popover_track_b_path.set_wrap(True)
        self.label_popover_track_b_path.set_wrap_mode(Gtk.WrapMode.CHAR)
        self.label_popover_track_b_path.set_max_width_chars(40) # required by wrap
        self.label_popover_track_b_path.set_visible(False)
        box_label_popover_b.append(self.label_popover_track_b_path)

        self.popover_track_b.set_child(box_label_popover_b)
        btn_right_track_info.set_popover(self.popover_track_b)

        self.img_right_track_status = Gtk.Image(icon_name='emblem-ok-symbolic')
        self.img_right_track_status.set_margin_start(5)
        self.img_right_track_status.set_visible(False)
        box_right_side_track_buttons.append(self.img_right_track_status)

        box_right_spacer = Gtk.Box()
        box_right_spacer.set_hexpand(True)
        box_right_side_track_buttons.append(box_right_spacer)

        self.label_count_b = Gtk.Label(tooltip_text='Track B counting statistics')
        self.label_count_b.add_css_class('label_count')
        self.label_count_b.set_text(self.text_counts_b.format(0, 0))
        self.label_count_b.set_halign(Gtk.Align.END)
        box_right_side_track_buttons.append(self.label_count_b)

        self.box_track_buttons.append(box_right_side_track_buttons)

        box_layout.append(self.box_track_buttons)

        #######################################################################

        box.append(box_layout)
        self.set_content(box)

        # Extra signals.
        self.app.player_pipeline.connect('update-widgets-sensitivity', self.on_widgets_sensitive)
        self.app.player_pipeline.connect('update-progress-position', self.on_update_track_progress)
        self.app.player_pipeline.connect('end-of-stream', self.on_stop)
        self.app.player_pipeline.connect('error-occured', self.on_error_dialog_by_signal)

    def on_play(self, btn):
        if self.app.track_a_path and self.app.track_b_path:
            state = self.app.player_pipeline.get_state()
            if state != None and state != Gst.State.PLAYING:
                self.app.player_pipeline.play()
        else:
            self.on_error_dialog('Cannot Play', 'Set both tracks first.')

    def on_pause(self, btn):
        state = self.app.player_pipeline.get_state()
        if state != None and state == Gst.State.PLAYING:
            self.app.player_pipeline.pause()
        else:
            self.on_error_dialog('Cannot Pause', 'Unusial GStreamer state.')

    def on_stop(self, btn, end_of_stream):
        state = self.app.player_pipeline.get_state()
        if state != None and (state == Gst.State.PLAYING or state == Gst.State.PAUSED):
            if end_of_stream: # progress 1
                self.app.player_pipeline.stop(1)
            else: # progress 0
                self.app.player_pipeline.stop(0)

    def on_enable_level_match(self, btn, toggled):
        if btn.get_active():
            if self.btn_level_match.has_css_class('btn_level_match_shade'):
                self.btn_level_match.remove_css_class('btn_level_match_shade')
        else:
            if not self.btn_level_match.has_css_class('btn_level_match_shade'):
                self.btn_level_match.add_css_class('btn_level_match_shade')

    def on_level_match_target(self, btn):
        self.level_match_target_lufs = btn.get_value()
        if self.app.track_a_path != None:
            self.app.track_a_gain_to_be_added = round(self.level_match_target_lufs - self.app.track_a_l_kg, 2)
        self.app.player_pipeline.set_tag_gain(True)
        if self.app.track_b_path != None:
            self.app.track_b_gain_to_be_added = round(self.level_match_target_lufs - self.app.track_b_l_kg, 2)
        self.app.player_pipeline.set_tag_gain(False)

    def on_reset_levels(self, btn):
        self.spin_level_lufs.set_value(-14) # -14 LUFS

    def on_blind(self, btn):
        if btn.get_active():
            self.label_a.set_markup(self.text_x)
            self.label_b.set_markup(self.text_y)

            self.box_big_buttons_inner_bottom.set_visible(False)
            self.box_track_buttons.set_visible(False)

            btn.set_icon_name('eye-not-looking-symbolic')
            btn.set_tooltip_text('Blind Mode ON')

            # Randomly swap tracks or not.
            self.on_swap_tracks_on_random()
        else:
            self.label_a.set_markup(self.text_a)
            self.label_b.set_markup(self.text_b)

            self.box_big_buttons_inner_bottom.set_visible(True)
            self.box_track_buttons.set_visible(True)

            btn.set_icon_name('eye-open-negative-filled-symbolic')
            btn.set_tooltip_text('Blind Mode OFF')

            # Restore tracks to normal places.
            self.swapped_tracks = False

        self.on_assign_tracks_volume_mute()

    def on_assign_tracks_volume_mute(self):
        if self.last_selected_ab == 0:
            if self.swapped_tracks:
                self.app.player_pipeline.set_tracks_volume_mute(True, False) # swapped A
            else:
                self.app.player_pipeline.set_tracks_volume_mute(False, True) # normal A
        elif self.last_selected_ab == 1:
            if self.swapped_tracks:
                self.app.player_pipeline.set_tracks_volume_mute(False, True) # swapped B
            else:
                self.app.player_pipeline.set_tracks_volume_mute(True, False) # normal B
        else:
            pass

    def on_swap_tracks_on_random(self):
        self.swapped_tracks = random.choice([True, False])

    def on_reset_stats(self, btn):
        self.total_picks_made = 0
        self.count_a_abs = 0
        self.count_b_abs = 0
        self.label_count_a.set_text(self.text_counts_a.format(0, 0))
        self.label_count_b.set_text(self.text_counts_b.format(0, 0))

    def on_pick(self, btn):
        if self.last_selected_ab == 0: # A active
            self.total_picks_made += 1
            if self.swapped_tracks:
                self.count_b_abs += 1 # swapped A
            else:
                self.count_a_abs += 1 # normal A
            count_a_percent = round(100 * (self.count_a_abs / self.total_picks_made), 1)
            count_b_percent = round(100 * (self.count_b_abs / self.total_picks_made), 1)
            self.label_count_a.set_text(self.text_counts_a.format(count_a_percent, self.count_a_abs))
            self.label_count_b.set_text(self.text_counts_b.format(self.count_b_abs, count_b_percent))
        elif self.last_selected_ab == 1: # B active
            self.total_picks_made += 1
            if self.swapped_tracks:
                self.count_a_abs += 1 # swapped B
            else:
                self.count_b_abs += 1 # normal B
            count_a_percent = round(100 * (self.count_a_abs / self.total_picks_made), 1)
            count_b_percent = round(100 * (self.count_b_abs / self.total_picks_made), 1)
            self.label_count_a.set_text(self.text_counts_a.format(count_a_percent, self.count_a_abs))
            self.label_count_b.set_text(self.text_counts_b.format(self.count_b_abs, count_b_percent))
        else: # -1, neither A nor B is active
            pass

    def on_ab_click(self, btn):
        if btn == self.btn_a:
            if self.last_selected_ab != 0: # prevent re-selection of track A
                self.last_selected_ab = 0
                if not self.btn_a.has_css_class('btn_active_style'):
                    self.btn_a.add_css_class('btn_active_style')
                    self.label_separator1.add_css_class('label_active_style')
                if self.btn_b.has_css_class('btn_active_style'):
                    self.btn_b.remove_css_class('btn_active_style')
                    self.label_separator2.remove_css_class('label_active_style')
        else:
            if self.last_selected_ab != 1: # prevent re-selection of track B
                self.last_selected_ab = 1
                if not self.btn_b.has_css_class('btn_active_style'):
                    self.btn_b.add_css_class('btn_active_style')
                    self.label_separator2.add_css_class('label_active_style')
                if self.btn_a.has_css_class('btn_active_style'):
                    self.btn_a.remove_css_class('btn_active_style')
                    self.label_separator1.remove_css_class('label_active_style')

        if self.btn_blind.get_active():
            self.on_swap_tracks_on_random()

        self.on_assign_tracks_volume_mute()

    def on_gesture_click_track(self, gesture, n_press, x, y):
        fraction = x / self.track_progress.get_width()
        if self.app.track_a_path and self.app.track_b_path: # check for existing tracks
            self.app.player_pipeline.set_position(
                int(fraction * self.app.player_pipeline.seconds_to_nanoseconds(self.app.playback_duration))
            )
        else:
            print('Tracks are not properly set, cannot change playback location.')

    # Only Track A is used, the user is responsible for providing equal duration tracks.
    def on_update_track_progress(self, player_pipeline, fraction):
        self.track_progress.set_fraction(fraction)

    def on_show_track_info(self, btn, a_or_b):
        if a_or_b:
            self.popover_track_a.popup()
        else:
            self.popover_track_b.popup()

    def on_set_file_dialog(self, btn, a_or_b):
        dialog = Gtk.FileDialog()
        dialog.set_modal(True)
        dialog.set_title(f'Set {'A' if a_or_b else 'B'} File')
        dialog.a_or_b = a_or_b
        dialog.open(self, None, self.on_set_file_dialog_cb)

    def on_set_file_dialog_cb(self, dialog, response):
        try:
            file = dialog.open_finish(response)

            info = file.query_info('standard::content-type,standard::size', Gio.FileQueryInfoFlags.NONE, None)
            mimetype = info.get_content_type()

            if info.get_attribute_uint64('standard::size') < 1:
                raise ValueError(f'File size is 0.\n\n{file.get_path()}')

            if (mimetype is None) or (not mimetype.lower().startswith('audio/')):
                raise ValueError(f'File type is not supported.\n\nType: {mimetype}')

            if dialog.a_or_b:
                self.app.track_a_path = file.get_path()
            else:
                self.app.track_b_path = file.get_path()

            self.spinning_dialog(dialog.a_or_b)
        except GLib.GError:
            pass # Ignore cancel: 'gtk-dialog-error-quark: Dismissed by user'
        except Exception as e:
            error = 'Error'
            str_e = str(e)
            print(f'{error}: {str_e.replace('\n', ' ')}')
            self.on_error_dialog(error, str_e)

    def spinning_dialog(self, a_or_b):
        dialog = Adw.Dialog()
        dialog.set_follows_content_size(True) # Adw size problems.
        dialog.set_size_request(240, 160)
        dialog.set_title('Processing Audio...')

        headerbar = Adw.HeaderBar()

        spinner = Gtk.Spinner()
        spinner.set_margin_start(10)
        spinner.start()

        headerbar.pack_start(spinner)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.append(headerbar)

        label = Gtk.Label(label='...')
        label.set_halign(Gtk.Align.CENTER)
        label.set_valign(Gtk.Align.CENTER)
        label.set_hexpand(True)
        label.set_vexpand(True)
        label.set_margin_top(15)
        label.set_margin_end(15)
        label.set_margin_bottom(15)
        label.set_margin_start(15)
        label.set_wrap(True)
        label.set_wrap_mode(1) # CHAR
        label.set_text(self.app.track_a_path if a_or_b else self.app.track_b_path)

        box.append(label)

        dialog.set_child(box)
        dialog.present(self)

        # Probe audio data with FFMPEG.
        thread = threading.Thread(target=self.app.true_peaks_and_loudness, args=(dialog, a_or_b,))
        thread.start()

    def ready_indicator(self, a_or_b):
        num_channels = 1
        if a_or_b:
            self.label_popover_track_a_path.set_text(self.app.track_a_path)
            self.label_popover_track_a_path.set_visible(True)
            result_text = f'Target Loudness: {self.adjustment_level_lufs.get_value()} LUFS\n'
            result_text += f' Track Loudness: {self.app.track_a_l_kg} LUFS\n'
            result_text += f'    Replay Gain: {self.app.track_a_gain_to_be_added} dB\n'
            result_text += f'      True Peak: {self.app.track_a_true_peak} dBTP'
            self.label_popover_track_a.set_text(result_text)
            self.img_left_track_status.set_visible(True)
        else:
            self.label_popover_track_b_path.set_text(self.app.track_b_path)
            self.label_popover_track_b_path.set_visible(True)
            result_text = f'Target Loudness: {self.adjustment_level_lufs.get_value()} LUFS\n'
            result_text += f' Track Loudness: {self.app.track_b_l_kg} LUFS\n'
            result_text += f'    Replay Gain: {self.app.track_b_gain_to_be_added} dB\n'
            result_text += f'      True Peak: {self.app.track_b_true_peak} dBTP'
            self.label_popover_track_b.set_text(result_text)
            self.img_right_track_status.set_visible(True)

    def on_unset_file(self, btn, a_or_b):
        if a_or_b:
            self.app.track_a_path = None 
            self.app.track_a_gain_to_be_added = 0.0
            self.app.track_a_l_kg = 0.0
            self.app.track_a_true_peak = 0.0
            self.app.track_a_true_peak_normalised = 0.0
            self.app.track_a_approximate_duration = 0.0
            self.label_popover_track_a.set_text('No Track A')
            self.label_popover_track_a_path.set_visible(False)
            self.img_left_track_status.set_visible(False)
        else:
            self.app.track_b_path = None 
            self.app.track_a_gain_to_be_added = 0.0
            self.app.track_b_l_kg = 0.0
            self.app.track_b_true_peak = 0.0
            self.app.track_b_true_peak_normalised = 0.0
            self.app.track_b_approximate_duration = 0.0
            self.label_popover_track_b.set_text('No Track B')
            self.label_popover_track_b_path.set_visible(False)
            self.img_right_track_status.set_visible(False)

    def on_widgets_sensitive(self, calling_widget, on_or_off=None):
        if on_or_off == None:
            return self.btn_level_match.get_sensitive() == True
        else: # True/False
            self.btn_level_match.set_sensitive(on_or_off)
            self.entry_a.set_sensitive(on_or_off)
            self.entry_b.set_sensitive(on_or_off)
            self.btn_left_track_load.set_sensitive(on_or_off)
            self.btn_right_track_load.set_sensitive(on_or_off)
            self.btn_left_track_reset.set_sensitive(on_or_off)
            self.btn_right_track_reset.set_sensitive(on_or_off)

    def on_error_dialog_by_signal(self, widget, heading, body):
        GLib.idle_add(self.on_error_dialog_present, heading, body)

    def on_error_dialog(self, heading, body):
        GLib.idle_add(self.on_error_dialog_present, heading, body)

    def on_error_dialog_present(self, heading, body):
        dialog_err = Adw.AlertDialog()
        dialog_err.set_heading(heading)
        #dialog_err.set_body(body)
        err_text = Gtk.Label() # to copy message text
        err_text.set_selectable(True)
        err_text.set_text(body)
        dialog_err.set_extra_child(err_text)
        dialog_err.add_response('cancel',  'Close')
        dialog_err.present(self)

    def on_style_change(self, action, gparam):
        style = action.get_state().get_string()
        if style == 'system': # (0) follow system
            Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.DEFAULT)
            self.app.radio_action_style.set_state(GLib.Variant.new_string('system'))
        elif style == 'light': # (1) light
            Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
            self.app.radio_action_style.set_state(GLib.Variant.new_string('light'))
        elif style == 'dark': # (2) dark
            Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK)
            self.app.radio_action_style.set_state(GLib.Variant.new_string('dark'))

    def on_clear_entry(self, entry, position):
        entry.set_text('')

    def on_clear(self, btn):
        self.on_unset_file(None, True)
        self.on_unset_file(None, False)
        self.on_reset_stats(None)
        self.on_stop(None, False)
        if self.btn_blind.get_active():
            self.btn_blind.emit("clicked") # also triggers on_blind()

class PlayerPipeline(GObject.GObject):

    __gtype_name__ = 'PlayerPipeline'

    __gsignals__ = {
        'update-widgets-sensitivity': (GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_BOOLEAN,)),
        'update-progress-position': (GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_FLOAT,)),
        'end-of-stream': (GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_BOOLEAN,)),
        'error-occured': (GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_STRING, GObject.TYPE_STRING,))
    }

    # For reference.
    #self.emit('update-progress-position', fraction) # float
    #self.emit('end-of-stream', eos) # bool
    #self.emit('error-occured', heading, error) # string

    # State Transition Workflow
    #
    # NULL → READY: The element prepares resources, such as opening devices.
    #               If resources are unavailable, the transition fails.
    # READY → PAUSED: Pads are activated, and streaming threads are started.
    #                 Sinks return ASYNC until they receive the first buffer or an End-of-Stream (EOS) event.
    # PAUSED → PLAYING: The pipeline synchronizes with the clock, and sinks begin rendering data.
    # PLAYING → PAUSED: The pipeline calculates the running time and pauses rendering.
    #                    Sinks may return ASYNC, if no buffer is pending.
    # PAUSED → READY: Streaming threads stop, pads are deactivated.
    # READY → NULL: Resources are released, the element resets its internal state.
    #
    # pre-amp + album gain (if album-mode and album tags exist)
    # pre-amp + track gain (if track gain exists, but no album-mode or album tags)
    # pre-amp + fallback-gain (if no ReplayGain tags at all)
    #
    # GST_TAG_TRACK_GAIN range -60 dB to +12 dB, 0 dB for no change.

    app = None

    broken_pipeline = None # None - good, error string - broken pipeline

    timer_id = None

    bus = None

    pipeline = None
    filesrcA = None
    tag_injectA = None
    rgvolumeA = None
    volumeA = None
    queueA = None
    filesrcB = None
    tag_injectB = None
    rgvolumeB = None
    volumeB = None
    queueB = None

    def __init__(self, app):
        super().__init__()

        self.app = app

        self.pipeline = Gst.Pipeline.new('ABClassifier-Audio-Pipeline')

        self.filesrcA = Gst.ElementFactory.make('filesrc', 'file-source-A')
        decodebinA = Gst.ElementFactory.make('decodebin', 'decode-bin-A')
        self.tag_injectA = Gst.ElementFactory.make("taginject", "taginject-A")
        self.rgvolumeA = Gst.ElementFactory.make('rgvolume', 'rgvolume-A')
        audioconvertA = Gst.ElementFactory.make('audioconvert', 'audio-convert-A')
        audioresampleA = Gst.ElementFactory.make('audioresample', 'audio-resample-A')
        self.volumeA = Gst.ElementFactory.make('volume', 'volume-A')
        self.volumeA.set_property('mute', False)
        self.queueA = Gst.ElementFactory.make('queue', 'queue-A')

        self.filesrcB = Gst.ElementFactory.make('filesrc', 'file-source-B')
        decodebinB = Gst.ElementFactory.make('decodebin', 'decode-bin-B')
        self.tag_injectB = Gst.ElementFactory.make("taginject", "taginject-B")
        self.rgvolumeB = Gst.ElementFactory.make('rgvolume', 'rgvolume-B')
        audioconvertB = Gst.ElementFactory.make('audioconvert', 'audio-convert-B')
        audioresampleB = Gst.ElementFactory.make('audioresample', 'audio-resample-B')
        self.volumeB = Gst.ElementFactory.make('volume', 'volume-B')
        self.volumeB.set_property('mute', False)
        self.queueB = Gst.ElementFactory.make('queue', 'queue-B')

        audiomixer = Gst.ElementFactory.make('audiomixer', 'audio-mixer')
        autoaudiosink = Gst.ElementFactory.make('autoaudiosink', 'audio-sink')

        self.pipeline.add(self.filesrcA)
        self.pipeline.add(decodebinA)
        self.pipeline.add(self.tag_injectA)
        self.pipeline.add(self.rgvolumeA)
        self.pipeline.add(audioconvertA)
        self.pipeline.add(audioresampleA)
        self.pipeline.add(self.volumeA)
        self.pipeline.add(self.queueA)

        self.pipeline.add(self.filesrcB)
        self.pipeline.add(decodebinB)
        self.pipeline.add(self.tag_injectB)
        self.pipeline.add(self.rgvolumeB)
        self.pipeline.add(audioconvertB)
        self.pipeline.add(audioresampleB)
        self.pipeline.add(self.volumeB)
        self.pipeline.add(self.queueB)

        self.pipeline.add(audiomixer)
        self.pipeline.add(autoaudiosink)

        # Track A.

        if not self.filesrcA.link(decodebinA):
            error = 'GStreamer Pipeline Failure: Could not link filesrcA to decodebinA'
            print(error)
            self.broken_pipeline = error
            return

        decodebinA.connect('pad-added', self.on_pad_added, self.tag_injectA)

        if not self.tag_injectA.link(self.rgvolumeA):
            error = 'GStreamer Pipeline Failure: Could not link tag_injectA to rgvolumeA'
            print(error)
            self.broken_pipeline = error
            return

        if not self.rgvolumeA.link(audioconvertA):
            error = 'GStreamer Pipeline Failure: Could not link rgvolumeA to audioconvertA'
            print(error)
            self.broken_pipeline = error
            return

        if not audioconvertA.link(audioresampleA):
            error = 'GStreamer Pipeline Failure: Could not link audioconvertA to audioresampleA'
            print(error)
            self.broken_pipeline = error
            return

        if not audioresampleA.link(self.volumeA):
            error = 'GStreamer Pipeline Failure: Could not link audioresampleA to volumeA'
            print(error)
            self.broken_pipeline = error
            return

        if not self.volumeA.link(self.queueA):
            error = 'GStreamer Pipeline Failure: Could not link volumeA to queueA'
            print(error)
            self.broken_pipeline = error
            return

        if not self.queueA.link(audiomixer):
            error = 'GStreamer Pipeline Failure: Could not link queueA to audiomixer'
            print(error)
            self.broken_pipeline = error
            return

        # Track B.

        if not self.filesrcB.link(decodebinB):
            error = 'GStreamer Pipeline Failure: Could not link filesrcB to decodebinB'
            print(error)
            self.broken_pipeline = error
            return

        decodebinB.connect('pad-added', self.on_pad_added, self.tag_injectB)

        if not self.tag_injectB.link(self.rgvolumeB):
            error = 'GStreamer Pipeline Failure: Could not link tag_injectB to rgvolumeB'
            print(error)
            self.broken_pipeline = error
            return

        if not self.rgvolumeB.link(audioconvertB):
            error = 'GStreamer Pipeline Failure: Could not link rgvolumeB to audioconvertB'
            print(error)
            self.broken_pipeline = error
            return

        if not audioconvertB.link(audioresampleB):
            error = 'GStreamer Pipeline Failure: Could not link audioconvertB to audioresampleB'
            print(error)
            self.broken_pipeline = error
            return

        if not audioresampleB.link(self.volumeB):
            error = 'GStreamer Pipeline Failure: Could not link audioresampleB to volumeB'
            print(error)
            self.broken_pipeline = error
            return

        if not self.volumeB.link(self.queueB):
            error = 'GStreamer Pipeline Failure: Could not link volumeB to queueB'
            print(error)
            self.broken_pipeline = error
            return

        if not self.queueB.link(audiomixer):
            error = 'GStreamer Pipeline Failure: Could not link queueB to audiomixer'
            print(error)
            self.broken_pipeline = error
            return

        if not audiomixer.link(autoaudiosink):
            error = 'GStreamer Pipeline Failure: Could not link audiomixer to autoaudiosink'
            print(error)
            self.broken_pipeline = error
            return

        # Disable any interfering album ReplayGain tags.
        self.rgvolumeA.set_property('album-mode', False)
        self.rgvolumeB.set_property('album-mode', False)

        # Adjust latency to quickly apply audio switching between tracks.
        self.queueA.set_property('max-size-time', 100000000) # limits to 100ms of audio
        self.queueA.set_property('max-size-buffers', 1) # limits to a single buffer (tight)
        self.queueA.set_property('max-size-bytes', 0) # disables byte-count limit (stop overriding time/buffer)

        self.queueB.set_property('max-size-time', 100000000) # limits to 100ms of audio
        self.queueB.set_property('max-size-buffers', 1) # limits to a single buffer (tight)
        self.queueB.set_property('max-size-bytes', 0) # disables byte-count limit (stop overriding time/buffer)

        # Catch Gst.Bus messages.
        self.bus = self.pipeline.get_bus()
        self.bus.add_watch(GLib.PRIORITY_DEFAULT, self.bus_callback)

    def bus_callback(self, bus, message):
        match message.type:
            #case Gst.MessageType.STATE_CHANGED:
            #    old_state, new_state, pending_state = message.parse_state_changed()
            #    print(f"State changed from {Gst.Element.state_get_name(old_state)} to {Gst.Element.state_get_name(new_state)}")
            #case Gst.MessageType.ELEMENT:
            #    structure = message.get_structure()
            #    if structure.get_name().startswith('rgvolume'):
            #        print(f'ReplayGain ({structure.get_name()}): {structure.get_value('gain')} dB')
            case Gst.MessageType.ERROR:
                error, debug = message.parse_error()
                print('Error in Gstreamer bus_callback(): ' + error.message)
                self.emit('error-occured', 'GStreamer Bus Error', error.message)
            case Gst.MessageType.EOS:
                self.emit('end-of-stream', True)
            case _:
                pass

        return True # keep watching

    def on_pad_added(self, element, pad, target_element):
        string = pad.query_caps(None).to_string()
        if string.startswith('audio/x-raw'):
            sink_pad = target_element.get_static_pad('sink')
            if not sink_pad.is_linked():
                if pad.link(sink_pad) != Gst.PadLinkReturn.OK:
                    print(f'ERROR: Could not link {pad.get_name()} to {sink_pad.get_name()}')
                else:
                    return True # print(f'Linked {pad.get_name()} to {sink_pad.get_name()}')

    def set_media(self, a_or_b): # R128_TRACK_GAIN
        self.set_state(Gst.State.READY)
        if a_or_b:
            self.filesrcA.set_property('location', self.app.track_a_path)
        else:
            self.filesrcB.set_property('location', self.app.track_b_path)
        self.set_tag_gain(a_or_b)

    def set_tag_gain(self, a_or_b):
        if a_or_b == True:
            self.tag_injectA.set_property(
                'tags',
                f'replaygain-track-gain={self.app.track_a_gain_to_be_added}, replaygain-track-peak={self.app.track_a_true_peak_normalised}'
            )
        else:
            self.tag_injectB.set_property(
                'tags',
                f'replaygain-track-gain={self.app.track_b_gain_to_be_added}, replaygain-track-peak={self.app.track_b_true_peak_normalised}'
            )

    def get_state(self):
        result, state, pending = self.pipeline.get_state(3 * Gst.SECOND)
        if result == Gst.StateChangeReturn.SUCCESS:
            return state
        else:
            return None

    def set_state(self, state):
        return self.pipeline.set_state(state) != Gst.StateChangeReturn.FAILURE # SUCCESS can be multiple states

    def play(self): # basic playback methods
        if self.set_state(Gst.State.PLAYING):
            self.emit('update-widgets-sensitivity', False) # insensitive widgets
            self.progress_update_ui(True)
        else:
            error = 'ERROR in play() Gst.StateChangeReturn.FAILURE'
            print(error)
            self.emit('error-occured', 'Playback Error', error)
            self.progress_update_ui(False)

    def pause(self):
        if self.set_state(Gst.State.PAUSED):
            self.emit('update-widgets-sensitivity', True) # sensitive widgets
            self.progress_update_ui(False)
        else:
            error = 'ERROR in pause() Gst.StateChangeReturn.FAILURE'
            print(error)
            self.emit('error-occured', 'Playback Error', error)

    def stop(self, specific):
        if self.set_state(Gst.State.READY):
            self.emit('update-widgets-sensitivity', True) # sensitive widgets
            self.update_position(specific) # final update
            self.set_position(0)
        else:
            error = 'ERROR in stop() Gst.StateChangeReturn.FAILURE'
            print(error)
            self.emit('error-occured', 'Playback Error', error)

        self.progress_update_ui(False)

    def progress_update_ui(self, start_or_top):
        if start_or_top:
            # UI track progressbar position update
            #if GLib.MainContext.default().find_source_by_id(self.timer_id) != None:
            if not self.timer_id:
                self.timer_id = GLib.timeout_add_seconds(1, self.update_position)
        else:
            # stop track progress position updates
            if self.timer_id:
                GLib.source_remove(self.timer_id)
                self.timer_id = None

    def get_position(self):
        result, value = self.pipeline.query_position(Gst.Format.TIME)
        if result:
            return self.nanoseconds_to_seconds(value) # stream position in nanoseconds
        else:
            return -1 # failed query, unknown position

    def set_position(self, pos): # nanosecond position
        self.pipeline.seek(
            1.0,
            Gst.Format.TIME, # time in nanoseconds
            Gst.SeekFlags.FLUSH,
            Gst.SeekType.SET,
            pos,
            Gst.SeekType.NONE,
            self.get_duration()
        )

    # update track progressbar position every second
    def update_position(self, specific_position=-1.0): # -1.0 for normal playback
        if specific_position < 0: # playing state update
            self.emit(
                'update-progress-position',
                self.get_position() / self.app.playback_duration
            )
        else:
            self.emit('update-progress-position', specific_position)

        return True # keep calling every second

    def get_duration(self):
        result, value = self.pipeline.query_duration(Gst.Format.TIME)
        if result:
            return value # total stream duration in nanoseconds
        else:
            return self.seconds_to_nanoseconds(self.app.playback_duration)

    def set_tracks_volume_mute(self, mute_track_a, mute_track_b):
        self.volumeA.set_property('mute', mute_track_a)
        self.volumeB.set_property('mute', mute_track_b)

    def get_track_volume_mute(self):
        track_A_mute = self.volumeA.get_property('mute')
        track_B_mute = self.volumeB.get_property('mute')
        return track_A_mute, track_B_mute

    def nanoseconds_to_seconds(self, nanoseconds):
        return int(nanoseconds / 1000000000)

    def seconds_to_nanoseconds(self, seconds):
        return int(seconds * 1000000000)

class ABClassifier(Adw.Application):

    app_name = 'AB Classifier'

    radio_action_style = None # application style

    player_pipeline = None # two tracks, one pipeline

    playback_duration = 0 # the longer track A or B duration

    track_a_path = None
    track_a_gain_to_be_added = 0.0
    track_a_l_kg = 0.0 # loudness
    track_a_true_peak = 0.0 # combined true peak
    track_a_true_peak_normalised = 0.0
    track_a_approximate_duration = 0.0

    track_b_path = None
    track_b_gain_to_be_added = 0.0
    track_b_l_kg = 0.0
    track_b_true_peak = 0.0
    track_b_true_peak_normalised = 0.0
    track_b_approximate_duration = 0.0

    win = None

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            application_id='io.audio.ABClassifier',
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
            **kwargs
        )

        self.set_option_context_summary('AB Classifier compares two audio files.')

        self.add_main_option(
            'theme',
            ord('t'),
            GLib.OptionFlags.NONE,
            GLib.OptionArg.STRING,
            'Application theme light or dark.',
            None,
        )

        self.connect('activate', self.on_activate)

        # hold state for Adw.SplitButton in a dummy action
        self.radio_action_style = Gio.SimpleAction.new_stateful(
            'radio_group_style',
            GLib.VariantType.new('s'),
            GLib.Variant.new_string('system')
        )
        self.add_action(self.radio_action_style)

        self.player_pipeline = PlayerPipeline(self)

        self.connect('shutdown', self.on_shutdown) # clean-up

    def on_activate(self, app):
        self.win = self.props.active_window
        if not self.win:
            self.win = ABClassifierWindow(self.app_name, application=self)
            css_provider = Gtk.CssProvider()
            css_provider.load_from_string('''
                .btn_stop {}
                .btn_stop:hover {
                  color: var(--accent-bg-color, orange);
                }

                .btn_play:hover {
                  color: var(--accent-bg-color, orange);
                }

                .btn_pause {}
                .btn_pause:hover {
                  color: var(--accent-bg-color, orange);
                }

                .btn_blind {}
                .btn_blind:checked {
                  background-color: var(--accent-bg-color, orange);
                  box-shadow: inset  4px  4px 4px lighter(var(--accent-bg-color, orange)),
                              inset -4px -4px 4px lighter(var(--accent-bg-color, orange)),
                              inset  4px -4px 4px lighter(var(--accent-bg-color, orange)),
                              inset -4px  4px 4px lighter(var(--accent-bg-color, orange));
                }

                .btn_level_match_shade {
                  color: red;
                }
                .spin_level_match_lufs {}
                .spin_level_match_lufs.horizontal button.up {
                  border-radius: 0px;
                }
                .spin_level_match_lufs.horizontal text {
                  padding-left: 20px;
                  padding-right: 10px;
                }
                .btn_spin_level_match_reset {}
                .btn_spin_level_match_reset:hover {
                  color: red;
                }

                .btn_reset_stats {}
                .btn_reset_stats:hover {
                  color: orange;
                }

                .btn_clear:hover {
                  color: red;
                }
                .btn_style:hover {
                  color: orange;
                }

                .btn_a {
                  font-family: "Times New Roman";
                }
                .btn_a:active {
                  background-color: var(--accent-bg-color, orange);
                }
                .btn_pick {
                  font-family: "Times New Roman";
                }
                .btn_pick:active {
                  color: white;
                  background-color: var(--accent-bg-color, orange);
                  background-image: radial-gradient(circle, var(--accent-bg-color, orange) 0%, shade(var(--accent-bg-color, orange), 0.6) 100%);
                }
                .btn_b {
                  font-family: "Times New Roman";
                }
                .btn_b:active {
                  background-color: var(--accent-bg-color, orange);
                }
                .btn_active_style {
                  color: white;
                  background-image: radial-gradient(circle, var(--accent-bg-color, orange) 0%, shade(var(--accent-bg-color, orange), 0.6) 100%);
                }
                .label_active_style {
                  color: green;
                }

                .entry_track_label {
                  border-radius: 30px;
                }
                .entry_track_label image.left:hover {
                  color: red;
                }
                .entry_track_label image.right:hover {
                  color: red;
                }

                .progressbar_track {
                  min-height: 32px;
                }
                .progressbar_track trough {
                  min-height: 32px;
                }
                .progressbar_track trough progress {
                  min-height: 32px;
                  border-top-right-radius: 0px;
                  border-bottom-right-radius: 0px;
                }

                .btn_track_a_load {
                  border-radius: 0px;
                }
                .btn_track_a_load:hover {
                  color: green;
                }
                .btn_track_a_reset {
                  border-top-left-radius: 0px;
                  border-top-right-radius: 30px;
                  border-bottom-left-radius: 0px;
                  border-bottom-right-radius: 30px;
                }
                .btn_track_a_reset:hover {
                  color: red;
                }
                .btn_track_b_load {
                  border-radius: 0px;
                }
                .btn_track_b_load:hover {
                  color: green;
                }
                .btn_track_b_reset {
                  border-top-left-radius: 30px;
                  border-top-right-radius: 0px;
                  border-bottom-left-radius: 30px;
                  border-bottom-right-radius: 0px;
                }
                .btn_track_b_reset:hover {
                  color: red;
                }
                .btn_left_track_info {
                  border-top-left-radius: 0px;
                  border-top-right-radius: 30px;
                  border-bottom-left-radius: 0px;
                  border-bottom-right-radius: 30px;
                }
                .btn_left_track_info:hover {
                  border-top-left-radius: 30px;
                  border-top-right-radius: 0px;
                  border-bottom-left-radius: 30px;
                  border-bottom-right-radius: 0px;
                  color: lightskyblue;
                }
                .btn_left_track_info button {
                  border-top-left-radius: 30px;
                  border-top-right-radius: 0px;
                  border-bottom-left-radius: 30px;
                  border-bottom-right-radius: 0px;
                }
                .btn_left_track_info button.toggle {
                  border-top-left-radius: 30px;
                  border-top-right-radius: 0px;
                  border-bottom-left-radius: 30px;
                  border-bottom-right-radius: 0px;
                }
                .btn_right_track_info {
                  border-top-left-radius: 0px;
                  border-top-right-radius: 30px;
                  border-bottom-left-radius: 0px;
                  border-bottom-right-radius: 30px;
                }
                .btn_right_track_info:hover {
                  border-top-left-radius: 0px;
                  border-top-right-radius: 30px;
                  border-bottom-left-radius: 0px;
                  border-bottom-right-radius: 30px;
                  color: lightskyblue;
                }
                .btn_right_track_info button {
                  border-top-left-radius: 0px;
                  border-top-right-radius: 30px;
                  border-bottom-left-radius: 0px;
                  border-bottom-right-radius: 30px;
                }
                .btn_right_track_info button.toggle {
                  border-top-left-radius: 0px;
                  border-top-right-radius: 30px;
                  border-bottom-left-radius: 0px;
                  border-bottom-right-radius: 30px;
                }

                .label_count {
                  font-size: 16pt;
                }

                .label_popover_track {
                  font-family: monospace, monospace;
                }
            ''')
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(),
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        self.win.present()

        # Notify, if GStreamer pipeline cannot be built.
        if self.player_pipeline.broken_pipeline != None:
            self.win.on_error_dialog(
                'GStreamer Error',
                f'The application cannot process audio, due to broken GStreamer pipeline.\n\n{self.player_pipeline.broken_pipeline}'
            )

    def do_command_line(self, command_line):
        options = command_line.get_options_dict()
        options = options.end().unpack()

        if len(options) == 1:
            print(f'one option: {options}')
            match options['theme']:
                case 'light':
                    Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_LIGHT)
                    self.radio_action_style.set_state(GLib.Variant.new_string('light'))
                case 'dark':
                    Adw.StyleManager.get_default().set_color_scheme(Adw.ColorScheme.FORCE_DARK)
                    self.radio_action_style.set_state(GLib.Variant.new_string('dark'))
                case _:
                    pass

        self.activate() # Activate/create window, once.

        return 0

    def true_peaks_and_loudness(self, dialog, a_or_b):
        file_path = self.track_a_path if a_or_b else self.track_b_path
        try:
            ffmpeg = subprocess.run(
                ['ffmpeg', '-hide_banner', '-i', file_path, '-af', 'loudnorm=print_format=json', '-f', 'null', '-'],
                capture_output=True,
                text=True
            )

            if ffmpeg.returncode != 0:
                raise ValueError('FFMPEG returned code other than 0.')

            str_raw = None
            if ffmpeg.stdout and len(ffmpeg.stdout) > 2:
                str_raw = ffmpeg.stdout
            elif ffmpeg.stderr:
                str_raw = ffmpeg.stderr

            if str_raw:
                duration_in_seconds = 0.0
                match = re.search('^\\s{2}Duration: (.*?)(?=\\.).*', str_raw, re.MULTILINE) # expecting '00:00:00.00'
                if match:
                    str_duration = match.group(1)
                    list_duration = str_duration.split(':')
                    for d in range(len(list_duration)):
                        if d == 2:
                            duration_in_seconds += float(list_duration[d])
                        elif d == 1:
                            duration_in_seconds += 60.0 * float(list_duration[d])
                        else:
                            duration_in_seconds += 3600.0 * float(d)
                else:
                    raise ValueError('Processing FFMPEG data failed, no track duration found.')

                input_i = None # loudness
                match = re.search(r'.*\"input_i\" : \"(.*)\"\,.*', str_raw)
                if match:
                    input_i = float(match.group(1))
                else:
                    raise ValueError('Processing FFMPEG data failed, no integrated loudness.')

                input_tp = None # true peak
                match = re.search(r'.*\"input_tp\" : \"(.*)\"\,.*', str_raw)
                if match:
                    input_tp = float(match.group(1))
                else:
                    raise ValueError('Processing FFMPEG data failed, no true peak.')

                if a_or_b:
                    self.track_a_l_kg = input_i # loudness
                    self.track_a_true_peak = input_tp # true peak
                    self.track_a_true_peak_normalised = 10 ** (input_tp / 20) # true peak normalised
                    self.track_a_gain_to_be_added = round(self.win.level_match_target_lufs - self.track_a_l_kg, 2)
                    self.track_a_approximate_duration = duration_in_seconds
                else:
                    self.track_b_l_kg = input_i # loudness
                    self.track_b_true_peak = input_tp # average true peak
                    self.track_b_true_peak_normalised = 10 ** (input_tp / 20) # true peak normalised
                    self.track_b_gain_to_be_added = round(self.win.level_match_target_lufs - self.track_b_l_kg, 2)
                    self.track_b_approximate_duration = duration_in_seconds

                self.player_pipeline.set_media(a_or_b) # set in GStreamer pipeline

                self.win.ready_indicator(a_or_b)

                # Check files are different.
                if (self.track_a_path and self.track_b_path) and (self.track_a_path == self.track_b_path):
                    self.win.on_error_dialog(
                        'Same Files!',
                        'The chosen file paths are identical.\nWhat do you want to compare?'
                    )

                # The longer track dictates the pipeline duration.
                if self.track_a_approximate_duration == self.track_b_approximate_duration:
                    self.playback_duration = self.track_a_approximate_duration
                elif self.track_a_approximate_duration > self.track_b_approximate_duration:
                    self.playback_duration = self.track_a_approximate_duration
                else:
                    self.playback_duration = self.track_b_approximate_duration
            else:
                raise ValueError('FFMPEG did not provide requested data.')
        except Exception as e:
            print(f'Failed Probe: {file_path} {str(e)}')
            self.win.on_error_dialog('Failed Probe', f'{str(e)}\n\n{file_path}')
            self.win.on_unset_file(None, a_or_b)

        if dialog and dialog.get_visible():
            dialog.close()

    def on_shutdown(self, application): # clean-up GStreamer
        self.player_pipeline.set_state(Gst.State.NULL)

def main():
    app = ABClassifier()
    app.run(sys.argv)

if __name__ == "__main__":
    main()
