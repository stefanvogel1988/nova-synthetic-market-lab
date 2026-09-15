from nova_lab.providers.base import SimulationEngine


class GenericLLMAdapter:
    """Optional adapter boundary. V1 acceptance never requires a paid provider."""

    def __init__(self, client: object):
        self.client = client
