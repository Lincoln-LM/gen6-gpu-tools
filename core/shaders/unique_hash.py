"""Kernel interface for unique hash search"""

import hashlib
import importlib.resources
import struct
import numpy as np
import pyopencl as cl
from qtpy.QtCore import QThread, Signal
from .. import shaders

SHADER_CODE = importlib.resources.read_text(shaders, "unique_hash.cl")


class SearchUniqueHashThread(QThread):
    """Interface for unique_hash shader"""

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
        (platform, device, n3ds_flag, low, high) = self.args
        ctx = cl.Context(
            dev_type=cl.device_type.ALL,
            properties=[(cl.context_properties.PLATFORM, platform)],
        )
        queue = cl.CommandQueue(ctx, device)
        program = cl.Program(ctx, SHADER_CODE).build(
            shaders.build_shader_constants(
                ds_type=2 if n3ds_flag else 0,
                target_low=low,
                target_high=high,
            )
        )

        find_unique = program.find_unique

        host_result = np.zeros(1, np.uint32)
        device_result = cl.Buffer(ctx, cl.mem_flags.READ_WRITE, host_result.nbytes)
        cl.enqueue_copy(queue, device_result, host_result)
        # TODO: custom lfcs starting point
        LFCS_RANGE = (0, 0x05000000 if n3ds_flag else 0x0B000000)
        LFCS_HALF_RANGE = (LFCS_RANGE[1] - LFCS_RANGE[0]) >> 1
        CHUNK_SIZE = 0x800
        self.init_progress_bar.emit(LFCS_HALF_RANGE)
        for offset in range(0, LFCS_HALF_RANGE, CHUNK_SIZE):
            for sign in (1, -1):
                if sign == -1:
                    offset += CHUNK_SIZE
                start = LFCS_RANGE[0] + LFCS_HALF_RANGE + sign * offset
                find_unique(
                    queue, (CHUNK_SIZE << 16,), None, np.uint32(start), device_result
                )
                cl.enqueue_copy(queue, host_result, device_result)
                if host_result[0]:
                    lfcs = start | int(host_result[0] >> 16)
                    rand = int(host_result[0]) & 0xFFFF
                    salt = 0x55D
                    m = hashlib.sha256()
                    m.update(
                        (lfcs).to_bytes(4, "little")
                        + ((rand << 16) | (2 if n3ds_flag else 0)).to_bytes(4, "little")
                        + (salt).to_bytes(4, "little")
                    )
                    low, high = struct.unpack("<" + "I" * 8, m.digest())[-2:]
                    self.results.emit(low ^ high)
                    self.progress.emit(LFCS_HALF_RANGE)
                    return
            self.progress.emit(offset + CHUNK_SIZE)
