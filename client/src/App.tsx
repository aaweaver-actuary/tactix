import { useEffect, useMemo, useState } from 'react';
import { DashboardPayload, fetchDashboard, triggerPipeline } from './api';

function Badge({ label }: { label: string }) {
  return (
    <span className="px-2 py-1 text-xs rounded-full bg-rust/30 text-sand border border-rust/60">
      {label}
    </span>
  );
}

function MetricCard({
  title,
  value,
  note,
}: {
  title: string;
  value: string;
  note?: string;
}) {
  return (
    <div className="card p-4 flex flex-col gap-2">
      <p className="text-sm text-sand/70 uppercase tracking-[0.08em]">
        {title}
      </p>
      <p className="text-3xl font-display text-teal">{value}</p>
      {note ? <p className="text-xs text-sand/60">{note}</p> : null}
    </div>
  );
}

function TacticsTable({ data }: { data: DashboardPayload['tactics'] }) {
  return (
    <div className="card p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-display text-sand">Recent tactics</h3>
        <Badge label="Live" />
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-sand/60">
            <tr>
              <th className="text-left py-2">Motif</th>
              <th className="text-left">Result</th>
              <th className="text-left">Move</th>
              <th className="text-left">Delta (cp)</th>
            </tr>
          </thead>
          <tbody className="text-sand/90">
            {data.map((row) => (
              <tr
                key={row.tactic_id}
                className="odd:bg-white/0 even:bg-white/5/5 border-b border-white/5"
              >
                <td className="py-2 font-display text-sm uppercase tracking-wide">
                  {row.motif}
                </td>
                <td>
                  <Badge label={row.result} />
                </td>
                <td className="font-mono text-xs">{row.user_uci}</td>
                <td className="font-mono text-xs text-rust">
                  {row.eval_delta}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function MetricsGrid({ data }: { data: DashboardPayload['metrics'] }) {
  return (
    <div className="card p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-display text-sand">Motif breakdown</h3>
        <Badge label="Updated" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {data.map((row) => (
          <MetricCard
            key={row.motif}
            title={row.motif}
            value={`${row.found}/${row.total}`}
            note={`${row.missed} missed, ${row.failed_attempt} failed`}
          />
        ))}
      </div>
    </div>
  );
}

function PositionsList({ data }: { data: DashboardPayload['positions'] }) {
  return (
    <div className="card p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-lg font-display text-sand">Latest positions</h3>
        <Badge label="Fen" />
      </div>
      <div className="flex flex-col gap-3">
        {data.map((pos) => (
          <div
            key={pos.position_id}
            className="flex items-center justify-between text-sm border-b border-white/10 pb-2"
          >
            <div>
              <p className="font-mono text-xs text-sand/70">{pos.fen}</p>
              <p className="text-sand/90">
                Move {pos.move_number} · {pos.san}
              </p>
            </div>
            <Badge label={`${pos.clock_seconds ?? '--'}s`} />
          </div>
        ))}
      </div>
    </div>
  );
}

function Hero({
  onRun,
  loading,
  version,
}: {
  onRun: () => void;
  loading: boolean;
  version: number;
}) {
  return (
    <div className="card p-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
      <div>
        <p className="text-sm text-sand/70">Airflow DAG · daily_game_sync</p>
        <h1 className="text-3xl md:text-4xl font-display text-sand mt-2">
          Lichess rapid pipeline
        </h1>
        <p className="text-sand/70 mt-2">
          Execution stamped via metrics version {version}
        </p>
      </div>
      <div className="flex gap-3">
        <button
          className="button bg-teal text-night px-4 py-3 rounded-lg font-display"
          onClick={onRun}
          disabled={loading}
        >
          {loading ? 'Running…' : 'Run + Refresh'}
        </button>
        <button
          className="button border border-sand/40 text-sand px-4 py-3 rounded-lg"
          onClick={onRun}
          disabled={loading}
        >
          Cache bust
        </button>
      </div>
    </div>
  );
}

function App() {
  const [data, setData] = useState<DashboardPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = await fetchDashboard();
      setData(payload);
    } catch (err) {
      console.error(err);
      setError('Failed to load dashboard');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleRun = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = await triggerPipeline();
      setData(payload);
    } catch (err) {
      console.error(err);
      setError('Pipeline run failed');
    } finally {
      setLoading(false);
    }
  };

  const totals = useMemo(() => {
    if (!data) return { positions: 0, tactics: 0 };
    return {
      positions: data.positions.length,
      tactics: data.tactics.length,
    };
  }, [data]);

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
      <Hero
        onRun={handleRun}
        loading={loading}
        version={data?.metrics_version ?? 0}
      />

      {error ? <div className="card p-3 text-rust">{error}</div> : null}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <MetricCard
          title="Positions"
          value={`${totals.positions}`}
          note="Captured when you were to move"
        />
        <MetricCard
          title="Tactics"
          value={`${totals.tactics}`}
          note="Analyzed via Stockfish"
        />
        <MetricCard
          title="Metrics ver."
          value={`${data?.metrics_version ?? 0}`}
          note="Cache bust signal"
        />
      </div>

      {data ? <MetricsGrid data={data.metrics} /> : null}
      {data ? <TacticsTable data={data.tactics} /> : null}
      {data ? <PositionsList data={data.positions} /> : null}
    </div>
  );
}

export default App;
