import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Loader } from 'lucide-react';
import ComprehensiveReferralViewer from '../components/ComprehensiveReferralViewer';
import { api } from '../../services/api';

export default function ReferralViewerPage() {
  const { shipmentId, referralId } = useParams();
  const navigate = useNavigate();
  const [referral, setReferral] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchReferral = async () => {
      try {
        setLoading(true);
        setError(null);

        let response;
        if (referralId) {
          // Fetch specific referral by ID
          response = await fetch(`/api/referrals/${referralId}`);
        } else if (shipmentId) {
          // Fetch referral for shipment (will generate if not exists)
          response = await fetch(`/api/referrals/shipment/${shipmentId}`);
        } else {
          throw new Error('No referral or shipment ID provided');
        }

        if (!response.ok) {
          throw new Error(`Failed to load referral: ${response.statusText}`);
        }

        const data = await response.json();
        if (data.status === 'success' && data.referral) {
          setReferral(data.referral);
        } else {
          throw new Error(data.detail || 'Unknown error');
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    };

    fetchReferral();
  }, [shipmentId, referralId]);

  const handleAnnotationSave = async (annotations: any[]) => {
    if (!referral) return;

    try {
      const response = await fetch(`/api/referrals/${referral.referral_id}/annotations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(annotations),
      });

      if (!response.ok) {
        throw new Error('Failed to save annotations');
      }
    } catch (err) {
      console.error('Error saving annotations:', err);
    }
  };

  if (loading) {
    return (
      <div className="w-full h-screen flex items-center justify-center bg-[#F7F9FC]">
        <div className="text-center">
          <Loader className="w-8 h-8 animate-spin text-[#0B1F33] mx-auto mb-3" />
          <p className="text-slate-600 font-semibold">Generating comprehensive referral package...</p>
          <p className="text-xs text-slate-500 mt-1">This may take 30-60 seconds for AI narratives</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="w-full h-screen flex items-center justify-center bg-[#F7F9FC]">
        <div className="bg-white p-6 rounded-lg border border-red-300 max-w-md">
          <h2 className="text-lg font-bold text-red-700 mb-2">Error Loading Referral</h2>
          <p className="text-sm text-slate-700 mb-4">{error}</p>
          <button
            onClick={() => navigate(-1)}
            className="px-4 py-2 bg-[#0B1F33] text-white rounded text-sm font-bold hover:bg-[#005EA2]"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  if (!referral) {
    return (
      <div className="w-full h-screen flex items-center justify-center bg-[#F7F9FC]">
        <p className="text-slate-600">No referral found</p>
      </div>
    );
  }

  return (
    <div className="w-full h-screen flex flex-col bg-[#F7F9FC]">
      {/* Navigation */}
      <button
        onClick={() => navigate(-1)}
        className="px-6 py-3 bg-slate-100 hover:bg-slate-200 text-[#0B1F33] font-semibold flex items-center gap-2 transition-colors"
      >
        <ArrowLeft className="w-4 h-4" />
        Back
      </button>

      {/* Referral Viewer */}
      <ComprehensiveReferralViewer referral={referral} onAnnotationSave={handleAnnotationSave} />
    </div>
  );
}
