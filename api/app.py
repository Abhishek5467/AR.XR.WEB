from quart import Quart, request, jsonify
from quart_cors import cors
from aiortc import RTCPeerConnection, RTCSessionDescription

from webrtc import VideoProcessorTrack
from state import state


app = Quart(__name__)
app = cors(app, allow_origin="*")

pcs = set()


# ================= WEBRTC =================
@app.route("/offer", methods=["POST"])
async def offer():
    params = await request.get_json()  # ← must await in Quart

    pc = RTCPeerConnection()
    pcs.add(pc)

    print("New PeerConnection")

    @pc.on("track")
    def on_track(track):
        print("Track received:", track.kind)

        if track.kind == "video":
            pc.addTrack(VideoProcessorTrack(track))

    @pc.on("connectionstatechange")
    async def on_state_change():
        if pc.connectionState in ["failed", "closed", "disconnected"]:
            await pc.close()
            pcs.discard(pc)
            print("PeerConnection closed")

    offer = RTCSessionDescription(
        sdp=params["sdp"],
        type=params["type"]
    )

    await pc.setRemoteDescription(offer)

    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return jsonify({
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type
    })


# ================= API =================
@app.route("/status")
async def status():
    return jsonify(state.get_metadata())


@app.route("/record/<valve>", methods=["POST"])
async def record(valve):
    state.request_record(valve)
    return jsonify({"status": "ok"})


# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)