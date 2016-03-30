rrplayer - respectful remote player
===================================

desired features
----------------

- [ ] DJ/Party mode: music never stops
- [ ] themes can be defined with individual rules
- [ ] clients can see what's currently being played
- [ ] music can be voted
- [ ] play lists are being recorded
- [ ] the scheduler is 'listener aware' - respects present listeners
- [ ] server provides fuzzy search among available files
- [ ] listeners can upload files/urls which are being downloaded
- [ ] clients can find and control multiple servers
- [ ] tagging of files/folders/artists
- [ ] server and client side blacklists/tags/upvotes


naming
------

social smart media player party mode 


technical approaches
--------------------

. how is music being played?
  - cross-fading
  - support mixing/filtering
  - supports mp3 m4a ogg opus flac
  - supports streaming
- ? musicplayer?
- ? pygame ?

. how is online content being accessed?


https://github.com/rg3/youtube-dl


interesting links
-----------------
* http://albertz.github.io/music-player/
  https://pypi.python.org/pypi/musicplayer


API
---

client -> server
++++++++++++++++

* hello, I'm here
* add folder
* select rule


server -> clients (publish)
+++++++++++++++++++++++++++

* current song
* errors


requirements
------------
python3

python3-pygame
 pip3
 mercurial
 pip3 -v install hg+http://bitbucket.org/pygame/pygame
 SDL-devel
 http://pkgs.org/search/smpeg-devel