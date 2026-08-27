from importlib.metadata import PackageNotFoundError, version


DIST_NAME = 'gentleman-agents'


try:
    __version__ = version(DIST_NAME)

except PackageNotFoundError:
    __version__ = '0.0.0+unknown'

