"""A simulated end-to-end stack: voice -> intent -> plan -> policy -> router -> fake robot.

It wires the real voice, AI-engine and safety-layer code to a fake robot, so tests exercise
the actual interfaces between components. It does not involve guardian-core or hardware.
"""

import math

from guardian_ai_engine.command_router import CommandRouter
from guardian_ai_engine.intent_parser import IntentParser
from guardian_ai_engine.llm_connector import FakeLLM
from guardian_ai_engine.memory import Memory
from guardian_ai_engine.planner import Planner
from guardian_ai_engine.policy_engine import PolicyEngine
from guardian_safety_layer.estop import EmergencyStop
from guardian_safety_layer.safety_fsm import SafetyFSM, SafetyLevel
from guardian_voice.command_pipeline import CommandPipeline
from guardian_voice.speech_to_text import FakeSTT
from guardian_voice.text_to_speech import FakeTTS, Speaker

LOUD_FRAME = [0.5 * math.sin(i) for i in range(160)]


class FakeRobot:
    def __init__(self):
        self.state = "READY"
        self.estop = EmergencyStop()
        self.safety = SafetyFSM()
        self.calls = []
        self.estop.on_trigger(lambda reason: self._stopped(reason))

    def _stopped(self, reason):
        self.state = "EMERGENCY_STOP"
        self.safety.escalate(SafetyLevel.EMERGENCY_STOP)

    def handlers(self):
        def record(name, new_state=None):
            def handler():
                self.calls.append(name)
                if new_state:
                    self.state = new_state
            return handler

        def emergency_stop():
            self.calls.append("emergency_stop")
            self.estop.trigger("operator command")

        def recover():
            self.calls.append("recover")
            self.safety.clear_emergency_stop()
            self.estop.reset()
            self.state = "READY"

        return {
            "report_status": record("report_status"),
            "battery_level": record("battery_level"),
            "run_diagnostics": record("run_diagnostics"),
            "start_patrol": record("start_patrol", "MISSION"),
            "return_to_base": record("return_to_base", "RTB"),
            "abort_mission": record("abort_mission", "READY"),
            "emergency_stop": emergency_stop,
            "recover": recover,
        }


class Stack:
    def __init__(self, stt_results, llm_responses=None):
        self.robot = FakeRobot()
        self.memory = Memory()
        self.parser = IntentParser(FakeLLM(llm_responses) if llm_responses is not None else None)
        self.planner = Planner()
        self.router = CommandRouter(self.robot.handlers(), PolicyEngine(), lambda: self.robot.state, self.memory)
        self.tts = FakeTTS()
        self.pipeline = CommandPipeline(FakeSTT(stt_results), self._handle, Speaker(self.tts))
        self.last_results = []

    def _handle(self, command_text):
        intent = self.parser.parse(command_text)
        self.last_results = self.router.route_plan(self.planner.plan(intent))
        return ", ".join(f"{r.intent.name}:{r.status}" for r in self.last_results)

    def utter(self):
        """Process the next scripted utterance."""
        return self.pipeline.process([LOUD_FRAME])
