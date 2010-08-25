#!/usr/bin/python
# -*- coding: utf-8 -*-

"""Implementation of stackless API on top of greenlet module.

Inspired by http://aigamedev.com/open/articles/round-robin-multi-tasking
"""

from collections import deque

import greenlet


#Schedule queue: optimized for front/side operations.
_scheduled = deque()

#Reference to the current active tasklet.
_current = None


def switch(next):
    """Switch the control to the given tasklet.

    Keywords:
        next tasklet object.
    """
    global _current

    _current = next
    if next.firstrun:
        next.firstrun = False
        next.greenlet.switch(*next.args, **next.kwargs)
    else:
        next.greenlet.switch()

def schedule():
    """Schedule a new tasklet.
    """
    global _scheduled
    global _current

    if _current and not _current.blocked:
        _scheduled.append(_current)

    while True:
        next = _scheduled.popleft()
        if not next.alive:
            continue
        
        switch(next)
        break

def getruncount():
    """Get the number of queued tasklets.
    """
    global _scheduled

    return len(_scheduled)

def run():
    """Schedule tasklets untill there are active ones.
    """
    while getruncount() > 0:
        schedule()


class tasklet(object):
    """Wrapper of greenlet object.
    """

    def __init__(self, func):
        """Constructor.
        
        Keywords:
            func body of the tasklet.
        """
        global _scheduled
        
        self.greenlet = greenlet.greenlet(func)
        self.firstrun = True
        self.alive = True
        self.blocked = False
        self.args = ()
        self.kwargs = {}
        
        _scheduled.append(self)
        
    def __call__(self, *args, **kwargs):
        """Load arguments for tasklet initialization.
        """
        self.args = args
        self.kwargs = kwargs

    def run(self):
        """Insert the tasklet in the front of scheduled queue.
        """
        global _scheduled
        
        _scheduled.append(self)
        
class channel(object):
    """Synchronization object used by tasklets.
    """

    def __init__(self):
        """Constructor.
        """
        self.receivers = []
        self.senders = []
        self.data = None
        self.balance = 0

    def send(self, data):
        """Send a new message into the channel or block if no listener is
        available.

        Keywords:
            data message.
        """
        global _scheduled
        global _current
        
        if len(self.receivers) == 0:
            self.senders.append(_current)
            self.balance += 1
            _current.blocked = True
            schedule()

        _scheduled.appendleft(_current)
        g = self.receivers.pop(0)
        g.blocked = False
        self.data = data
        switch(g)

    def receive(self):
        """Receive a message from the channel or block if no message is
        available.
        """
        if len(self.senders) > 0:
            next = self.senders.pop(0)
            next.blocked = False
            next.run() #XXX

        if self.data is None:
            global _current

            self.receivers.append(_current)
            self.balance -= 1
            _current.blocked = True
            schedule()

        data, self.data = self.data, None
        return data
