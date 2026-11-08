# Raster backend

`render.c` uses the bundled stb_truetype and stb_image headers (upstream: https://github.com/nothings/stb; licenses included in each header). Text and PNG assets are composed in memory, then emitted as grayscale PGM. Landscape pixels are rotated counterclockwise into the same 1072×1448 portrait framebuffer used by the original working dashboard. The menu alone chooses the layout; there is no orientation or FBInk state query.

Build with Zig 0.14.1: `ZIG=/path/to/zig sh kindle/native/build.sh`. The target is static ARM Linux EABI, Cortex-A9 (the connected Kindle generation). A host build is also produced for the actual-raster preview checks. The target binary cannot run directly on macOS.

Minute updates emit only the clock crop. `preview.py` verifies byte-for-byte that the crop is identical to the same rectangle on the full page, for each orientation. Working images and commands live in `/tmp` on Kindle, not on USB flash storage.

`tickwait.c` blocks on the powerd-event FIFO until resume or the next ten-minute boundary. No touch watcher is built or installed. Physical power-key exit is handled by the separate stock-powerd event subscription in `button-exit.sh`; it is not coupled to RTC support or Wi-Fi state. No helper writes the kernel power state.

`reportread.c` validates JSON before outputting draw commands or the asset manifest. Private downloads use GitHub raw media responses and validate SHA-256 for the immutable image bundle before atomically choosing a complete report cache. The GitHub read token stays in the device curl config, outside the report and process arguments.
