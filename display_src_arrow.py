import sys
import numpy as np
import cv2
from painterly import get_source_map_img, displayImg

ARROW_COLOR = (255, 0, 0)
ARROW_WIDTH = 1
ARROW_HEAD_LEN = 0.05
show_empty = True
EMPTY_COLOR = (0, 0, 255)
EMPTY_RAD = 2

if __name__ == "__main__":

    img_path = sys.argv[1]
    src_map_path = sys.argv[2]
    grid = int(sys.argv[3])
    output_path = sys.argv[4]

    # load img
    img = cv2.imread(img_path, cv2.IMREAD_COLOR)[:,:,::-1]
    
    # load src map
    f = np.load(src_map_path)
    srcU = f['source_U']
    srcV = f['source_V']

    assert(img.shape[:-1] == srcU.shape == srcV.shape)
    # canvas = get_source_map_img(img, srcU, srcV)
    canvas = img
    canvas = np.array(canvas)

    # add arrows
    height, width, _ = canvas.shape

    for v in range(0, width, grid):
        for u in range(0, height, grid):
            src_u = srcU[u,v]
            src_v = srcV[u,v]
            if src_u == img.shape[0] or src_v == img.shape[1]: # check if empty
                if show_empty:
                    cv2.circle(canvas, (v, u), EMPTY_RAD, EMPTY_COLOR, -1)
                continue
            cv2.arrowedLine(canvas, (src_v, src_u), (v, u), ARROW_COLOR, ARROW_WIDTH, line_type=cv2.LINE_AA, tipLength=ARROW_HEAD_LEN)

    # display
    displayImg(canvas)

    # save
    cv2.imwrite(output_path, canvas[:,:,::-1])
