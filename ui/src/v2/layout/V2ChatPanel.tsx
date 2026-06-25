import React, { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, ChevronLeft, ChevronRight, Database, AlertCircle, Database as DbIcon } from 'lucide-react';

interface SourceCard {
  tool: string;
  summary: string;
  hit: boolean;
}

interface Message {
  role: 'user' | 'assistant';
  text: string;
  sources?: SourceCard[];
  isDone?: boolean;
}

interface V2ChatPanelProps {
  caseContext?: {
    id: string;
    name: string;
    target: string;
    riskScore: number;
    officer: string;
    shipmentId?: string;
  };
  isExpanded?: boolean;
  onToggleExpand?: () => void;
  currentPage?: string;
  selectedEntity?: string;
}

export default function V2ChatPanel({
  caseContext,
  isExpanded = true,
  onToggleExpand,
  currentPage = 'dashboard',
  selectedEntity
}: V2ChatPanelProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      text: 'Authorized Sentry Platform Secure Assistant live. Ask me about active cases, entity intelligence, risk scores, corridors, or referral packages.',
      sources: []
    },
  ]);
  const [currentMessage, setCurrentMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const chatRef = useRef<HTMLDivElement>(null);
  const sessionIdRef = useRef<string>(generateUUID());

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

    // Add placeholder assistant message for streaming
    setMessages(prev => [...prev, {
      role: 'assistant',
      text: '',
      sources: [],
      isDone: false
    }]);

    try {
      const params = new URLSearchParams({
        message: userText,
        session_id: sessionIdRef.current!,
        page: currentPage,
        ...(caseContext?.shipmentId && { shipment_id: caseContext.shipmentId }),
        ...(caseContext?.target && { entity: caseContext.target }),
        ...(selectedEntity && { entity: selectedEntity }),
      });

      const response = await fetch(`/api/gemini/assistant/stream?${params}`, {
        method: 'GET',
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let currentText = '';
      let currentSources: SourceCard[] = [];

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const event = JSON.parse(line.substring(6));

                if (event.type === 'text') {
                  currentText += event.content;
                  // Update message incrementally
                  setMessages(prev => {
                    const updated = [...prev];
                    updated[updated.length - 1] = {
                      ...updated[updated.length - 1],
                      text: currentText,
                    };
                    return updated;
                  });
                } else if (event.type === 'source') {
                  const source: SourceCard = {
                    tool: event.tool,
                    summary: event.summary,
                    hit: event.hit,
                  };
                  currentSources.push(source);
                  setMessages(prev => {
                    const updated = [...prev];
                    updated[updated.length - 1] = {
                      ...updated[updated.length - 1],
                      sources: [...currentSources],
                    };
                    return updated;
                  });
                } else if (event.type === 'done') {
                  setMessages(prev => {
                    const updated = [...prev];
                    updated[updated.length - 1] = {
                      ...updated[updated.length - 1],
                      isDone: true,
                    };
                    return updated;
                  });
                } else if (event.type === 'error') {
                  setMessages(prev => [...prev, {
                    role: 'assistant',
                    text: `Error: ${event.content}`,
                    sources: [],
                    isDone: true
                  }]);
                }
              } catch (e) {
                // Skip non-JSON lines
              }
            }
          }
        }
      }
    } catch (error) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        text: 'Error: Unable to connect to AI service. Please try again.',
        sources: [],
        isDone: true
      }]);
    } finally {
      setLoading(false);
    }
  };

  function generateUUID(): string {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
      const r = Math.random() * 16 | 0;
      const v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }

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
                className={`max-w-[85%] px-3 py-2 rounded-lg text-xs leading-relaxed whitespace-pre-wrap ${
                  msg.role === 'user'
                    ? 'bg-[#005EA2] text-white rounded-br-none'
                    : 'bg-[#F7F9FC] border border-[#D0D7DE] text-[#1B1B1B] rounded-bl-none'
                }`}
              >
                {msg.text}
              </div>
            </div>
            {msg.sources && msg.sources.length > 0 && (
              <div className="flex justify-start mt-2 px-1 flex-wrap gap-2">
                {msg.sources.map((source, sidx) => (
                  <div
                    key={sidx}
                    className={`inline-flex items-center space-x-1 px-2 py-1 rounded text-[8px] font-mono border ${
                      source.hit
                        ? 'bg-blue-50 border-blue-200 text-blue-700'
                        : 'bg-gray-50 border-gray-200 text-gray-700'
                    }`}
                    title={source.summary}
                  >
                    {source.hit && source.summary.includes('HIT') && (
                      <AlertCircle className="w-3 h-3" />
                    )}
                    {!source.hit && source.summary.includes('Error') && (
                      <AlertCircle className="w-3 h-3 text-red-500" />
                    )}
                    <DbIcon className="w-3 h-3" />
                    <span className="truncate max-w-[120px]">{source.tool}: {source.summary.substring(0, 40)}</span>
                  </div>
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
