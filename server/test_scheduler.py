#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from scheduler import scheduler
import os

def test_scheduler():

    config = {'music_file_pattern':    (".mp3", ".mp4", ".m4a",
                                        ".ogg", ".opus", ),
              'input_dirs':            (os.path.dirname(__file__),),
              'playlist_folder':       './lists',
              'notification_endpoint': 'inproc://step2',
              }

    with scheduler(config) as s:
        lists = s.get_smartlists()
        print(lists)
        assert s.get_active_smartlist() == 'unspecified'
        s.add_path(path=os.path.dirname(__file__))

        s.activate_smartlist('party')

        # upvote
        s.upvote(subject='rel/path/to/file', pos=123, user='frans')

        #ban
        s.add_tag('some/file_substring', user='frans')

        print(s.present_listeners())
        s.add_present_listener('frans')
        s.add_present_listener('julia')

        print(s.present_listeners())
        s.remove_present_listener('frans')

        #def get_next(self):
        #def _on_aquired(self, url, path):
        #def set_player(self, player_inst):

        #def set_acquirer(self, acquirer_inst):

        #def _is_music(self, filename):
        #def _get_music(self, files):

        #def _crawl_path(self, path=None):

if __name__ == '__main__':
    test_scheduler()