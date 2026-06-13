import React, { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, ChevronLeft, ChevronRight } from 'lucide-react';

interface Source {
  type?: string;
  label?: string;
  excerpt?: string;
}

interface SuggestedAction {
  type?: string;
  label?: string;
  text?: string;
}

interface Message {
  role: 'user' | 'assistant';
  text: string;
  sources?: Source[];
  suggestedActions?: SuggestedAction[];
}

interface V2ChatPanelProps {
  caseContext?: {
    id: string;
    name: string;
    target: string;
    riskScore: number;
    officer: string;
  };
  isExpanded?: boolean;
  onToggleExpand?: () => void;
}

export default function V2ChatPanel({ caseContext, isExpanded = true, onToggleExpand }: V2ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      text: 'Authorized Sentry Platform Secure Assistant live. Ask me to cross-reference container logs, evaluate routing anomalies, or draft a DOJ referral narrative.',
    },
  ]);
  const [currentMessage, setCurrentMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const chatRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSendMessage = async () => {
    if (!currentMessage.trim()) return;

    const userText = currentMessage;
    setCurrentMessage('');
    setMessages(prev => [...prev, { role: 'user', text: userText }]);
    setLoading(true);

    try {
      const response = await fetch('/api/agent/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: userText,
          conversationHistory: messages.map(m => ({ role: m.role, content: m.text })),
          userRole: 'cbp_officer',
          contextType: caseContext ? 'shipment' : undefined,
          contextId: caseContext?.id,
          context: caseContext,
        }),
      });

      const data = await response.json();
      setMessages(prev => [...prev, {
        role: 'assistant',
        text: data.answer || data.text || 'No response received.',
        sources: data.sources || [],
        suggestedActions: data.suggestedActions || data.suggested_actions || [],
      }]);
    } catch (error) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        text: 'Error: Unable to connect to AI service. Please try again.',
      }]);
    } finally {
      setLoading(false);
    }
  };

  // Collapsed view
  if (!isExpanded) {
    return (
      <div className="w-16 bg-white border-l border-[#D0D7DE] flex flex-col h-full shadow-lg items-center py-2">
        <button
          onClick={onToggleExpand}
          className="p-2 hover:bg-slate-100 rounded transition-colors"
          title="Expand Assistant"
        >
          <ChevronLeft className="w-5 h-5 text-[#112E51]" />
        </button>
        <div className="flex-1" />
        <div className="h-10 w-10 flex items-center justify-center hover:bg-slate-100 rounded mb-2 cursor-pointer" title="Assistant">
          <Sparkles className="w-5 h-5 text-cyan-500" />
        </div>
      </div>
    );
  }

  // Expanded view
  return (
    <div className="w-80 bg-white border-l border-[#D0D7DE] flex flex-col h-full shadow-lg">
      {/* Header */}
      <div className="p-3 border-b border-[#D0D7DE] bg-[#F7F9FC] flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <Sparkles className="h-4 w-4 text-cyan-500" />
          <span className="text-xs font-bold text-[#112E51] uppercase font-mono">Assistant</span>
        </div>
        <button
          onClick={onToggleExpand}
          className="p-1 hover:bg-slate-200 rounded transition-colors"
          title="Collapse Assistant"
        >
          <ChevronRight className="w-4 h-4 text-slate-600" />
        </button>
      </div>

      {/* Chat Messages */}
      <div
        ref={chatRef}
        className="flex-1 overflow-y-auto p-3 space-y-3"
      >
        {messages.map((msg, idx) => (
          <div key={idx}>
            <div
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[85%] px-3 py-2 rounded-lg text-xs leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-[#005EA2] text-white rounded-br-none'
                    : 'bg-[#F7F9FC] border border-[#D0D7DE] text-[#1B1B1B] rounded-bl-none'
                }`}
              >
                {msg.text}
              </div>
            </div>
            {msg.sources && msg.sources.length > 0 && (
              <div className="flex justify-start mt-1 px-1">
                <div className="text-[9px] text-slate-500 font-mono">
                  Sources: {msg.sources.map(s => s.label || s.type || String(s)).join(', ')}
                </div>
              </div>
            )}
            {msg.suggestedActions && msg.suggestedActions.length > 0 && (
              <div className="flex justify-start mt-1 px-1 flex-wrap gap-1">
                {msg.suggestedActions.slice(0, 3).map((action, i) => (
                  <button
                    key={i}
                    onClick={() => setCurrentMessage(action.text || action.label || '')}
                    className="text-[9px] bg-slate-100 hover:bg-slate-200 border border-slate-300 text-slate-600 rounded px-1.5 py-0.5 font-mono cursor-pointer transition-colors"
                  >
                    {action.label || action.text}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-[#F7F9FC] border border-[#D0D7DE] px-3 py-2 rounded-lg rounded-bl-none">
              <div className="flex space-x-1">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="p-3 border-t border-[#D0D7DE] flex space-x-2">
        <input
          type="text"
          value={currentMessage}
          onChange={(e) => setCurrentMessage(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleSendMessage();
            }
          }}
          placeholder="Ask a question..."
          className="flex-1 bg-[#F7F9FC] border border-[#D0D7DE] rounded px-2.5 py-1.5 text-xs focus:outline-none focus:border-[#005EA2] focus:ring-1 focus:ring-[#005EA2]"
          disabled={loading}
        />
        <button
          onClick={handleSendMessage}
          disabled={loading || !currentMessage.trim()}
          className="px-2.5 py-1.5 bg-[#005EA2] hover:bg-[#0076D6] disabled:bg-gray-300 text-white rounded text-xs font-bold cursor-pointer transition-all"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}
