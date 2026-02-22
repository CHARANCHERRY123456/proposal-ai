import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useAuth } from "@/context/AuthContext";
import { api, Opportunity } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  FileText,
  Search,
  Calendar,
  ArrowRight,
  LogOut,
  Loader2,
  AlertCircle,
} from "lucide-react";

const Opportunities = () => {
  const { logout } = useAuth();
  const navigate = useNavigate();
  const [search, setSearch] = useState("");

  const { data, isLoading, error } = useQuery({
    queryKey: ["opportunities"],
    queryFn: () => api.getOpportunities(50, 0),
  });

  const filtered = data?.items.filter(
    (o) =>
      o.title.toLowerCase().includes(search.toLowerCase()) ||
      o.solicitationNumber?.toLowerCase().includes(search.toLowerCase())
  );

  const handleApply = (noticeId: string) => {
    navigate(`/proposal/${encodeURIComponent(noticeId)}`);
  };

  const formatDate = (d: string) => {
    if (!d) return "—";
    try {
      return new Date(d).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      });
    } catch {
      return d;
    }
  };

  const isDeadlineSoon = (d: string) => {
    if (!d) return false;
    const diff = new Date(d).getTime() - Date.now();
    return diff > 0 && diff < 7 * 24 * 60 * 60 * 1000;
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-card sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
              <FileText className="w-4 h-4 text-primary-foreground" />
            </div>
            <span className="font-semibold text-foreground">ProposalAI</span>
          </div>
          <Button variant="ghost" size="sm" onClick={() => { logout(); navigate("/login"); }}>
            <LogOut className="w-4 h-4 mr-1.5" /> Sign out
          </Button>
        </div>
      </header>

      {/* Content */}
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-8 fade-in">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-foreground mb-1">Government Opportunities</h1>
          <p className="text-muted-foreground">Browse and apply to open solicitations</p>
        </div>

        {/* Search */}
        <div className="relative mb-6 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Search by title or solicitation number…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 h-10"
          />
        </div>

        {/* States */}
        {isLoading && (
          <div className="flex items-center justify-center py-20 text-muted-foreground">
            <Loader2 className="w-5 h-5 animate-spin mr-2" /> Loading opportunities…
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 py-20 justify-center text-destructive">
            <AlertCircle className="w-5 h-5" />
            <span>{(error as Error).message}</span>
          </div>
        )}

        {filtered && filtered.length === 0 && (
          <div className="text-center py-20 text-muted-foreground">
            No opportunities found.
          </div>
        )}

        {/* List */}
        {filtered && filtered.length > 0 && (
          <div className="space-y-3">
            {filtered.map((opp, i) => (
              <OpportunityCard
                key={opp.noticeId}
                opportunity={opp}
                onApply={handleApply}
                formatDate={formatDate}
                isDeadlineSoon={isDeadlineSoon}
                index={i}
              />
            ))}
          </div>
        )}

        {data && (
          <p className="text-xs text-muted-foreground mt-6">
            Showing {filtered?.length} of {data.total} opportunities
          </p>
        )}
      </main>
    </div>
  );
};

function OpportunityCard({
  opportunity: opp,
  onApply,
  formatDate,
  isDeadlineSoon,
  index,
}: {
  opportunity: Opportunity;
  onApply: (id: string) => void;
  formatDate: (d: string) => string;
  isDeadlineSoon: (d: string) => boolean;
  index: number;
}) {
  return (
    <div
      className="glass-card p-5 hover:shadow-md transition-shadow"
      style={{ animationDelay: `${index * 40}ms` }}
    >
      <div className="flex flex-col sm:flex-row sm:items-start gap-4 justify-between">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-foreground text-sm leading-snug mb-1.5 line-clamp-2">
            {opp.title}
          </h3>
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
            <span>{opp.solicitationNumber}</span>
            {opp.type && (
              <span className="inline-flex items-center px-2 py-0.5 rounded-md bg-badge-bg text-badge-text font-medium">
                {opp.type}
              </span>
            )}
            {opp.responseDeadLine && (
              <span className={`inline-flex items-center gap-1 ${isDeadlineSoon(opp.responseDeadLine) ? "text-warning font-medium" : ""}`}>
                <Calendar className="w-3 h-3" />
                Due {formatDate(opp.responseDeadLine)}
              </span>
            )}
          </div>
          {opp.typeOfSetAsideDescription && (
            <p className="text-xs text-muted-foreground mt-1.5">{opp.typeOfSetAsideDescription}</p>
          )}
        </div>
        <Button
          size="sm"
          className="shrink-0 gap-1.5"
          onClick={() => onApply(opp.noticeId)}
        >
          Apply <ArrowRight className="w-3.5 h-3.5" />
        </Button>
      </div>
    </div>
  );
}

export default Opportunities;
