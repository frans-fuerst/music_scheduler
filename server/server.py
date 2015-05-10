#!/usr/bin/env python

import sys
import os
import fnmatch

import musicplayer

''' design guidelines
    - base components have only non-blocking methods
    - base components are meant to not having to know
      each other. for faster prototyping for now they interact 
      directly
    - base components should be replacable by remote stubs
    
'''

class player:
    
    def __init__(self):
        pass
    
    def set_scheduler(self, scheduler):
        assert hasattr(scheduler, '_on_next')
        self._scheduler = scheduler

    def play(self):
        pass


class acquirer:
    ''' takes links and makes sure they are available. e.g. takes a 
        link to a youtube video and returns a path to a downloaded 
        file
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
        pass

    def _on_next(self):
        pass

    def _on_aquired(self, url, path):
        pass
    
    def set_player(self, player):
        assert hasattr(player, 'play')
        self._player = player
        
    def set_acquirer(self, acquirer):
        assert hasattr(acquirer, 'aquire')
        self._acquirer = acquirer
        
    def add_path(self, path='.'):
        pass

    def play(self):
        pass


def main():
    p = player()
    s = scheduler()
    a = acquirer()
    
    p.set_scheduler(s)
    s.set_player(p)
    
    s.add_path('.')
    
    s.play()


if __name__ == '__main__':
    main()

