import subprocess
import os
import sys

if sys.platform == 'win32':
    try:
        import win32serviceutil
        import win32service
        import win32event
        import servicemanager
    except ImportError:
        win32serviceutil = None
        win32service = None
        win32event = None
        servicemanager = None
else:
    # Mock win32com for non-Windows platforms (development purposes)
    win32com = None
    pythoncom = None

class PythonAppService(win32serviceutil.ServiceFramework):
    _svc_name_ = "MyPythonAppService"
    _svc_display_name_ = "My Python API Service"
    _svc_description_ = "Runs the Flask QuickBooks integration service."

    def __init__(self, args):
        super().__init__(args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        self.process = None

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        if self.process:
            self.process.terminate()

    def SvcDoRun(self):
        servicemanager.LogInfoMsg("Starting My Python API Service")
        self.main()

    def main(self):
        # Caminho até seu app principal (ex: app.py ou app.pyz)
        app_path = os.path.join(os.path.dirname(__file__), "app.py")

        # Executa como subprocesso
        self.process = subprocess.Popen([sys.executable, app_path])

        # Aguarda sinal de parada
        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)


if __name__ == '__main__':
    win32serviceutil.HandleCommandLine(PythonAppService)
