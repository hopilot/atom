import os

from system.hardware import EON, TICI, PC
from selfdrive.manager.process import PythonProcess, NativeProcess, DaemonProcess

WEBCAM = os.getenv("USE_WEBCAM") is not None

procs = [
  DaemonProcess("manage_athenad", "selfdrive.athena.manage_athenad", "AthenadPid"),
  # due to qualcomm kernel bugs SIGKILLing camerad sometimes causes page table corruption
  NativeProcess("camerad", "system/camerad", ["./camerad"], unkillable=True, driverview=True),
  NativeProcess("clocksd", "system/clocksd", ["./clocksd"]),
  NativeProcess("dmonitoringmodeld", "selfdrive/modeld", ["./dmonitoringmodeld"], enabled=(not PC or WEBCAM), driverview=True),
  NativeProcess("logcatd", "system/logcatd", ["./logcatd"]),
  NativeProcess("loggerd", "selfdrive/loggerd", ["./loggerd"]),
  NativeProcess("modeld", "selfdrive/modeld", ["./modeld"]),
  NativeProcess("navd", "selfdrive/ui/navd", ["./navd"], enabled=(PC or TICI), persistent=True),
  NativeProcess("proclogd", "system/proclogd", ["./proclogd"]),
  NativeProcess("sensord", "selfdrive/sensord", ["./sensord"], enabled=not PC, persistent=EON, sigkill=EON),
  NativeProcess("ubloxd", "selfdrive/locationd", ["./ubloxd"], enabled=(not PC or WEBCAM)),
  NativeProcess("ui", "selfdrive/ui", ["./ui"], persistent=True, watchdog_max_dt=(5 if TICI else None)),
  NativeProcess("soundd", "selfdrive/ui/soundd", ["./soundd"], persistent=True),
  NativeProcess("locationd", "selfdrive/locationd", ["./locationd"]),
  NativeProcess("boardd", "selfdrive/boardd", ["./boardd"], enabled=False),
  PythonProcess("calibrationd", "selfdrive.locationd.calibrationd"),
  PythonProcess("torqued", "selfdrive.locationd.torqued"),  
  PythonProcess("controlsd", "selfdrive.controls.controlsd"),
  PythonProcess("deleter", "selfdrive.loggerd.deleter", persistent=True),
  PythonProcess("dmonitoringd", "selfdrive.monitoring.dmonitoringd", enabled=(not PC or WEBCAM), driverview=True),
  PythonProcess("logmessaged", "system.logmessaged", persistent=True),
  PythonProcess("pandad", "selfdrive.boardd.pandad", persistent=True),
  PythonProcess("paramsd", "selfdrive.locationd.paramsd"),
  PythonProcess("plannerd", "selfdrive.controls.plannerd"),
  PythonProcess("radard", "selfdrive.controls.radard"),
  PythonProcess("thermald", "selfdrive.thermald.thermald", persistent=True),
  PythonProcess("timezoned", "system.timezoned", enabled=TICI, persistent=True),
  PythonProcess("tombstoned", "selfdrive.tombstoned", enabled=not PC, persistent=True),
  PythonProcess("updated", "selfdrive.updated", enabled=not PC, persistent=True),
  PythonProcess("uploader", "selfdrive.loggerd.uploader", persistent=True),
  PythonProcess("statsd", "selfdrive.statsd", persistent=True),

  # EON only
  PythonProcess("rtshield", "selfdrive.rtshield", enabled=EON),
  PythonProcess("shutdownd", "system.hardware.eon.shutdownd", enabled=EON),
  PythonProcess("androidd", "system.hardware.eon.androidd", enabled=EON, persistent=True),

  # Experimental
  PythonProcess("rawgpsd", "selfdrive.sensord.rawgps.rawgpsd", enabled=os.path.isfile("/persist/comma/use-quectel-rawgps")),
]

managed_processes = {p.name: p for p in procs}
