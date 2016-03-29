#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from scheduler import scheduler
import os

if __name__ == '__main__':

    config = {'music_file_pattern':    (".mp3", ".mp4", ".m4a",
                                        ".ogg", ".opus", ),
              'input_dirs':            (os.path.dirname(__file__),),
              'notification_endpoint': 'inproc://step2',
              }

    with scheduler(config) as s:
        s.add_path(path=os.path.dirname(__file__))

        #def get_next(self):
    #def _on_aquired(self, url, path):

    #def set_player(self, player_inst):

    #def set_acquirer(self, acquirer_inst):


    #def _is_music(self, filename):
    #def _get_music(self, files):

    #def _crawl_path(self, path=None):

