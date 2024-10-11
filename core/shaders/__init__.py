"""OpenCL Shader Files"""


def build_shader_constants(**kwargs) -> list[str]:
    """Build cmdline options for specifying constants in OpenCL shaders"""
    return [f"-D {key.upper()}={value}" for key, value in kwargs.items()]
