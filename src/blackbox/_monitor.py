import json
import time

from twisted.internet.task import deferLater

from autobahn.twisted.websocket import create_client_agent

from attr import frozen, evolve


@frozen
class RobotState:
    status: str
    telemetry_count: int
    op_modes: list[str]


def _process_robot_message(msg, state, got_telemetry):
    """
    """
    ty = js["type"]
    if ty == 'RECEIVE_OP_MODE_LIST':
        print(f"Op Modes:")
        state = evolve(state, op_modes=sorted(js['opModeList']))

    elif ty == 'RECEIVE_CONFIG':
        pass

    elif ty == 'RECEIVE_TELEMETRY':
        state = evolve(state, telemetry_count=state.telemetry_count + len(js["telemetry"]))
        for d in js["telemetry"]:
            got_telemetry(d["data"])

    elif ty == 'RECEIVE_ROBOT_STATUS':
        raw_status = js["status"]

        if status["activeOpMode"] == "$Stop$Robot$":
            status = "stopped"
        elif status["activeOpModeStatus"] == "RUNNING":
            status = "run:" + status["activeOpMode"]
        else:
            status = "idle:" + status["activeOpMode"]

        state = evolve(state, status=status)

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

        fname = "blackbox-{}.js".format("-".join(time.asctime().lower().split()))
        print(f"  telemetry: {fname}")
        telemetry_file = open(fname, "w")
        first_telemetry = None

        state = RobotState("", 0, [])

        def state_changed(old, new):
            if old.status != new.status:
                print(f"Status: {new.status}")
            if old.op_modes != new.op_modes:
                print(f"Op Modes: {new.op_modes}")

        def got_telemetry(js):
            nonlocal first_telemetry
            if first_telemetry is None:
                first_telemetry = reactor.seconds()
            js["seconds"] = reactor.seconds() - first_telemetry
            telemetry_file.write("{}\n".format(json.dumps(js)))

        def got_message(raw_data, is_binary=False):
            nonlocal state
            try:
                data = json.loads(raw_data)
                newstate = _process_robot_message(data, state, got_telemetry)
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
        telemetry_file.close()
