#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import zmq
import threading
import time
import argparse
import json

from scheduler import scheduler
import error

import logging
log = logging.getLogger('server')


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
    class error(Exception):
        pass

    class file_load_error(error):
        pass

    class backend_pygame:
        def __init__(self, comm, handler):
            self._comm = comm
            self._handler = handler

        def __enter__(self):
            import pygame
            pygame.init()
            pygame.mixer.init()
            return self

        def load_file(self, filename):
            import pygame
            try:
                pygame.mixer.music.load(filename)
            except pygame.error as ex:
                raise player.file_load_error(
                    'pygame.mixer.music.load threw an exception: "%s"' % repr(ex))

        def blocking_play(self):
            import pygame
            self._comm['skip'] = False
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy() and not self._comm['skip']:
                time.sleep(1)
                #_notification_socket.send_json({
                    #'type': 'tick',
                    #'time': str(time.time())})

    class backend_mplayer:
        def __init__(self, comm, handler):
            self._comm = comm
            self._handler = handler
            self._filename = None

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return

        def load_file(self, filename):
            self._filename = filename

        def blocking_play(self):
            import subprocess
            import select
            self._comm['skip'] = False
            _process = subprocess.Popen(args=['mplayer', '-nolirc', self._filename],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                stdin=subprocess.PIPE, bufsize=0)

            _to_poll = [_process.stdout.fileno(), _process.stderr.fileno()]

            while _process.poll() is None and not self._comm['skip']:
                if self._comm['pause']:
                    self._comm['pause'] = False
                    _process.stdin.write('p'.encode())
                if self._comm['volup']:
                    self._comm['volup'] = False
                    _process.stdin.write('0'.encode())
                if self._comm['voldown']:
                    self._comm['voldown'] = False
                    _process.stdin.write('9'.encode())
                for data in select.select(_to_poll, [], [], .2):
                    if _process.stdout.fileno() in data:
                        self._handle_output(
                            _process.stdout.read(1000).decode(
                                errors='replace'))
                    if _process.stderr.fileno() in data:
                        _str = _process.stderr.read(1000).decode(
                            errors='replace').strip()
                        if _str.strip() != "":
                            log.warning("STDERR: '%s'", _str)

            if _process.poll() is None:
                _process.kill()

        def _handle_output(self, line):
            elems = line.strip().split()
            if len(elems) == 0:
                return
            if elems[0] == "A:":
                try:
                    self._handler.update_pos(float(elems[1]), float(elems[4]))
                except Exception as ex:
                    print("EXCEPTION: %s", repr(ex))
            else:
                log.debug("[mplayer] %s", line)
                log.debug("[mplayer] %s", str(elems))


    def __init__(self, context, config):
        #self._backend = player.backend_pygame
        self._backend = player.backend_mplayer

        self._comm = {}
        self._reset_comm()
        self._config = config
        self._current_file = None
        self._playing = False
        self._stop = False
        self._play_thread = None
        self._scheduler = None
        self._context = context
        self._last_pos = 0
        self._notification_socket = None

    def _reset_comm(self):
        self._comm['skip'] = False
        self._comm['pause'] = False
        self._comm['volup'] = False
        self._comm['voldown'] = False

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
        self.skip()
        try:
            self._play_thread.join()
        except AttributeError:
            pass

    def _fetch(self):
        self._current_file = None
        # todo: must know if there's nothing to play
        while self._current_file is None:
            self._current_file = self._scheduler.get_next()

    def skip(self):
        self._comm['skip'] = True

    def pause(self):
        self._comm['pause'] = True

    def volume_up(self):
        self._comm['volup'] = True

    def volume_down(self):
        self._comm['voldown'] = True

    def current_track(self):
        return self._current_file

    def update_pos(self, now, total):
        if now - self._last_pos < 1.:
            return
        self._last_pos = now
        self._notification_socket.send_json({
            'type': 'now_playing',
            'current_pos': str(now),
            'track_length': str(total)})

    def current_pos(self) -> int:
        return self._last_pos

    def _player_fn(self):
        self._notification_socket = self._context.socket(zmq.PAIR)
        self._notification_socket.connect(self._config['notification_endpoint'])

        self._notification_socket.send_json({
                'type': 'hello from player'})

        with self._backend(self._comm, self) as _player:
            self._playing = True
            self._stop = False
            while not self._stop:
                self._fetch()
                self._notification_socket.send_json({
                    'type': 'now_playing',
                    'current_track': self._current_file})

                log.info('play %s', self._current_file)

                try:
                    _player.load_file(self._current_file)
                except player.file_load_error as ex:
                    log.error(repr(ex))
                    time.sleep(3)
                    continue

                self._last_pos = 0
                self._reset_comm()

                try:
                    _player.blocking_play()
                except Exception as ex:
                    log.error("an exception occured while playing: '%s'", repr(ex))
                    time.sleep(3)

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

