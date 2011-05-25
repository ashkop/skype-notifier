#!/usr/bin/python

import Skype4Py
import pynotify
import logging
import indicate
import gtk


Skype4Py.Skype._SetEventHandlerObj = Skype4Py.Skype._SetEventHandlerObject


class FixedDbusApi(Skype4Py.api.posix_dbus.SkypeAPI):
    
    def run(self):
        self.logger.info('thread started')
        if self.run_main_loop:
            context = self.mainloop.get_context()
            while True:
                context.iteration(False)
                time.sleep(0.2)
        self.logger.info('thread finished')


class Indicators:
    
    def __init__(self, skype):
        
        self.skype_handler = skype
        
        self.server = indicate.indicate_server_ref_default()
        self.server.set_type("message.im")
        self.server.set_desktop_file("/usr/share/applications/skype.desktop")
        self.server.connect("server-display", skype.focus)
        
        self._indicators = dict()
        
    def add_indicator(self, label, handle, msg_time, msg_id):
        if label in self._indicators:
            indicator = self._indicators[label]
            count = indicator.get_property('count')
            if count:
                count += 1
            else:
                count = 2
            indicator.set_property_int('count', count)
        
        else:
            indicator = indicate.Indicator()
            indicator.set_property('name', label)
            indicator.set_property('handle', handle)
            indicator.messages = list()
            indicator.connect('user-display', self.skype_handler.open_conversation)
            
        indicator.set_property_time('time', msg_time)
        indicator.set_property_bool('draw-attention', True)
        indicator.messages.append(msg_id)
        
        self._indicators[label] = indicator
            
    
    def remove_indicator(self, label, msg_id):
        if label in self._indicators:
            if msg_id in self._indicators[label].messages:
                indicator = self._indicators[label]
                indicator.messages.remove(msg_id)
                count = indicator.get_property('count')
                if count and count > 1:
                    indicator.set_property_int('count', count - 1)
                else:
                    indicator.hide()
                    indicator.set_property_bool('draw-attention', False)


class SkypeHandler:
    
    def __init__(self, indicators):
        
        self.client = self.get_client()
        self.client.Attach()
        self.indicators = indicators
        
    def get_client(self):

        skype = Skype4Py.Skype(Events=self, Api=FixedDbusApi())

        if not skype.Client.IsRunning:
            raise Exception("Skype is not running")
        
        return skype
    
    def focus(self, server, object_):
        self.client.Client.Focus() 
        
    def open_conversation(self, indicator, object_):
        handle = indicator.get_property('handle')
        self.client.OpenDialog('IM', handle)
        
    def MessageStatus(self, message, status):
        if status == "RECEIVED":
            if (len(msg.Chat.Members) > 2):
                label = msg.ChatName
                handle = msg.ChatName
            else:
                label = msg.FromHandle
                handle = msg.FromHandle
                self.indicators.add_indicator(label, handle, msg.Timestamp, msg.Id)
        elif status == "READ":
            self.indicators.remove_indicator(label, msg.Id)
        


if __name__ == '__main__':
    indicators = Indicators()
    SkypeHandler(indicators)
    gtk.main()