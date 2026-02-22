import { useState } from "react";
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
              <SectionCard key={i} section={section} index={i} />
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
                <div className="space-y-2.5">
                  {data.ragChunks.map((chunk, i) => (
                    <SourceChip key={chunk.id || i} chunk={chunk} index={i} />
                  ))}
                </div>
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

function SectionCard({ section, index }: { section: { heading: string; content: string }; index: number }) {
  const [expanded, setExpanded] = useState(true);

  const handleRefine = (action: string) => {
    // Placeholder for future refine API
    console.log(`Refine section "${section.heading}" with action: ${action}`);
  };

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
        <span className="text-xs text-muted-foreground">Section {index + 1}</span>
      </button>

      {expanded && (
        <>
          <div className="px-5 pb-4 border-t border-border pt-4">
            {renderMarkdown(section.content)}
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
  const filename =
    (chunk.metadata?.filename as string) ||
    (chunk.metadata?.source as string) ||
    `Source ${index + 1}`;
  const snippet = chunk.text?.slice(0, 120);

  return (
    <div className="rounded-lg bg-citation-bg border border-citation-border overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-3 py-2 text-left"
      >
        <span className="text-xs font-medium text-citation-text flex items-center gap-1.5">
          <ExternalLink className="w-3 h-3 shrink-0" />
          <span className="truncate">{filename}</span>
        </span>
        <span className="text-[10px] text-citation-text/60 shrink-0 ml-2">
          {(chunk.score * 100).toFixed(0)}% match
        </span>
      </button>
      {open && snippet && (
        <div className="px-3 pb-2 text-xs text-citation-text/80 leading-relaxed border-t border-citation-border/50 pt-2">
          "{snippet}…"
        </div>
      )}
    </div>
  );
}

export default ProposalReview;
