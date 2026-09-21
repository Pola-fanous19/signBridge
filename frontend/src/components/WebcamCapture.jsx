import React, { useRef, useEffect, useState, useCallback } from 'react';
import { Holistic, VERSION } from '@mediapipe/holistic';
import { Camera } from '@mediapipe/camera_utils';

export default function WebcamCapture({ onHolisticResults, onMhrReceived }) {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const holisticRef = useRef(null);
  const cameraRef = useRef(null);
  const mediaRecorderRef = useRef(null);

  const [hasCamera, setHasCamera] = useState(false);
  const [cameraError, setCameraError] = useState(null);
  const [recordedChunks, setRecordedChunks] = useState([]);
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [word, setWord] = useState('');
  const [enableLiveMimicry, setEnableLiveMimicry] = useState(false);
  const [statusMsg, setStatusMsg] = useState(null);

  // 1. Native Camera Stream Initialization
  useEffect(() => {
    let active = true;

    async function setupCamera() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
          audio: false
        });
        if (!active) {
          stream.getTracks().forEach(t => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
        setHasCamera(true);
        setCameraError(null);
      } catch (err) {
        console.error("Webcam access error:", err);
        if (active) {
          setCameraError("Camera access denied or unavailable: " + err.message);
        }
      }
    }

    setupCamera();

    return () => {
      active = false;
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(t => t.stop());
        streamRef.current = null;
      }
    };
  }, []);

  // 2. Optional MediaPipe Holistic Live Mimicry
  useEffect(() => {
    if (!enableLiveMimicry || !hasCamera) {
      if (cameraRef.current) {
        try { cameraRef.current.stop(); } catch(e) {}
        cameraRef.current = null;
      }
      if (holisticRef.current) {
        try { holisticRef.current.close(); } catch(e) {}
        holisticRef.current = null;
      }
      return;
    }

    let hInstance = null;
    try {
      hInstance = new Holistic({
        locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/holistic@${VERSION}/${file}`
      });

      hInstance.setOptions({
        modelComplexity: 0,
        smoothLandmarks: true,
        enableSegmentation: false,
        smoothSegmentation: false,
        refineFaceLandmarks: false,
        minDetectionConfidence: 0.6,
        minTrackingConfidence: 0.6
      });

      hInstance.onResults((results) => {
        if (onHolisticResults) onHolisticResults(results);
      });

      holisticRef.current = hInstance;

      if (videoRef.current) {
        cameraRef.current = new Camera(videoRef.current, {
          onFrame: async () => {
            if (videoRef.current && holisticRef.current) {
              await holisticRef.current.send({ image: videoRef.current });
            }
          },
          width: 480,
          height: 360
        });
        cameraRef.current.start();
      }
    } catch (err) {
      console.warn("MediaPipe initialization skipped or failed:", err);
    }

    return () => {
      if (cameraRef.current) {
        try { cameraRef.current.stop(); } catch(e) {}
        cameraRef.current = null;
      }
      if (holisticRef.current) {
        try { holisticRef.current.close(); } catch(e) {}
        holisticRef.current = null;
      }
    };
  }, [enableLiveMimicry, hasCamera, onHolisticResults]);

  // 3. Recording Controls
  const handleStartCaptureClick = useCallback(() => {
    if (!streamRef.current) return;
    setIsRecording(true);
    setRecordedChunks([]);
    try {
      const recorder = new MediaRecorder(streamRef.current, { mimeType: 'video/webm' });
      recorder.addEventListener('dataavailable', ({ data }) => {
        if (data.size > 0) {
          setRecordedChunks((prev) => prev.concat(data));
        }
      });
      recorder.start();
      mediaRecorderRef.current = recorder;
    } catch (err) {
      console.error("MediaRecorder start error:", err);
      setIsRecording(false);
    }
  }, []);

  const handleStopCaptureClick = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
  }, []);

  // 4. Upload to MHR Server
  const handleUpload = useCallback(async () => {
    if (recordedChunks.length && word) {
      setIsProcessing(true);
      const blob = new Blob(recordedChunks, { type: 'video/webm' });
      const formData = new FormData();
      formData.append('video', blob, `${word}.webm`);
      formData.append('word', word);

      try {
        const configRes = await fetch('/config.json');
        const config = await configRes.json();
        const colabUrl = config.colabUrl.replace(/\/$/, "");

        const response = await fetch(`${colabUrl}/api/process-video`, {
          method: 'POST',
          body: formData,
        });

        if (response.ok) {
          const data = await response.json();
          if (onMhrReceived && data.frames) {
            onMhrReceived(data.frames, word);
          }
          setStatusMsg(`✓ Successfully processed MHR mocap for ${word}!`);
          setTimeout(() => setStatusMsg(null), 5000);
          setRecordedChunks([]);
        } else {
          const errText = await response.text();
          setStatusMsg(`Error processing video: ${errText}`);
        }
      } catch (error) {
        setStatusMsg(`Upload failed: ${error.message}`);
      } finally {
        setIsProcessing(false);
      }
    }
  }, [recordedChunks, word, onMhrReceived]);

  return (
    <div style={{ position: 'absolute', bottom: 10, right: 10, zIndex: 10, display: 'flex', flexDirection: 'column', gap: 10 }}>
      <div style={{ border: '2px solid #88aaff', borderRadius: 8, overflow: 'hidden', position: 'relative', width: 320, height: 240, background: '#111' }}>
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          style={{ width: '100%', height: '100%', objectFit: 'cover', transform: 'scaleX(-1)' }}
        />
        <div style={{ position: 'absolute', top: 5, left: 5, background: enableLiveMimicry ? '#2e7d32' : 'rgba(0,0,0,0.6)', color: 'white', padding: '2px 6px', borderRadius: 4, fontSize: '0.75rem' }}>
          {cameraError ? 'Camera Error' : enableLiveMimicry ? '● Live Avatar Active' : 'Camera Ready'}
        </div>
      </div>

      <div style={{ background: '#fff', padding: 10, borderRadius: 8, boxShadow: '0 2px 8px rgba(0,0,0,0.2)', display: 'flex', flexDirection: 'column', gap: 8, width: 320 }}>
        {cameraError && (
          <div style={{ color: 'red', fontSize: '0.75rem', wordBreak: 'break-word' }}>
            {cameraError}
          </div>
        )}

        {statusMsg && (
          <div style={{ color: statusMsg.startsWith('✓') ? '#2e7d32' : '#d32f2f', fontSize: '0.8rem', fontWeight: 'bold' }}>
            {statusMsg}
          </div>
        )}

        <label style={{ fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', color: '#333' }}>
          <input
            type="checkbox"
            checked={enableLiveMimicry}
            onChange={(e) => setEnableLiveMimicry(e.target.checked)}
          />
          Live Avatar Mirroring (MediaPipe)
        </label>

        <input
          type="text"
          placeholder="Word to record (e.g. THUMBS_UP)"
          value={word}
          onChange={(e) => setWord(e.target.value.toUpperCase())}
          style={{ padding: '6px' }}
        />

        <div style={{ display: 'flex', gap: 8 }}>
          {isRecording ? (
            <button onClick={handleStopCaptureClick} style={{ flex: 1, background: 'red', color: 'white', padding: '8px', border: 'none', borderRadius: 4, cursor: 'pointer' }}>
              Stop Recording
            </button>
          ) : (
            <button onClick={handleStartCaptureClick} disabled={!hasCamera} style={{ flex: 1, background: hasCamera ? '#4CAF50' : '#ccc', color: 'white', padding: '8px', border: 'none', borderRadius: 4, cursor: hasCamera ? 'pointer' : 'not-allowed' }}>
              Start Record
            </button>
          )}
        </div>

        {recordedChunks.length > 0 && !isRecording && (
          <button
            onClick={handleUpload}
            disabled={isProcessing || !word}
            style={{
              background: (isProcessing || !word) ? '#ccc' : '#2196F3',
              color: 'white',
              padding: '8px',
              border: 'none',
              borderRadius: 4,
              cursor: (isProcessing || !word) ? 'not-allowed' : 'pointer'
            }}
          >
            {isProcessing ? 'Processing Mocap Data...' : 'Upload & Process JSON'}
          </button>
        )}
      </div>
    </div>
  );
}
