try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except ImportError:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

#from PyQt4.QtOpenGL import *

#from libs.corner import Corner
from libs.lib import distance
import numpy as np
import cv2
from PIL import Image
import requests
#import StringIO
import urllib
import sys
import glob
from scene import Scene
import os

sys.path.append('../code/')
Image.MAX_IMAGE_PIXELS = 1000000000

CURSOR_DEFAULT = Qt.ArrowCursor
CURSOR_POINT = Qt.PointingHandCursor
CURSOR_DRAW = Qt.CrossCursor
CURSOR_MOVE = Qt.ClosedHandCursor
CURSOR_GRAB = Qt.OpenHandCursor

# class Canvas(QGLWidget):


class Canvas(QWidget):
    newCorner = pyqtSignal()
    cornerMoved = pyqtSignal()
    drawing = pyqtSignal(bool)

    CREATE, EDIT = list(range(2))
    image = None

    def __init__(self, *args, **kwargs):
        super(Canvas, self).__init__(*args, **kwargs)
        # Initialise local state.

        self.prevPoint = QPointF()
        self._painter = QPainter()
        # Set widget options.
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.WheelFocus)

        self.width = 1280
        self.height = 960

        self.layout_width = 1000
        self.layout_height = 1000

        self.offsetX = 10
        self.offsetY = 10

        self.currentLabel = 0
        self.hiding = False
        self.resize(self.width, self.height)
        self.imageIndex = -1
        self.mode = 'layout'
        self.ctrlPressed = False
        self.shiftPressed = False

        self.patchOffsets = np.zeros(2, dtype=np.int32)
        self.patchSizes = np.full((2, ), 1000, dtype=np.int32)
        self.topdownOffset = 0
        self.topdownScale = 1
        self.topdownImage = None
        return

    # def creating(self):
    #     return self.mode == self.CREATE

    # def editing(self):
    #     return self.mode == self.EDIT

    # def setMode(self, value=True):
    #     self.mode = self.CREATE if value else self.EDIT
    #     if value:  # Create
    #         self.unHighlight()
    #         self.deSelectCorner()
    #     self.prevPoint = QPointF()
    #     self.repaint()


    def readDepth(self, point):
        u = point[0] / self.color_width * self.depth_width
        v = point[1] / self.color_height * self.depth_height
        return self.depth[int(round(v)), int(round(u))]

    def mousePressEvent(self, ev):
        #print(self.drawing(), pos)
        point = self.transformPos(ev.pos())
        if ev.button() == Qt.LeftButton:
            self.scene.addCorner(point + self.patchOffsets, axisAligned=not self.shiftPressed)
            pass
        self.prevPoint = point

        #if ev.button() == Qt.RightButton:
        #pos = self.transformPos(ev.pos(), moving=True)
        #pass
        self.repaint()
        return

    def mouseMoveEvent(self, ev):
        """Update line with last point and current coordinates."""

        if (Qt.RightButton & ev.buttons()):
            point = self.transformPos(ev.pos())
            self.patchOffsets -= (point - self.prevPoint).astype(np.int32)
            sizes = np.array([self.scene.topdown.shape[1], self.scene.topdown.shape[0]])
            self.patchOffsets = np.minimum(np.maximum(self.patchOffsets, 0), sizes - self.patchSizes)
            #self.scene.reloadTopdown()
            self.repaint()
            #self.patchOffsets = np.minimum(np.maximum(self.patchOffsets, 0), self.patchSizes)
            self.prevPoint = point
            #self.loadTopdownImage()
            return

        if (Qt.LeftButton & ev.buttons()):
            point = self.transformPos(ev.pos())
            self.scene.moveCorner(point - self.prevPoint)
            self.repaint()
            #self.patchOffsets = np.minimum(np.maximum(self.patchOffsets, 0), self.patchSizes)
            self.prevPoint = point
            #self.loadTopdownImage()
            return

        return

    def mouseReleaseEvent(self, ev):
        if self.ctrlPressed and self.shiftPressed and self.scene.selectedCornerIndex != -1:
            point = self.transformPos(ev.pos())
            self.scene.moveCorner(point, self.extrinsics_inv, self.intrinsics, self.imageIndex, recording=True)
            pass
        elif self.shiftPressed and self.scene.selectedCornerIndex != -1:
            point = self.transformPos(ev.pos())
            self.scene.moveCorner(point, self.extrinsics_inv, self.intrinsics, self.imageIndex, concave=True)
            self.repaint()
            pass
        self.scene.selectedLayoutCorner = [-1, -1]
        self.scene.selectedCornerIndex = -1
        self.scene.selectedEdgeIndex = -1

        return

    def wheelEvent(self, ev):
        if ev.delta() < 0:
            self.topdownScale = max(self.topdownScale - 1, 1)
        else:
            self.topdownScale = self.topdownScale + 1
            pass
        #self.scene.reloadTopdown()
        self.repaint()
        return

    def handleDrawing(self, pos):
        self.update()

    def selectCornerPoint(self, point):
        """Select the first corner created which contains this point."""
        self.deSelectCorner()
        for corner in reversed(self.corners):
            if corner.selectCorner(point, self.epsilon):
                self.selectCorner(corner)
                #self.calculateOffsets(corner, point)
                break
            continue
        return

    def paintEvent(self, event):
        if (self.imageIndex == -1 or not self.image) and self.mode != 'layout':
            return super(Canvas, self).paintEvent(event)

        p = self._painter
        p.begin(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.HighQualityAntialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)

        self.scene.paint(p, self.patchOffsets, self.patchSizes, self.topdownOffset, self.topdownScale, self.offsetX, self.offsetY)

        p.end()
        return

    def transformPos(self, point, moving=False):
        """Convert from widget-logical coordinates to painter-logical coordinates."""

        return np.array([float(point.x() - self.offsetX), float(point.y() - self.offsetY)])


    def closeEnough(self, p1, p2):
        return distance(p1 - p2) < self.epsilon


    def keyPressEvent(self, ev):
        key = ev.key()
        if (ev.modifiers() & Qt.ControlModifier):
            self.ctrlPressed = True
            if self.hiding:
                self.repaint()
                pass
        else:
            self.ctrlPressed = False
            pass
        if (ev.modifiers() & Qt.ShiftModifier):
            self.shiftPressed = True
            if self.hiding:
                self.repaint()
                pass
        else:
            self.shiftPressed = False
            pass

        if key == Qt.Key_Escape:
            #self.mode = 'moving'
            self.scene.deleteSelected()
            self.repaint()
        if key == Qt.Key_Z:
            self.scene.removeLast()
            self.repaint()
        elif key == Qt.Key_R:
            if self.ctrlPressed:
                self.scene.reset('init')
                self.repaint()
                pass
        elif key == Qt.Key_H:
            #and Qt.ControlModifier == int(ev.modifiers()):
            self.hiding = not self.hiding
            self.repaint()
        elif key == Qt.Key_A:
            self.scene.finalize()
        elif key == Qt.Key_Q:
            if self.mode != 'layout':
                self.mode = 'point'
                pass
        elif key == Qt.Key_S:
            if self.ctrlPressed:
                print('save')
                self.scene.save()
                pass
        elif key == Qt.Key_D:
            self.setCurrentLabel(2)
            self.setMode(False)
        elif key == Qt.Key_F:
            self.setCurrentLabel(3)
            self.setMode(False)
        elif key == Qt.Key_M:
            self.writePLYFile()
        elif key == Qt.Key_Right:
            self.moveToNextImage()
        elif key == Qt.Key_Left:
            self.moveToPreviousImage()
        elif key == Qt.Key_Down:
            self.moveToNextImage(5)
        elif key == Qt.Key_Up:
            self.moveToPreviousImage(5)
        elif key == Qt.Key_1:
            self.moveToNextImage()
            self.mode = 'move'
            self.repaint()
        elif key == Qt.Key_2:
            self.showDensityImage()
            self.mode = 'layout'
            self.repaint()
        elif key == Qt.Key_E:
            if self.ctrlPressed:
                self.scene.exportPly()
                pass
        elif key == Qt.Key_Space:
            self.scene.finalize()
            self.repaint()
            pass
        return

    def keyReleaseEvent(self, ev):
        if self.hiding and self.ctrlPressed:
            self.repaint()
            pass
        self.ctrlPressed = False
        self.shiftPressed = False
        return

    def setCurrentLabel(self, label):
        self.currentLabel = label
        return



    def loadCorners(self, corners):
        self.corners = list(corners)
        self.current = None
        self.currentGroup = currentGroup
        self.repaint()

    def onPoint(self, pos):
        for corner in self.corners:
            if corner.nearestVertex(pos, self.epsilon) is not None:
                return True
            continue
        return False


    def loadScene(self, scenePath):
        self.scene = Scene(scenePath)

        #self.scene.reloadTopdown()
        self.repaint()
        return

    def showDensityImage(self):
        image = self.scene.getDensityImage(self.layout_width, self.layout_height)
        self.image = QPixmap(QImage(image[:, :, ::-1].reshape(-1), self.layout_width, self.layout_height, self.layout_width * 3, QImage.Format_RGB888))
        return

    def moveToNextImage(self, delta=1):
        self.imageIndex = min(self.imageIndex + delta, len(self.imagePaths) - 1)
        self.loadImage()
        return

    def moveToPreviousImage(self, delta=1):
        self.imageIndex = max(self.imageIndex - delta, 0)
        self.loadImage()
        return

    def loadImage(self):
        image = cv2.imread(self.imagePaths[self.imageIndex])
        self.image = QPixmap(QImage(image[:, :, ::-1].reshape(-1), self.color_width, self.color_height, self.color_width * 3, QImage.Format_RGB888))

        self.depth = cv2.imread(self.imagePaths[self.imageIndex].replace('color.jpg', 'depth.pgm'), -1).astype(np.float32) / 1000


        self.extrinsics_inv = []
        with open(self.imagePaths[self.imageIndex].replace('color.jpg', 'pose.txt'), 'r') as f:
            for line in f:
                self.extrinsics_inv += [float(value) for value in line.strip().split(' ') if value.strip() != '']
                continue
            pass
        self.extrinsics_inv = np.array(self.extrinsics_inv).reshape((4, 4))
        self.extrinsics = np.linalg.inv(self.extrinsics_inv)
        self.repaint()
        return

    # def loadTopdownImage(self):
    #     topdown = self.scene.grabTopdown(self.patchOffsets, self.patchSizes)
    #     #topdown = topdown[:, :, ::-1]
    #     topdown = np.minimum((topdown - self.topdownOffset).astype(np.float32) / self.topdownScale * 255, 255).astype(np.uint8)
    #     topdown = np.tile(np.expand_dims(topdown, axis=-1), [1, 1, 3])
    #     self.topdownImage = QPixmap(QImage(topdown.reshape(-1), self.patchSizes[0], self.patchSizes[1], self.patchSizes[0] * 3, QImage.Format_RGB888))
    #     self.repaint()
    #     return

    def removeLastPoint(self):
        self.corners = self.corners[:-1]
        self.repaint()
        return

    def sizeHint(self):
        return self.minimumSizeHint()

    def minimumSizeHint(self):
        if self.image:
            return self.image.size()
        return super(Canvas, self).minimumSizeHint()
