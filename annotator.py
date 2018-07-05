import sys
import os
from functools import partial
import numpy as np

try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except ImportError:
    # needed for py3+qt4
    # Ref:
    # http://pyqt.sourceforge.net/Docs/PyQt4/incompatible_apis.html
    # http://stackoverflow.com/questions/21217399/pyqt4-qtcore-qvariant-object-instead-of-a-string
    if sys.version_info.major >= 3:
        import sip
        sip.setapi('QVariant', 2)
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

import resources
# Add internal libs
from libs.constants import *
from libs.lib import struct, newAction, newIcon, addActions, fmtShortcut, generateColorByText
from libs.settings import Settings
from libs.canvas import Canvas
from libs.ustr import ustr
from libs.version import __version__
import glob

__appname__ = 'annotator'

class MainWindow(QMainWindow):
    FIT_WINDOW, FIT_WIDTH, MANUAL_ZOOM = list(range(3))

    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle(__appname__)

        self.settings = Settings()
        self.settings.load()
        settings = self.settings

        self.dataFolder = '../floor_plan_chinese/'

        self.canvas = Canvas()

        self.setCentralWidget(self.canvas)

        action = partial(newAction, self)

        nextU = action('&NextU', self.moveToNextUnannotated,
                      'n', 'nextU', u'Move to next unannotated example')
        next = action('&Next', self.moveToNext,
                      'Ctrl+n', 'next', u'Move to next example')


        # Store actions for further handling.
        self.actions = struct(nextU=nextU, next=next)


        #self.scenePaths = os.listdir(self.dataFolder)
        imagePaths = glob.glob('../floor_plan_chinese/*') + glob.glob('../floor_plan_chinese/*/*') + glob.glob('../floor_plan_chinese/*/*/*') + glob.glob('../floor_plan_chinese/*/*/*/*')
        self.imagePaths = [imagePath for imagePath in imagePaths if '.jpg' in imagePath or '.png' in imagePath or '.jpeg' in imagePath]
        print(len(self.imagePaths))
        self.imageIndex = 0
        
        self.moveToNextUnannotated()

        size = settings.get(SETTING_WIN_SIZE, QSize(640, 480))
        position = settings.get(SETTING_WIN_POSE, QPoint(0, 0))
        self.resize(size)
        self.move(position)

        self.queueEvent(self.loadImage)


    def paintCanvas(self):
        #assert not self.image.isNull(), "cannot paint null image"
        self.canvas.adjustSize()
        self.canvas.update()
        return

    def moveToNextUnannotated(self):
        self.imageIndex = (self.imageIndex + 1) % len(self.imagePaths)
        self.loadImage()
        return

    def moveToNext(self):
        self.imageIndex = (self.imageIndex + 1) % len(self.imagePaths)
        self.loadImage()        
        return

    def loadImage(self):
        imagePath = self.imagePaths[self.imageIndex]
        self.canvas.loadScene(imagePath)
        self.paintCanvas()
        self.setWindowTitle(__appname__ + ' ' + imagePath)
        self.canvas.setFocus(True)
        return


    def queueEvent(self, function):
        QTimer.singleShot(0, function)
        return


def get_main_app(argv=[]):
    """
    Standard boilerplate Qt application code.
    Do everything but app.exec_() -- so that we can test the application in one thread
    """
    app = QApplication(argv)
    app.setApplicationName(__appname__)
    app.setWindowIcon(newIcon("app"))
    # Tzutalin 201705+: Accept extra agruments to change predefined class file
    # Usage : labelImg.py image predefClassFile
    win = MainWindow()
    win.show()
    return app, win


def main(argv=[]):
    '''construct main app and run it'''
    app, _win = get_main_app(argv)
    return app.exec_()

if __name__ == '__main__':
    sys.exit(main(sys.argv))
