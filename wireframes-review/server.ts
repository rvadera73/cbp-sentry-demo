import express, { Request, Response } from 'express';
import path from 'path';
import { createServer as createViteServer } from 'vite';
import { GoogleGenAI } from '@google/genai';
import dotenv from 'dotenv';

dotenv.config();

const app = express();
const PORT = 3000;

// Middleware
app.use(express.json());

// Lazy-initialized Gemini API client
let aiInstance: GoogleGenAI | null = null;

function getGeminiClient(): GoogleGenAI {
  if (!aiInstance) {
    const key = process.env.GEMINI_API_KEY;
    if (!key || key.includes('MY_GEMINI_API_KEY')) {
      throw new Error('GEMINI_API_KEY is not configured in environment variables');
    }
    aiInstance = new GoogleGenAI({
      apiKey: key,
      httpOptions: {
        headers: {
          'User-Agent': 'aistudio-build',
        }
      }
    });
  }
  return aiInstance;
}

// ==========================================
// API ENDPOINTS (First registered)
// ==========================================

// AI Assistant Endpoint - Custom prompt context
app.post('/api/gemini/assistant', async (req: Request, res: Response) => {
  try {
    const { message, history, context } = req.body;
    
    // Attempt real Gemini generation
    try {
      const client = getGeminiClient();
      
      const systemInstruction = `You are CBP Sentry AI, a senior federal trade enforcement intelligence assistant. 
You assist Customs and Border Protection (CBP) officers and trade analysts. 
Keep your tone authoritative, analytical, highly precise, objective, and compliant with DHS guidelines. 
Reference specific trade and shipping metrics (e.g., container weights, port routing, AIS spoofing) where appropriate.
If discussing a specific case context, refer specifically to these parameters:
${JSON.stringify(context || {})}
Provide scannable, high-density recommendations. Use bolding to represent risk levels or specific entities.`;

      // Structure contents with history
      const formattedContents: any[] = [];
      if (history && Array.isArray(history)) {
        history.forEach((h: any) => {
          formattedContents.push({
            role: h.role === 'user' ? 'user' : 'model',
            parts: [{ text: h.content }]
          });
        });
      }
      formattedContents.push({
        role: 'user',
        parts: [{ text: message }]
      });

      const response = await client.models.generateContent({
        model: 'gemini-3.5-flash',
        contents: formattedContents,
        config: {
          systemInstruction,
          temperature: 0.2
        }
      });

      res.json({ text: response.text });
    } catch (apiError: any) {
      console.warn('Gemini API call skipped or failed. Using intelligent fallback:', apiError.message);
      
      // Intelligent fallback simulator
      const responseText = simulateAISuggestion(message, context);
      res.json({ 
        text: responseText, 
        isDemoMode: true,
        warning: 'Running in Secure Demo Mode. Configure GEMINI_API_KEY to enable full live intelligence.'
      });
    }
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// Synopsis Builder Endpoint
app.post('/api/gemini/synopsis', async (req: Request, res: Response) => {
  try {
    const { caseName, entity, category, shipments, findings } = req.body;
    
    try {
      const client = getGeminiClient();
      const prompt = `Develop a highly precise 2-3 sentence technical synopsis for a CBP active trade investigation.
Case Name: ${caseName}
Target Entity: ${entity}
Product Category: ${category}
Related Flagged Shipments: ${JSON.stringify(shipments || [])}
Flagged AI Findings: ${JSON.stringify(findings || [])}

Focus purely on detailing:
1. Specific origin-evasion methodologies suspected (e.g. transshipment corridors, route adjustments, paperwork discrepancies).
2. The supply-chain flow of materials from origin to US port of entry.
3. Quantifiable risks (like unpaid tariffs or restricted factories under UFLPA).
Keep the style dense, formal, objective, and expert. Do not use generic introductions or high-flown narrative tags. Only output the 2-3 sentence text itself.`;

      const response = await client.models.generateContent({
        model: 'gemini-3.5-flash',
        contents: prompt,
        config: {
          temperature: 0.1
        }
      });
      
      res.json({ synopsis: response.text });
    } catch (apiError: any) {
      console.warn('Synopsis fallback triggered:', apiError.message);
      
      // Dynamic fallback based on the actual case inputs
      const sample = `AI analysis indicates probable origin-evasion patterns for ${entity} regarding imports under HS code ${category}. Analysis of cargo shipping routes and billing trails points to sourcing originating from high-risk sanctioned facilities, with container transfers occurring in nearby secondary transit ports to mislead inspectors. This is done to evade anti-dumping duties or bypass statutory import exclusions.`;
      res.json({ 
        synopsis: sample, 
        isDemoMode: true 
      });
    }
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// Draft Referral Narrative Builder Endpoint
app.post('/api/gemini/draft-referral', async (req: Request, res: Response) => {
  try {
    const { caseName, targetEntity, category, shipments, findings, sections } = req.body;
    
    try {
      const client = getGeminiClient();
      const prompt = `You are a Senior Federal Trade Enforcement Advisor drafting an official trade fraud referral package to the Department of Justice and DHS General Counsel.
Case: ${caseName}
Subject under Investigation: ${targetEntity}
Product HS Classification: ${category}

Supporting Shipments:
${JSON.stringify(shipments || [])}

Key Findings Selected as Evidence:
${JSON.stringify(findings || [])}

Draft a realistic executive summary and subject overview for the following section: "${sections.join(', ')}". 
For each drafted section, provide concrete paragraphs with specific legal language, referring to statutes like 19 U.S.C. § 1592 or specific container codes listed in the shipments above.
Adopt an authoritative, meticulous, forensic style. Separate the sections using markdown headers titled with the section names. Only return the narrative markdown itself.`;

      const response = await client.models.generateContent({
        model: 'gemini-3.5-flash',
        contents: prompt,
        config: {
          temperature: 0.1
        }
      });
      
      res.json({ narrative: response.text });
    } catch (apiError: any) {
      console.warn('Referral generator fallback triggered:', apiError.message);
      
      // Create high-quality markdown template narrative
      const formattedMarkdown = generateMockMarkdownReferral(caseName, targetEntity, category, shipments, findings);
      res.json({ 
        narrative: formattedMarkdown, 
        isDemoMode: true 
      });
    }
  } catch (err: any) {
    res.status(500).json({ error: err.message });
  }
});

// Helper: Intelligent local mockup responses to keep interface highly responsive and realistic
function simulateAISuggestion(message: string, context: any): string {
  const msg = message.toLowerCase();
  
  // Custom smart responses based on analyst keywords
  if (msg.includes('silicon') || msg.includes('solar') || msg.includes('vina')) {
    return `### **CBP Sentry Intelligence Analysis — Solar Modules**

Based on active container telemetry for **Vina Solar Technologies LLC**:
1. **Physical Manifest Mismatch**: Container **MSKU-8209412** weighs 24,310 kg—substantially exceeding the maximum weight density of standard finished solar module arrays (average 21,100 kg per nominal container load). This indicates the potential concealment of underlying raw aluminum frames or sub-silicon components originating secretly from Chinese smelting mills.
2. **Entity Resolution Audit**: Registration addresses inside Bac Giang industrial park match previous filings linked to **Jiangsu Solar Holdings** (a restricted parent enterprise).
3. **Recommended Immediate Action**:
   - Issue a physical cargo examination targeting order at LA Port terminal 400.
   - Require BrightPath Solar Corp to present a full bill of materials with sub-wafer chemical assays.`;
  }
  
  if (msg.includes('steel') || msg.includes('apex')) {
    return `### **CBP Sentry Intelligence Analysis — Steel Channels**

Based on trade intelligence audits for **Apex Steel Builders Group**:
1. **Route Shielding**: High-risk alloy structural billets shipped on COSCO vessels from Tianjin are trans-loaded onto regional feeder ships in the Sriracha coastline sector. AIS data shows COSCO feeds frequently turning off transponders for 24-48 hour intervals.
2. **Tax Auditing Alarm**: The Sriracha mill facility has local power consumption equivalent to simple hand-polishing and varnishing workshops, completely inconsistent with multi-thousand-ton heavy smelting operations.
3. **Recommended Action**:
   - Classify shipments under 19 U.S.C. § 1592 as intentional evasion.
   - Dispatch immediate inquiry to Ban Laem shipping agents.`;
  }

  if (msg.includes('recommend') || msg.includes('next action') || msg.includes('steps')) {
    return `### **DHS/CBP Trade Enforcement Recommendations**

For high-confidence transshipment cases:
1. **Red Seizure Flagging**: Set status inside the CBP targeting portal to **Seize-and-Hold** prior to freight vessel port arrival.
2. **Sub-tier Identification**: Query UFLPA restricted lists against the immediate three levels of raw material supply lists.
3. **Enforcement Referral**: Consolidate the **Referral Package** incorporating the manifest anomalies, AIS coordinate drops, and third-party invoice paths, then export to DHS General Counsel.`;
  }

  return `### **CBP Intel Assessment**

Assessing active command database regarding: "${message}"...

**Active System Diagnostic**:
- Monitoring 5 High-Value investigations on our regional watch boards.
- AI anomaly classifiers scoring live feeder-ships from high-risk SE Asian transshipment Hubs.
- Active correlation rules include: cargo weight discrepancies, AIS dark-periods, circular invoicing pathways, and UFLPA blacklist proximity.

*Officer Tip: Ask me specifically about "Vina Solar Modules", "Apex Steel", or "Referral Assembly checklists" to drill down into active intelligence panels.*`;
}

function generateMockMarkdownReferral(caseName: string, targetEntity: string, category: string, shipments: any = [], findings: any = []): string {
  const activeShipments = shipments.length > 0 ? shipments : [{ shipment_id: "SH-904101", container_id: "MSKU-8209412", raw_weight: "24.3MT" }];
  
  return `### **CBP Case Referral Pack: ${caseName}**
---

#### **I. Executive Summary**
This formal trade fraud referral is developed for submission under United States Customs and Border Protection Authority. Evidence compiled indicates a strategic, systemic evasion of Section 301 duties and compliance restrictions on goods classified under HS Code **${category}**. 
Investigations of the subject **${targetEntity}** demonstrate intentional origin-concealment operations designed to evade anti-dumping remedies amounting to millions in uncollected federal Duties.

#### **II. Subject Under Investigation**
- **Target Enterprise**: ${targetEntity}
- **Entity Identification No.**: ENT-${Math.floor(Math.random() * 800 + 100)}
- **Filing Destination**: United States Ports of Entry (Discharge Point: Los Angeles Harbor and New York Port terminals)
- **Suspected Offense**: Evasive Transshipment via Southeast Asian logistics networks, and potential violation of statutory restrictions (including Uyghur Forced Labor Prevention Act - UFLPA compliance rules).

#### **III. Forensic Evidence Accumulation**
The following critical evidentiary files and container records have been compiled into this official referral package:

${activeShipments.map((s: any) => `- **Customs Manifest Record ${s.shipment_id || s}**: Container ID \`${s.container_id || 'MSKU-8209412'}\` declared at arrival as Vietnamese product, showing clear physical weight disparities of other core alloys (+14% overload).`).join('\n')}

#### **IV. Trade Pattern and Circular Invoice Analytics**
Visual maritime pattern tracing indicates that materials originate directly from Chinese regional suppliers before routing to transshipment ports inside third-party territories. Local processing logs show no evidence of substantial transformation of the raw inputs:
- Bulk components arrive via feeder vessels.
- Re-packaging, minor painting, and labeling changes are performed rapidly inside local Export Processing Zones.
- Cargo is immediately loaded onto US-bound carriers utilizing newly established legal shells of nominal owners.

#### **V. Recommended Legal & Enforcement Actions**
DHS counsel suggests immediate execution of the following responses:
1. **Judicial Seizure**: Issue physical seizure orders at coastal ports under **19 U.S.C. § 1592** for all pending arrivals.
2. **Civil Money Penalty Assessment**: Double tariff penalty calculations representing the intentional nature of the evasion.
3. **DOJ Criminal Referral**: Transfer structural business documentation, network registry logs, and billing trails for prosecution under **18 U.S.C. § 545** (smuggling).

---
*Draft compiled by CBP Sentry S-Trade AI Engine. Ready for human supervisor signature review and agency seal.*`;
}

// ==========================================
// VITE OR STATIC SERVING MIDDLEWARE
// ==========================================

const startServer = async () => {
  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath));
    app.get('*', (req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`CBP Sentry Server actively running on http://0.0.0.0:${PORT}`);
    console.log(`Environment: ${process.env.NODE_ENV || 'development'}`);
  });
};

startServer().catch((err) => {
  console.error('Failed to start CBP Sentry Server:', err);
});
