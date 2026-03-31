import av
from aiortc import VideoStreamTrack
from state import state
from processor import Processor


class VideoProcessorTrack(VideoStreamTrack):
    """
    Receives video from browser → processes it → sends back processed frames
    """

    def __init__(self, track):
        super().__init__()
        self.track = track

        # Each connection gets its own processor instance
        self.processor = Processor()

    async def recv(self):
        """
        This is called for EVERY frame (critical path)
        """

        # 1. Receive frame from browser
        frame = await self.track.recv()
        # print("Frame Received")

        # 2. Convert to numpy (OpenCV format)
        img = frame.to_ndarray(format="bgr24")

        # 3. Process using your pipeline
        processed_frame, metadata = self.processor.process(img)

        # (optional) attach metadata later via data channel
        # for now we ignore it here
        state.update_metadata(metadata)
        # 4. Convert back to WebRTC frame
        new_frame = av.VideoFrame.from_ndarray(processed_frame, format="bgr24")

        # Preserve timing (VERY IMPORTANT)
        new_frame.pts = frame.pts
        new_frame.time_base = frame.time_base

        return new_frame