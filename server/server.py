#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import fnmatch
import zmq
import logging
import threading
import time
import re
import random

import musicplayer

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
    
    def set_scheduler(self, scheduler):
        assert hasattr(scheduler, '_on_next')
        self._scheduler = scheduler

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
        while self._current_file is None:
            self._current_file = self._next_file
            self._next_file = self._scheduler._on_next()
        while self._next_file is None:
            self._next_file = self._scheduler._on_next()
            
    def _player_fn(self):
        self._playing = True
        self._stop = False
        while not self._stop:
            self._fetch()
            print('play %s (next: %s)' % (self._current_file, self._next_file))
            time.sleep(2)

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
        _folder = random.choice(self._folders.keys())
        _file = random.choice(self._folders[_folder])
        return os.path.join(_folder, _file)

    def _on_aquired(self, url, path):
        pass
    
    def set_player(self, player):
        assert hasattr(player, 'play')
        self._player = player
        
    def set_acquirer(self, acquirer):
        assert hasattr(acquirer, 'aquire')
        self._acquirer = acquirer
        
    def add_path(self, path='.'):
        ''' this '''
        self._sources.append(path)
        self._crawl_path(path)
        
    def _is_music(self, filename):
        return filename.lower().endswith('.mp3')

    def _has_music(self, files):
        for f in files:
            if self._is_music(f):
                return True
        return False

    def _get_music(self, files):
        return [f for f in files if self._is_music(f)]
    
    def _crawl_path(self, path=None):
        print('add path "%s"' % os.path.abspath(path))
        for _parent, _folders, _files in os.walk(path):
            # if p == '.git': continue
            #if re.search('.*/.git/.*', a) is not None: continue
            #print(a, p, f)
            if self._has_music(_files):
                if not _parent in self._folders:
                    self._folders[_parent] = self._get_music(_files)
                    print(_parent)
                    
def main():
    p = player()
    s = scheduler()
    a = acquirer()
    
    p.set_scheduler(s)
    s.set_player(p)
    
    s.add_path('../mucke')
    
   
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind('tcp://127.0.0.1:9876')
    
    while True:
        print('listening..')
        request = socket.recv_json()
        print(request)
        if 'type' not in request:
            socket.send_json({'type': 'error'})
            
        elif request['type'] == 'play':
            p.play()
            socket.send_json({'type': 'ok'})
            
        elif request['type'] == 'stop':
            p.stop()
            socket.send_json({'type': 'ok'})
            
        elif request['type'] == 'quit':
            socket.send_json({'type': 'ok'})
            break
        
        else:
            socket.send_json({'type': 'error'})
        print('ready')

    socket.close()
    context.close()
    

if __name__ == '__main__':
    main()

