#!/usr/bin/env python
# -*- coding: utf-8 -*-

import server

def test_player():
    class scheduler_stub:
        def __init__(self):
            pass
        def _on_next(self):
            pass
    p = server.player()
    p.set_scheduler(scheduler_stub)
    p.play()
    

def test_scheduler():
    class player_stub:
        def __init__(self):
            pass
        def play(self):
            pass
    class acquirer_stub:
        def __init__(self):
            pass
        def aquire(self, url):
            pass
    s = server.scheduler()
    s.set_player(player_stub())
    s.set_acquirer(acquirer_stub())
    s.play()

def test_acquirer():
    class scheduler_stub:
        def __init__(self):
            pass
        def _on_next(self):
            pass
        def _on_aquired(self, url, path):
            pass
    a = server.acquirer()
    a.set_scheduler(scheduler_stub())

if __name__ == '__main__':
    test_player()
    test_scheduler()
    test_acquirer()
