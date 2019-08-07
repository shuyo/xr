#!/usr/bin/env python
# -*- coding: utf-8 -*-

# 3D Model Generation from Wide Aperture Photo
# This code is available under the MIT License.
# (c)2019 Nakatani Shuyo / Cybozu Labs Inc.

import os, sys, io, numpy, random
from PIL import Image
from scipy.interpolate import RegularGridInterpolator
from scipy.ndimage.filters import gaussian_filter
from scipy import signal

import argparse
parser = argparse.ArgumentParser(description='3D Model Generation from Wide Aperture Photo')
parser.add_argument('--dir', default="model", help="output directory")
parser.add_argument('--mesh', type=int, default=400, help="mesh size of output model")
parser.add_argument('--range', type=float, default=5)
parser.add_argument('--nconv', type=int, default=10, help="number of convolutions")
parser.add_argument('--gfliter', action='store_true', help='use gaussian filter')
parser.add_argument('input', help='input file path')
args = parser.parse_args()

if not os.path.exists(args.dir): os.mkdir(args.dir)

MTL = """
newmtl None
Ns 0.000000
Ka 0.000000 0.000000 0.000000
Kd 0.800000 0.800000 0.800000
Ks 0.468293 0.468293 0.468293
Ke 0.800000 0.800000 0.800000
Ni 1.000000
d 1.000000
illum 2
map_Kd %s
"""

def extract_edof(data):
    if data[:3] != b'\xff\xd8\xff': raise "not JPEG"
    idx = data.find(b"\x00edof\x00")
    if idx <= 0: raise "no EDOF"

    orientation = data[idx + 12]
    columns = int.from_bytes(data[idx + 21: idx + 23], 'little')
    rows = int.from_bytes(data[idx + 23: idx + 25], 'little')

    img = Image.frombuffer('L', (columns, rows), data[idx+73:], 'raw', 'L', 0, 0)
    buf = numpy.frombuffer(data[idx+73:], 'uint8', columns * rows).reshape(rows, columns)[::-1,:]
    if orientation == 0x10:
        img = img.transpose(Image.ROTATE_180)
        buf = numpy.rot90(buf,2)
    elif orientation == 0x11:
        img = img.transpose(Image.ROTATE_90)
        buf = numpy.rot90(buf)
    elif orientation == 0x13:
        img = img.transpose(Image.ROTATE_270)
        buf = numpy.rot90(buf,-1)
    return buf #numpy.asarray(img)

def extract_texture(data, im_width):
    i = 0
    while True:
        i = data.find(b"\xff\xd8", i+1)
        if i < 0: return Image.open(data)
        try:
            im = Image.open(io.BytesIO(data[i:]))
            if im.width == im_width: return im
        except:
            pass
    raise "No images match."

if __name__ == "__main__":
    root, ext = os.path.splitext(os.path.basename(args.input))
    opath = lambda e, dir=args.dir: os.path.join(dir, root + e)

    with open(args.input, "rb") as fin:
        data = fin.read()
        im = Image.open(fin)
    w, h = im.size

    edof = extract_edof(data)
    ey, ex = edof.shape
    #print(edof.shape, edof.max(), edof.min(), edof.mean(), edof[0,0])

    # texture
    tim = extract_texture(data, w).resize((2048, 2048))
    tim.save(opath(".jpg"), quality=90, optimize=True)

    edof2 = numpy.array(edof, dtype=float)
    if args.gfliter:
        edof2 = gaussian_filter(edof2, [8,8])
    else: # blur
        #mask = numpy.ones((3,3))/9
        mask = numpy.array([[1,2,3,2,1], [2,4,6,4,2], [3,6,9,6,3], [2,4,6,4,2], [1,2,3,2,1]])/81.
        for k in range(args.nconv):
            edof2 = signal.convolve2d(edof2, mask, "same", "wrap")
            edof2 = numpy.clip(edof2, edof-args.range, edof+args.range)

    yy = numpy.linspace(0,1,ey)
    xx = numpy.linspace(0,1,ex)
    interpolate = RegularGridInterpolator((yy, xx), edof2)

    xlim = max(w/h, 1)
    ylim = max(h/w, 1)

    vx = args.mesh # x 方向の頂点数-1
    vy = args.mesh - (args.mesh % 2) # y 方向の頂点数-1, 偶数

    vlist = [] # 頂点リスト ([-xlim,xlim], [-ylim,ylim], [-∞,0]) 左下原点
    tlist = [] # テクスチャ頂点リスト ([0,1], [0,1]) 左下原点
    for j in range(vy+1):
        odd = j % 2
        y = ylim - 2*j*ylim/vy
        ty = 1 - j/vy
        for i in range(vx+1-odd):
            x = (2*i+odd)*xlim/vx-xlim
            tx = (i+odd/2)/vx
            d = interpolate([1-ty,1-tx])[0]
            r = 1 + d / 128.
            vlist.append((x*r, y*r, -d/24.))
            tlist.append((tx, ty))

    with open(opath(".mtl"), "w") as f:
        f.write(MTL % opath(".jpg", "."))

    with open(opath(".obj"), "w") as f:
        f.write("mtllib %s\n" % opath(".mtl", "."))
        f.write("o Object.001\n")
        for v in vlist:
            f.write("v %s\n" % " ".join("%.5f" % x for x in v))
        for t in tlist:
            f.write("vt %s\n" % " ".join("%.5f" % x for x in t))
        f.write("usemtl None\n")
        f.write("s off\n")

        fout = lambda x, y, z: f.write("f %d/%d %d/%d %d/%d\n" % (x,x,y,y,z,z))
        odd_top = 1
        for j in range(vy//2):
            even_top = odd_top + vx + 1
            for i in range(vx):
                fout(odd_top+i, odd_top+i+1, even_top+i)
                if i>0: fout(even_top+i-1, even_top+i, odd_top+i)
            fout(odd_top, even_top, even_top + vx)
            fout(even_top-1, even_top + vx-1, even_top + vx * 2)
            odd_top = even_top + vx
            for i in range(vx):
                fout(odd_top+i, odd_top+i+1, even_top+i)
                if i>0: fout(even_top+i-1, even_top+i, odd_top+i)

