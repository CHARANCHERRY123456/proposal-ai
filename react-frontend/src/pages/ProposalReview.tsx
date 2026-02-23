import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/context/AuthContext";
import { api, RagChunk } from "@/lib/api";
import { Button } from "@/components/ui/button";
import {
  FileText,
  ArrowLeft,
  CheckCircle2,
  BookOpen,
  Maximize2,
  Minimize2,
  Type,
  Loader2,
  AlertCircle,
  ChevronDown,
  ChevronRight,
  ExternalLink,
} from "lucide-react";

// Simple markdown-to-sections parser
function parseSections(draft: string): { heading: string; content: string }[] {
  const lines = draft.split("\n");
  const sections: { heading: string; content: string }[] = [];
  let current: { heading: string; content: string } | null = null;

  for (const line of lines) {
    const match = line.match(/^#{1,3}\s+(.+)/);
    if (match) {
      if (current) sections.push(current);
      current = { heading: match[1], content: "" };
    } else {
      if (!current) current = { heading: "Introduction", content: "" };
      current.content += line + "\n";
    }
  }
  if (current) sections.push(current);
  return sections;
}

// Render simple markdown (bold, lists, paragraphs)
function renderMarkdown(text: string) {
  const lines = text.trim().split("\n");
  const elements: React.ReactNode[] = [];
  let listItems: string[] = [];

  const flushList = () => {
    if (listItems.length > 0) {
      elements.push(
        <ul key={`list-${elements.length}`} className="list-disc list-inside space-y-1 text-sm text-foreground/90 mb-3">
          {listItems.map((item, i) => (
            <li key={i} dangerouslySetInnerHTML={{ __html: boldify(item) }} />
          ))}
        </ul>
      );
      listItems = [];
    }
  };

  const boldify = (s: string) =>
    s.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");

  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      listItems.push(trimmed.slice(2));
    } else {
      flushList();
      if (trimmed.length > 0) {
        elements.push(
          <p
            key={`p-${elements.length}`}
            className="text-sm text-foreground/90 leading-relaxed mb-3"
            dangerouslySetInnerHTML={{ __html: boldify(trimmed) }}
          />
        );
      }
    }
  }
  flushList();
  return elements;
}

const ProposalReview = () => {
  const { noticeId } = useParams<{ noticeId: string }>();
  const navigate = useNavigate();
  const { companyId } = useAuth();

  const { data, isLoading, error } = useQuery({
    queryKey: ["proposal", noticeId, companyId],
    queryFn: () => api.createDraftProposal(noticeId!, companyId!),
    enabled: !!noticeId && !!companyId,
    retry: false,
  });

  // Debug: Log citation data
  useEffect(() => {
    if (data) {
      console.log("[CITATIONS DEBUG] Full proposal data:", data);
      console.log("[CITATIONS DEBUG] RAG Chunks count:", data.ragChunks?.length || 0);
      if (data.ragChunks && data.ragChunks.length > 0) {
        console.log("[CITATIONS DEBUG] First chunk:", data.ragChunks[0]);
        console.log("[CITATIONS DEBUG] First chunk metadata:", data.ragChunks[0].metadata);
        data.ragChunks.forEach((chunk, i) => {
          console.log(`[CITATIONS DEBUG] Chunk ${i}:`, {
            id: chunk.id,
            filename: chunk.metadata?.filename,
            section_name: chunk.metadata?.section_name,
            section_type: chunk.metadata?.section_type,
            requirement_flag: chunk.metadata?.requirement_flag,
            is_critical: chunk.metadata?.is_critical,
            score: chunk.score,
            text_length: chunk.text?.length || 0,
          });
        });
      } else {
        console.warn("[CITATIONS DEBUG] No RAG chunks found in response!");
      }
    }
  }, [data]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center fade-in">
          <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto mb-4" />
          <h2 className="text-lg font-semibold text-foreground mb-1">Generating your proposal…</h2>
          <p className="text-sm text-muted-foreground">
            Analyzing the opportunity and crafting a tailored draft
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center px-4">
        <div className="text-center fade-in max-w-md">
          <AlertCircle className="w-8 h-8 text-destructive mx-auto mb-4" />
          <h2 className="text-lg font-semibold text-foreground mb-2">Something went wrong</h2>
          <p className="text-sm text-muted-foreground mb-6">{(error as Error).message}</p>
          <Button variant="outline" onClick={() => navigate("/opportunities")}>
            <ArrowLeft className="w-4 h-4 mr-1.5" /> Back to opportunities
          </Button>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const sections = parseSections(data.draft);
  const oppTitle = (data.opportunity as any)?.title || "Untitled Opportunity";
  const oppNoticeId = (data.opportunity as any)?.noticeId || noticeId;
  const companyName = (data.company as any)?.name || (data.company as any)?.companyName || "Your Company";

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="sm" onClick={() => navigate("/opportunities")}>
              <ArrowLeft className="w-4 h-4 mr-1" /> Back
            </Button>
            <div className="h-5 w-px bg-border" />
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-lg bg-primary flex items-center justify-center">
                <FileText className="w-3.5 h-3.5 text-primary-foreground" />
              </div>
              <span className="font-semibold text-foreground text-sm hidden sm:inline">Proposal Review</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1.5 text-xs font-medium text-success bg-success/10 px-2.5 py-1 rounded-full">
              <CheckCircle2 className="w-3.5 h-3.5" /> Draft ready
            </span>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        {/* Trust banner */}
        <div className="mb-8 fade-in">
          <h1 className="text-2xl font-bold text-foreground mb-1">Your draft is ready</h1>
          <p className="text-muted-foreground text-sm">
            Review the AI-generated proposal below. All claims are grounded in the provided sources.
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Draft – main content */}
          <div className="lg:col-span-2 space-y-4 slide-up">
            {sections.map((section, i) => (
              <SectionCard key={i} section={section} index={i} allChunks={data.ragChunks} />
            ))}
          </div>

          {/* Sidebar */}
          <aside className="space-y-4 fade-in">
            {/* Opportunity info */}
            <div className="glass-card p-5">
              <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
                Opportunity
              </h3>
              <p className="text-sm font-medium text-foreground leading-snug mb-1">{oppTitle}</p>
              <p className="text-xs text-muted-foreground">{oppNoticeId}</p>
            </div>

            {/* Company */}
            <div className="glass-card p-5">
              <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3">
                Applicant
              </h3>
              <p className="text-sm font-medium text-foreground">{companyName}</p>
            </div>

            {/* Sources */}
            <div className="glass-card p-5">
              <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3 flex items-center gap-1.5">
                <BookOpen className="w-3.5 h-3.5" /> Sources & Evidence
              </h3>
              {data.ragChunks && data.ragChunks.length > 0 ? (
                <>
                  <p className="text-xs text-muted-foreground mb-3">
                    {data.ragChunks.length} source{data.ragChunks.length !== 1 ? "s" : ""} used to generate this proposal
                  </p>
                  <div className="space-y-2.5">
                    {data.ragChunks.map((chunk, i) => (
                      <SourceChip key={chunk.id || i} chunk={chunk} index={i} />
                    ))}
                  </div>
                </>
              ) : (
                <p className="text-xs text-muted-foreground italic">
                  No additional sources were used beyond the solicitation document.
                </p>
              )}
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
};

