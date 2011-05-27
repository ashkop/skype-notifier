#!/usr/bin/python

# enable X11 multi-threading
from Skype4Py.api.posix_x11 import threads_init
threads_init()
# use X11 based API instead of D-Bus
from Skype4Py.api.posix_x11 import SkypeAPI

import Skype4Py

import indicate
import pynotify
import threading
import signal
import os
import gtk
import time

# Fix Skype4Py spelling issue
Skype4Py.Skype._SetEventHandlerObj = Skype4Py.Skype._SetEventHandlerObject

class Indicators:
    """ This class represents a set of indicators in Ubuntu Messaging Menu """
    def __init__(self, skype):
        """ Initialize indicator server"""
        self.skype_handler = skype
        
        self.server = indicate.indicate_server_ref_default()
        self.server.set_type("message.im")
        self.server.set_desktop_file("/usr/share/applications/skype.desktop")
        self.server.connect("server-display", skype.focus)
        self.server.show()
        
        self._indicators = dict()
        self._messages = dict()
        self._lock = threading.Lock()

    def add_indicator(self, label, handle, msg_time, msg_id):
        """ Process single message
            If sender indicator exists than increment count property.
            Create new indicator otherwise
        """
        if handle not in self._indicators.keys():
            indicator = indicate.Indicator()
            indicator.set_property('subtype', "im")
            indicator.set_property('handle', handle)
            indicator.connect('user-display', self.skype_handler.open_conversation)
            
            self._indicators[handle] = indicator
            self._messages[handle] = list()
        else:
            indicator = self._indicators[handle]
            count = indicator.get_property('count')
            # Don't set count = 1 cause, so time is used for single message
            if count:
               count = int(count) + 1
            else:
               count = 2
            indicator.set_property('count', str(count))
        indicator.set_property_time('time', msg_time)
        indicator.set_property_bool('draw-attention', True)
        indicator.show()
        # Set name property after show(), otherwise indicator appears in menu without name
        indicator.set_property("name", label)
        
        self._messages[handle].append(msg_id)


    def remove_indicator(self, handle, msg_id):
        if handle in self._indicators and handle in self._messages:
            if msg_id in self._messages[handle]:
                indicator = self._indicators[handle]
                self._messages[handle].remove(msg_id)
                count = indicator.get_property('count')
                if count and int(count) > 1:
                    indicator.set_property('count', str(int(count) - 1))
                else:
                    indicator.hide()
                    indicator.set_property_bool('draw-attention', False)
                    del self._indicators[handle]

    def notify(self, label, msg_body):
        n = pynotify.Notification('Skype', "%s:  %s" % (label, msg_body), 'skype')
        n.set_hint_string('append', '')
        n.show()


class SkypeHandler:

    def __init__(self):

        self.client = self.get_client()
        self.client.Attach()
        self.indicators = Indicators(self)
        
        # Handle messages that were received before script launch
        self.handle_unread_messages()

    def get_client(self):
        """ Reveice Skype4Py.Skype instance
            ** Maybe launch Skype if not launched?
        """
        skype = Skype4Py.Skype(Events=self, Api=SkypeAPI({}))

        if not skype.Client.IsRunning:
            raise Exception("Skype is not running")

        return skype

    def focus(self, server, object_):
        """ Callback for indicator server """
        self.client.Client.Focus()

    def open_conversation(self, indicator, object_):
        """ Callback for message indicators """
        handle = indicator.get_property('handle')
        try:
            chat = self.client.Chat(handle)
        except Skype4Py.errors.SkypeError:
            try:
                self.client.Client.OpenDialog("IM", handle)
            except Skype4Py.errors.SkypeError, exc:
                # Workaround to fix Skype API issue - OpenDialog("IM", handle, text=u"")
                # raises exception if text is empty but opens dialog
                if exc[0] != 7:
                    raise
        else:
            chat.OpenWindow()

    def MessageStatus(self, msg, status):
        """ Skype event handler """ 
        if (len(msg.Chat.Members) > 2):
            label = msg.Chat.Topic
            handle = msg.ChatName
            icon = None
        else:
            label = msg.FromDisplayName
            handle = msg.FromHandle
        if status == 'RECEIVED':
            self.indicators.add_indicator(label, handle, msg.Timestamp, msg.Id)
            self.indicators.notify(label, msg.Body)
        elif status == "READ":
            self.indicators.remove_indicator(handle, msg.Id)

    def handle_unread_messages(self):
        for msg in self.client.MissedMessages:
            self.MessageStatus(msg, msg.Status)



if __name__ == '__main__':
    SkypeHandler()
    # Allow Ctrl+C while running
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    gtk.main()
