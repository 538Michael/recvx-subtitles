# Third-party notices

The released programs `make-ps3-font.exe` and `make-ps3-font` (Linux) are built with
[PyInstaller](https://pyinstaller.org/) and contain, besides `make_ps3_font.py` (MIT, see
`LICENSE`), these components under their own licences:

| Component | Licence |
|---|---|
| [Python](https://www.python.org/) | [Python Software Foundation License](https://docs.python.org/3/license.html) |
| [NumPy](https://numpy.org/) (with OpenBLAS; on Linux also libgfortran and libquadmath) | [BSD-3-Clause](https://github.com/numpy/numpy/blob/main/LICENSE.txt) (OpenBLAS: BSD-3-Clause; libgfortran: GPL-3.0 with the GCC Runtime Library Exception; libquadmath: LGPL-2.1) |
| [Pillow](https://python-pillow.org/) (with libjpeg-turbo, libpng, zlib, FreeType and others) | [MIT-CMU](https://github.com/python-pillow/Pillow/blob/main/LICENSE) (bundled libraries: their own licences, listed there) |
| [fontTools](https://github.com/fonttools/fonttools) | [MIT](https://github.com/fonttools/fonttools/blob/main/LICENSE) |
| [Tcl/Tk](https://www.tcl.tk/) (the window, through tkinter) | [Tcl/Tk License](https://www.tcl.tk/software/tcltk/license.html) (BSD-style) |
| PyInstaller bootloader | [GPL-2.0 with the bootloader exception](https://github.com/pyinstaller/pyinstaller/blob/develop/COPYING.txt), which allows bundling programs under any licence |

The fonts in `mods/subtitles/fonts/` are subsets of [Noto Sans CJK](https://github.com/notofonts/noto-cjk)
under the SIL Open Font License 1.1 (`mods/subtitles/fonts/OFL.txt`).

Resident Evil and Code: Veronica are trademarks of Capcom. This project is not affiliated with or
endorsed by Capcom, Sony or the recvx-enhanced-port project.