function SectionCard({ 
  section, 
  index, 
  allChunks 
}: { 
  section: { heading: string; content: string }; 
  index: number;
  allChunks?: RagChunk[];
}) {
  const [expanded, setExpanded] = useState(true);

  const handleRefine = (action: string) => {
    // Placeholder for future refine API
    console.log(`Refine section "${section.heading}" with action: ${action}`);
  };

  // Find relevant chunks for this section based on section heading keywords
  const getRelevantChunks = () => {
    if (!allChunks || allChunks.length === 0) return [];
    const headingLower = section.heading.toLowerCase();
    return allChunks.filter(chunk => {
      const sectionType = (chunk.metadata?.section_type as string || "").toLowerCase();
      const sectionName = (chunk.metadata?.section_name as string || "").toLowerCase();
      const text = (chunk.text || "").toLowerCase();
      
      // Match if section type or name contains keywords from heading
      const headingKeywords = headingLower.split(/\s+/).filter(w => w.length > 3);
      return headingKeywords.some(keyword => 
        sectionType.includes(keyword) || 
        sectionName.includes(keyword) ||
        text.includes(keyword)
      ) || chunk.metadata?.requirement_flag || chunk.metadata?.is_critical;
    }).slice(0, 3); // Limit to 3 most relevant
  };

  const relevantChunks = getRelevantChunks();

  return (
    <div className="glass-card overflow-hidden" style={{ animationDelay: `${index * 60}ms` }}>
      {/* Section header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-muted/50 transition-colors"
      >
        <span className="text-sm font-semibold text-foreground flex items-center gap-2">
          {expanded ? <ChevronDown className="w-4 h-4 text-muted-foreground" /> : <ChevronRight className="w-4 h-4 text-muted-foreground" />}
          {section.heading}
        </span>
        <div className="flex items-center gap-2">
          {relevantChunks.length > 0 && (
            <span className="text-[10px] text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
              {relevantChunks.length} source{relevantChunks.length !== 1 ? "s" : ""}
            </span>
          )}
          <span className="text-xs text-muted-foreground">Section {index + 1}</span>
        </div>
      </button>

      {expanded && (
        <>
          <div className="px-5 pb-4 border-t border-border pt-4">
            {renderMarkdown(section.content)}
            
            {/* Show relevant citations for this section */}
            {relevantChunks.length > 0 && (
              <div className="mt-4 pt-4 border-t border-border/50">
                <div className="flex items-center gap-1.5 mb-2">
                  <BookOpen className="w-3 h-3 text-muted-foreground" />
                  <span className="text-xs font-medium text-muted-foreground">Referenced Sources:</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {relevantChunks.map((chunk, i) => {
                    const filename = (chunk.metadata?.filename as string || `Source ${i + 1}`).replace(/\.[^/.]+$/, "");
                    return (
                      <span
                        key={chunk.id || i}
                        className="text-[10px] px-2 py-0.5 rounded bg-citation-bg border border-citation-border text-citation-text font-medium"
                        title={`${filename} (${(chunk.score * 100).toFixed(0)}% match)`}
                      >
                        {filename.slice(0, 20)}{filename.length > 20 ? "…" : ""}
                      </span>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Refinement actions */}
          <div className="px-5 py-3 bg-muted/30 border-t border-border flex flex-wrap gap-2">
            <Button variant="outline" size="sm" className="h-7 text-xs gap-1" onClick={() => handleRefine("expand")}>
              <Maximize2 className="w-3 h-3" /> Expand
            </Button>
            <Button variant="outline" size="sm" className="h-7 text-xs gap-1" onClick={() => handleRefine("shorten")}>
              <Minimize2 className="w-3 h-3" /> Shorten
            </Button>
            <Button variant="outline" size="sm" className="h-7 text-xs gap-1" onClick={() => handleRefine("formal")}>
              <Type className="w-3 h-3" /> More formal
            </Button>
          </div>
        </>
      )}
    </div>
  );
}

function SourceChip({ chunk, index }: { chunk: RagChunk; index: number }) {
  const [open, setOpen] = useState(false);
  const filename = chunk.metadata?.filename as string || `Source ${index + 1}`;
  const sectionName = chunk.metadata?.section_name as string || "";
  const sectionType = chunk.metadata?.section_type as string || "other";
  const isRequirement = chunk.metadata?.requirement_flag as boolean || false;
  const isCritical = chunk.metadata?.is_critical as boolean || false;
  const fullText = chunk.text || "";
  const snippet = fullText.slice(0, 150);

  // Debug log for each source chip
  useEffect(() => {
    console.log(`[CITATIONS DEBUG] SourceChip ${index}:`, {
      id: chunk.id,
      filename,
      sectionName,
      sectionType,
      isRequirement,
      isCritical,
      hasText: !!fullText,
      textLength: fullText.length,
      metadata: chunk.metadata,
    });
  }, [chunk, index, filename, sectionName, sectionType, isRequirement, isCritical, fullText]);

  const getSectionTypeColor = (type: string) => {
    switch (type) {
      case "requirement": return "bg-blue-500/20 text-blue-600 dark:text-blue-400";
      case "specification": return "bg-purple-500/20 text-purple-600 dark:text-purple-400";
      case "evaluation_criteria": return "bg-green-500/20 text-green-600 dark:text-green-400";
      case "scope_of_work": return "bg-orange-500/20 text-orange-600 dark:text-orange-400";
      default: return "bg-gray-500/20 text-gray-600 dark:text-gray-400";
    }
  };

  return (
    <div className="rounded-lg bg-citation-bg border border-citation-border overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-start justify-between px-3 py-2.5 text-left hover:bg-citation-bg/80 transition-colors"
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-1">
            <ExternalLink className="w-3 h-3 shrink-0 text-citation-text/70" />
            <span className="text-xs font-medium text-citation-text truncate">{filename}</span>
          </div>
          {sectionName && (
            <div className="text-[10px] text-citation-text/60 mb-1.5 line-clamp-1">
              {sectionName}
            </div>
          )}
          <div className="flex items-center gap-1.5 flex-wrap">
            {sectionType !== "other" && (
              <span className={`text-[9px] px-1.5 py-0.5 rounded ${getSectionTypeColor(sectionType)} font-medium`}>
                {sectionType.replace("_", " ")}
              </span>
            )}
            {isRequirement && (
              <span className="text-[9px] px-1.5 py-0.5 rounded bg-red-500/20 text-red-600 dark:text-red-400 font-medium">
                Requirement
              </span>
            )}
            {isCritical && (
              <span className="text-[9px] px-1.5 py-0.5 rounded bg-yellow-500/20 text-yellow-600 dark:text-yellow-400 font-medium">
                Critical
              </span>
            )}
          </div>
        </div>
        <span className="text-[10px] text-citation-text/60 shrink-0 ml-2 mt-0.5">
          {(chunk.score * 100).toFixed(0)}%
        </span>
      </button>
      {open && (
        <div className="px-3 pb-3 text-xs text-citation-text/80 leading-relaxed border-t border-citation-border/50 pt-2.5 space-y-2">
          {snippet && (
            <div className="italic">
              "{snippet}{fullText.length > 150 ? "…" : ""}"
            </div>
          )}
          {fullText.length > 150 && (
            <details className="group">
              <summary className="cursor-pointer text-citation-text/60 hover:text-citation-text text-[10px] font-medium">
                View full text
              </summary>
              <div className="mt-2 p-2 bg-citation-bg/50 rounded text-[11px] whitespace-pre-wrap max-h-48 overflow-y-auto">
                {fullText}
              </div>
            </details>
          )}
          <div className="text-[10px] text-citation-text/50 pt-1 border-t border-citation-border/30">
            Chunk ID: {chunk.id}
          </div>
        </div>
      )}
    </div>
  );
}

export default ProposalReview;
