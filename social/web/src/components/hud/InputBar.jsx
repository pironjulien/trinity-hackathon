import { Mic, Send, Paperclip, ChevronDown, ChevronUp, X, Check } from 'lucide-react';
import { useState, useMemo, useRef, useEffect } from 'react';
import { useCyberSound } from '../../hooks/useCyberSound';
import { useTrinityStore } from '../../stores/trinityStore';
import { getTrinityHeaders } from '../../services/angelService';
import enLocale from '../../locales/en.json';
import frLocale from '../../locales/fr.json';

const LOCALES = { en: enLocale, fr: frLocale };
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

export default function InputBar() {
    const [text, setText] = useState('');
    const [isRecording, setIsRecording] = useState(false);
    const [transcript, setTranscript] = useState('');
    const [showFileToast, setShowFileToast] = useState(false);
    const recognitionRef = useRef(null);

    const [files, setFiles] = useState([]);
    const fileInputRef = useRef(null);

    const { playType, playClick } = useCyberSound();
    const locale = useTrinityStore(state => state.locale);
    const chatMessages = useTrinityStore(state => state.chatMessages);
    const isChatCollapsed = useTrinityStore(state => state.isChatCollapsed);
    const setChatCollapsed = useTrinityStore(state => state.setChatCollapsed);
    const clearChat = useTrinityStore(state => state.clearChat);
    const addUserMessage = useTrinityStore(state => state.addUserMessage);
    const addTrinityMessage = useTrinityStore(state => state.addTrinityMessage);
    const isWaitingForReply = useTrinityStore(state => state.isWaitingForReply);
    const t = useMemo(() => LOCALES[locale]?.ui || LOCALES.en.ui, [locale]);

    // SOTA 2026: Trigger 'down' gaze video on chat focus
    const setPendingGaze = useTrinityStore(state => state.setPendingGaze);


    // SOTA 2026: Speech Recognition
    useEffect(() => {
        if (!SpeechRecognition || !isRecording) return;

        const recognition = new SpeechRecognition();
        recognition.lang = locale === 'fr' ? 'fr-FR' : 'en-US';
        recognition.continuous = true;
        recognition.interimResults = true;

        recognition.onresult = (event) => {
            let fullTranscript = '';
            for (let i = 0; i < event.results.length; i++) {
                fullTranscript += event.results[i][0].transcript;
            }
            setTranscript(fullTranscript);
        };

        recognition.onerror = () => setIsRecording(false);
        recognition.onend = () => {
            if (isRecording) {
                try { recognition.start(); } catch { setIsRecording(false); }
            }
        };

        recognitionRef.current = recognition;
        try { recognition.start(); } catch { setIsRecording(false); }

        return () => {
            recognition.stop();
            recognitionRef.current = null;
        };
    }, [isRecording, locale]);

    const convertToBase64 = (file) => {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.readAsDataURL(file);
            reader.onload = () => {
                // Remove data:image/png;base64, prefix
                const base64String = reader.result.split(',')[1];
                resolve(base64String);
            };
            reader.onerror = error => reject(error);
        });
    };

    const handleFileSelect = async (e) => {
        const selectedFiles = Array.from(e.target.files);
        const processedFiles = [];

        for (const file of selectedFiles) {
            try {
                const base64 = await convertToBase64(file);
                processedFiles.push({
                    name: file.name,
                    mimeType: file.type,
                    data: base64,
                    preview: URL.createObjectURL(file) // For UI preview
                });
            } catch (err) {
                console.error("File processing error", err);
            }
        }

        setFiles(prev => [...prev, ...processedFiles]);
        // Reset input
        e.target.value = '';
    };

    const removeFile = (index) => {
        setFiles(prev => prev.filter((_, i) => i !== index));
    };

    const sendPrompt = async (prompt) => {
        const historyForBackend = chatMessages.map(m => ({ role: m.role, content: m.content }));

        // Prepare files for backend (remove preview URL)
        const payloadFiles = files.map(f => ({
            mime_type: f.mimeType,
            data: f.data
        }));

        addUserMessage(prompt);

        // Optimistic UI for files not really needed as they are sent
        // But we clear them from UI immediately
        setFiles([]);

        try {
            const res = await fetch('/api/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', ...getTrinityHeaders() },
                body: JSON.stringify({
                    text: prompt,
                    history: historyForBackend,
                    files: payloadFiles
                })
            });
            const data = await res.json();
            addTrinityMessage(data.reply || '*Silence...*');
        } catch {
            addTrinityMessage('*Connexion perdue*');
        }
    };

    const handleSend = () => {
        if ((!text.trim() && files.length === 0) || isWaitingForReply) return;
        playClick();
        setChatCollapsed(false); // SOTA 2026: Auto-expand chat on send
        sendPrompt(text);
        setText('');
    };

    const handleMicClick = () => {
        if (!SpeechRecognition) {
            alert('Speech recognition non supporté');
            return;
        }
        if (isRecording) {
            recognitionRef.current?.stop();
            setIsRecording(false);
            if (transcript.trim()) {
                setText(prev => prev + (prev ? ' ' : '') + transcript.trim());
            }
            setTranscript('');
        } else {
            setTranscript('');
            setIsRecording(true);
        }
    };

    const handleCancelRecording = () => {
        recognitionRef.current?.stop();
        setIsRecording(false);
        setTranscript('');
    };

    const handleFileClick = () => {
        fileInputRef.current?.click();
    };

    // Derived state
    const hasMessages = chatMessages.length > 0;

    return (
        <div className="w-full max-w-2xl mx-auto mb-8 pointer-events-auto relative">
            <input
                id="trinity-file-upload"
                name="trinity-file-upload"
                type="file"
                ref={fileInputRef}
                onChange={handleFileSelect}
                className="hidden"
                multiple
                accept="image/*,application/pdf"
            />

            {/* File Previews */}
            {files.length > 0 && (
                <div className="flex gap-2 mb-2 px-2 overflow-x-auto">
                    {files.map((file, idx) => (
                        <div key={idx} className="relative group bg-black/60 border border-neon-blue/30 rounded-lg p-1 min-w-[60px] max-w-[100px] aspect-square flex items-center justify-center overflow-hidden">
                            {file.mimeType.startsWith('image/') ? (
                                <img src={file.preview} alt="preview" className="w-full h-full object-cover rounded" />
                            ) : (
                                <span className="text-xs text-white break-all text-center">{file.name}</span>
                            )}
                            <button
                                onClick={() => removeFile(idx)}
                                className="absolute top-0 right-0 bg-red-500/80 hover:bg-red-500 text-white rounded-full p-0.5 m-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
                            >
                                <X size={10} />
                            </button>
                        </div>
                    ))}
                </div>
            )}

            {/* Recording Overlay */}
            {isRecording && (
                <div className="absolute bottom-full mb-2 left-0 right-0 bg-black/90 backdrop-blur-xl border-2 border-neon-pink rounded-xl shadow-xl z-50 p-4">
                    <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                            <div className="w-3 h-3 bg-neon-pink rounded-full animate-pulse" />
                            <span className="text-neon-pink text-sm font-medium">🎤 Écoute...</span>
                        </div>
                        <button onClick={handleCancelRecording} className="p-1.5 text-white/50 hover:text-white hover:bg-white/10 rounded-full">
                            <X size={16} />
                        </button>
                    </div>
                    <div className="min-h-[40px] text-white text-lg">
                        {transcript || <span className="text-white/40 italic">Parlez maintenant...</span>}
                    </div>
                    <div className="flex gap-2 mt-3">
                        <button onClick={handleCancelRecording} className="flex-1 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg text-sm">
                            Annuler
                        </button>
                        <button
                            onClick={handleMicClick}
                            disabled={!transcript.trim()}
                            className={`flex-1 py-2 rounded-lg text-sm flex items-center justify-center gap-1
                                ${transcript.trim() ? 'bg-neon-pink hover:bg-neon-pink/80 text-white' : 'bg-white/10 text-white/30'}`}
                        >
                            <Check size={14} /> Valider
                        </button>
                    </div>
                </div>
            )}

            {/* Main Input Container */}
            <div
                onClick={() => setPendingGaze('down')}
                className="
                relative flex items-center gap-3 px-4 py-3
                bg-glass backdrop-blur-xl
                border border-neon-blue/50 rounded-xl
                shadow-[0_0_30px_rgba(0,243,255,0.15)]
                transition-all duration-300
                focus-within:border-neon-blue focus-within:shadow-[0_0_50px_rgba(0,243,255,0.3)]
            ">
                {/* Left Controls - Simplified */}
                <div className="flex items-center gap-1">
                    {/* Collapse - Only if messages exist */}
                    {hasMessages && (
                        <button
                            onClick={() => setChatCollapsed(!isChatCollapsed)}
                            className="p-2 text-neon-blue hover:text-white hover:bg-white/10 rounded-full transition-colors"
                            title={isChatCollapsed ? 'Afficher' : 'Replier'}
                        >
                            <ChevronUp
                                size={18}
                                className={`transition-transform duration-300 ${isChatCollapsed ? 'rotate-0' : 'rotate-180'}`}
                            />
                        </button>
                    )}
                </div>

                {/* Separator - Only if controls visible */}
                {hasMessages && <div className="w-px h-6 bg-white/20" />}

                {/* Prompt Indicator */}
                <span className={`text-neon-blue font-bold text-lg ${isWaitingForReply ? 'animate-spin' : 'animate-pulse'}`}>
                    {isWaitingForReply ? '◌' : '❯'}
                </span>

                {/* Text Input */}
                <input
                    id="trinity-chat-input"
                    name="trinity-chat-input"
                    type="text"
                    value={text}
                    onChange={(e) => { setText(e.target.value); playType(); }}
                    onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
                    placeholder={isWaitingForReply ? 'Trinity réfléchit...' : t.accessTrinityCore}
                    className="flex-1 bg-transparent border-none outline-none text-lg text-white placeholder-white/30 font-medium"
                    autoComplete="off"
                    disabled={isWaitingForReply || isRecording}
                />

                {/* Right Actions */}
                <div className="flex items-center gap-1">
                    <button onClick={handleFileClick} className={`p-2 rounded-full transition-colors ${files.length > 0 ? 'text-neon-pink' : 'text-white/40 hover:text-white hover:bg-white/10'}`}>
                        <Paperclip size={18} />
                    </button>
                    <button
                        onClick={handleMicClick}
                        disabled={isWaitingForReply}
                        className={`p-2 rounded-full transition-all ${isRecording ? 'text-neon-pink bg-neon-pink/20 animate-pulse' : 'text-white/40 hover:text-neon-pink hover:bg-white/10'}`}
                    >
                        <Mic size={18} />
                    </button>
                    <button
                        onClick={handleSend}
                        disabled={isWaitingForReply || (!text.trim() && files.length === 0)}
                        className={`p-2 rounded-full transition-all ${isWaitingForReply || (!text.trim() && files.length === 0) ? 'text-white/20' : 'text-neon-blue hover:text-white hover:bg-neon-blue'}`}
                    >
                        <Send size={18} />
                    </button>
                </div>

                {/* Decorative corners */}
                <div className="absolute -top-1 -left-1 w-3 h-3 border-t-2 border-l-2 border-neon-blue rounded-tl pointer-events-none" />
                <div className="absolute -bottom-1 -right-1 w-3 h-3 border-b-2 border-r-2 border-neon-blue rounded-br pointer-events-none" />
            </div>
        </div>
    );
}