class listener:
    def __init__(self):
        self.user_id = None
        self.user_name = None

class server:
    def __init__(self, config):
        self._t1 = time.time()
        self._config = config
        self._listeners = {}
        self._application_exit_request = False
        self._context = zmq.Context()
        self._player = player(self._context, config)
        self._scheduler = scheduler(config)
        self._acquirer = acquirer()
        self._player.set_scheduler(self._scheduler)


    def __enter__(self):
        return self

    def __exit__(self, *args):
        return

    def run(self):
        for p in self._config ['input_dirs']:
            _path = os.path.expanduser(p)
            if not os.path.exists(_path):
                log.warning('input dir does not exist: "%s"', p)
                continue
            log.info('add "%s"', _path)
            log.info('found %d files', self._scheduler.add_path(_path))

        _req_socket = self._context.socket(zmq.ROUTER)
        _req_socket.bind('tcp://*:9876')
        _pub_socket = self._context.socket(zmq.PUB)
        _pub_socket.bind('tcp://*:9875')  # todo: make random

        _notification_socket = self._context.socket(zmq.PAIR)
        _notification_socket.bind(self._config['notification_endpoint'])

        _poller = zmq.Poller()
        _poller.register(_req_socket, zmq.POLLIN)
        _poller.register(_notification_socket, zmq.POLLIN)

        while not self._application_exit_request:
            log.debug('ready')
            for _source, _ in _poller.poll():
                if _source is _notification_socket:
                    _message = _notification_socket.recv_json()
                    _pub_socket.send_json(_message)
                    log.debug("publish: '%s'", _message)

                elif _source is _req_socket:
                    _client, _, _msg = _req_socket.recv_multipart()
                    _request = zmq.utils.jsonapi.loads(_msg)
                    _reply = self._handle_request(_client, _request)
                    _req_socket.send_multipart(
                        (_client, b'', zmq.utils.jsonapi.dumps(_reply)))

        _req_socket.close()
        _pub_socket.close()
        self._context.close()

    def _handle_request(self, client_signature, request):
        log.info('request from %s',
                 ' '.join("{:02x}".format(b) for b in client_signature))
        if client_signature not in self._listeners:
            log.info('new listener: %s',
                     ' '.join("{:02x}".format(b) for b in client_signature))
            self._listeners[client_signature] = listener()

        _listener = self._listeners[client_signature]

        _td = time.time() - self._t1
        log.info('listening.. (%.2fs)', _td)
        self._t1 = time.time()
        log.debug(request)
        try:
            if 'type' not in request:
                log.error('got request without "type"')
                raise error.bad_request("'type' is missing")

            _command = request['type']

            if _command == 'hello':
                log.info('got "hello" request: "%s"', request)
                if not ('user_id' in request and 'user_name' in request):
                    raise error.not_identified("insufficient credentials")

                _listener.user_id = request['user_id']
                _listener.user_name = request['user_name']

                return  {'type': 'ok',
                         'notifications': '9875',
                         'server_version': 0,
                         'current_track': self._player.current_track()}

            if _listener.user_id is None:
                log.error('unknown listener tried to give instructions')
                raise error.not_identified("you're unknown. say hello first")

            log.info("listener '%s' sent '%s'", _listener.user_name, _command)

            if _command == 'play':
                self._player.play()
                return {'type': 'ok'}

            elif _command == 'stop':
                log.info("listener '%s' sent 'stop'", _listener.user_name)
                #self._player.stop()
                return error.bad_request('not implemented')

            elif _command == 'pause':
                log.info("listener '%s' sent 'pause'", _listener.user_name)
                self._player.pause()
                return {'type': 'ok'}

            elif _command == 'skip':
                log.info('got "skip" request')
                self._player.skip()
                return {'type': 'ok'}

            elif _command == 'volup':
                log.info('got "volup" request')
                self._player.volume_up()
                return {'type': 'ok'}

            elif _command == 'voldown':
                log.info('got "voldown" request')
                self._player.volume_down()
                return {'type': 'ok'}

            elif _command == 'add':
                log.info('got "add" request')
                return {'type': 'ok'}

            elif _command == 'add_tag':
                log.info('got "add_tag" request: %s', request)
                if self._player.current_track() is None:
                    raise error.invalid_state(
                        'no track is currently being played')
                self._scheduler.add_tag(
                    _listener.user_id, self._player.current_track(),
                    self._player.current_pos(), request)
                return {'type': 'ok'}

            elif _command == 'search':
                log.info('got "search" request: %s', request)
                return {'type': 'ok',
                        'result': ','.join(self._scheduler.search_filenames(
                            request['query']))}

            elif _command == 'schedule':
                log.info('got "schedule" request: %s', request)
                self._scheduler.schedule_next_item(request['item'])
                return {'type': 'ok'}

            elif _command == 'quit':
                log.info('got "quit" request')
                self._application_exit_request = True
                return {'type': 'ok'}

            else:
                log.warning('got unknown request: "%s"', request)
                raise error.bad_request('got unknown request type: "%s"'% request)
        except error.rrp_error as ex:
            return {'type': 'error', 'id': ex.id_str, 'what': str(ex)}
        except Exception as ex:
            return {'type': 'error', 'id': error.internal_error.id_str,
                    'what': repr(ex)}


