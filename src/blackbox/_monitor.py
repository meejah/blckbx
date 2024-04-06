import json
import time

from twisted.internet.task import deferLater

from autobahn.twisted.websocket import create_client_agent

from attr import frozen, evolve
import automat


@frozen
class RobotState:
    status: str
    telemetry_count: int
    op_modes: list[str]


class Robot:
    _m = automat.MethodicalMachine()

    def __init__(self, reactor):
        self._open_telemetry()
        self._first_telemetry = None
        self._telemetry_count = 0
        self._reactor = reactor

    def _get_current_time(self):
        return self._reactor.seconds()

    @_m.input()
    def stop(self):
        """
        The robot is stopped
        """

    @_m.input()
    def init(self, op):
        """
        The robot has entered Idle for a particular op-mode
        """

    @_m.input()
    def play(self, op):
        """
        The robot is running some op-mode
        """

    @_m.input()
    def got_telemetry(self, telemetry):
        """
        Got a new batch of telemetry
        """

    @_m.state(initial=True)
    def stopped(self):
        """
        Nothing going on
        """

    @_m.state()
    def initializing(self):
        """
        Nothing going on
        """

    @_m.state()
    def running(self):
        """
        """

    @_m.output()
    def _starting(self, op):
        print(f"Starting: {op}")

    @_m.output()
    def _playing(self, op):
        print(f"Playing: {op}")

    @_m.output()
    def _rotate_telemetry(self):
        self.telemetry_file.close()
        self._telemetry_count = 0
        self._open_telemetry()

    def _open_telemetry(self):
        fname = "blackbox-{}.js".format("-".join(time.asctime().lower().split()))
        print(f"  telemetry: {fname}")
        self.telemetry_file = open(fname, "w")

    @_m.output()
    def _write_telemetry(self, telemetry):
        self._telemetry_count += 1
        if self._first_telemetry is None:
            self._first_telemetry = self._get_current_time()
        telemetry["seconds"] = self._get_current_time() - self._first_telemetry
        self.telemetry_file.write("{}\n".format(json.dumps(telemetry)))

    stopped.upon(stop, enter=stopped, outputs=[])
    stopped.upon(play, enter=stopped, outputs=[])
    stopped.upon(init, enter=initializing, outputs=[_starting])
    stopped.upon(got_telemetry, enter=stopped, outputs=[_write_telemetry])

    initializing.upon(init, enter=initializing, outputs=[])
    initializing.upon(got_telemetry, enter=initializing, outputs=[_write_telemetry])
    initializing.upon(play, enter=running, outputs=[_playing])
    initializing.upon(stop, enter=stopped, outputs=[_rotate_telemetry])

    running.upon(play, enter=running, outputs=[])
    running.upon(got_telemetry, enter=running, outputs=[_write_telemetry])
    running.upon(stop, enter=stopped, outputs=[_rotate_telemetry])


def _process_robot_message(msg, state, state_machine):
    """
    """
    ty = msg["type"]
    if ty == 'RECEIVE_OP_MODE_LIST':
        print("Op Modes:")
        for om in sorted(msg['opModeList']):
            print(f"  {om}")

    elif ty == 'RECEIVE_CONFIG':
        pass

    elif ty == 'RECEIVE_TELEMETRY':
        state = evolve(state, telemetry_count=state.telemetry_count + len(msg["telemetry"]))
        for d in msg["telemetry"]:
            state_machine.got_telemetry(d["data"])

    elif ty == 'RECEIVE_ROBOT_STATUS':
        status = msg["status"]
        st = "unknown"
        if status["activeOpMode"] == "$Stop$Robot$":
            state_machine.stop()
            st = "stopped"
        elif status["activeOpModeStatus"] == "RUNNING":
            state_machine.play(status["activeOpMode"])
            st = "running"
        else:
            state_machine.init(status["activeOpMode"])
            st = "idle"

        state = evolve(state, status=st)

    else:
        print(f"Unknown message type: {ty}")

    return state


async def _monitor_dashboard(reactor, wsaddr="ws://192.168.43.1:8000/"):
    """
    Connect to and monitor an FTC Dashboard instance.
    """
    agent = create_client_agent(reactor)
    options = {}

    while True:
        print(f"connecting: {wsaddr}")
        try:
            proto = await agent.open(wsaddr, options)
        except Exception as e:
            print(f"Error: {e}")
            await deferLater(reactor, 1.0, lambda: None)
            continue
        print("Connected.")

        state = RobotState("", 0, [])
        statemachine = Robot(reactor)

        def state_changed(old, new):
            if old.status != new.status:
                print(f"Status: {new.status}")
            if old.op_modes != new.op_modes:
                print(f"Op Modes: {new.op_modes}")

        def got_message(raw_data, is_binary=False):
            nonlocal state
            try:
                data = json.loads(raw_data)
                newstate = _process_robot_message(data, state, statemachine)
                if newstate != state:
                    state_changed(state, newstate)
                    state = newstate
            except Exception as e:
                print(f"ERROR: got message: {e}")
        proto.on('message', got_message)

        await proto.is_open

        # if we don't periodically send these, the WebSocket is disconnected
        def send_update_request():
            proto.sendMessage(json.dumps({"type": "GET_ROBOT_STATUS"}).encode("utf8"))
            deferLater(reactor, 1, send_update_request)
        send_update_request()

        try:
            await proto.is_closed
            print("Stream closed, re-connecting.")
        except Exception as e:
            print(f"Error, stream closed: {e}")
        # XXX FIXME use an input
        statemachine.telemetry_file.close()
