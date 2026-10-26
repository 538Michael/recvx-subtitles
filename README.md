# recvx-subtitles

Subtitles for [recvx-enhanced-port](https://github.com/aikatore/recvx-enhanced-port), the PC port of
*Resident Evil Code: Veronica X*: the pre-rendered movies and the dialogue of the real-time
cutscenes, in 13 languages.

> **Resident Evil and its dialogue © Capcom.** Unofficial fan project, not affiliated with or
> endorsed by Capcom. You need your own copy of the game. Will be removed on request.

## What's included

- Subtitles for the movies and the cutscene dialogue, with the speaker of each line (shown as
  "Claire: …" if you turn on *Speaker names*).
- **Languages:** English, Portuguese (Brazil), French, Italian, German, Spanish (Spain), Spanish
  (Latin America), Polish, Russian, Japanese, Korean, Simplified Chinese, Traditional Chinese.
- Fonts with the Japanese, Korean and Chinese letters the subtitles use.
- **Optional:** [`make-ps3-font`](#optional-the-ps3-version-s-hd-lettering), a small program that
  gives the subtitles the HD lettering of the PS3 version, made from your own PS3 copy.

## Requirements

- **recvx-enhanced-port with subtitle support.** The official port has none; use the build
  [recvx-enhanced-port 0.8.0](https://github.com/538Michael/recvx-enhanced-port/releases/tag/v0.8.0)
  (0.6.10 plus subtitles and game languages; a Brazilian Portuguese pack for the game itself is at
  [recvx-ptbr](https://github.com/538Michael/recvx-ptbr)).
- Your own US PS2 disc image (SLUS-20184), as the port always needs.

## Install

1. Download `recvx-subtitles-1.0.0.zip` from the [releases](https://github.com/538Michael/recvx-subtitles/releases).
2. Extract it into the port's folder (the one with `recvx.exe`). It creates `mods/subtitles/`.
3. Start the game. In **Settings > DISPLAY** (F1 or OPTION > ENHANCED SETTINGS):
   - **Subtitles**: On
   - **Subtitle language**: your language
   - **Speaker names** / **Speaker name colors**: the speaker before each line, in colour
   - **Subtitle size**: Small, Medium or Large
   - **Subtitle font**: *Game* (the game's own lettering) or *Modern* (a system font)

With *Subtitle font: Game* the port makes the game's lettering itself, from your disc.

## Optional: the PS3 version's HD lettering

If you own *Resident Evil Code: Veronica X HD* for PlayStation 3, `make-ps3-font` makes the subtitle
font from its sharper, HD-redrawn lettering. It reads your own copy; nothing of the game is included.

1. Install your PS3 copy in the [RPCS3](https://rpcs3.net/) emulator: **File > Install
   Packages/Raps/Edats**, then choose your game's `.pkg` (and its `.rap` licence). The tool can't read
   the `.pkg` or a disc image directly, because they are encrypted.
2. Download `make-ps3-font.exe` (Windows) or `make-ps3-font-linux-x86_64.tar.gz` (Linux) from the
   releases and put it in the port's folder, next to `recvx.exe`.
3. **Drag your RPCS3 folder onto `make-ps3-font.exe`.** Or open it, choose the folder, and click
   **Make font**. You can also give it the installed game (`dev_hdd0/game/NPUB30467`) or the file
   `syseff.arc`.

It writes `mods/subtitles/fonts/cvx.otf` (an older one is kept as `cvx.otf.bak`), and the game uses
it with *Subtitle font: Game*. The font is made from the game, so keep it for yourself.

- **Windows** may warn about an unknown program (SmartScreen: *More info > Run anyway*), as the
  program isn't signed. The source is [here](ps3-font/make_ps3_font.py) if you'd rather run it with
  Python (`pip install -r ps3-font/requirements.txt`, then `python ps3-font/make_ps3_font.py`).
- **Linux**: extract it and make it executable (`chmod +x make-ps3-font`). Whether you can drop a
  folder onto a program depends on your file manager; otherwise open it and choose the folder.
- **Command line**: `make-ps3-font PATH [--game RECVX_FOLDER] [--out FILE] [--cli]`.

## Licences

- **`ps3-font/`** (the program and its build scripts): MIT, see [LICENSE](LICENSE). The released
  programs also contain Python and libraries under their own licences, see
  [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
- **Fonts** in `mods/subtitles/fonts/`: subsets of Noto Sans CJK, SIL Open Font License 1.1, see
  [OFL.txt](mods/subtitles/fonts/OFL.txt).
- **Subtitle files** (`.srt`, `.json`): not covered by these licences; the dialogue belongs to Capcom.
