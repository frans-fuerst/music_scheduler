#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import server
import zmq
import os

CONFIG = {'music_file_pattern':    (".mp3", ".mp4", ".m4a",
                                     ".ogg", ".opus", ),
           'input_dirs':            (os.path.dirname(__file__),),
           'playlist_folder':       './lists',
           'notification_endpoint': 'inproc://step2',
           }

def test_player():
    class scheduler_stub:
        def __init__(self):
            pass

        def get_next(self) -> tuple:
            pass

    _context = zmq.Context()

    p = server.player(_context, CONFIG)
    p.set_scheduler(scheduler_stub())
    p.play()


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
    test_acquirer()
