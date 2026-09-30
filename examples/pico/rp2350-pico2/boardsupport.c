/* Board support for Embench on a Raspberry Pi Pico, clocked by pico-turbo.
 *
 * Embench asks a board for three functions -- initialise_board(), start_trigger()
 * and stop_trigger() -- and the reference implementation for Arm
 * (examples/arm/stm32f4-discovery/boardsupport.c) times with the Cortex-M cycle
 * counter in DWT.  That counter does not count on this chip: with the same
 * enable sequence, an eleven-second timed region at 150 MHz read 168 cycles where
 * 1.68e9 were expected.  The likely reason is that the debug and trace blocks are
 * in a power domain that a debugger has to bring up, and keeping a debugger
 * attached through a run is the one thing this bench forbids -- so the port times
 * with the SDK's microsecond timer instead, which is what the coremark port in the
 * sibling repository uses and which was checked against the host's clock to 0.05%
 * (RANKINGS.md, section 8).
 *
 * Microseconds also remove a host-side variable: the reference runner converts
 * cycles to milliseconds with a cpu_mhz it has to be told, whereas here the tick
 * *is* time, and the clock the chip measured itself at is on the line below.
 *
 * SPDX-License-Identifier: GPL-3.0-or-later */

#include <stdio.h>
#include <stdlib.h>

#include "pico/stdlib.h"
#include "hardware/clocks.h"
#include "pico_turbo.h"

#include "support.h"

static volatile uint32_t start_us;
static volatile uint32_t elapsed_us;

/* The benchmark's own verify_benchmark, which -Wl,--wrap=verify_benchmark keeps
   under this name while redirecting the harness's call to __wrap_verify_benchmark
   below.  Declared rather than included: it is per-benchmark code and this file
   knows nothing else about it. */
int __real_verify_benchmark (int res);

void
initialise_board (void)
{
  pico_turbo_init ();

  stdio_uart_init_full (uart0, 115200, 0, 1);
  stdio_usb_init ();

  /* One line a log can be read back from, the same shape the coremark port
     prints: what was asked for, what the chip is actually running (measured with
     the hardware frequency counter, not read out of the configuration), and the
     rest of the clocks the answer depends on.  A result without this line is a
     result nobody can attribute to a configuration. */
  {
    pico_turbo_state_t st = pico_turbo_state ();
    uint32_t measured = frequency_count_khz (CLOCKS_FC0_SRC_VALUE_CLK_SYS);

    printf ("PICO-TURBO: %lu kHz asked, %lu kHz configured, %lu kHz measured, "
	    "vreg sel %u, flash %lu kHz, clk_peri %lu kHz, usb %s\n",
	    (unsigned long) st.requested_khz,
	    (unsigned long) st.sys_clk_khz,
	    (unsigned long) measured, (unsigned) st.vreg_sel,
	    (unsigned long) st.flash_clk_khz,
	    (unsigned long) st.peri_clk_khz,
	    st.usb_ok ? "ok" : "WRONG");
    /* The scale factor is here because it is what decides how long a run takes:
       Embench sizes each benchmark so a run is about four seconds on the platform
       its numbers were published for, and on a chip at half a gigahertz the same
       work is over in a fraction of that.  A time without the scale factor that
       produced it is a number nobody can compare with anything. */
    printf ("EMBENCH: %s scale %d heat %d\n",
	    EMBENCH_BENCHMARK_NAME, (int) GLOBAL_SCALE_FACTOR, (int) WARMUP_HEAT);
  }
}

/* Both of these are called from the harness with the timed region between them.
   noinline and externally_visible are what the reference implementation uses and
   what any timing hook needs: an inlined trigger is a trigger the compiler may
   move across the code it is supposed to bracket. */
void __attribute__ ((noinline)) __attribute__ ((externally_visible))
start_trigger (void)
{
  start_us = time_us_32 ();
}

void __attribute__ ((noinline)) __attribute__ ((externally_visible))
stop_trigger (void)
{
  elapsed_us = time_us_32 () - start_us;
}

/* The harness calls verify_benchmark() and returns its result as the exit code,
   which the reference runner reads out of a register over GDB.  This port does not
   run under a debugger, so the build wraps the call (-Wl,--wrap=verify_benchmark,
   set in CMakeLists.txt) and the verdict is printed here, together with the only
   other thing the host needs.  One line, at the end, so a reader that starts late
   still sees it -- the line the result is judged by is also the line that says the
   benchmark finished. */
int
__wrap_verify_benchmark (int res)
{
  int ok = __real_verify_benchmark (res);

  printf ("EMBENCH-PICO: %s %lu us %s\n",
	  EMBENCH_BENCHMARK_NAME, (unsigned long) elapsed_us,
	  ok ? "pass" : "FAIL");

  return ok;
}
