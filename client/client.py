#!/usr/bin/env python
# -*- coding: utf-8 -*-

import zmq
import sys
import os
import signal
import threading

try:
    from PyQt4 import QtGui, QtCore, uic
except ImportError:
    print("you have to have PyQt4 for your version of Python (%s) installed"
          % ".".join(str(x) for x in sys.version_info))
    sys.exit(-1)

class client: # (QtCore.QObject):

    def __init__(self, hostname):
        self._context = zmq.Context()
        self._req_socket = self._context.socket(zmq.REQ)
        self._req_socket.connect('tcp://%s:9876' % hostname)
        self._req_poller = zmq.Poller()
        self._req_poller.register(self._req_socket, zmq.POLLIN)
        self._notification_handler = None
        self._running = True
        self._sub_thread = threading.Thread(target=self._subscriber_thread_fn)
        self._sub_thread.start()

    def set_notification_handler(self, handler):
        assert hasattr(handler, '_on_notification')
        self._notification_handler = handler

    def request(self, msg):
        self._req_socket.send_json(msg)
        while True:
            if self._req_poller.poll(1000) == []:
                print('server timeout!')
                continue
            break
        reply = self._req_socket.recv_json()
        self._notification_handler._on_message("reply: %s" % reply)
        return reply

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
        _sub_socket.setsockopt(zmq.SUBSCRIBE, b"")

        _sub_poller = zmq.Poller()
        _sub_poller.register(_sub_socket, zmq.POLLIN)

        while True:
            if not self._running:
                break
            if _sub_poller.poll(200) == []:
                continue
            _msg = _sub_socket.recv_json()
            print('published "%s"' % _msg)
            if self._notification_handler:
                self._notification_handler._on_notification(_msg)

        _sub_socket.close()
        print("disconnect from broadcasts")


class yousched_ui(QtGui.QMainWindow):

    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        uic.loadUi(os.path.join(os.path.dirname(__file__), 'yousched.ui'), self)
        self._client = client('127.0.0.1')
        self._client.set_notification_handler(self)
        self.pb_play.clicked.connect(self.on_pb_play_Clicked)
        self.pb_skip.clicked.connect(self.on_pb_skip_Clicked)
        self.pb_upvote.clicked.connect(self.on_pb_upvote_Clicked)
        self.pb_ban.clicked.connect(self.on_pb_ban_Clicked)
        self.pb_stop.clicked.connect(self.on_pb_stop_Clicked)
        self.pb_add.clicked.connect(self.on_pb_add_Clicked)

        # should be done by client
        _result = self._client.request({'type': 'hello', 'name': 'frans'})
        if 'current_track' in _result:
            self._update_track_info(_result['current_track'])

    def _update_track_info(self, filename):
        self.lbl_current_track.setText(os.path.basename(filename))

    def _on_notification(self, msg):
        QtCore.QMetaObject.invokeMethod(
            self, "_on_server_notification",
            QtCore.Qt.QueuedConnection,
            QtCore.Q_ARG(dict, msg))

    def _on_message(self, msg):
        QtCore.QMetaObject.invokeMethod(
            self, "_message_out",
            QtCore.Qt.QueuedConnection,
            QtCore.Q_ARG(str, msg))

    @QtCore.pyqtSlot(dict)
    def _on_server_notification(self, msg):
        self._message_out(msg)
        if 'track' in msg:
            self._update_track_info(msg['track'])

    @QtCore.pyqtSlot(str)
    def _message_out(self, msg):
        self.lst_messages.addItem(str(msg))
        self.lst_messages.scrollToBottom()
        print(msg)

    def on_pb_play_Clicked(self):
        print('play')
        self._client.request({'type': 'play'})

    def on_pb_skip_Clicked(self):
        print('skip')
        self._client.request({'type': 'skip'})

    def on_pb_upvote_Clicked(self):
        print('upvote')
        self._client.request({'type': 'upvote'})

    def on_pb_ban_Clicked(self):
        print('ban')
        self._client.request({'type': 'ban'})

    def on_pb_stop_Clicked(self):
        print('stop')
        self._client.request({'type': 'stop'})

    def on_pb_add_Clicked(self):
        print('add %s' % self.le_add.text())
        self._client.request(
            {'type': 'add',
             'url':  str(self.le_add.text())})

    def closeEvent(self, event):
        self._client.shutdown()


if __name__ == '__main__':
    print("Python info: %s, %s" % (
        '.'.join((str(e) for e in sys.version_info)),
        sys.executable))

    app = QtGui.QApplication(sys.argv)
    ex = yousched_ui()
    ex.show()
    sys.exit(app.exec_())

