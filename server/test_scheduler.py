#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from scheduler import scheduler
import os
import sys
import time
import shutil

CONFIG = {'music_file_pattern':    (".mp3", ".mp4", ".m4a",
                                    ".ogg", ".opus", ),
          'input_dirs':            (os.path.dirname(__file__),),
          'playlist_folder':       './lists',
          'notification_endpoint': 'inproc://step2',
          }

def test_rule():
    r1 = scheduler.rule(line='123.23, frans, ban, bla/bla/bla, 12')
    r2 = scheduler.rule(listener='frans',
                        tag_name='ban', tag_string='michael jackson')
    assert r2._folder_component is None and r2._file_component is None

    r3 = scheduler.rule(listener='frans',
                        tag_name='ban', tag_string='some/path')
    assert r3._folder_component is None and r3._file_component is None
    assert r3.tag_string == 'some/path'
    r4 = scheduler.rule(
        listener='frans', tag_name='ban',
        tag_string='reykjavik/nu - man o to (original mix).wmv-ksmebecxzya.m4a')
    assert not r4.matches('reykjavik', 'Worakls - From Now On-1fcOQ6YbL9Q.opus')


def test_scheduler():

    if os.path.isdir('./lists'):
        print('remove playlist folder')
        shutil.rmtree('./lists')

    with scheduler(config=CONFIG) as s:
        lists = s.get_smartlists()
        print(lists)
        assert s.get_active_smartlist() == 'unspecified'
        s.add_path(path=os.path.dirname(__file__))

        s.activate_smartlist('party')

        _some_track = ('/root', 'some/path', 'file.mp3')

        # upvote
        s.add_tag(listener='frans',
                  track=('/root', 'some/path', 'file.mp3'), pos=123,
                  details={'tag_name': 'upvote'})

        #ban
        s.add_tag(listener='frans', track=_some_track, pos=123,
                  details={'tag_name': 'ban', 'subject' : 'some/file_substring'})

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
    print(sys.version_info)
    test_rule()
    test_scheduler()
