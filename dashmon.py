import json
import time

from twisted.internet.task import react, deferLater
from twisted.internet.defer import ensureDeferred

from autobahn.twisted.websocket import create_client_agent


def decode_robot_message(js, got_telemetry):
    ty = js["type"]
    if ty == 'RECEIVE_OP_MODE_LIST':
        print(f"op-modes: {js['opModeList']}")
    elif ty == 'RECEIVE_CONFIG':
        print("got config")
    elif ty == 'RECEIVE_TELEMETRY':
        for d in js["telemetry"]:
            got_telemetry(d["data"])
            print(".", end="", flush=True)
    elif ty == 'RECEIVE_ROBOT_STATUS':
        status = js["status"]
        print("status:")
        if status["activeOpMode"] == "$Stop$Robot$":
            print("  stopped")
        elif status["activeOpModeStatus"] == "RUNNING":
            print("  ACTIVE: {}".format(status["activeOpMode"]))
        else:
            print("    idle: {}".format(status["activeOpMode"]))
    else:
        print("unknown", ty)


async def _real_main(reactor):
    agent = create_client_agent(reactor)
    wsaddr = "ws://192.168.43.1:8000/"
    options = {
        # "headers": {
        #     "x-foo": "bar",
        # }
    }

    if True:#    while True:
        print(f"connecting: {wsaddr}")
        try:
            proto = await agent.open(wsaddr, options)
        except Exception as e:
            print(f"Error: {e}")
            return
            ##continue
        print("connected")

        fname = "match-{}.js".format(time.asctime())
        print(f"writing: {fname}")
        telemetry_file = open(fname, "w")
        first_telemetry = None

        def got_telemetry(js):
            nonlocal first_telemetry
            if first_telemetry is None:
                first_telemetry = reactor.seconds()
            js["seconds"] = reactor.seconds() - first_telemetry
            telemetry_file.write("{}\n".format(json.dumps(js)))

        def got_message(raw_data, is_binary=False):
            try:
                data = json.loads(raw_data)
                decode_robot_message(data, got_telemetry)
            except Exception as e:
                print("ERROR:got message", e)
        proto.on('message', got_message)

        await proto.is_open

        def send_update_request():
            proto.sendMessage(json.dumps({"type": "GET_ROBOT_STATUS"}).encode("utf8"))
            deferLater(reactor, 1, send_update_request)
        send_update_request()

        print("protocol open")
        await deferLater(reactor, 0, lambda: None)

        #proto.sendClose(code=1000, reason="byebye")
        x = await proto.is_closed
        print("CLOSED", x)
        telemetry_file.close()


@react
def main(reactor):
    return ensureDeferred(_real_main(reactor))
