#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import zmq
import threading
import time
import argparse
import json

try:
    from espeak import espeak
except ImportError:
    espeak = None

from scheduler import scheduler
import error

import logging
log = logging.getLogger('server')

SERVER_VERSION = '0.1.6'

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
            # We try to maintain as little state as possible in this class.
            # All needed state should be queried from self._handler
            self._comm = comm
            self._handler = handler

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return

        def blocking_play(self):
            import subprocess
            import select
            self._comm['skip'] = False
            _process = subprocess.Popen(
                args=['mplayer', '-slave', '-nolirc',
                                              self._handler.handler_get_filename()],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                stdin=subprocess.PIPE, bufsize=0)

            _to_poll = [_process.stdout.fileno(), _process.stderr.fileno()]
            while _process.poll() is None and not self._comm['skip']:
                if self._comm['pause']:
                    self._comm['pause'] = False
                    _process.stdin.write('pause\n'.encode())
                    self._handler.handler_set_pause(
                        not self._handler.handler_get_pause())
                if self._comm['volume']:
                    self._comm['volume'] = False
                    x = self._handler.handler_get_volume()
                    x = 'volume %d 1\n' % (self._handler.handler_get_volume() * 100)
                    print(x)
                    _process.stdin.write(
                        ('volume %d 1\n' % (self._handler.handler_get_volume() * 100)).encode())
                if self._comm['seek']:
                    self._comm['seek'] = False
                    _process.stdin.write(
                        ('seek %d 2\n' % self._handler._seek_position).encode())
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
                    self._handler.handler_update_pos(float(elems[1]), float(elems[4]))
                except Exception as ex:
                    log.error("EXCEPTION: %s", repr(ex))
            else:
                log.debug("[mplayer] %s", line)
                log.debug("[mplayer] %s", str(elems))


    def __init__(self, context, config):
        self._comm = {}
        self._backend = player.backend_mplayer(self._comm, self)
        self._reset_comm()
        self._config = config
        self._current_file = None
        self._pause = False
        self._volume = 1.0
        self._seek_position = 0
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
        self._comm['volume'] = False
        self._comm['seek'] = False

    def set_scheduler(self, scheduler_inst):
        assert hasattr(scheduler, 'get_next')
        self._scheduler = scheduler_inst

    #def set_publication_handler(self, handler):
        #assert hasattr(handler, '_on_publication')
        #self._publication_handler = handler

    def play(self):
        if self._playing:
            self.resume()
            return
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
        if self._pause:
            return
        self._comm['pause'] = True

    def resume(self):
        if not self._pause:
            return
        self._comm['pause'] = True

    def toggle_pause(self):
        self._comm['pause'] = True

    def volume_up(self):
        self._volume += .1
        if self._volume > 1.0: self._volume = 1.0
        self._comm['volume'] = True

    def volume_down(self):
        self._volume -= .1
        if self._volume < 0.0: self._volume = 0.0
        self._comm['volume'] = True

    def set_volume(self, value: float) -> None:
        self._volume = value
        if self._volume < 0.0: self._volume = 0.0
        if self._volume > 1.0: self._volume = 1.0
        self._comm['volume'] = True

    def get_volume(self) -> float:
        return self._volume

    def seek(self, position: int):
        self._seek_position = position
        self._comm['seek'] = True

    def current_track(self):
        return self._current_file

    def handler_get_volume(self) -> float:
        return self._volume

    def handler_get_pause(self) -> bool:
        return self._pause

    def handler_set_pause(self, value: bool) -> None:
        self._pause = value

    def handler_update_pos(self, now, total):
        if now - self._last_pos < 1.:
            return
        self._last_pos = now
        self._notification_socket.send_json({
            'type': 'now_playing',
            'current_pos': str(now),
            'track_length': str(total)})

    def handler_get_filename(self) -> str:
        return os.path.join(*self._current_file)

    def current_pos(self) -> int:
        return self._last_pos

    def _player_fn(self):
        self._notification_socket = self._context.socket(zmq.PAIR)
        self._notification_socket.connect(self._config['notification_endpoint'])

        self._notification_socket.send_json({
                'type': 'hello from player'})

        self._playing = True
        self._stop = False
        while not self._stop:
            self._fetch()
            self._notification_socket.send_json({
                'type': 'now_playing',
                'current_track': ':'.join(self._current_file)})

            log.info('play %s', os.path.join(*self._current_file[1:]))

            self._last_pos = 0
            self._reset_comm()

            try:
                self._backend.blocking_play()
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
        self._scheduler = scheduler(config=config)
        self._acquirer = acquirer()
        self._player.set_scheduler(self._scheduler)


    def __enter__(self):
        return self

    def __exit__(self, *args):
        return

    def run(self):
        _t = time.time()
        _full_count = 0
        for p in self._config ['input_dirs']:
            _path = os.path.expanduser(p)
            if not os.path.exists(_path):
                log.warning('input dir does not exist: "%s"', p)
                continue
            log.info('add "%s"', _path)
            _count = self._scheduler.add_path(_path)
            _full_count += _count
            log.info('%d files', _count)
        _t = time.time() - _t
        log.info('found a total of %d music tracks in %.1f sec', _full_count, _t)
        self._scheduler.debug_check()

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

                if espeak is not None:
                    espeak.synth("hello %s" % _listener.user_name)

                return  {'type':           'ok',
                         'notifications':  '9875',
                         'server_version': SERVER_VERSION,
                         'volume':         str(self._player.get_volume()),
                         'current_track': (
                             ':'.join(self._player.current_track())
                             if self._player.current_track() is not None
                             else None)}

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
                self._player.toggle_pause()
                return {'type': 'ok'}

            elif _command == 'skip':
                self._player.skip()
                return {'type': 'ok'}

            elif _command == 'volup':
                self._player.volume_up()
                return {'type': 'ok'}

            elif _command == 'voldown':
                self._player.volume_down()
                return {'type': 'ok'}

            elif _command == 'set_volume':
                self._player.set_volume(float(request['value']))
                return {'type': 'ok'}

            elif _command == 'seek':
                self._player.seek(int(request['position']))
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
                _search_result = self._scheduler.search_filenames(
                    request['query'])
                _search_result = (':'.join((str(i) for i in e)) for e in _search_result)
                return {'type': 'ok',
                        'result': '|'.join(_search_result)}

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
              'playlist_folder':       '~/.pmp/lists'
              }
    try:
        config.update(
            json.load(
                open(os.path.expanduser('~/.pmp/pmprc'))))
    except FileNotFoundError:
        try:
            os.makedirs(os.path.expanduser('~/.pmp'))
        except FileExistsError:
            pass
        with open(os.path.expanduser('~/.pmp/pmprc'), 'w') as f:
            f.write('{\n')
            f.write('    "input_dirs":            ["~/Music"],\n')
            f.write('    "playlist_folder":       "~/.pmp/lists"\n')
            f.write('}\n')
        log.info("config file could not be found - I've created one for you at "
                 "~/.pmp/pmprc")

    server(config).run()


if __name__ == '__main__':
    main()
