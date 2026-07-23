from core.kernel import EyeKernel

kernel = EyeKernel()

kernel.register_service("Logger", object())
kernel.register_service("Dashboard", object())

kernel.start()