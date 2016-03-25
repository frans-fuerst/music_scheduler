#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import fnmatch
import zmq
import threading
import time
import re
import random
import argparse
import pygame

import logging as log


''' design guidelines
    - base components have only non-blocking methods
    - base components are meant to not having to know
      each other. for faster prototyping for now they interact
      directly
    - base components should be replacable by remote stubs
    - base components should be startable as separate processes

'''

class player:
    ''' The player plays a given file on the FS (no URLs). In the
        future it will be responsible for cross fading, gapless play back
        and filtering. If it needs a next file to play it informs a scheduler
        handler.
    '''
    def __init__(self):
        self._current_file = None
        self._next_file = None
        self._playing = False
        self._stop = False
        self._play_thread = None
        self._scheduler = None
        self._publication_handler = None
        self._skip = False

    def set_scheduler(self, scheduler_inst):
        assert hasattr(scheduler, '_on_next')
        self._scheduler = scheduler_inst

    def set_publication_handler(self, handler):
        assert hasattr(handler, '_on_publication')
        self._publication_handler = handler

    def play(self):
        if self._playing:
            return False
        self._play_thread = threading.Thread(target=self._player_fn)
        self._play_thread.start()
        return True

    def stop(self):
        self._stop = True
        try:
            self._play_thread.join()
        except AttributeError:
            pass

    def _fetch(self):
        self._current_file = self._next_file
        self._next_file = None
        # todo: must know if there's nothing to play
        while self._current_file is None:
            self._current_file = self._next_file
            self._next_file = self._scheduler._on_next()
        while self._next_file is None:
            self._next_file = self._scheduler._on_next()

    def skip(self):
        self._skip = True

    def current_track(self):
        return self._current_file

    def _player_fn(self):
        pygame.init()
        pygame.mixer.init()

        self._playing = True
        self._stop = False
        while not self._stop:
            self._fetch()
            if self._publication_handler:
                self._publication_handler._on_publication({
                    'type': 'now_playing',
                    'track': self._current_file})

            log.info('play %s (next: %s)' % (self._current_file, self._next_file))
            try:
                pygame.mixer.music.load(self._current_file)
            except pygame.error as ex:
                log.error('pygame.mixer.music.load threw an exception: "%s"', ex)
                time.sleep(3)
                continue
            self._skip = False
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy() and not self._skip:
                pygame.time.Clock().tick(10)

        self._playing = False

class acquirer:
    ''' Takes links and makes them available on the FS. e.g. takes a
        link to a youtube video and returns a path to a downloaded
        file. As soon as a file has been downloaded it informs a scheduler
        handler.
    '''
    def __init__(self):
        pass

    def set_scheduler(self, scheduler):
        assert hasattr(scheduler, '_on_aquired')
        self._scheduler = scheduler

    def aquire(self, url):
        pass


class scheduler:

    def __init__(self):
        self.count = 0
        self._sources = []
        self._folders = {}

    def _on_next(self):
        if len(self._folders) == 0:
            time.sleep(1)
            return None  # slow down endless loops
        _folder = random.choice(list(self._folders.keys()))
        _file = random.choice(self._folders[_folder])
        return os.path.join(_folder, _file)

    def _on_aquired(self, url, path):
        pass

    def set_player(self, player_inst):
        assert hasattr(player, 'play')
        self._player = player_inst

    def set_acquirer(self, acquirer):
        assert hasattr(acquirer, 'aquire')
        self._acquirer = acquirer

    def add_path(self, path='.'):
        log.info('add "%s"', path)
        self._sources.append(path)
        self._crawl_path(path)

    def _is_music(self, filename):
        return os.path.splitext(filename.lower())[1] in (
        #    '.mp3',
            '.ogg',
        #    '.opus',
        #    '.m4a',
        )

    def _has_music(self, files):
        for f in files:
            if self._is_music(f):
                return True
        return False

    def _get_music(self, files):
        return [f for f in files if self._is_music(f)]

    def _crawl_path(self, path=None):
        _path = os.path.expanduser(path)

        log.info('crawl path "%s"' % os.path.abspath(_path))
        for _parent, _folders, _files in os.walk(_path):
            # if p == '.git': continue
            #if re.search('.*/.git/.*', a) is not None: continue
            #log.info(a, p, f)
            if not self._has_music(_files):
                continue
            if _parent in self._folders:
                continue
            self._folders[_parent] = self._get_music(_files)
            log.debug(_parent)

def main():
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--verbose', '-v',     action='count', default = 0)
    args = parser.parse_args()

    _level = log.INFO
    if args.verbose >= 1:
        _level = log.INFO
    if args.verbose >= 2:
        _level = log.DEBUG

    log.basicConfig(level=_level)
    log.debug('.'.join((str(e) for e in sys.version_info)))

    class server:
        def run(self):
            # turn into with x(player(), scheduler(), aquirer()) as (p, s, a):
            p = player()
            s = scheduler()
            a = acquirer()

            p.set_scheduler(s)
            p.set_publication_handler(self)
            s.set_player(p)

            s.add_path('~/Music/pp')

            context = zmq.Context()
            # pylint: disable=no-member
            req_socket = context.socket(zmq.REP)
            req_socket.bind('tcp://127.0.0.1:9876')
            self._pub_socket = context.socket(zmq.PUB)
            self._pub_socket.bind('tcp://127.0.0.1:9875')  # todo: make random

            t1 = time.time()
            while True:
                _td = time.time() - t1
                log.info('listening.. (%.2fs)' % _td)
                request = req_socket.recv_json()
                t1 = time.time()
                log.debug(request)
                reply = {'type': 'error'}
                try:
                    if 'type' not in request:
                        log.error('got request without "type"')
                        reply = {'type': 'error'}

                    elif request['type'] == 'hello':
                        log.info('got "play" request')
                        reply = {'type': 'ok',
                                 'notifications': 'tcp://127.0.0.1:9875',
                                 'current_track': p.current_track()}

                    elif request['type'] == 'play':
                        log.info('got "play" request')
                        p.play()
                        reply = {'type': 'ok'}

                    elif request['type'] == 'stop':
                        log.info('got "stop" request')
                        p.stop()
                        reply = {'type': 'ok'}

                    elif request['type'] == 'skip':
                        log.info('got "skip" request')
                        p.skip()
                        reply = {'type': 'ok'}

                    elif request['type'] == 'quit':
                        log.info('got "quit" request')
                        reply = {'type': 'ok'}
                        break

                    elif request['type'] == 'add':
                        log.info('got "add" request')
                        reply = {'type': 'ok'}
                        break

                    else:
                        reply = {
                            'type': 'error',
                            'what': 'command "%s" '
                            'not known' % request['type']}
                except Exception as e:
                    reply = {'type': 'error', 'what': str(e)}

                req_socket.send_json(reply)
                log.info('ready')

            req_socket.close()
            context.close()

        def _on_publication(self, msg):
            # todo: queue and run in same thread
            self._pub_socket.send_json(msg)
            if msg['type'] == 'now_playing':
                self._cached_current_track_name = msg['track']

    server().run()

if __name__ == '__main__':
    main()

