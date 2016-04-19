Documentation
-------------

- [ ] explain intension

Component independent features
------------------------------
- [ ] Guess Artist / Album / Track name
    - read metainfo/ID3 tags from files

Client
------
- [ ] show/edit tagging
- [ ] continuous connection
- [ ] select playlist
- [ ] Icon
- [ ] send continuous hello/status (heartbeat)
- [ ] smarter logging (colors more infoless boilerplate)
- [ ] download current track/folder
- [ ] "remember for <playlist>" button
- [x] save options
- [x] split track name

Sever core
----------
- [ ] say welcome
- [ ] Listener aware scheduling
    - keep list of connected listeners
- [ ] Provide download option (http?)
- [ ] shutdown gracefully on CTRL-C

player backend
--------------
- [ ] set volume absolutely
- [ ] play/resume
- [ ] stop (unload player process)
- [ ] use -slave commands
- [ ] Play/Pause SM
- [ ] Jump/Seek

Scheduler
---------
- [ ] escape ','
- [ ] ignore equal rules
- [ ] improve scheduling: stick to folders
- [ ] make use of upvotes
- [ ] find similar strings: "üé-_"
- [ ] favor 'similar' items (same path, same artist)

Aquirer
-------
* recognize youtube links, incorporate youtube-dl
