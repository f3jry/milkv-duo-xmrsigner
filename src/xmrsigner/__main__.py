from __future__ import annotations
from xmrsigner.controller import Controller
# Get the one and only Controller instance and start our main loop
Controller.get_instance().start()
