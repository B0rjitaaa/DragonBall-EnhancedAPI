"""Lanzador de tests: cada test empieza con la caché vacía (límites de peticiones, candados como el del sync…).

Con la caché en memoria de los tests (ver settings: TESTING) nada se arrastra de un test a otro ni choca con la web
que esté corriendo en la misma máquina."""
import unittest

from django.core.cache import cache
from django.test.runner import DiscoverRunner


class IsolatedRunner(DiscoverRunner):
    def get_resultclass(self):
        base = super().get_resultclass() or unittest.TextTestResult

        class FreshCacheResult(base):
            def startTest(self, test):
                cache.clear()
                super().startTest(test)

        return FreshCacheResult
