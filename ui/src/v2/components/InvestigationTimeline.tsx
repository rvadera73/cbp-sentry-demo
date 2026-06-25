import React from 'react';
import { AlertTriangle, Flag, Shield, Send, CheckCircle } from 'lucide-react';

interface TimelineEvent {
  event_id: string;
  event_type: 'Risk Escalation' | 'Flag Detected' | 'Pattern Matched' | 'Review Started' | 'Referral Sent';
  title: string;
  description: string;
  timestamp: string;
  severity?: 'critical' | 'high' | 'medium' | 'low';
  details?: Record<string, string>;
}

interface InvestigationTimelineProps {
  caseId: string;
  events?: TimelineEvent[];
  onEventClick?: (event: TimelineEvent) => void;
}

function getEventIcon(type: string) {
  switch (type) {
    case 'Risk Escalation':
      return <AlertTriangle className="w-5 h-5 text-[#D83933]" />;
    case 'Flag Detected':
      return <Flag className="w-5 h-5 text-orange-600" />;
    case 'Pattern Matched':
      return <Shield className="w-5 h-5 text-[#0076D6]" />;
    case 'Review Started':
      return <AlertTriangle className="w-5 h-5 text-amber-600" />;
    case 'Referral Sent':
      return <Send className="w-5 h-5 text-green-600" />;
    default:
      return <CheckCircle className="w-5 h-5 text-slate-400" />;
  }
}

function getEventColor(type: string): string {
  switch (type) {
    case 'Risk Escalation':
      return 'bg-red-50 border-red-200';
    case 'Flag Detected':
      return 'bg-orange-50 border-orange-200';
    case 'Pattern Matched':
      return 'bg-blue-50 border-blue-200';
    case 'Review Started':
      return 'bg-amber-50 border-amber-200';
    case 'Referral Sent':
      return 'bg-green-50 border-green-200';
    default:
      return 'bg-slate-50 border-slate-200';
  }
}

const FIXTURE_EVENTS: TimelineEvent[] = [
  {
    event_id: 'EVT-001',
    event_type: 'Risk Escalation',
    title: 'Risk Score Increased to 65%',
    description: 'Prior EAPA determination detected for shipper entity',
    timestamp: '2026-05-27 14:32',
    severity: 'high',
    details: { reason: 'EAPA match', change: '45% → 65%' },
  },
  {
    event_id: 'EVT-002',
    event_type: 'Flag Detected',
    title: 'Director Shared with High-Risk Entity',
    description: 'Greenfield HK shares director with SunPath US (prior sanctions case)',
    timestamp: '2026-05-27 13:15',
    severity: 'high',
    details: { director: 'John Smith', related_cases: '3' },
  },
  {
    event_id: 'EVT-003',
    event_type: 'Pattern Matched',
    title: 'Transshipment Hub Pattern Detected',
    description: 'Multi-hop routing via Singapore consolidation center identified',
    timestamp: '2026-05-26 10:45',
    severity: 'medium',
    details: { pattern: 'VN → HK → SG → US', frequency: '12 shipments/month' },
  },
  {
    event_id: 'EVT-004',
    event_type: 'Review Started',
    title: 'Investigation Opened',
    description: 'Case opened for detailed entity and shipment analysis',
    timestamp: '2026-05-25 09:00',
    severity: 'low',
    details: { opened_by: 'Officer Jane Doe', reason: 'Routine screening' },
  },
];

export default function InvestigationTimeline({
  caseId,
  events = FIXTURE_EVENTS,
  onEventClick,
}: InvestigationTimelineProps) {
  return (
    <div className="space-y-3">
      {/* Timeline */}
      <div className="relative">
        {events.map((event, index) => (
          <div key={event.event_id} className="flex gap-3 pb-4 last:pb-0">
            {/* Timeline Line + Icon */}
            <div className="flex flex-col items-center">
              <div className="p-1.5 bg-white border-2 border-[#D0D7DE] rounded-full">
                {getEventIcon(event.event_type)}
              </div>
              {index < events.length - 1 && (
                <div className="w-1 h-12 bg-[#D0D7DE] mt-1" />
              )}
            </div>

            {/* Event Card */}
            <div
              onClick={() => onEventClick?.(event)}
              className={`flex-1 p-3 border rounded-sm cursor-pointer transition-all hover:shadow-md ${getEventColor(
                event.event_type
              )}`}
            >
              <div className="flex items-start justify-between mb-1">
                <div className="flex-1">
                  <h4 className="text-[9px] font-bold text-[#0B1F33] uppercase">{event.event_type}</h4>
                  <h3 className="text-[10px] font-bold text-[#0B1F33] mt-0.5">{event.title}</h3>
                </div>
                <span className="text-[8px] text-[#5C5C5C] font-mono whitespace-nowrap ml-2">{event.timestamp}</span>
              </div>

              <p className="text-[9px] text-[#5C5C5C] mb-2">{event.description}</p>

              {/* Event Details */}
              {event.details && (
                <div className="grid grid-cols-2 gap-2 bg-white bg-opacity-50 p-2 rounded text-[8px]">
                  {Object.entries(event.details).map(([key, value]) => (
                    <div key={key}>
                      <div className="font-bold text-[#5C5C5C] capitalize">{key}</div>
                      <div className="text-[#0B1F33]">{value}</div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
