import { useMemo } from 'react';

/**
 * ChatBubble - Message bubble component for the messenger interface.
 * SOTA 2026: Outline-only style - dark transparent bg with colored borders
 * User messages on the right (pink border), Trinity on the left (cyan border).
 */
export default function ChatBubble({ message, isUser, timestamp }) {
    const time = useMemo(() => {
        if (!timestamp) return '';
        const d = new Date(timestamp);
        return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }, [timestamp]);

    return (
        <div className={`flex w-full ${isUser ? 'justify-end' : 'justify-start'} mb-3`}>
            <div
                className={`
                    relative max-w-[75%] px-4 py-3 rounded-2xl
                    backdrop-blur-md border-2 shadow-lg
                    bg-black/85
                    ${isUser
                        ? 'border-neon-pink text-white rounded-br-sm'
                        : 'border-neon-blue text-white rounded-bl-sm'
                    }
                `}
                style={{
                    // SOTA 2026: Subtle glow effect
                    textShadow: isUser
                        ? '0 0 8px rgba(255,0,127,0.6)'
                        : '0 0 8px rgba(0,243,255,0.8), 0 0 2px rgba(0,243,255,0.6)'
                }}
            >
                {/* Message Content */}
                <p className="text-sm leading-relaxed whitespace-pre-wrap font-medium">{message}</p>

                {/* Timestamp */}
                <span className={`
                    text-[10px] opacity-60 mt-1 block
                    ${isUser ? 'text-right' : 'text-left'}
                `}>
                    {time}
                </span>

                {/* Decorative Border Glow */}
                <div className={`
                    absolute -inset-[2px] rounded-2xl opacity-30 blur-md -z-10
                    ${isUser ? 'bg-neon-pink' : 'bg-neon-blue'}
                `} />
            </div>
        </div>
    );
}
