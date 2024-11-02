"""Kernel interface for pokemon blink search"""

import importlib.resources
import numpy as np
import pyopencl as cl
from qtpy.QtCore import QThread, Signal
from .. import shaders

SHADER_CODE = importlib.resources.read_text(shaders, "pokemon_blink.cl")


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
        (platform, device, blinks, leeway, advance_range) = self.args
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

        device_results = cl.Buffer(ctx, cl.mem_flags.READ_WRITE, host_results.nbytes)
        device_count = cl.Buffer(ctx, cl.mem_flags.READ_WRITE, host_count.nbytes)

        cl.enqueue_copy(queue, device_results, host_results)
        cl.enqueue_copy(queue, device_count, host_count)
        # TODO: custom step count/chunk size
        self.init_progress_bar.emit(0x100)
        for offset in range(0x100):
            find_initial_seeds(
                queue,
                (0x10000, 0x100),
                None,
                np.uint32(offset << 8),
                device_count,
                device_results,
            ).wait()
            self.progress.emit(offset + 1)
        cl.enqueue_copy(queue, host_results, device_results)
        cl.enqueue_copy(queue, host_count, device_count)
        self.results.emit(host_results[: host_count[0]])
