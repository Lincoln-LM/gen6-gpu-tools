"""Kernel interface for iv search"""

from functools import reduce
import importlib.resources
import numpy as np
import pyopencl as cl
import numba
from numba_pokemon_prngs.mersenne_twister import MersenneTwister
from qtpy.QtCore import QThread, Signal
from .. import shaders

SHADER_CODE = importlib.resources.read_text(shaders, "iv_search.cl")


@numba.njit
def test_seed(seed, target_ivs_min, target_ivs_max, min_advance, max_advance) -> int:
    """Test if a seed contains the target ivs within the given range"""
    mt = MersenneTwister(seed)
    mt.advance(min_advance + 63)
    ivs = np.uint32(0)
    ivs |= mt.next_rand(32)
    ivs <<= 5
    ivs |= mt.next_rand(32)
    ivs <<= 5
    ivs |= mt.next_rand(32)
    ivs <<= 5
    ivs |= mt.next_rand(32)
    ivs <<= 5
    ivs |= mt.next_rand(32)
    ivs <<= 5
    ivs |= mt.next_rand(32)
    for adv in range(min_advance, max_advance):
        valid = True
        for i in range(6):
            if not (
                (target_ivs_min >> i * 5) & 31
                <= (ivs >> i * 5) & 31
                <= (target_ivs_max >> i * 5) & 31
            ):
                valid = False
                break
        if valid:
            return adv
        ivs <<= 5
        ivs |= mt.next_rand(32)
    return None


class SearchIVThread(QThread):
    """Interface for iv_search shader"""

    finished = Signal()
    log = Signal(str)
    results = Signal(object)
    init_progress_bar = Signal(int)
    progress = Signal(int)
    started = Signal()

    def __init__(self, *args) -> None:
        super().__init__()
        self.args = args

    def run(self) -> None:
        """Thread work"""
        (
            platform,
            device,
            ivs_1,
            ivs_2,
            ivs_max_1,
            advance_range_1,
            advance_range_2,
            start,
            chunks,
        ) = self.args
        ctx = cl.Context(
            dev_type=cl.device_type.ALL,
            properties=[(cl.context_properties.PLATFORM, platform)],
        )
        queue = cl.CommandQueue(ctx, device)
        program = cl.Program(ctx, SHADER_CODE).build(
            shaders.build_shader_constants(
                ivs=reduce(lambda x, y: (x << 5) | y, ivs_1),
                ivs_max=(
                    reduce(lambda x, y: (x << 5) | y, ivs_max_1) if ivs_max_1 else 0
                ),
                min_advance=advance_range_1.start,
                max_advance=advance_range_1.stop,
            )
        )
        target_ivs = None
        if ivs_2 is not None:
            target_ivs = reduce(lambda x, y: (x << 5) | y, ivs_2)

        find_initial_seeds = (
            program.find_initial_seeds
            if ivs_max_1 is None
            else program.find_initial_seeds_range
        )

        host_results = np.zeros(
            round(4 * (advance_range_1.stop - advance_range_1.start) * 1.5), np.uint32
        )
        host_count = np.zeros(1, np.int32)

        device_results = cl.Buffer(ctx, cl.mem_flags.READ_WRITE, host_results.nbytes)
        device_count = cl.Buffer(ctx, cl.mem_flags.READ_WRITE, host_count.nbytes)

        cl.enqueue_copy(queue, device_results, host_results)
        cl.enqueue_copy(queue, device_count, host_count)
        # TODO: custom step count/chunk size
        self.init_progress_bar.emit(chunks)
        self.started.emit()
        last_count = 0
        for chunk in range(chunks):
            if self.isInterruptionRequested():
                break
            find_initial_seeds(
                queue,
                (0x1000000,),
                None,
                np.uint32(start + (chunk << 24)),
                device_count,
                device_results,
            )
            cl.enqueue_copy(queue, host_results, device_results)
            cl.enqueue_copy(queue, host_count, device_count)
            for i in range(last_count, host_count[0]):
                # partial search
                if target_ivs is None:
                    self.results.emit(
                        (
                            host_results[i],
                            test_seed(
                                host_results[i],
                                reduce(lambda x, y: (x << 5) | y, ivs_1),
                                reduce(lambda x, y: (x << 5) | y, ivs_max_1),
                                advance_range_1.start,
                                advance_range_1.stop,
                            ),
                        )
                    )
                # full search
                elif (
                    test_seed(
                        host_results[i],
                        target_ivs,
                        target_ivs,
                        advance_range_2.start,
                        advance_range_2.stop,
                    )
                    is not None
                ):
                    self.results.emit(host_results[i])
            last_count = host_count[0]
            self.progress.emit(chunk + 1)
