"""Kernel interface for pokemon blink search"""

import importlib.resources
import numpy as np
import pyopencl as cl
import numba
from qtpy.QtCore import QThread, Signal
from numba_pokemon_prngs.mersenne_twister import TinyMersenneTwister
from .. import shaders

SHADER_CODE = importlib.resources.read_text(shaders, "pokemon_blink.cl")


@numba.njit
def find_matching_advances(
    seed, target_blinks, leeway, min_advance, max_advance
) -> int:
    """Finds advances from a given seed that generates the target blinks"""
    mt = TinyMersenneTwister(seed)
    mt.advance(min_advance)
    test_rng = TinyMersenneTwister(0)
    results = []
    for adv in range(min_advance, max_advance):
        test_rng.state[:] = mt.state
        mt.next()
        valid = True
        for blink in target_blinks:
            if not (blink - leeway <= test_rng.next_rand(240) <= blink + leeway):
                valid = False
                break
        if valid:
            results.append(adv)
    return results


class PokemonBlinkFidgetThread(QThread):
    """Interface for pokemon_blink shader"""

    finished = Signal()
    log = Signal(str)
    results = Signal(object)
    init_progress_bar = Signal(int)
    progress = Signal(int)

    def __init__(self, *args) -> None:
        super().__init__()
        self.args = args

    def run(self) -> None:
        """Thread work"""
        (
            platform,
            device,
            blinks,
            leeway,
            advance_range,
            start,
            chunks,
            reidentfication,
        ) = self.args
        # TODO: cleaner threading impl a la lgpe-item-rng-tool
        if reidentfication:
            self.init_progress_bar.emit(1)
            self.progress.emit(1)
            self.results.emit(
                (
                    find_matching_advances(
                        start, blinks, leeway, advance_range.start, advance_range.stop
                    ),
                )
            )
        else:
            ctx = cl.Context(
                dev_type=cl.device_type.ALL,
                properties=[(cl.context_properties.PLATFORM, platform)],
            )
            queue = cl.CommandQueue(ctx, device)
            program = cl.Program(ctx, SHADER_CODE).build(
                shaders.build_shader_constants(
                    blink_count=len(blinks),
                    blink_data=",".join(map(str, blinks)),
                    leeway=leeway,
                    base_advance=advance_range.start,
                    max_advance=advance_range.stop,
                )
            )

            find_initial_seeds = program.find_initial_seeds

            host_results = np.zeros(150, np.uint32)
            host_count = np.zeros(1, np.int32)

            device_results = cl.Buffer(
                ctx, cl.mem_flags.READ_WRITE, host_results.nbytes
            )
            device_count = cl.Buffer(ctx, cl.mem_flags.READ_WRITE, host_count.nbytes)

            cl.enqueue_copy(queue, device_results, host_results)
            cl.enqueue_copy(queue, device_count, host_count)
            self.init_progress_bar.emit(chunks)
            for chunk in range(chunks):
                find_initial_seeds(
                    queue,
                    (0x1000000,),
                    None,
                    np.uint32(start + (chunk << 24)),
                    device_count,
                    device_results,
                ).wait()
                self.progress.emit(chunk + 1)
            cl.enqueue_copy(queue, host_results, device_results)
            cl.enqueue_copy(queue, host_count, device_count)
            self.results.emit(
                (
                    host_results[: host_count[0]],
                    find_matching_advances(
                        host_results[0],
                        blinks,
                        leeway,
                        advance_range.start,
                        advance_range.stop,
                    )[0],
                )
            )