def setup_logging(level=logging.INFO):
    logging.basicConfig(
        format="%(asctime)s %(name)15s %(levelname)s:  %(message)s",
        datefmt="%y%m%d-%H%M%S",
        level=level)
    logging.addLevelName(logging.CRITICAL, "CC")
    logging.addLevelName(logging.ERROR,    "EE")
    logging.addLevelName(logging.WARNING,  "WW")
    logging.addLevelName(logging.INFO,     "II")
    logging.addLevelName(logging.DEBUG,    "DD")
    logging.addLevelName(logging.NOTSET,   "NA")

def main():
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--verbose', '-v',     action='count', default = 0)
    args = parser.parse_args()

    _level = logging.INFO
    if args.verbose >= 1:
        _level = logging.INFO
    if args.verbose >= 2:
        _level = logging.DEBUG

    setup_logging(level=_level)

    if sys.version_info < (3, ):
        log.error('Python 2 is no longer supported. Get over it.')
        sys.exit(-1)

    log.debug('.'.join((str(e) for e in sys.version_info)))

    config = {'music_file_pattern':    (".mp3", ".mp4", ".m4a",
                                        ".ogg", ".opus", ),
              'input_dirs':            (os.path.dirname(__file__),),
              'notification_endpoint': 'inproc://step2',
              'playlist_folder':       '~/.rrplayer/lists'
              }
    try:
        config.update(
            json.load(
                open(os.path.expanduser('~/.rrplayer/rrplayerrc'))))
    except FileNotFoundError:
        try:
            os.makedirs(os.path.expanduser('~/.rrplayer'))
        except FileExistsError:
            pass
        with open(os.path.expanduser('~/.rrplayer/rrplayerrc'), 'w') as f:
            f.write('{\n')
            f.write('    "input_dirs":            ["~/Music"],\n')
            f.write('    "playlist_folder":       "~/.rrplayer/lists"\n')
            f.write('}\n')
        log.info("config file could not be found - I've created one for you at "
                 "~/.rrplayer/rrplayerrc")

    server(config).run()


if __name__ == '__main__':
    main()
