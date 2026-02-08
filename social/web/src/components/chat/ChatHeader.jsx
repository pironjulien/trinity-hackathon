import { useState } from 'react';
import { ChevronDown, ChevronUp, MessageSquarePlus, History } from 'lucide-react';
import { useTrinityStore } from '../../stores/trinityStore';

/**
 * ChatHeader - Always visible header above InputBar
 * SOTA 2026: Shows conversation controls even when no messages
 */
export default function ChatHeader() {
    const chatMessages = useTrinityStore(state => state.chatMessages);
    const conversations = useTrinityStore(state => state.conversations);
    const isChatCollapsed = useTrinityStore(state => state.isChatCollapsed);
    const setChatCollapsed = useTrinityStore(state => state.setChatCollapsed);
    const saveConversation = useTrinityStore(state => state.saveConversation);
    const loadConversation = useTrinityStore(state => state.loadConversation);
    const clearChat = useTrinityStore(state => state.clearChat);

    const [showHistory, setShowHistory] = useState(false);

    const handleNewChat = () => {
        // Save current before clearing
        if (chatMessages.length > 0) {
            saveConversation();
        }
        clearChat();
        setShowHistory(false);
    };

    const handleLoadConversation = (id) => {
        loadConversation(id);
        setShowHistory(false);
    };

    // Only show if there are messages OR conversations in history
    const hasContent = chatMessages.length > 0 || conversations.length > 0;
    if (!hasContent) return null;

    return (
        <div className="w-full max-w-2xl mx-auto mb-2 pointer-events-auto">
            <div className="flex items-center justify-between px-3 py-2 bg-black/60 backdrop-blur-md rounded-xl border border-neon-blue/30">
                {/* Collapse Toggle - Only show if messages exist */}
                {chatMessages.length > 0 ? (
                    <button
                        onClick={() => setChatCollapsed(!isChatCollapsed)}
                        className="flex items-center gap-2 text-neon-blue hover:text-white transition-colors"
                    >
                        {isChatCollapsed ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
                        <span className="text-xs font-medium uppercase tracking-wider">
                            {isChatCollapsed ? 'Afficher' : 'Replier'}
                        </span>
                    </button>
                ) : (
                    <span className="text-xs text-white/40 uppercase tracking-wider">
                        Nouvelle conversation
                    </span>
                )}

                {/* Actions */}
                <div className="flex items-center gap-2">
                    {/* History Dropdown */}
                    {conversations.length > 0 && (
                        <div className="relative">
                            <button
                                onClick={() => setShowHistory(!showHistory)}
                                className={`p-2 rounded-lg transition-colors ${showHistory ? 'bg-neon-blue/20 text-neon-blue' : 'text-white/50 hover:text-white hover:bg-white/10'}`}
                                title="Historique"
                            >
                                <History size={16} />
                            </button>

                            {showHistory && (
                                <div className="absolute right-0 top-full mt-1 w-56 bg-black/90 backdrop-blur-xl border border-neon-blue/40 rounded-lg shadow-xl z-50 overflow-hidden">
                                    {conversations.map((conv) => (
                                        <button
                                            key={conv.id}
                                            onClick={() => handleLoadConversation(conv.id)}
                                            className="w-full px-3 py-2 text-left text-sm text-white/80 hover:bg-neon-blue/20 hover:text-white transition-colors border-b border-white/10 last:border-b-0"
                                        >
                                            <div className="truncate">{conv.title}</div>
                                            <div className="text-[10px] text-white/40 mt-0.5">
                                                {new Date(conv.createdAt).toLocaleDateString()}
                                            </div>
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}

                    {/* New Chat */}
                    <button
                        onClick={handleNewChat}
                        className="p-2 text-white/50 hover:text-neon-pink hover:bg-white/10 rounded-lg transition-colors"
                        title="Nouvelle conversation"
                    >
                        <MessageSquarePlus size={16} />
                    </button>
                </div>
            </div>
        </div>
    );
}
