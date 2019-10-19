#!/usr/bin/env python3
# coding: utf-8

# Copyright (C) 2017, 2018 Robert Griesel
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk
from gi.repository import GLib

from dialogs.document_wizard.pages.page import Page, PageView

import os


class LetterSettingsPage(Page):

    def __init__(self, current_values):
        self.current_values = current_values
        self.view = LetterSettingsPageView()

    def observe_view(self):
        def row_selected(box, row, user_data=None):
            child_name = row.get_child().get_text()
            self.current_values['letter']['page_format'] = child_name

        def scale_change_value(scale, scroll, value, user_data=None):
            self.current_values['letter']['font_size'] = int(value)

        self.view.page_format_list.connect('row-selected', row_selected)
        self.view.font_size_entry.connect('change-value', scale_change_value)

    def load_presets(self, presets):
        try:
            row = self.view.page_format_list_rows[presets['letter']['page_format']]
        except KeyError:
            row = self.view.page_format_list_rows[self.current_values['letter']['page_format']]
        self.view.page_format_list.select_row(row)

        try:
            value = presets['letter']['font_size']
        except KeyError:
            value = self.current_values['letter']['font_size']
        self.view.font_size_entry.set_value(value)

    def on_activation(self):
        GLib.idle_add(self.view.page_format_list.get_selected_row().grab_focus)


class LetterSettingsPageView(PageView):

    def __init__(self):
        PageView.__init__(self)
        self.set_document_settings_page()
            
        self.header.set_text('Letter settings')

        self.pack_start(self.header, False, False, 0)
        self.left_content.pack_start(self.subheader_page_format, False, False, 0)
        self.left_content.pack_start(self.page_format_list, False, False, 0)
        self.left_content.pack_start(self.subheader_font_size, False, False, 0)
        self.left_content.pack_start(self.font_size_entry, False, False, 0)
        self.content.pack_start(self.left_content, False, False, 0)
        self.pack_start(self.content, False, False, 0)
        self.show_all()


