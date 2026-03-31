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
    frame = await self.track.recv()

    img = frame.to_ndarray(format="bgr24")

    try:
        processed_frame, metadata = self.processor.process(img)

        # fallback if processing fails or returns invalid output
        if processed_frame is None:
            print("processed_frame is None, using original frame")
            processed_frame = img

        if len(processed_frame.shape) != 3:
            print("Invalid frame shape, using original frame:", processed_frame.shape)
            processed_frame = img

        if processed_frame.shape[2] != 3:
            print("Invalid channel count, using original frame:", processed_frame.shape)
            processed_frame = img

        if processed_frame.dtype != img.dtype:
            print("Invalid dtype, converting:", processed_frame.dtype)
            processed_frame = processed_frame.astype(img.dtype)

        state.update_metadata(metadata)

    except Exception as e:
        print("Processor error:", e)
        processed_frame = img

    new_frame = av.VideoFrame.from_ndarray(processed_frame, format="bgr24")
    new_frame.pts = frame.pts
    new_frame.time_base = frame.time_base

    return new_frame