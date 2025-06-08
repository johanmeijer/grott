"""Grott Growatt monitor base"""
#       For more information how to see aditional documentation on github wiki. #
#       For version history see: version_history.txt
# Updated: 2025-04-06

import sys
import argparse
import logging
from grottconf import Conf
from grottproxy import Proxy
from grottsniffer import Sniff
from grottserver import *
#from collections import defaultdict

VERREL = "3.2.1_20250608"

#set logging definities
LOGGERFORMAT = '%(asctime)s - %(name)s - \t%(levelname)s: %(message)s'
logging.basicConfig(level=logging.INFO,format=LOGGERFORMAT)
DEBUG_LEVELV_NUM = 5


def addLoggingLevel(levelName, levelNum, methodName=None):
    if not methodName:
        methodName = levelName.lower()

    if hasattr(logging, levelName):
        raise AttributeError("{} already defined in logging module".format(levelName))
    if hasattr(logging, methodName):
        raise AttributeError("{} already defined in logging module".format(methodName))
    if hasattr(logging.getLoggerClass(), methodName):
        raise AttributeError("{} already defined in logger class".format(methodName))

    def logForLevel(self, message, *args, **kwargs):
        if self.isEnabledFor(levelNum):
            self._log(levelNum, message, args, **kwargs)

    def logToRoot(message, *args, **kwargs):
        logging.log(levelNum, message, *args, **kwargs)

    logging.addLevelName(levelNum, levelName)
    setattr(logging, levelName, levelNum)
    setattr(logging.getLoggerClass(), methodName, logForLevel)
    setattr(logging, methodName, logToRoot)

addLoggingLevel("DEBUGV", logging.DEBUG - 5)

logger = logging.getLogger(__name__)

logger.info('Grott started, version : %s',VERREL)

#proces config file
conf = Conf(VERREL)
#change loglevel might be changed after config processing.
logger.setLevel(conf.loglevel.upper())

if conf.mode == 'proxy':
    proxy = Proxy(conf)
    try:
        proxy.main(conf)
    #except KeyboardInterrupt:
    except KeyboardInterrupt:
        logger.info("Ctrl C - Stopping server:")
        try:
            proxy.on_close()
        except AttributeError:
            logger.info("no client ports to close")
        sys.exit(1)

if conf.mode == 'sniff':
    sniff = Sniff(conf)
    try:
        sniff.main(conf)
    except KeyboardInterrupt:
        logger.info("Ctrl C - Stopping server")
        sys.exit(1)

if conf.mode in ['server', 'serversa']:

    server = Server(conf)
    try:
        server.main(conf)
    except KeyboardInterrupt:
        logger.info("Ctrl C - Stopping server")
        sys.exit(1)

else:
    logger.critical("Grott undefined mode")
