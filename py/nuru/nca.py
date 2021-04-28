# All credits (Apache 2.0) to
# https://github.com/google-research/self-organising-systems

import base64
import io
import requests

import numpy as np
import PIL.Image


def imread(url, max_size=None, mode=None):
  if isinstance(url, str):
    if url.startswith(('http:', 'https:')):
      r = requests.get(url)
      f = io.BytesIO(r.content)
    else:
      f = GFile(url, mode='rb')
  else:
    f = url
  img = PIL.Image.open(f)
  if max_size is not None:
    img.thumbnail((max_size, max_size), PIL.Image.ANTIALIAS)
  if mode is not None:
    img = img.convert(mode)
  img = np.float32(img)/255.0
  return img


def np2pil(a):
  if a.dtype in [np.float32, np.float64]:
    a = np.uint8(np.clip(a, 0, 1)*255)
  return PIL.Image.fromarray(a)


def imwrite(f, a, fmt=None):
  a = np.asarray(a)
  if isinstance(f, str):
    fmt = f.rsplit('.', 1)[-1].lower()
    if fmt == 'jpg':
      fmt = 'jpeg'
    f = GFile(f, mode='wb')
  np2pil(a).save(f, fmt, quality=95)


def imencode(a, fmt='jpeg'):
  a = np.asarray(a)
  if len(a.shape) == 3 and a.shape[-1] == 4:
    fmt = 'png'
  f = io.BytesIO()
  imwrite(f, a, fmt)
  return f.getvalue()


def im2url(a, fmt='jpeg'):
  encoded = imencode(a, fmt)
  base64_byte_string = base64.b64encode(encoded).decode('ascii')
  return 'data:image/' + fmt.upper() + ';base64,' + base64_byte_string


def tile2d(a, w=None):
  a = np.asarray(a)
  if w is None:
    w = int(np.ceil(np.sqrt(len(a))))
  th, tw = a.shape[1:3]
  pad = (w-len(a))%w
  a = np.pad(a, [(0, pad)]+[(0, 0)]*(a.ndim-1), 'constant')
  h = len(a)//w
  a = a.reshape([h, w]+list(a.shape[1:]))
  a = np.rollaxis(a, 2, 1).reshape([th*h, tw*w]+list(a.shape[4:]))
  return a


def export_models_to_js(models, fixed_filter_n=4):
  '''Exoprt numpy models in a form that ca.js can read.'''
  model_names = list(models.keys())
  models_js = {'model_names':model_names, 'layers': []}
  params = models.values()
  quant_scale_zero = [(2.0, 0.0), (4.0, 127.0 / 255.0)]
  for i, layer in enumerate(zip(*params)):
    shape = layer[0].shape
    layer = np.array(layer)  # shape: [n, h, w]
    if i == 0:
      # Replaced with np equiv. for time being so this works internally.
      # layer[:,:-1] = rearrange(layer[:,:-1], 'n (h c) w -> n (c h) w', c=fixed_filter_n)
      s = layer[:, :-1].shape
      layer[:, :-1] = (layer[:, :-1]
                       .reshape(s[0], -1, fixed_filter_n, s[2])
                       .transpose(0, 2, 1, 3)
                       .reshape(s))
    #layer = rearrange(layer, 'n h (w c) -> h (n w) c', c=4)
    # N.B. this 4 is not the fixed filter number, but a webgl implementation detail.
    # Pad when number of channels is not a multiple of 4.
    s = layer.shape
    layer = np.pad(layer, ((0,0), (0,0), (0, (4 - s[2]) % 4)), mode='constant')
    layer = layer.reshape(s[0], s[1], -1, 4)
    n, ht, wt = layer.shape[:3]
    w = 1
    while w<n and w*wt < (n+w-1)//w*ht:
      w += 1
    layer = tile2d(layer, w)
    layout = (w, (n+w-1)//w)

    scale = 2.0*np.abs(layer).max()
    layer = np.round(layer/scale*255.0+127.0)
    layer = np.uint8(layer.clip(0, 255))

    url = im2url(layer, 'png')
    layer_js = {'scale': scale,
                'data': url,
                'shape':shape,
                'quant_scale_zero': quant_scale_zero[i],
                'layout': layout}
    models_js['layers'].append(layer_js)
  return models_js