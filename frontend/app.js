let pc = null;
let isStarted = false;

// ================= START WEBRTC =================
export async function startWebRTC() {
    if (isStarted) return;
    isStarted = true;

    pc = new RTCPeerConnection({
        iceServers: [
            { urls: "stun:stun.l.google.com:19302" }
        ]
    });

    const video = document.getElementById("video");

    // receive processed stream
    pc.ontrack = (event) => {
        video.srcObject = event.streams[0];
    };
    const devices = await navigator.mediaDevices.enumerateDevices();
    console.log(devices);

    // get webcam
    const stream = await navigator.mediaDevices.getUserMedia({
    video: true,
    audio: false
});

    stream.getTracks().forEach(track => pc.addTrack(track, stream));

    // create offer
    const offer = await pc.createOffer();
    await pc.setLocalDescription(offer);

    // send to backend
    const res = await fetch("http://localhost:5000/offer", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            sdp: pc.localDescription.sdp,
            type: pc.localDescription.type
        })
    });

    const answer = await res.json();
    await pc.setRemoteDescription(answer);

    console.log("WebRTC connected");
}


// ================= STOP =================
export function stopWebRTC() {
    if (!pc) return;

    pc.getSenders().forEach(sender => {
        if (sender.track) sender.track.stop();
    });

    pc.close();
    pc = null;
    isStarted = false;

    document.getElementById("video").srcObject = null;

    console.log("WebRTC stopped");
}


// ================= STATUS POLLING =================
export function startPolling() {
    setInterval(async () => {
        try {
            const res = await fetch("http://localhost:5000/status");
            const data = await res.json();

            updateUI(data);

        } catch (err) {
            console.log("Polling error:", err);
        }
    }, 500);
}


// ================= UI UPDATE =================
function updateUI(data) {
    const valveEl = document.getElementById("valve");
    const warningsEl = document.getElementById("warnings");
    const multiEl = document.getElementById("multi");

    valveEl.innerText = data.valve || "None";

    warningsEl.innerText =
        data.warnings && data.warnings.length
            ? data.warnings.join(", ")
            : "None";

    multiEl.innerText = data.multi_person ? "True" : "False";
}


// ================= RECORD =================
export async function recordValve(valve) {
    try {
        await fetch(`http://localhost:5000/record/${valve}`, {
            method: "POST"
        });

        console.log("Recording requested:", valve);
    } catch (err) {
        console.log("Record error:", err);
    }
}


// ================= INIT =================
window.onload = () => {
    const startBtn = document.getElementById("startBtn");

    startBtn.onclick = async () => {
        await startWebRTC();
        startPolling();
    };
};