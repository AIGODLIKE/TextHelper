"""BLF access for HUD draw callbacks (safe after extension reload)."""


def get_blf():
    import blf

    return blf
