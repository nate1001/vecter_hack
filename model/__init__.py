
try:
    from messenger import Messenger, Signal
    import config
except ImportError:
    import sys
    sys.path.append('.')
    try:
        from messenger import Messenger, Signal
        import config
    except ImportError:
        sys.path.append('..')
        from messenger import Messenger, Signal
        import config

