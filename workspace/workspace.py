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

import os.path
import time
import pickle

from document.document import Document
from helpers.observable import *
import workspace.workspace_presenter as workspace_presenter
import workspace.workspace_controller as workspace_controller
import workspace.preview.preview as preview
import workspace.sidebar.sidebar as sidebar
import workspace.build_log.build_log as build_log
import workspace.headerbar.headerbar_presenter as headerbar_presenter
import workspace.keyboard_shortcuts.shortcuts as shortcuts
import workspace.document_switcher.document_switcher as document_switcher
from app.service_locator import ServiceLocator


class Workspace(Observable):
    ''' A workspace contains a user's open documents. '''

    def __init__(self):
        Observable.__init__(self)

        self.pathname = os.path.expanduser('~') + '/.setzer'

        self.open_documents = list()
        self.master_document = None
        self.recently_opened_documents = dict()
        self.untitled_documents_no = 0

        self.active_document = None

        settings = ServiceLocator.get_settings()
        self.sidebar = sidebar.Sidebar()
        self.show_sidebar = settings.get_value('window_state', 'show_sidebar')
        self.sidebar_position = settings.get_value('window_state', 'sidebar_paned_position')
        self.preview = preview.Preview()
        self.show_preview = settings.get_value('window_state', 'show_preview')
        self.preview_position = settings.get_value('window_state', 'preview_paned_position')
        self.build_log = build_log.BuildLog(self)
        self.show_build_log = settings.get_value('window_state', 'show_build_log')
        self.build_log_position = settings.get_value('window_state', 'build_log_paned_position')

    def init_workspace_controller(self):
        self.presenter = workspace_presenter.WorkspacePresenter(self)
        self.headerbar = headerbar_presenter.HeaderbarPresenter(self)
        self.document_switcher = document_switcher.DocumentSwitcher(self)
        self.controller = workspace_controller.WorkspaceController(self)
        self.shortcuts = shortcuts.Shortcuts(self, self.controller)

    def add_document(self, document):
        if self.open_documents.count(document) != 0: return False
        if document.get_filename() == None:
            document.set_displayname('Untitled Document ' + str(self.untitled_documents_no + 1))
            self.untitled_documents_no += 1
        if document.get_buffer() != None:
            self.open_documents.append(document)
            self.add_change_code('new_document', document)
            self.update_recently_opened_document(document.get_filename(), notify=True)

    def remove_document(self, document):
        document.save_document_data()
        self.open_documents.remove(document)
        if self.active_document == document:
            candidate = self.get_last_active_document()
            if candidate == None:
                self.set_active_document(None)
            else:
                self.set_active_document(candidate)
        if document == self.master_document:
            self.unset_master_document()
        self.add_change_code('document_removed', document)

    def create_document_from_filename(self, filename, activate=False):
        document = Document(self.pathname, with_buffer=True)
        document.set_filename(filename)
        document.populate_from_filename()
        self.add_document(document)

        if activate:
            self.set_active_document(document)

    def get_document_by_filename(self, filename):
        for document in self.open_documents:
            if filename == document.get_filename():
                return document
        return None

    def get_active_document(self):
        return self.active_document
        
    def set_active_document(self, document):
        if self.active_document != None:
            self.add_change_code('new_inactive_document', self.active_document)

        self.active_document = document
        if self.active_document != None:
            self.active_document.set_last_activated(time.time())
            self.add_change_code('new_active_document', document)
        self.set_build_log()
        
    def set_build_log(self):
        if self.get_active_document() != None:
            if self.master_document != None:
                self.build_log.set_document(self.master_document)
            else:
                self.build_log.set_document(self.active_document)

    def get_last_active_document(self):
        for document in sorted(self.open_documents, key=lambda val: -val.last_activated):
            return document
        return None

    def get_earliest_active_document(self):
        for document in sorted(self.open_documents, key=lambda val: val.last_activated):
            return document
        return None

    def update_recently_opened_document(self, filename, date=None, notify=True):
        if not isinstance(filename, str): return False
        if not os.path.isfile(filename): return False
        if date == None: date = time.time()
        if len(self.recently_opened_documents) >= 1000: 
            del(self.recently_opened_documents[sorted(self.recently_opened_documents.values(), key=lambda val: -val['date'])[0]['filename']])
        self.recently_opened_documents[filename] = {'filename': filename, 'date': date}
        if notify:
            self.add_change_code('update_recently_opened_documents', self.recently_opened_documents)
    
    def populate_from_disk(self):
        try: filehandle = open(self.pathname + '/workspace.pickle', 'rb')
        except IOError: pass
        else:
            try: data = pickle.load(filehandle)
            except EOFError: self.add_document(Document(self.pathname, with_buffer=True))
            else:
                for item in sorted(data['open_documents'].values(), key=lambda val: val['last_activated']):
                    document = Document(self.pathname, with_buffer=True)
                    document.set_filename(item['filename'])
                    if document.populate_from_filename() != False:
                        self.add_document(document)
                for item in data['recently_opened_documents'].values():
                    self.update_recently_opened_document(item['filename'], item['date'], notify=False)
        self.add_change_code('update_recently_opened_documents', self.recently_opened_documents)

    def save_to_disk(self):
        try: filehandle = open(self.pathname + '/workspace.pickle', 'wb')
        except IOError: pass
        else:
            open_documents = dict()
            for document in self.open_documents:
                filename = document.get_filename()
                if filename != None:
                    open_documents[filename] = {
                        'filename': filename,
                        'last_activated': document.get_last_activated()
                    }
            data = {
                'open_documents': open_documents,
                'recently_opened_documents': self.recently_opened_documents
            }
            pickle.dump(data, filehandle)
            
    def get_unsaved_documents(self):
        unsaved_documents = list()
        for document in self.open_documents:
            if document.get_modified():
                unsaved_documents.append(document)

        return unsaved_documents if len(unsaved_documents) >= 1 else None
        
    def get_all_documents(self):
        return self.open_documents.copy() if len(self.open_documents) >= 1 else None

    def set_one_document_master(self, master_document):
        self.master_document = master_document
        for document in self.open_documents:
            if document == master_document:
                document.set_is_master(True)
            else:
                document.set_is_master(False)
        self.add_change_code('master_state_change', 'one_document')
        self.set_build_log()

    def unset_master_document(self):
        for document in self.open_documents:
            document.set_is_master(False)
        self.master_document = None
        self.add_change_code('master_state_change', 'no_master_document')
        self.set_build_log()

    def set_show_sidebar(self, show_sidebar, animate=False):
        if show_sidebar != self.show_sidebar:
            self.show_sidebar = show_sidebar
            self.add_change_code('set_show_sidebar', show_sidebar)

    def set_sidebar_position(self, sidebar_position):
        self.sidebar_position = sidebar_position

    def set_preview_position(self, preview_position):
        self.preview_position = preview_position

    def set_build_log_position(self, build_log_position):
        self.build_log_position = build_log_position

    def set_show_preview(self, show_preview, animate=False):
        if show_preview != self.show_preview:
            self.show_preview = show_preview
            self.add_change_code('set_show_preview', show_preview)

    def set_show_build_log(self, show_build_log):
        if show_build_log != self.show_build_log:
            self.show_build_log = show_build_log
            self.add_change_code('show_build_log_state_change', show_build_log)

    def get_show_build_log(self):
        if self.show_build_log != None:
            return self.show_build_log
        else:
            return False
        
