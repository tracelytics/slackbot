# -*- coding: utf-8 -*-
from __future__ import absolute_import
import imp
import importlib
import logging
import re
import time
from glob import glob
from six.moves import _thread
from slackbot import settings
from slackbot.manager import PluginsManager
from slackbot.slackclient import SlackClient
from slackbot.dispatcher import MessageDispatcher

logger = logging.getLogger(__name__)


class Bot(object):
    def __init__(self):
        self._client = SlackClient(
            settings.API_TOKEN,
            bot_icon=settings.BOT_ICON if hasattr(settings,
                                                  'BOT_ICON') else None,
            bot_emoji=settings.BOT_EMOJI if hasattr(settings,
                                                    'BOT_EMOJI') else None
        )
        self._plugins = PluginsManager()
        self._dispatcher = MessageDispatcher(self._client, self._plugins,
                                             settings.ERRORS_TO)

    def run(self):
        self._plugins.init_plugins()
        self._dispatcher.start()
        self._client.rtm_connect()
        _thread.start_new_thread(self._keepactive, tuple())
        logger.info('connected to slack RTM api')
        self._dispatcher.loop()

    def _keepactive(self):
        logger.info('keep active thread started')
        while True:
            time.sleep(30 * 60)
            self._client.ping()

class Matcher(object):
    def __init__(self, pattern, flags, key, allow_bots):
        self.pattern = re.compile(pattern, flags)
        self.key = key
        self.allow_bots = allow_bots

    def __hash__(self):
        return hash(self.pattern)

    def match(self, msg):
        """ Match according to configured rules.
        If bot matches are not permitted, and this is a known bot, return immediately.
        If we have provided a key function, run the key function on the message
        to extract the text.
        Then match the pattern against the text.
        """
        if not self.allow_self and msg['bot']:
            return None
        if key is not None:
            txt = key(msg)
        else:
            txt = msg['text']
        return self.pattern.search(txt)


def respond_to(matchstr, flags=0, key=None, allow_bots=False):
    def wrapper(func):
        matcher = Matcher(matchstr, flags, key, allow_bots)
        PluginsManager.commands['respond_to'][matcher] = func
        logger.info('registered respond_to plugin "%s" to "%s"', func.__name__,
                    matchstr)
        return func

    return wrapper


def listen_to(matchstr, flags=0, key=None, allow_bots=False):
    def wrapper(func):
        matcher = Matcher(matchstr, flags, key, allow_bots)
        PluginsManager.commands['listen_to'][matcher] = func
        logger.info('registered listen_to plugin "%s" to "%s"', func.__name__,
                    matchstr)
        return func

    return wrapper


# def default_reply(matchstr=r'^.*$', flags=0):
def default_reply(*args, **kwargs):
    """
    Decorator declaring the wrapped function to the default reply hanlder.

    May be invoked as a simple, argument-less decorator (i.e. ``@default_reply``) or
    with arguments customizing its behavior (e.g. ``@default_reply(matchstr='pattern')``).
    """
    invoked = bool(not args or kwargs)
    matchstr = kwargs.pop('matchstr', r'^.*$')
    flags = kwargs.pop('flags', 0)
    key = kwargs.pop('key', None)
    allow_bots = kwargs.pop('allow_bots', False)

    if not invoked:
        func = args[0]

    def wrapper(func):
        matcher = Matcher(matchstr, flags, key, allow_bots)
        PluginsManager.commands['default_reply'][matcher] = func
        logger.info('registered default_reply plugin "%s" to "%s"', func.__name__,
                    matchstr)
        return func

    return wrapper if invoked else wrapper(func)
