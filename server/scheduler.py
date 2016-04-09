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
        self._wishlist = []
        self._acquirer = None
        self._music_pattern = ()
        self._config = config
        if 'music_file_pattern' in config:
            self._music_pattern = config['music_file_pattern']
        self._smartlists = set()
        self._active_list = None
        self._rules = []
        self._present_listeners = set()
        self._dirty = False
        self._init_lists()
        self._name_components = {}

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
        log.info("loaded smartlist '%s' with %d rules",
                 list_name, len(self._rules))

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

        # todo: not needed in production mode but might be useful though
        self._store_list()

    def present_listeners(self):
        return self._present_listeners

    def add_present_listener(self, name):
        self._present_listeners.add(name)

    def remove_present_listener(self, name):
        self._present_listeners.remove(name)

    def search_filenames(self, query: str) -> list:
        _query = query.lower().split()
        _result = []
        for _path, _files in self._folders.items():
            _score_plus = 0
            _p2 = self._get_name_component(_path[1])
            for q in _query:
                if q in _p2.lower():
                    _score_plus += 1
            for f in _files:
                _f = self._get_name_component(f.name_index)
                _score = 0
                for q in _query:
                    if q in _f.lower():
                        _score += 1
                if _score + _score_plus > 0:
                    _result.append(
                        ("%d/%d/%d" % (_path[0], _path[1], f.name_index),
                         os.path.join(_p2, _f),
                         _score + _score_plus))
        _result.sort(key=lambda tup: tup[2], reverse=True)
        return _result[:20]

    def schedule_next_item(self, item: str) -> None:
        _components = (int(e) for e in item.split('/'))
        self._wishlist.append(self._get_name_components(_components))

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
        self.activate_smartlist('unspecified')

    def get_next(self) -> tuple:
        while len(self._wishlist) > 0:
            _item = self._wishlist.pop(0)
            if os.path.exists(os.path.join(*_item)):
                log.info("scheduling wishlist-item %s", _item)
                return _item
            else:
                log.warn("removing non-existing item '%s' from wishlist", _item)

        if len(self._folders) == 0:
            time.sleep(1)
            return None  # slow down endless loops

        def passes(filename):
            for e in self._rules:
                print(e)
                if e[2] == 'ban' and e[3] in filename:
                    return False
            return True

        while True:
            _location = random.choice(list(self._folders.keys()))
            _p1, _p2 = self._get_name_components(_location)
            if not (passes(_p1) and passes(_p2)):
                log.info('skipped banned location "%s/%s"', _p1, _p2)
                continue
            _file = random.choice(self._folders[_location])
            _f =  self._get_name_component(_file.name_index)
            if not passes(_f):
                log.info('skipped banned file "%s/%s"', _p2, _f)
                continue
            return (_p1, _p2, _f)

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
                return [tuple((e.strip() for e in l.split(','))) for l in _f.readlines()]
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
        # todo: count init/del
        class fileinfo:
            def __init__(self, filename_index):
                self.name_index = filename_index
        return [fileinfo(self._get_name_component_index(f))
                for f in files if self._is_music(f)]

    def _get_name_component_index(self, name_component:str) -> int:
        if not name_component in self._name_components:
            _new_index = len(self._name_components)
            assert _new_index not in self._name_components
            self._name_components[name_component] = _new_index
            self._name_components[_new_index] = name_component
            return _new_index
        return self._name_components[name_component]

    def _get_name_component(self, name_component_index: int) -> str:
        assert name_component_index in self._name_components
        return self._name_components[name_component_index]

    def _get_name_components(self, indices: tuple) -> tuple:
        return tuple(self._get_name_component(e) for e in indices)

    def _crawl_path(self, path: str):
        _path = os.path.normpath(path)
        assert _path.startswith('/')
        assert not _path.endswith('/')
        _path_idx = self._get_name_component_index(_path)
        _result_count = 0
        for _parent, _folders, _files in os.walk(_path):
            if '.git' in _folders: del _folders['.git']
            if '.svn' in _folders: del _folders['.svn']

            assert _parent.startswith(_path)
            assert _parent == os.path.normpath(_parent)
            _relpath = _parent[len(_path):].strip('/')
            _relpath_idx = self._get_name_component_index(_relpath)
            assert _parent == os.path.normpath(os.path.join(_path, _relpath))

            if _parent in self._folders:
                continue
            if not self._has_music(_files):
                continue
            _music_file_list = self._get_music(_files)
            self._folders[(_path_idx, _relpath_idx)] = _music_file_list
            _result_count += len(_music_file_list)
            log.debug(_relpath)

        return _result_count
