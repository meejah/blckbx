import json

from twisted.internet.task import react, deferLater
from twisted.internet.defer import ensureDeferred

from autobahn.twisted.websocket import create_client_agent


def decode_robot_message(js, got_telemetry):
    ty = js["type"]
    print(ty)
    if ty == 'RECEIVE_OP_MODE_LIST':
        print("op-modes: {ty[opModeList]}")
    elif ty == 'RECEIVE_CONFIG':
        print("got config")
    elif ty == 'RECEIVE_TELEMETRY':
        print("telemetry")
        for d in js["telemetry"]:
            got_telemetry(d["data"])
    else:
        print("unknown", ty)


async def _real_main(reactor):
    agent = create_client_agent(reactor)
    options = {
        # "headers": {
        #     "x-foo": "bar",
        # }
    }
    print("connecting")
    proto = await agent.open("ws://192.168.43.1:8000/", options)
    print("connected")

    telemetry_file = open("last_match.js", "w")
    first_telemetry = None

    def got_telemetry(js):
        nonlocal first_telemetry
        if first_telemetry is None:
            first_telemetry = reactor.seconds()
        js["seconds"] = first_telemetry - reactor.seconds()
        telemetry_file.write("{}\n".format(json.dumps(js)))

    def got_message(raw_data, is_binary=False):
        try:
            data = json.loads(raw_data)
            decode_robot_message(data, got_telemetry)
        except Exception as e:
            print("ERROR:got message", e)
    proto.on('message', got_message)

    await proto.is_open

    print("protocol open")
    await deferLater(reactor, 0, lambda: None)

    #proto.sendClose(code=1000, reason="byebye")
    x = await proto.is_closed
    print("CLOSED", x)
    telemetry_file.close()


@react
def main(reactor):
    return ensureDeferred(_real_main(reactor))
