#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import random
import logging
log = logging.getLogger('scheduler')

class scheduler:

    def __init__(self, config):
        self.count = 0
        self._sources = []
        self._folders = {}
        self._player = None
        self._acquirer = None
        self._music_pattern = ()
        if 'music_file_pattern' in config:
            self._music_pattern = config['music_file_pattern']

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return

    def get_next(self):
        if len(self._folders) == 0:
            time.sleep(1)
            return None  # slow down endless loops
        _folder = random.choice(list(self._folders.keys()))
        _file = random.choice(self._folders[_folder])
        return os.path.join(_folder, _file)

    def _on_aquired(self, url, path):
        pass

    def set_player(self, player_inst):
        assert hasattr(player_inst, 'play')
        self._player = player_inst

    def set_acquirer(self, acquirer_inst):
        assert hasattr(acquirer_inst, 'aquire')
        self._acquirer = acquirer_inst

    def add_path(self, path='.'):
        log.info('add "%s"', path)
        self._sources.append(path)
        self._crawl_path(path)

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
        for _parent, _folders, _files in os.walk(path):
            # if p == '.git': continue
            #if re.search('.*/.git/.*', a) is not None: continue
            #log.info(a, p, f)
            if not self._has_music(_files):
                continue
            if _parent in self._folders:
                continue
            self._folders[_parent] = self._get_music(_files)
            log.debug(_parent)
