import cv2
import numpy as np

MAX_ITERATIONS = 100
EMPTY_COLOR = (255, 255, 255)

def add_hsv_jitter(image, hue_jitter, sat_jitter, val_jitter):

    # get HSV
    hsv_image = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)
    height, width, _ = hsv_image.shape

    # get random value
    hue_diff = np.random.randint(-hue_jitter, hue_jitter+1, size=(height, width), dtype=np.int)
    sat_diff = np.random.randint(-sat_jitter, sat_jitter+1, size=(height, width), dtype=np.int)
    val_diff = np.random.randint(-val_jitter, val_jitter+1, size=(height, width), dtype=np.int)

    # clip
    hsv_image[:,:,0] = (hsv_image[:,:,0] + hue_diff) % 180
    hsv_image[:,:,1] = np.clip(hsv_image[:,:,1] + sat_diff, 0, 255)
    hsv_image[:,:,2] = np.clip(hsv_image[:,:,2] + val_diff, 0, 255)

    # get RGB
    jittered_image = cv2.cvtColor(hsv_image, cv2.COLOR_HSV2RGB)

    return jittered_image

def normal_x(x, width):
    return (int)(x * (width - 1) + 0.5)
def normal_y(y, height):
    return (int)(y * (height - 1) + 0.5)

