#!/usr/bin/env python
# -*- coding: utf-8 -*-

import zmq
import time
import sys
import os
import signal
import threading

try:
    from PyQt4 import QtGui, QtCore, Qt, uic
except:
    print("you have to have PyQt4 for your version of Python (%s) installed" 
          % ".".join(str(x) for x in sys.version_info))
    sys.exit(-1)

class client:

    def __init__(self):
        self._context = zmq.Context()
        self._req_socket = self._context.socket(zmq.REQ)
        self._req_socket.connect('tcp://127.0.0.1:9876')
        self._req_poller = zmq.Poller()
        self._req_poller.register(self._req_socket, zmq.POLLIN)
        self._running = True
        self._sub_thread = threading.Thread(target=self._subscriber_thread_fn)
        self._sub_thread.start()

    def request(self, msg):
        self._req_socket.send_json(msg)
        while True:
            if self._req_poller.poll(1000) == []:
                print('server timeout!')
                continue
            break
        reply = self._req_socket.recv_json()
        print(reply)

    def shutdown(self):
        print('shutdown client..')
        self._running = False
        self._sub_thread.join()
        self._req_socket.close()
        self._context.term()
        print('ready!')

    def _subscriber_thread_fn(self):
        print("connect to broadcasts")
        _sub_socket = self._context.socket(zmq.SUB)
        _sub_socket.connect('tcp://127.0.0.1:9875')
        _sub_socket.setsockopt(zmq.SUBSCRIBE, "")
        
        _sub_poller = zmq.Poller()
        _sub_poller.register(_sub_socket, zmq.POLLIN)

        while True:
            if not self._running:
                break
            if _sub_poller.poll(200) == []:
                continue
            _msg = _sub_socket.recv_json()
            print('published "%s"' % _msg)
        _sub_socket.close()
        print("disconnect from broadcasts")

class yousched_ui(QtGui.QMainWindow):

    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'yousched.ui'), self)
        self._client = client()
        self.pb_play.clicked.connect(self.on_pb_play_Clicked)
        self.pb_stop.clicked.connect(self.on_pb_stop_Clicked)

    def on_pb_play_Clicked(self):
        print('play')
        self._client.request({'type': 'play'})

    def on_pb_stop_Clicked(self):
        print('stop')
        self._client.request({'type': 'stop'})

    def closeEvent(self, event):
        self._client.shutdown()


if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    ex = yousched_ui()
    ex.show()
    sys.exit(app.exec_())

