# -*- coding: utf-8 -*-
"""
Basic helper functions that can be used elsewhere.

@author: René Vollmer
"""

import os
import numpy as np


def ensure_file_ending(filename, ending) -> str:
    splits = filename.split('.')
    if len(splits) == 1 or splits[-1].lower() != ending:
        return filename + "." + ending
    return filename


def remove_file_ending(filename, ending) -> str:
    splits = filename.split('.')
    if len(splits) == 1:
       return filename
    elif splits[-1].lower() == ending:
        return filename[:-(len(ending) + 1)]
    return filename



def spiral(radius: float, step_size: float, alpha: float = 1,
           clockwise: bool = True, inside_out: bool = True):
    # From inside to outside

    # Helper variables
    a = alpha * step_size / (2. * np.pi)
    Tc = radius / a

    # Number of points
    K = int(0.5 * alpha / (2. * np.pi) * (Tc * (1 + Tc ** 2) ** 0.5 + np.log(Tc + (1 + Tc ** 2) ** 0.5)))

    x = np.empty(K)  # x coords
    y = np.empty(K)  # y coords
    theta = np.empty(K)

    # generate spiral, keeping the angular mesh
    k = 0
    t = 0
    while t < Tc:
        r = t if inside_out else (Tc - t)
        theta[k] = (-1 + (2 * clockwise)) * t
        x[k] = r * np.cos(theta[k])
        y[k] = r * np.sin(theta[k])

        t += 2 * np.pi / (alpha * (1.0 + t ** 2) ** 0.5)
        k += 1

    # rescale result
    x = x[:k] * a
    y = y[:k] * a
    theta = theta[:k] * a

    return x, y, theta


def circle(radius: float, step_size: float, alpha: float = 1):
    # Number of points
    K = round(2 * np.pi * radius / step_size)

    # generate a Circle
    ang = np.linspace(0, 2 * np.pi, K)
    x = radius * np.cos(ang)
    y = radius * np.sin(ang)

    return x, y


def square(width: float, height: float, step_size: float, start: int = 0, clockwise: bool = True):
    # start=0 -> top left corner
    # start=1 -> top right corner
    # start=2 -> bottom right corner
    # start=3 -> bottom left corner

    # print("w/h", width, height)
    Kw: int = int(width / step_size)
    Kh: int = int(height / step_size)
    assert Kw > 1, "Width smaller than two steps!"
    assert Kh > 1, "Height smaller than two steps!"
    # K = 2*(Kw+Kh)
    # print("steps", Kw, Kh)
    xs = []
    ys = []

    h = np.linspace(-width / 2, +width / 2, Kw)
    v = np.linspace(-height / 2, +height / 2, Kh)

    if Kw > Kh:
        h = h[1:-1]
        Kw -= 2
    else:
        v = v[1:-1]
        Kh -= 2

    xs.append(h)
    ys.append(np.ones(Kw) * (+height / 2))

    xs.append(np.ones(Kh) * (+width / 2))
    ys.append(np.flip(v))

    xs.append(np.flip(h))
    ys.append(np.ones(Kw) * (-height / 2))

    xs.append(np.ones(Kh) * (-width / 2))
    ys.append(v)

    x, y = [], []
    for i in range(4):
        x = np.append(x, xs[(i + start) % 4])
        y = np.append(y, ys[(i + start) % 4])

    assert len(x) == len(y), "Programming error!"

    if clockwise:
        return x, y
    else:
        return np.flip(x), np.flip(y)


def arange_sym(length, step):
    print(length, step)
    return np.linspace(-0.5, +0.5, int(length / step) + 1) * length


def ensure_folder_exists(path: str, give_warning: bool = True):
    if not os.path.exists(path):
        os.makedirs(path)
    elif give_warning:
        print("\n\n> Warning: overwriting previous files!\n\n")


def zip_folder(path: str):
    import zipfile

    with zipfile.ZipFile(path + '.zip', 'w', zipfile.ZIP_DEFLATED) as ziph:
        # ziph is zipfile handle
        for root, dirs, files in os.walk(path):
            for file in files:
                ziph.write(os.path.join(root, file))

