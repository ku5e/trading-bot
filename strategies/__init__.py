from strategies import trailing_stop

REGISTRY = {
    "trailing_stop": trailing_stop,
}


def get_strategy(name):
    if name not in REGISTRY:
        raise ValueError(f"Unknown strategy: {name!r}. Available: {list(REGISTRY.keys())}")
    return REGISTRY[name]
