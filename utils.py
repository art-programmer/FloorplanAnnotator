import numpy as np

class ColorPalette:
    def __init__(self, numColors):
        np.random.seed(1)

        self.colorMap = np.array([[255, 0, 0],
                                  [50, 150, 0],
                                  [0, 0, 255],
                                  [80, 128, 255],
                                  [255, 230, 180],
                                  [255, 0, 255],
                                  [0, 255, 255],
                                  [255, 255, 0],
                                  [0, 255, 0],
                                  [200, 255, 255],
                                  [255, 200, 255],
                                  [100, 0, 0],
                                  [0, 100, 0],
                                  [128, 128, 80],
                                  [0, 50, 128],
                                  [0, 100, 100],
                                  [0, 255, 128],
                                  [0, 128, 255],
                                  [255, 0, 128],
                                  [128, 0, 255],
                                  [255, 128, 0],
                                  [128, 255, 0],
        ], dtype=np.uint8)
        self.colorMap = np.concatenate([self.colorMap, self.colorMap], axis=0)

        #self.colorMap = np.maximum(self.colorMap, 1)

        if numColors > self.colorMap.shape[0]:
            self.colorMap = np.concatenate([self.colorMap, np.random.randint(255, size = (numColors, 3), dtype=np.uint8)], axis=0)
            pass

        return

    def getColorMap(self):
        return self.colorMap

    def getColor(self, index):
        if index >= colorMap.shape[0]:
            return np.random.randint(255, size = (3), dtype=np.uint8)
        else:
            return self.colorMap[index]
            pass

def intersectFaceLine(face, line, return_ratio=False):
    faceNormal = np.cross(face[1] - face[0], face[2] - face[0])
    faceArea = 0
    for c in xrange(1, len(face) - 1):
        faceArea += np.linalg.norm(np.cross(face[c] - face[0], face[c + 1] - face[c])) / 2
        pass
    faceNormal /= np.maximum(faceArea * 2, 1e-4)
    faceOffset = np.sum(faceNormal * face[0])
    offset_1 = np.sum(faceNormal * line[0])
    offset_2 = np.sum(faceNormal * line[1])
    if offset_2 == offset_1:
        if return_ratio:
            return False, 0
        else:
            return False

    alpha = (faceOffset - offset_1) / (offset_2 - offset_1)
    if alpha <= 0 or alpha >= 1:
        if return_ratio:
            return False, alpha
        else:
            return False

    point = line[0] + alpha * (line[1] - line[0])
    intersectionArea = 0
    for c in xrange(len(face)):
        intersectionArea += np.linalg.norm(np.cross(point - face[c], point - face[(c + 1) % len(face)])) / 2
        continue
    #print(intersectionArea, faceArea)
    if intersectionArea <= faceArea + 1e-4:
        if return_ratio:
            return True, alpha
        else:
            return True
    else:
        if return_ratio:
            return False, alpha
        else:
            return False
    return


if __name__ == '__main__':
    line = [np.array([ 2.4764291 ,  4.37349266, -9.5168555 ]), np.array([ 2.4764291 ,  4.37349266, 10.4831445 ])]
    face = [np.array([2.1361478 , 0.01942726, 0.06335368]), np.array([8.41647591, 2.27955277, 0.06335368]), np.array([6.15570054, 8.74293862, 0.06335368]), np.array([-0.12478519,  6.48326369,  0.06335368])]
    intersection, ratio = intersectFaceLine(face, line, return_ratio=True)
    print(face)
    print(line)
    print(intersection, ratio)
    exit(1)
