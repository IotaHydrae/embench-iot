/*
 * Board: WeAct Studio RP2350A core board (V1.0).  RP2350A rev 2, Winbond
 * W25Q32FV/JV 4 MB.
 *
 * Everything this firmware touches is a Pico 2's: the chip, the pinout, the size
 * of the flash.  What is not the same is what the bench measures -- 520 MHz
 * validated and 546 MHz hard-faulted here, where the official board and the
 * Luckfox clone both reach 564 -- and that is not a pin definition, so it does not
 * live in this file.  It goes to pico-turbo's boards/weact_rp2350a.cmake, which is
 * keyed by PICO_BOARD.
 *
 * The name exists so that file can exist.  A clone sharing `pico2` inherits a
 * ceiling measured on somebody else's board, which is exactly the mistake this
 * repository keeps finding: a board's name is not a specification (RANKINGS.md,
 * section 7).  If a V2.0 of this board turns up, it wants a name of its own for
 * the same reason -- nobody has measured whether the two are the same board.
 *
 * The three declarations below are written out rather than inherited, but not for the
 * reason first given for them, which does not hold up.  The SDK does read this file as
 * text when it decides what a board *is* (`cmake/generic_board.cmake`: a
 * `file(STRINGS)` and a pattern per line) -- and it *does* follow
 * `#include "boards/..."`: it resolves the named header in `PICO_BOARD_HEADER_DIRS`,
 * reads it, and prepends its lines to the ones it is walking.  `pico2.h` is always
 * findable there, because the SDK appends its own `src/boards/include/boards` to that
 * list last.  A header carrying nothing but that include was measured both ways and
 * resolved to `PICO_PLATFORM:STRING=rp2350-arm-s`, with a UF2 family id of 0xe48bff57
 * (rp2350-arm-s); the build that reached rp2040 came from somewhere else, and a
 * `PICO_PLATFORM` left behind in a CMakeCache is what that looks like.
 *
 * Written out anyway: saying what this board is, in the file named after it, costs
 * three lines and depends on none of the above.  (C tolerates them because pico.h
 * defines them to nothing.)
 */
#ifndef _BOARDS_WEACT_RP2350A_H
#define _BOARDS_WEACT_RP2350A_H

pico_board_cmake_set(PICO_PLATFORM, rp2350)
pico_board_cmake_set_default(PICO_FLASH_SIZE_BYTES, (4 * 1024 * 1024))
pico_board_cmake_set_default(PICO_RP2350_A2_SUPPORTED, 1)

#include "boards/pico2.h"

#endif
