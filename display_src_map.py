import sys
import numpy as np
import cv2
from painterly import get_source_map_img, displayImg

if __name__ == "__main__":

    img_path = sys.argv[1]
    src_map_path = sys.argv[2]

    # load img
    img = cv2.imread(img_path, cv2.IMREAD_COLOR)[:,:,::-1]
    
    # load src map
    f = np.load(src_map_path)
    srcU = f['source_U']
    srcV = f['source_V']

    assert(img.shape[:-1] == srcU.shape == srcV.shape)

    # get mapped img
    src_map_img = get_source_map_img(img, srcU, srcV)
    displayImg(src_map_img)