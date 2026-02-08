import { useState, useEffect, useRef } from 'react';
import { Mic, X, Check } from 'lucide-react';

// SOTA 2026: Web Speech API wrapper
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

/**
 * VoiceModal - Modal for voice-to-text with live transcription
 * SOTA 2026: Real-time feedback with validate/cancel actions
 */
export default function VoiceModal({ isOpen, onClose, onConfirm, locale = 'fr' }) {
    const [transcript, setTranscript] = useState('');
    const [isListening, setIsListening] = useState(false);
    const recognitionRef = useRef(null);

    useEffect(() => {
        if (!SpeechRecognition || !isOpen) return;

        const recognition = new SpeechRecognition();
        recognition.lang = locale === 'fr' ? 'fr-FR' : 'en-US';
        recognition.continuous = true;
        recognition.interimResults = true;

        recognition.onresult = (event) => {
            let finalTranscript = '';
            let interimTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; i++) {
                const result = event.results[i];
                if (result.isFinal) {
                    finalTranscript += result[0].transcript;
                } else {
                    interimTranscript += result[0].transcript;
                }
            }

            setTranscript(prev => {
                // If we have final results, append them
                if (finalTranscript) {
                    return (prev + ' ' + finalTranscript).trim();
                }
                // For interim, show current + interim
                return prev;
            });
        };

        recognition.onerror = (event) => {
            console.error('Speech recognition error:', event.error);
            if (event.error === 'no-speech') {
                // Continue listening
            } else {
                setIsListening(false);
            }
        };

        recognition.onend = () => {
            // Auto-restart if still listening
            if (isListening && recognitionRef.current) {
                try {
                    recognitionRef.current.start();
                } catch {
                    setIsListening(false);
                }
            }
        };

        recognitionRef.current = recognition;

        // Auto-start on open
        try {
            recognition.start();
            setIsListening(true);
        } catch {
            setIsListening(false);
        }

        return () => {
            recognition.stop();
            setIsListening(false);
        };
    }, [isOpen, locale]);

    const handleConfirm = () => {
        if (recognitionRef.current) {
            recognitionRef.current.stop();
        }
        setIsListening(false);
        onConfirm(transcript.trim());
        setTranscript('');
    };

    const handleCancel = () => {
        if (recognitionRef.current) {
            recognitionRef.current.stop();
        }
        setIsListening(false);
        setTranscript('');
        onClose();
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center pointer-events-auto">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/70 backdrop-blur-sm"
                onClick={handleCancel}
            />

            {/* Modal */}
            <div className="relative w-full max-w-lg mx-4 bg-black/90 border-2 border-neon-pink rounded-2xl shadow-[0_0_40px_rgba(255,0,127,0.3)] overflow-hidden">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-neon-pink/30">
                    <div className="flex items-center gap-3">
                        <div className={`p-2 rounded-full ${isListening ? 'bg-neon-pink/20 animate-pulse' : 'bg-white/10'}`}>
                            <Mic size={24} className={isListening ? 'text-neon-pink' : 'text-white/50'} />
                        </div>
                        <span className="text-white font-medium">
                            {isListening ? '🎤 Écoute en cours...' : '🎤 Micro'}
                        </span>
                    </div>
                    <button
                        onClick={handleCancel}
                        className="p-2 text-white/50 hover:text-white hover:bg-white/10 rounded-full transition-colors"
                    >
                        <X size={20} />
                    </button>
                </div>

                {/* Transcript Area */}
                <div className="px-6 py-8 min-h-[150px]">
                    {transcript ? (
                        <p className="text-white text-lg leading-relaxed">{transcript}</p>
                    ) : (
                        <p className="text-white/40 text-lg italic text-center">
                            {isListening ? 'Parlez maintenant...' : 'En attente...'}
                        </p>
                    )}
                </div>

                {/* Waveform Indicator */}
                {isListening && (
                    <div className="flex justify-center gap-1 pb-4">
                        {[...Array(5)].map((_, i) => (
                            <div
                                key={i}
                                className="w-1 bg-neon-pink rounded-full animate-pulse"
                                style={{
                                    height: `${20 + Math.random() * 20}px`,
                                    animationDelay: `${i * 0.1}s`
                                }}
                            />
                        ))}
                    </div>
                )}

                {/* Actions */}
                <div className="flex gap-3 px-6 py-4 border-t border-neon-pink/30">
                    <button
                        onClick={handleCancel}
                        className="flex-1 py-3 px-4 bg-white/10 hover:bg-white/20 text-white rounded-xl transition-colors font-medium"
                    >
                        Annuler
                    </button>
                    <button
                        onClick={handleConfirm}
                        disabled={!transcript.trim()}
                        className={`flex-1 py-3 px-4 rounded-xl transition-colors font-medium flex items-center justify-center gap-2
                            ${transcript.trim()
                                ? 'bg-neon-pink hover:bg-neon-pink/80 text-white'
                                : 'bg-white/10 text-white/30 cursor-not-allowed'
                            }`}
                    >
                        <Check size={18} />
                        Valider
                    </button>
                </div>
            </div>
        </div>
    );
}
