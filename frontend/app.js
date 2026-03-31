let pc = null;
let isStarted = false;
let pollingInterval = null;

// ================= START WEBRTC =================
export async function startWebRTC() {
	if (isStarted) return;
	isStarted = true;

	pc = new RTCPeerConnection({
		iceServers: [{ urls: 'stun:stun.l.google.com:19302' }],
	});

	const video = document.getElementById('video');

	// get webcam first
	const stream = await navigator.mediaDevices.getUserMedia({
		video: true,
		audio: false,
	});

	// show local preview immediately while WebRTC handshake happens
	video.srcObject = stream;

	stream.getTracks().forEach((track) => pc.addTrack(track, stream));

	// receive processed stream — only swap once remote track is actually live
	pc.ontrack = (event) => {
		const remoteStream = event.streams[0];
		const remoteTrack = remoteStream.getVideoTracks()[0];

		if (remoteTrack) {
			// swap to processed stream only when track is unmuted (data flowing)
			remoteTrack.onunmute = () => {
				video.srcObject = remoteStream;
				console.log('Switched to remote processed stream');
			};
		} else {
			// fallback: swap immediately if no unmute event
			video.srcObject = remoteStream;
		}
	};

	// create offer
	const offer = await pc.createOffer();
	await pc.setLocalDescription(offer);

	// send to backend via Vercel rewrite
	const res = await fetch('/api/offer', {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json',
		},
		body: JSON.stringify({
			sdp: pc.localDescription.sdp,
			type: pc.localDescription.type,
		}),
	});

	const answer = await res.json();
	await pc.setRemoteDescription(answer);

	console.log('WebRTC connected');
}

// ================= STOP =================
export function stopWebRTC() {
	if (!pc) return;

	pc.getSenders().forEach((sender) => {
		if (sender.track) sender.track.stop();
	});

	pc.close();
	pc = null;
	isStarted = false;

	if (pollingInterval) {
		clearInterval(pollingInterval);
		pollingInterval = null;
	}

	document.getElementById('video').srcObject = null;

	console.log('WebRTC stopped');
}

// ================= STATUS POLLING =================
export function startPolling() {
	if (pollingInterval) return;

	pollingInterval = setInterval(async () => {
		try {
			const res = await fetch('/api/status');
			const data = await res.json();
			console.log(data);

			updateUI(data);
		} catch (err) {
			console.log('Polling error:', err);
		}
	}, 500);
}

// ================= UI UPDATE =================
function updateUI(data) {
	const valveEl = document.getElementById('valve');
	const warningsEl = document.getElementById('warnings');
	const multiEl = document.getElementById('multi');

	valveEl.innerText = data.valve || 'None';

	warningsEl.innerText =
		data.warnings && data.warnings.length
			? data.warnings.join(', ')
			: 'None';

	multiEl.innerText = data.multi_person ? 'True' : 'False';
}

// ================= RECORD =================
export async function recordValve(valve) {
	try {
		await fetch(`/api/record/${valve}`, {
			method: 'POST',
		});

		console.log('Recording requested:', valve);
	} catch (err) {
		console.log('Record error:', err);
	}
}

// ================= INIT =================
window.onload = () => {
	const startBtn = document.getElementById('startBtn');

	startBtn.onclick = async () => {
		await startWebRTC();
		startPolling();
	};
};