import { useRef, useEffect } from 'react';
import ChatBubble from './ChatBubble';
import { useTrinityStore } from '../../stores/trinityStore';

/**
 * ChatContainer - Scrollable container for chat messages.
 * SOTA 2026: Pure message display, header logic moved to ChatHeader
 */
export default function ChatContainer() {
    const chatMessages = useTrinityStore(state => state.chatMessages);
    const isChatCollapsed = useTrinityStore(state => state.isChatCollapsed);
    const scrollRef = useRef(null);

    // Auto-scroll to bottom on new messages
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [chatMessages]);

    // Don't render if no messages
    if (!chatMessages || chatMessages.length === 0) {
        return null;
    }

    return (
        <div className={`w-full max-w-2xl mx-auto pointer-events-auto transition-[grid-template-rows] duration-300 ease-in-out grid ${isChatCollapsed ? 'grid-rows-[0fr]' : 'grid-rows-[1fr]'}`}>
            <div className="overflow-hidden">
                <div
                    ref={scrollRef}
                    className="
                        relative overflow-y-auto pr-2 mb-2
                        max-h-[80vh]
                        scrollbar-thin scrollbar-thumb-white/20 scrollbar-track-transparent
                    "
                    style={{
                        maskImage: 'linear-gradient(to bottom, transparent 0px, black 20px, black calc(100% - 40px), transparent 100%)',
                        WebkitMaskImage: 'linear-gradient(to bottom, transparent 0px, black 20px, black calc(100% - 40px), transparent 100%)'
                    }}
                >
                    {/* Messages */}
                    <div className="flex flex-col justify-end min-h-full px-2 pt-4 pb-4">
                        {chatMessages.map((msg, idx) => (
                            <ChatBubble
                                key={`${msg.ts}-${idx}`}
                                message={msg.content}
                                isUser={msg.role === 'user'}
                                timestamp={msg.ts}
                            />
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
