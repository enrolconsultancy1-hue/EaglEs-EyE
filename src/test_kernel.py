import unittest
from core.kernel import EyeKernel

class FakeService:
    def __init__(self, name):
        self.name = name
    def start(self):
        pass

class TestKernelRegistration(unittest.TestCase):
    def test_register_and_get_service(self):
        kernel = EyeKernel()
        svc = FakeService("TestService")
        kernel.register_service(svc)
        self.assertIs(kernel.get_service("TestService"), svc)

    def test_start_calls_service_start(self):
        started = []
        class CallbackService:
            name = "Callback"
            def start(self):
                started.append(True)
        kernel = EyeKernel()
        kernel.register_service(CallbackService())
        kernel.start()
        self.assertEqual(started, [True])