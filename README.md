# 🎨 Color Highlight

[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.me/Kronuz/25)
[![Package Control](https://img.shields.io/packagecontrol/dt/Color%20Highlight.svg)](https://packagecontrol.io/packages/Color%20Highlight)

Show color codes (like "#ffffff", 0xffffff "rgb(255, 255, 255)", "white",
hsl(0, 0%, 100%), etc.) with their real color as the background and/or gutter icons.

![Description](screenshots/screenshot.gif?raw=true)

## Installation

- **_Recommended_** - Using [Sublime Package Control](https://packagecontrol.io "Sublime Package Control")
    - <kbd>Ctrl</kbd>+<kbd>Shift</kbd>+<kbd>P</kbd> then select `Package Control: Install Package`
    - install `Color Highlight`
- Alternatively, download the package from [GitHub](https://github.com/Kronuz/ColorHighlight "Color Highlight") into your `Packages` folder and make sure to rename the directory to "Color Highlight".


## Usage

Supported color representations are:

- Named colors in the form of CSS3 color names
  e.g. `green`, `black` and many others are also supported.

- Hexademical in the form of `#RGB`, `#RGBA`, `#RRGGBB` or `#RRGGBBAA`
  (you can use both upper and lower case letters)

- Hexadecimal numbers with prefix 0x in the form of `0xRRGGBB` or `0xRRGGBBAA`

- RBG or RGBA value in the form of `rgb(red, green, blue)` or `rgba(red, green, blue, alpha)`
  with decimal channel values

- HSL or HSLA value in the form of `hsl(hue, sat%, lum%)` or `hsla(hue, sat%, lum%, alpha)`

- HSV or HSVA value in the form of `hsv(hue, sat%, val%)` or `hsva(hue, sat%, val%, alpha)`

- HWB value in the form of `hwb(hue, white%, black%)` or `hwb(hue, white%, black%, alpha)`

- CIELAB (Lab) value in the form of `lab(lum, a, b)` or `lab(lum, a, b, alpha)`

- Cylindrical CIELAB (LCH) in the form of `lch(hue, chroma, lum)` or `lch(hue, chroma, lum, alpha)`

- ANSI escape sequences: 3/4 bit (8-color), 8-bit (256-color), 24-bit (true color)
  in the form of `\033[3Xm`, `\033[4Xm`, `\033[38;5;IIIm` or `\033[38;2;RRR,GGG,BBBm`.
  Escape part accepting "`^[`[", "\033", "\x1b[", "\u001b[" and "\e["


Those will be shown with colored background and gutter icons when they're found in
your documents.


## Configuration

- You can disable live highlight directly from the command palette:
  `Color Highlight: Disable Color Highlight`

- Open settings using the command palette:
  `Preferences: Color Highlight Settings - User`

- Gutter icons can be switched among three flavors (or disabled) by using
  the `gutter_icon` setting:
 
  + "circle" - Gutter icon with the color in a circle
  + "square" - Gutter icon with the color in a square
  + "fill" - Fill whole gutter with color
  
  ```
  "user": {
    "gutter_icon": "fill"
  }
  ```

  ![Gutter Icon](screenshots/gutter_icon.png?raw=true)

- Highlighting the value region in the color can be enabled or disabled by
  using the `highlight_values` setting.

- Enabling/disabling coloring of different types of values can be configured.


## License

Copyright (C) 2018 German Mendez Bravo (Kronuz). All rights reserved.

MIT license

This plugin was initially a fork of
https://github.com/Monnoroch/ColorHighlighter
