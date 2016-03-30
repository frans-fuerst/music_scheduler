#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import random
import logging
log = logging.getLogger('scheduler')

import error


class scheduler:

    def __init__(self, config):
        assert 'playlist_folder' in config
        self.count = 0
        self._sources = []
        self._folders = {}
        self._acquirer = None
        self._music_pattern = ()
        self._config = config
        if 'music_file_pattern' in config:
            self._music_pattern = config['music_file_pattern']
        self._smartlists = set()
        self._active_list = None
        self._rules = []
        self._present_listeners = set()
        self._init_lists()
        self._dirty = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._store_list()

    def get_smartlists(self):
        return self._smartlists

    def get_active_smartlist(self):
        return self._active_list

    def activate_smartlist(self, list_name: str):
        if list_name not in self._smartlists:
            raise error.invalid_value('')
        self._store_list()
        self._rules = self._load_rules(list_name)
        self._active_list = list_name

    def add_tag(self, user: str, track: str, pos: int, details: dict):
        if 'tag_name' not in details:
            raise error.bad_request('add_tag request does not contain tag_name')

        _tag_name = details['tag_name']
        if _tag_name == 'ban':
            if 'subject' not in details:
                raise error.bad_request('add_tag request does not contain subject')
            _subject = details['subject']
        elif _tag_name == 'upvote':
            _subject = track
        else:
            raise error.bad_request('cannot handle tag name "%s"' % _tag_name)

        self._dirty = True
        self._rules.append((time.time(), user, _tag_name, _subject, pos))

    def present_listeners(self):
        return self._present_listeners

    def add_present_listener(self, name):
        self._present_listeners.add(name)

    def remove_present_listener(self, name):
        self._present_listeners.remove(name)

    def _init_lists(self):
        _smartlists = set(('unspecified',
                           'concentration',
                           'party',
                           'cometogether'))
        _path = os.path.expanduser(self._config['playlist_folder'])
        try:
            os.makedirs(_path)
        except FileExistsError:
            pass

        for f in os.listdir(_path):
            _smartlists.add(f)

        self._smartlists = _smartlists
        self._active_list = 'unspecified'

    def get_next(self):
        if len(self._folders) == 0:
            time.sleep(1)
            return None  # slow down endless loops
        _folder = random.choice(list(self._folders.keys()))
        _file = random.choice(self._folders[_folder])
        return os.path.join(_folder, _file)

    def _store_list(self):
        if not self._dirty:
            return
        _path = os.path.join(
            os.path.expanduser(self._config['playlist_folder']),
            self._active_list)
        with open(_path, 'w') as _f:
            for r in self._rules:
                _f.write('%s, %s, %s, %s\n' % (
                    str(r[0]), str(r[1]), str(r[2]), str(r[3])))
        self._dirty = False

    def _load_rules(self, list_file):
        _path = os.path.join(
            os.path.expanduser(self._config['playlist_folder']),
            list_file)

        try:
            with open(_path) as _f:
                return [l.split(',') for l in _f.readlines()]
        except FileNotFoundError:
            return []

    def _on_aquired(self, url, path):
        pass

    def set_acquirer(self, acquirer_inst):
        assert hasattr(acquirer_inst, 'aquire')
        self._acquirer = acquirer_inst

    def add_path(self, path:str='.') -> int:
        self._sources.append(path)
        return self._crawl_path(path)

    def _is_music(self, filename):
        return os.path.splitext(filename.lower())[1] in self._music_pattern

    def _has_music(self, files):
        for f in files:
            if self._is_music(f):
                return True
        return False

    def _get_music(self, files):
        return [f for f in files if self._is_music(f)]

    def _crawl_path(self, path=None):
        _result = 0
        for _parent, _folders, _files in os.walk(path):
            # if p == '.git': continue
            #if re.search('.*/.git/.*', a) is not None: continue
            #log.info(a, p, f)
            if not self._has_music(_files):
                continue
            if _parent in self._folders:
                continue
            self._folders[_parent] = self._get_music(_files)
            _result += len(self._folders[_parent])
            log.debug(_parent)
        return _result
