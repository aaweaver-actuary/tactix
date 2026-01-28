import { DashboardPayload } from '../api';
import Badge from './Badge';
import BaseCard from './BaseCard';

interface TacticsTableProps {
  tacticsData: DashboardPayload['tactics'];
}

/**
 * Renders a table displaying recent tactics data.
 *
 * @param tacticsData - An array of tactic objects containing motif, result, move, and evaluation delta.
 * @returns A styled card component with a table of tactics.
 *
 * @remarks
 * Each row displays the motif, result (with a badge), user's move in UCI format, and the evaluation delta in centipawns.
 */
export default function TacticsTable({ tacticsData }: TacticsTableProps) {
  const header = (
    <div className="flex items-center justify-between">
      <h3 className="text-lg font-display text-sand">Recent tactics</h3>
      <Badge label="Live" />
    </div>
  );

  return (
    <BaseCard className="p-4" header={header} contentClassName="pt-3">
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
            {tacticsData.map((row) => (
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
    </BaseCard>
  );
}
