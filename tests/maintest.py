from core.registry import REGISTRY, load_registry
load_registry()
print(REGISTRY["planets"].keys())