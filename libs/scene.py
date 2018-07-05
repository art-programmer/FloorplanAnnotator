import numpy as np

try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
except ImportError:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *
import copy
import os
from utils import *
import cv2
import glob
import json

COLOR_MAP = [QColor(255, 0, 0), QColor(0, 255, 0), QColor(0, 0, 255), QColor(255, 0, 255)]


class Scene():
    def __init__(self, scenePath):
        self.colorMap = ColorPalette(1000).getColorMap()
        self.scenePath = scenePath

        self.imageWidth = 256
        self.imageHeight = 256

        image = cv2.imread(scenePath)
        self.topdownImage = QPixmap(QImage(image.reshape(-1), image.shape[1], image.shape[0], image.shape[1] * 3, QImage.Format_RGB888))
        os.system('mkdir ' + self.scenePath + '_annotation')
        self.reset()
        return

    def reset(self, mode='load'):
        self.loading = True
        #self.topdownImage = None

        self.corners = []
        self.connections = []
        self.prevCornerIndex = -1

        if os.path.exists(self.scenePath + '_annotation/corners.npy'):
            self.corners = np.load(self.scenePath + '_annotation/corners.npy').tolist()
            pass
        if os.path.exists(self.scenePath + '_annotation/connections.npy'):
            self.connections = np.load(self.scenePath + '_annotation/connections.npy').tolist()
            pass

        #self.fixCornersOnEdges()
        self.load()
        return

    def fixCornersOnEdges(self, epsilon=10):
        while True:
            hasChange = False
            for cornerIndex, corner in enumerate(self.corners):
                for connection in self.connections:
                    if cornerIndex in connection:
                        continue
                    corner_1 = np.array(self.corners[connection[0]])
                    corner_2 = np.array(self.corners[connection[1]])
                    normal = corner_1 - corner_2
                    normal /= max(np.linalg.norm(normal), 1e-4)
                    normal = np.array([normal[1], -normal[0]])
                    distance = np.dot(corner_1, normal) - np.dot(corner, normal)
                    if abs(distance) < epsilon * 2 and ((abs(normal[1]) > abs(normal[0]) and corner[0] > min(corner_1[0], corner_2[0]) and corner[0] < max(corner_1[0], corner_2[0])) or (abs(normal[1]) < abs(normal[0]) and corner[1] > min(corner_1[1], corner_2[1]) and corner[1] < max(corner_1[1], corner_2[1]))):
                        self.connections.append((connection[0], cornerIndex))
                        self.connections.append((connection[1], cornerIndex))
                        self.connections.remove(connection)
                        hasChange = True
                        break
                    continue
                continue
            if not hasChange:
                break
            continue
        return

    def findRoomCorners(self):
        #for roomName, roomLabel in self.roomLabelDict.iteritems():
        self.roomCorners = {}
        initialCornerSize = 40
        for cornerIndex, corner in enumerate(self.corners):
            cornerSize = initialCornerSize
            corner = np.round(np.array(corner)).astype(np.int32)
            while True:
                roomLabels = self.roomSegmentation[max(corner[1] - cornerSize / 2, 0):min(corner[1] + cornerSize / 2, self.roomSegmentation.shape[0] - 1), max(corner[0] - cornerSize / 2, 0):min(corner[0] + cornerSize / 2, self.roomSegmentation.shape[1] - 1)]
                roomLabels = roomLabels[roomLabels > 0]
                if len(roomLabels) == 0:
                    cornerSize += 2
                    continue
                roomLabels = np.unique(roomLabels)
                for roomLabel in roomLabels:
                    if roomLabel not in self.roomCorners:
                        self.roomCorners[roomLabel] = []
                        pass
                    self.roomCorners[roomLabel].append(cornerIndex)
                    continue
                break
            continue
        return


    def paint(self, painter, patchOffsets, patchSizes, topdownOffset, topdownScale, offsetX, offsetY):
        if self.loading:
            return
        #sizes = np.array([self.topdown.shape[1], self.topdown.shape[0]])
        #patchOffsets = np.minimum(np.maximum(patchOffsets, 0), sizes - patchSizes)

        #topdown = self.topdown[patchOffsets[1]:patchOffsets[1] + patchSizes[1]][patchOffsets[0]:patchOffsets[0] + patchSizes[0]]
        #topdown = np.minimum((topdown - topdownOffset).astype(np.float32) / topdownScale * 255, 255).astype(np.uint8)
        #topdown = np.tile(np.expand_dims(topdown, axis=-1), [1, 1, 3])
        
        painter.drawPixmap(offsetX, offsetY, self.topdownImage)

        color = COLOR_MAP[0]
        pen = QPen(color)
        pen.setWidth(3)
        painter.setPen(pen)
        d = 10

        corner_path = QPainterPath()
        points = []
        for _, corner in enumerate(self.corners):
            point = QPoint(int(round(corner[0] - patchOffsets[0] + offsetX)), int(round(corner[1] - patchOffsets[1] + offsetY)))
            points.append(point)
            corner_path.addEllipse(point, d / 2.0, d / 2.0)
            continue
        painter.drawPath(corner_path)

        connection_path = QPainterPath()
        for connection in self.connections:
            connection_path.moveTo(points[connection[0]])
            connection_path.lineTo(points[connection[1]])
            continue
        painter.drawPath(connection_path)


        return


    def addCorner(self, newCorner, axisAligned=True, epsilon=10):
        newCornerIndex = -1
        for cornerIndex, corner in enumerate(self.corners):
            if np.linalg.norm(corner - newCorner) < epsilon:
                newCornerIndex = cornerIndex
                break
            continue
        if newCornerIndex == -1:
            newCornerIndex = len(self.corners)
            if self.prevCornerIndex != -1 and axisAligned:
                delta = newCorner - self.corners[self.prevCornerIndex]
                if abs(delta[0]) < abs(delta[1]):
                    delta[0] = 0
                else:
                    delta[1] = 0
                    pass
                newCorner = self.corners[self.prevCornerIndex] + delta
                pass

            for connection in self.connections:
                corner_1 = np.array(self.corners[connection[0]])
                corner_2 = np.array(self.corners[connection[1]])
                normal = corner_1 - corner_2
                normal /= max(np.linalg.norm(normal), 1e-4)
                normal = np.array([normal[1], -normal[0]])
                distance = np.dot(corner_1, normal) - np.dot(newCorner, normal)
                #print(abs(normal[1]) < abs(normal[0]), corner[1] > min(corner_1[1], corner_2[1]), corner[1] < max(corner_1[1], corner_2[1]))
                if abs(distance) < epsilon * 2 and ((abs(normal[1]) > abs(normal[0]) and newCorner[0] > min(corner_1[0], corner_2[0]) and newCorner[0] < max(corner_1[0], corner_2[0])) or (abs(normal[1]) < abs(normal[0]) and newCorner[1] > min(corner_1[1], corner_2[1]) and newCorner[1] < max(corner_1[1], corner_2[1]))):
                    #print(connection, corner_1, corner_2, newCorner, normal)
                    newCorner = newCorner + distance * normal
                    self.connections.append((connection[0], newCornerIndex))
                    self.connections.append((connection[1], newCornerIndex))
                    self.connections.remove(connection)
                    break
                continue

            self.corners.append(newCorner)
            pass
        if self.prevCornerIndex != -1 and self.prevCornerIndex != newCornerIndex:
            self.connections.append((self.prevCornerIndex, newCornerIndex))
            pass
        self.prevCornerIndex = newCornerIndex

        return

    def moveCorner(self, delta):
        if self.prevCornerIndex == -1:
            return
        self.corners[self.prevCornerIndex] += delta
        pass

    def finalize(self):
        self.prevCornerIndex = -1
        return

    def save(self):
        #scene_info = {'corners': self.corners, 'cornersOpp': self.cornersOpp, 'faces': self.faces, 'dominantNormals': self.dominantNormals}
        np.save(self.scenePath + '_annotation/corners.npy', np.array(self.corners))
        np.save(self.scenePath + '_annotation/connections.npy', np.array(self.connections))
        return

    
    def loadImage(self, imageIndex):
        imagePath = self.imagePaths[imageIndex % len(self.imagePaths)]
        #print(imagePath)
        with open(imagePath.replace('rgb/', 'pose/').replace('rgb.png', 'pose.json')) as f:
            pose = json.load(f)
            pass
        extrinsics = np.array(pose['camera_rt_matrix'])
        intrinsics = np.array(pose['camera_k_matrix'])

        image = cv2.imread(imagePath)
        imageSizes = np.array([image.shape[1], image.shape[0]])
        image = cv2.resize(image, (self.imageWidth, self.imageHeight))
        roomName = '_'.join(imagePath.split('/')[-1].split('_')[2:4])
        if roomName not in self.roomLabelDict:
            return None, []
        roomLabel = self.roomLabelDict[roomName]
        if roomLabel not in self.roomCorners:
            return None, []
        cornerIndices = self.roomCorners[roomLabel]
        corners2D = np.array([self.corners[cornerIndex] for cornerIndex in cornerIndices]).astype(np.float32)

        #print(corners2D)
        X = corners2D[:, 0] / self.box[4] * (self.box[1] - self.box[0]) + self.box[0]
        Y = -(corners2D[:, 1] / self.box[5] * (self.box[3] - self.box[2]) + self.box[2])
        cornerGT = []
        for cornerType, horizontalHeight in enumerate(self.box[6:8]):
            wallCorners3D = np.stack([X, Y, np.full(X.shape, horizontalHeight), np.ones(X.shape)], axis=-1)
            wallCorners3D = np.matmul(extrinsics, wallCorners3D.transpose()).transpose()
            wallCorners = np.matmul(intrinsics, wallCorners3D.transpose()).transpose()

            wallCorners = np.round(wallCorners[:, :2] / wallCorners[:, 2:3] / imageSizes * np.array([self.imageWidth, self.imageHeight])).astype(np.int32)
            cornerMask = np.logical_and(np.logical_and(wallCorners3D[:, 2] > 0, np.logical_and(np.logical_and(np.all(wallCorners >= 0, axis=-1), wallCorners[:, 0] < self.imageWidth), wallCorners[:, 1] < self.imageHeight)), wallCorners3D[:, 2] < 10)

            for index, wallCorner in enumerate(wallCorners):
                if not cornerMask[index]:
                    continue
                cornerGT.append(wallCorner.tolist() + [cornerType, cornerIndices[index], wallCorners3D[index, 2]])
                continue
            continue
        cornerGT = np.array(cornerGT)
        if True:
            cornerImage = image.copy()
            for index, wallCorner in enumerate(cornerGT):
                cv2.circle(cornerImage, (int(round(wallCorner[0])), int(round(wallCorner[1]))), 10, (0, 0, 255), -1)
                continue
            cv2.imwrite('test/corner.png', cornerImage)
            pass
        return image, cornerGT


    def loadImages(self):
        self.findRoomCorners()

        imagePaths = glob.glob(self.scenePath + '/data/rgb/*.png')
        self.imagePaths = sorted(imagePaths)
        self.trajectory = []
        return
        #centers = []
        for imageIndex, imagePath in enumerate(imagePaths):
            if imageIndex != 80:
                continue
            self.loadImage(imagePath)
            continue
        #centers = np.array(centers)
        return

    def load(self):
        self.loading = False
        return

    def removeLast(self):
        if self.prevCornerIndex == len(self.corners) - 1:
            self.corners = self.corners[:-1]
            self.connections = [connection for connection in self.connections if len(self.corners) not in connection]
            self.prevCornerIndex -= 1
        else:
            self.connections = self.connections[:-1]
            pass
        return
