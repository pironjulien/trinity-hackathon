import React, { useRef, useEffect } from 'react';

const BackgroundVideo = ({ isMuted }) => {
    const videoRef = useRef(null);
    const audioRef = useRef(null);

    const [videoReady, setVideoReady] = React.useState(false);

    useEffect(() => {
        if (videoRef.current) {
            videoRef.current.muted = isMuted;
        }
    }, [isMuted]);

    const handleLoop = () => {
        if (videoRef.current) {
            videoRef.current.currentTime = 0;
            videoRef.current.play();
        }
        if (audioRef.current) {
            audioRef.current.currentTime = 0;
            audioRef.current.play();
        }
    };

    return (
        <div className="absolute inset-0 w-full h-full overflow-hidden z-0 bg-black">
            {/* SOTA 2026: Hide Android WebView native poster until video explicitly plays */}
            {/* Native controls hiding */}
            <style>{`
                video::-webkit-media-controls { display: none !important; }
                video::-webkit-media-controls-enclosure { display: none !important; }
            `}</style>

            {!videoReady && <div className="absolute inset-0 z-50 bg-black" />}

            {/* SOTA 2026: Dual Asset Architecture (Video w/ SFX + Isolated Music) */}
            <video
                ref={videoRef}
                className="w-full h-full object-cover opacity-80 object-[52.5%_center]"
                autoPlay
                muted={isMuted}
                playsInline
                loop={false}
                onEnded={handleLoop}
                onPlay={() => setVideoReady(true)}
            >
                <source src="/videos/author.webm" type="video/webm" />
            </video>

            {/* Background Ambience / Music */}
            <audio
                ref={audioRef}
                src="/videos/music.webm"
                autoPlay
                muted={isMuted}
            />

            {/* Cinematic Overlay: Vignette + Color Grade */}
            <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/40 pointer-events-none" />
            <div className="absolute inset-0 bg-blue-900/10 mix-blend-overlay pointer-events-none" />
        </div>
    );
};

export default BackgroundVideo;