def draw(f, width=128, height=128):
    """ Draw a stroke onto a blank canvas
    Parameters
    ----------
    f : []
        Definition of bezier curve: x0, y0, x1, y1, x2, y2, width_start, width_end, opacity_start, opacity_end
    width : int, optional
        Width of canvas. (Default 128)
    height : int, optional
        Height of canvas. (Default 128)

    Returns
    -------
    np.array[height, width]
        matrix (boolean map) with the stroke drawn on it.
    """
    x0, y0, x1, y1, x2, y2, z0, z2, w0, w2 = f

    frac = 1. / MAX_ITERATIONS

    x1 = x0 + (x2 - x0) * x1
    y1 = y0 + (y2 - y0) * y1
    x0 = normal_x(x0, width * 2)
    x1 = normal_x(x1, width * 2)
    x2 = normal_x(x2, width * 2)
    y0 = normal_y(y0, height * 2)
    y1 = normal_y(y1, height * 2)
    y2 = normal_y(y2, height * 2)
    z0 = (int)(1 + z0 * width // 2)
    z2 = (int)(1 + z2 * width // 2)
    canvas = np.zeros([height * 2, width * 2]).astype('float32')

    for i in range(MAX_ITERATIONS):
        t = i * frac
        x = (int)((1-t) * (1-t) * x0 + 2 * t * (1-t) * x1 + t * t * x2)
        y = (int)((1-t) * (1-t) * y0 + 2 * t * (1-t) * y1 + t * t * y2)
        z = (int)((1-t) * z0 + t * z2)
        w = (1-t) * w0 + t * w2
        cv2.circle(canvas, (x, y), z, w, -1)
    return 1 - cv2.resize(canvas, dsize=(width, height))

def draw_spline_stroke(K, r, width=128, height=128):
    """
    Paint a stroke defined by a list of points onto a canvas

    args:
        K (List[Tup(int, int)]) : a nested list of points to draw. [(x_pixel, y_pixel),...]
        r (int) : radius in pixels of stroke

    kwargs:
        width (int) :  Width of canvas. (Default 128)
        height (int) :  Height of canvas. (Default 128)

    return:
        np.array[height, width] : matrix (boolean map) with the stroke drawn on it.
    """
    canvas = np.zeros([height, width]).astype('float32')

    for f in K:
        x = f[0]
        y = f[1]
        z = r
        w = 1.
        cv2.circle(canvas, (x, y), z, w, -1)
        
    return 1 - cv2.resize(canvas, dsize=(width, height))

def make_stroke(r, x0, x1, y0, y1, width, height):
    """
    Draw a straight line on a canvas

    args:
        r (int) : radius in pixels of stroke
        x0 (int) : starting x pixel
        x1 (int) : ending x pixel
        y0 (int) : starting y pixel
        y1 (int) : ending y pixel
        width (int) :  Width of canvas. (Default 128)
        height (int) :  Height of canvas. (Default 128)

    return:
        np.array[height, width] : matrix (boolean map) with the stroke drawn on it.
    """
    # f is (x0, y0, x1, y1, x2, y2, width_start, width_end, opacity_start, opacity_end)
    f = (x0, y0, (x1-x0)/2 + x0, (y1-y0)/2 + y0, x1, y1, r, r, 1., 1.)

    return draw(f, width=width, height=height)

# cache gradients
gradient, grad_x, grad_y = None, None, None

def make_spline_stroke(x0, y0, R, ref_image, canvas, max_stroke_length=None, min_stroke_length=None, fc=1):
    """
    Draw a curved line on a canvas from a starting point based on gradients

    args:
        x0 (int) : Starting x pixel
        x1 (int) : Ending x pixel
        R (int) : Radius in pixels of stroke
        ref_image (np.array[height, width, 3]) :  Reference image 0-255 RGB
        canvas (np.array[height, width, 3]) :  Current painting canvas 0-1 RGB

    kwargs:
        max_stroke_length (int) : Maximum length of a stroke in pixels.
        fc (float) : Curvature filter - used to limit or exaggerate stroke curvature. Default 1

    return:
        np.array[height, width] : Matrix (boolean map) with the stroke drawn on it.
    """
    stroke_color = ref_image[y0,x0,:]
    K = [(x0,y0)]

    x, y = x0, y0
    last_dx, last_dy = 0, 0

    global gradient, grad_x, grad_y
    if gradient is None:
        ref_image_gray = cv2.cvtColor(ref_image, cv2.COLOR_RGB2GRAY)
        ksize = min(R+1 if R%2 == 0 else R, 31)
        gradient = cv2.Laplacian(ref_image_gray,cv2.CV_64F, ksize=ksize)
        grad_x, grad_y = cv2.Sobel(ref_image_gray,cv2.CV_64F,1,0,ksize=ksize), cv2.Sobel(ref_image_gray,cv2.CV_64F,0,1,ksize=ksize)

        # Normalize Gradient
        gradient = (gradient - np.mean(gradient)) / np.std(gradient)
        grad_x = (grad_x - np.mean(grad_x)) / np.std(grad_x)
        grad_y = (grad_y - np.mean(grad_y)) / np.std(grad_y)

    # default max stroke length is 1/3rd of canvas width
    max_stroke_length = max_stroke_length if max_stroke_length is not None else int(ref_image.shape[1] * 0.1)
    min_stroke_length = min_stroke_length if min_stroke_length is not None else int(ref_image.shape[1] * 0.02)

    height, width, _ = ref_image.shape

    for i in range(1, max_stroke_length):
        x = max(min(x, ref_image.shape[1]-1), 0)
        y = max(min(y, ref_image.shape[0]-1), 0)

        if (i > min_stroke_length) and \
                (np.sum(np.abs(ref_image[y,x,:] - canvas[y,x,:]*255.)) < np.sum(np.abs(ref_image[y,x,:] - stroke_color))):
            break

        # detect vanishing gradient
        grad = np.sum(gradient[y,x])
        if np.abs(grad) < 1e-4:
            break

        # get unit vector of gradient
        gx, gy = np.sum(grad_x[y,x]),  np.sum(grad_y[y,x])

        # compute a normal direction
        dx, dy = -1.*gy, gx

        # if necessary, reverse direction
        if (last_dx * dx + last_dy * dy) < 0:
            dx, dy = -dx, -dy

        # filter the stroke direction
        dx, dy = fc*dx + (1-fc)*last_dx, fc*dy + (1-fc)*last_dy

        if (dx**2 + dy**2) != 0:
            dx, dy = dx / (dx**2 + dy**2)**(.5), dy / (dx**2 + dy**2)**(.5)
        else:
            break
        x, y = int(x + R*dx), int(y + R*dy)
        last_dx, last_dy = dx, dy

        K.append((x,y))

    return draw_spline_stroke(K, R, width=width, height=height)

def apply_stroke(canvas, stroke, color):
    """
    Apply a given stroke to the canvas with a given color

    args:
        canvas (np.array[height, width, 3]) : Current painting canvas 0-1 RGB
        stroke (np.array[height, width]) :  Stroke boolean map
        color (np.array[3]) : RGB color to use for the brush stroke

    return:
        np.array[height, width, 3] : Painting with additional stroke in 0-1 RGB format
    """
    s_expanded = np.tile(stroke[:,:, np.newaxis], (1,1,3))
    s_color = s_expanded * color[None, None, :]

    return canvas * (1 - s_expanded) + s_color

def set_stroke_source(sourceU, sourceV, stroke, ptX, ptY):

    X,Y = np.where(stroke == 1.0)
    sourceU[X,Y] = ptX
    sourceV[X,Y] = ptY

    return sourceU, sourceV

def paint_layer(canvas, reference_image, r, f_g, T, curved, f_c, max_str_len=None, min_str_len=None, src_U=None, src_V=None):
    """
    Go through the pixels and paint a layer of strokes with a given radius

    args:
        canvas (np.array[height, width, 3]) : Current painting canvas 0-1 RGB
        reference_image (np.array[height, width, 3]) :  Reference image 0-255 RGB
        r (int) : Brush radius to use
        f_g (float) : Grid size - controls spacing of brush strokes
        T (int) : Approximation threshold - how close the painting should be to target
                  In terms of pixel values.
        curved (bool) : Whether to use curved or straight brush strokes

    return:
        np.array[height, width, 3] : Painting in 0-1 RGB format
    """
    S = []

    # create a pointwise difference image
    D = np.sum(np.abs(canvas*255. - reference_image), axis=2)
    grid = int(f_g * r)

    height, width, _ = canvas.shape

    for x in range(0, width, grid):
        for y in range(0, height, grid):
            print('Radius = %.2f, (x,y) = (%d, %d)' % (r, x, y))
            # avg the error near (x,y)
            D = np.mean(np.abs(canvas*255. - reference_image), axis=2)
            region = D[max(y-grid//2, 0):y+grid//2, max(x-grid//2, 0):x+grid//2]
            areaError = np.mean(region) #np.sum(region) / (region.shape[0] * region.shape[1])

            if areaError > T:
                if curved:
                    s = 1 - make_spline_stroke(x, y, r, reference_image, canvas, fc=f_c, max_stroke_length=max_str_len, min_stroke_length=min_str_len)
                else:
                    noise = np.random.rand(region.shape[0], region.shape[1])*0.0001
                    y1, x1 = np.unravel_index((region + noise).argmax(), region.shape)
                    x1 += max(x - grid//2, 0)
                    y1 += max(y - grid//2, 0)
                    s = 1 - make_stroke(r/width*2, x/width, x1/width, y/height, y1/height, width, height)
                color = reference_image[y,x,:] / 255.

                canvas = apply_stroke(canvas, s, color)

                src_U, src_V = set_stroke_source(src_U, src_V, s, y, x)
        # break
    return canvas, src_U, src_V

def paint(source_image, R, T=100, curved=True, f_s=0, f_g=1, f_c=1, max_str_len=None, min_str_len=None):
    """
    Paint a given image

    args:
        source_image (np.array[height, width, 3]) : Target image 0-255 RGB
        R (list(int)) : List of brush radii to use
    kwargs:
        T (int) : Approximation threshold - how close the painting should be to target
                  Default 100. In terms of pixel values.
        curved (bool) : Whether to use curved or straight brush strokes
        f_g (float) : Grid size - controls spacing of brush strokes

    return:
        np.array[height, width, 3] : Painting in 0-1 RGB format
    """
    global gradient, grad_x, grad_y
    canvas = np.ones(source_image.shape)

    # Source pixel (U,V)
    sourceU = source_image.shape[0] * np.ones(source_image.shape[:-1]).astype('int')
    sourceV = source_image.shape[1] * np.ones(source_image.shape[:-1]).astype('int')

    # paint the canvas
    for r in sorted(R, reverse=True): # largest to smallest
        # apply Gaussian blur
        sigma = f_s * r # std. dev. of Gaussian
        reference_image = cv2.GaussianBlur(source_image, (r,r) if r%2 == 1 else (r+1, r+1), sigma)
        # reset gradiant cache
        gradient, grad_x, grad_y = None, None, None
        # paint a layer
        canvas, sourceU, sourceV = paint_layer(canvas, reference_image, r, T=T, curved=curved, f_g=f_g, f_c=f_c, max_str_len=max_str_len, min_str_len=min_str_len, src_U=sourceU, src_V=sourceV)

    return canvas, sourceU, sourceV

def resize_img(img, max_size=300):
    h, w, _ = img.shape
    if w > max_size and w > h:
        img = cv2.resize(img, (int((max_size/w) * h), max_size))
    elif h > max_size and h >= w:
        img = cv2.resize(img, (max_size, int((max_size/h) * w)))
    return img, w, h

def convertGray2RGB(grayscale_img):
    rgb_img = np.stack([grayscale_img] * 3, axis=-1)
    return rgb_img

def displayImg(img, windowName = 'Image'):
    img = img[:,:,::-1]
    cv2.imshow(windowName, img)
    cv2.waitKey(0)
    cv2.destroyWindow(windowName)

debug = False

def get_source_map_img(img, src_X, src_Y):

    # get empty cells
    empty_u,empty_v = np.where(src_X == img.shape[0])
    empty_u_2,empty_v_2 = np.where(src_Y == img.shape[1])
    assert(np.all(empty_u == empty_u_2) and np.all(empty_v == empty_v_2))

    # at empty cells, replace source as (0,0)
    src_X[empty_u,empty_v] = 0
    src_Y[empty_u,empty_v] = 0
    mapping = img[src_X, src_Y, :]

    # at empty cells, replace painting color with empty color
    mapping[empty_u,empty_v,:] = EMPTY_COLOR

    mapping = mapping / 255.0 # to float

    return mapping

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Paint an image')

    parser.add_argument('img', type=str, help='path to an image to paint')

    parser.add_argument('--r', nargs='+', type=int, default=[8,4,2], help='radii to use for brushes. Usage --r 8 4 2')
    parser.add_argument('--output', type=str, default='./output.jpg', help='output file name and path')
    parser.add_argument('--T', type=float, default=20., help='Approximation threshold - how close the painting should be to target')
    parser.add_argument('--straight', action='store_true', default=False, help='Use straight brush strokes. Default False=curved strokes.')
    parser.add_argument('--f_g', type=float, default=1., help='Grid size - controls spacing of brush strokes')
    parser.add_argument('--debug', action='store_true', default=False, help='Output information important for debugging.')
    parser.add_argument('--f_s', type=float, default=0., help='Std. Dev. of Gaussian kernel')
    parser.add_argument('--f_c', type=float, default=1., help='Curvature filter - to limit/exaggerate stroke curvature')
    parser.add_argument('--maxLength', type=int, default=None, help='Max. stroke length')
    parser.add_argument('--minLength', type=int, default=None, help='Min. stroke length')
    parser.add_argument('--j_h', type=float, default=0., help='Hue jitter')
    parser.add_argument('--j_s', type=float, default=0., help='Saturation jitter')
    parser.add_argument('--j_v', type=float, default=0., help='Value jitter')
    parser.add_argument('--source_map', type=str, default='./source_map.npz', help='Numpy file name and path to store source mapping')

    args = parser.parse_args()

    debug = args.debug

    img = cv2.imread(args.img, cv2.IMREAD_COLOR)[:,:,::-1]
    # img, original_width, original_height = resize_img(img)

    if args.j_h or args.j_s or args.j_v:
        hue_jitter = int(args.j_h*180)
        saturation_jitter = int(args.j_s*256)
        value_jitter = int(args.j_v*256)
        img = add_hsv_jitter(img, hue_jitter, saturation_jitter, value_jitter)
        displayImg(img)

    painting, srcU, srcV = paint(img, args.r, T=args.T, curved=(not args.straight), f_g=args.f_g, f_s=args.f_s, f_c=args.f_c, max_str_len=args.maxLength, min_str_len=args.minLength)
    painting = painting * 255.

    # painting = cv2.resize(painting, (original_width, original_height))
    cv2.imwrite(args.output, painting[:,:,::-1])

    # save srcXY mapping
    np.savez(args.source_map, source_U=srcU, source_V=srcV)

    # # display reconstructed painting from mapping
    # src_map_img = get_source_map_img(img, srcU, srcV)
    # displayImg(src_map_img)
