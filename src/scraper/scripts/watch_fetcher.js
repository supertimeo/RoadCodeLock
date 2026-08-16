async (video) => {
    const stream = video.captureStream();
    const recorder = new MediaRecorder(stream);
    const chunks = [];

    return await new Promise((resolve, reject) => {
        recorder.ondataavailable = e => {
            if (e.data.size > 0)
                chunks.push(e.data);
        };

        recorder.onstop = async () => {
            const blob = new Blob(chunks, {type: video.mimeType || "video/webm"});
            resolve(Array.from(new Uint8Array(await blob.arrayBuffer())));
        };

        recorder.onerror = reject;

        recorder.start();
        video.currentTime = 0;
        video.play();

        video.onended = () => recorder.stop();
    });
}