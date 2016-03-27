#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import zmq
import threading
import time
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
class application_exit_request(Exception):
    pass

class player:
    ''' The player plays a given file on the FS (no URLs). In the
        future it will be responsible for cross fading, gapless play back
        and filtering. If it needs a next file to play it informs a scheduler
        handler.
    '''
    def __init__(self, context, config):
        self._config = config
        self._current_file = None
        self._next_file = None
        self._playing = False
        self._stop = False
        self._play_thread = None
        self._scheduler = None
        self._skip = False
        self._context = context

    def set_scheduler(self, scheduler_inst):
        assert hasattr(scheduler, 'get_next')
        self._scheduler = scheduler_inst

    #def set_publication_handler(self, handler):
        #assert hasattr(handler, '_on_publication')
        #self._publication_handler = handler

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
            self._next_file = self._scheduler.get_next()
        while self._next_file is None:
            self._next_file = self._scheduler.get_next()

    def skip(self):
        self._skip = True

    def current_track(self):
        return self._current_file

    def _player_fn(self):
        _notification_socket = self._context.socket(zmq.PAIR)
        _notification_socket.connect(self._config['notification_endpoint'])

        _notification_socket.send_json({
                'type': 'hello from player'})

        pygame.init()
        pygame.mixer.init()

        self._playing = True
        self._stop = False
        while not self._stop:
            self._fetch()
            _notification_socket.send_json({
                'type': 'now_playing',
                'current_track': self._current_file})

            log.info('play %s (next: %s)', self._current_file, self._next_file)
            try:
                pygame.mixer.music.load(self._current_file)
            except pygame.error as ex:
                log.error('pygame.mixer.music.load threw an exception: "%s"', ex)
                time.sleep(3)
                continue
            self._skip = False
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy() and not self._skip:
                time.sleep(1)
                _notification_socket.send_json({
                    'type': 'tick',
                    'time': time.time()})

        self._playing = False

class acquirer:
    ''' Takes links and makes them available on the FS. e.g. takes a
        link to a youtube video and returns a path to a downloaded
        file. As soon as a file has been downloaded it informs a scheduler
        handler.
    '''
    def __init__(self):
        self._scheduler = None

    def set_scheduler(self, scheduler_inst):
        assert hasattr(scheduler, '_on_aquired')
        self._scheduler = scheduler_inst

    def aquire(self, url):
        pass


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
        assert hasattr(player, 'play')
        self._player = player_inst

    def set_acquirer(self, acquirer_inst):
        assert hasattr(acquirer, 'aquire')
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
        _path = os.path.expanduser(path)

        log.info('crawl path "%s"', os.path.abspath(_path))
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

    config = {'music_file_pattern': ('.mp3',
                                     '.ogg',
                                     # '.opus',
                                     #    '.m4a',
                                     ),
              'input_dirs': (os.path.dirname(__file__),
                             '~/Music/pp'),
              'notification_endpoint': 'inproc://step2',
              }

    class server:
        def __init__(self, config):
            self._t1 = time.time()
            self._config = config
            self._application_exit_request = False
            self._context = zmq.Context()
            self._player = player(self._context, config)
            self._scheduler = scheduler(config)
            self._acquirer = acquirer()

            self._player.set_scheduler(self._scheduler)
            self._scheduler.set_player(self._player)

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return

        def run(self):
            for p in config['input_dirs']:
                if not os.path.exists(p):
                    log.warning('input dir does not exist: "%s"', p)
                    continue
                self._scheduler.add_path(p)

            _req_socket = self._context.socket(zmq.REP)
            _req_socket.bind('tcp://*:9876')
            _pub_socket = self._context.socket(zmq.PUB)
            _pub_socket.bind('tcp://*:9875')  # todo: make random

            _notification_socket = self._context.socket(zmq.PAIR)
            _notification_socket.bind(self._config['notification_endpoint'])

            _poller = zmq.Poller()
            _poller.register(_req_socket, zmq.POLLIN)
            _poller.register(_notification_socket, zmq.POLLIN)

            while not self._application_exit_request:
                log.info('ready')
                for _source, _ in _poller.poll():
                    if _source is _notification_socket:
                        _message = _notification_socket.recv_json()
                        _pub_socket.send_json(_message)
                        log.info("publish: '%s'", _message)

                    elif _source is _req_socket:
                        _request = _req_socket.recv_json()
                        _reply = self._handle_request(_request)
                        _req_socket.send_json(_reply)

            _req_socket.close()
            _pub_socket.close()
            self._context.close()

        def _handle_request(self, request):
            _td = time.time() - self._t1
            log.info('listening.. (%.2fs)', _td)
            self._t1 = time.time()
            log.debug(request)
            try:
                if 'type' not in request:
                    log.error('got request without "type"')
                    return {'type': 'error'}

                elif request['type'] == 'hello':
                    log.info('got "hello" request: "%s"', request)
                    return  {'type': 'ok',
                             'notifications': '9875',
                             'current_track': self._player.current_track()}

                elif request['type'] == 'play':
                    log.info('got "play" request')
                    self._player.play()
                    return {'type': 'ok'}

                elif request['type'] == 'stop':
                    log.info('got "stop" request')
                    #self._player.stop()
                    return {'type': 'ok'}

                elif request['type'] == 'skip':
                    log.info('got "skip" request')
                    self._player.skip()
                    return {'type': 'ok'}

                elif request['type'] == 'add':
                    log.info('got "add" request')
                    return {'type': 'ok'}

                elif request['type'] == 'quit':
                    log.info('got "quit" request')
                    self._application_exit_request = True
                    return {'type': 'ok'}

                else:
                    log.warning('got unknown request: "%s"', request)
                    return {'type': 'error',
                            'what': 'command "%s" '
                            'not known' % request['type']}
            except Exception as e:
                return {'type': 'error', 'what': str(e)}


    server(config).run()

if __name__ == '__main__':
    main()

