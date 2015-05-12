#!/usr/bin/env python
# -*- coding: utf-8 -*-

import zmq
import time
import sys
import signal

try:
    from PyQt4 import QtGui, QtCore, Qt, uic
except:
    print("you have to have PyQt4 for your version of Python (%s) installed" 
          % ".".join(str(x) for x in sys.version_info))
    sys.exit(-1)

class client:

    def __init__(self):
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.REQ)
        self._socket.connect('tcp://127.0.0.1:9876')
        self._poller = zmq.Poller()
        self._poller.register(self._socket, zmq.POLLIN)

    def request(self, msg):
        self._socket.send_json(msg)
        while True:
            if self._poller.poll(1000) == []:
                print('server timeout!')
                continue
            break
        reply = self._socket.recv_json()
        print(reply)


class yousched_ui(QtGui.QMainWindow):

    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        uic.loadUi('yousched.ui', self)
        self._client = client()
        self.pb_play.clicked.connect(self.on_pb_play_Clicked)
        self.pb_stop.clicked.connect(self.on_pb_stop_Clicked)

    def on_pb_play_Clicked(self):
        print('play')
        self._client.request({'type': 'play'})

    def on_pb_stop_Clicked(self):
        print('stop')
        self._client.request({'type': 'stop'})


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    ex = yousched_ui()
    ex.show()
    sys.exit(app.exec_())

