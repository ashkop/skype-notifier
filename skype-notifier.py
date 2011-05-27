#!/usr/bin/python
from Skype4Py.api.posix_x11 import SkypeAPI
from Skype4Py.api.posix_x11 import threads_init
threads_init()
import Skype4Py

import logging
import indicate
import gtk
import time
import signal
import threading

Skype4Py.Skype._SetEventHandlerObj = Skype4Py.Skype._SetEventHandlerObject

logging.getLogger('Skype4Py').addHandler(logging.StreamHandler())
#logging.getLogger('Skype4Py').setLevel(logging.DEBUG)

class Indicators:
    def __init__(self, skype):
        self.skype_handler = skype
        self.server = indicate.indicate_server_ref_default()
        self.server.set_type("message.im")
        self.server.set_desktop_file("/usr/share/applications/skype.desktop")
        self.server.connect("server-display", skype.focus)
        self.server.show()
        self._indicators = dict()
        self._lock = threading.Lock()

    def add_indicator(self, label, handle, msg_time, msg_id):
        if handle not in self._indicators.keys():
            indicator = indicate.Indicator()
            indicator.set_property('subtype', "im")
            indicator.set_property('handle', handle)
            indicator.connect('user-display', self.skype_handler.open_conversation)
            self._indicators[handle] = indicator
        else:
            indicator = self._indicators[handle]
            count = indicator.get_property('count')
            if count:
               count = int(count) + 1
            else:
               count = 2
            indicator.set_property('count', str(count))
        indicator.set_property_time('time', msg_time)
        indicator.set_property_bool('draw-attention', True)
        indicator.show()
        indicator.set_property("name", label)


    def remove_indicator(self, handle, msg_id):
        if handle in self._indicators:
            indicator = self._indicators[handle]
            count = indicator.get_property('count')
            if count and int(count) > 1:
                indicator.set_property('count', str(int(count) - 1))
            else:
                indicator.hide()
                indicator.set_property_bool('draw-attention', False)
                del self._indicators[handle]


class SkypeHandler:

    def __init__(self):

        self.client = self.get_client()
        self.client.Attach()
        self.indicators = Indicators(self)

    def get_client(self):

        skype = Skype4Py.Skype(Events=self, Api=SkypeAPI({}))

        if not skype.Client.IsRunning:
            raise Exception("Skype is not running")

        return skype

    def focus(self, server, object_):
        self.client.Client.Focus()

    def open_conversation(self, indicator, object_):
        handle = indicator.get_property('handle')
        try:
            chat = self.client.Chat(handle)
        except Skype4Py.errors.SkypeError:
            try:
                self.client.Client.OpenDialog("IM", handle)
            except Skype4Py.errors.SkypeError, exc:
                if exc[0] != 7:
                    raise
        else:
            chat.OpenWindow()

    def MessageStatus(self, msg, status):
      with self._lock:
        if (len(msg.Chat.Members) > 2):
            label = msg.Chat.Topic
            handle = msg.ChatName
        else:
            label = msg.FromDisplayName
            handle = msg.FromHandle
        if status == 'RECEIVED':
            self.indicators.add_indicator(label, handle, msg.Timestamp, msg.Id)
        elif status == "READ":
            self.indicators.remove_indicator(handle, msg.Id)



if __name__ == '__main__':
    SkypeHandler()
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    gtk.main()
