import { PracticeQueueItem } from '../api';
import Badge from './Badge';
import BaseCard from './BaseCard';
import Text from './Text';

interface PracticeQueueProps {
  data: PracticeQueueItem[];
  includeFailedAttempt: boolean;
  onToggleIncludeFailedAttempt: (next: boolean) => void;
  loading: boolean;
}

/**
 * Displays a practice queue of missed tactics from the user's games, allowing them to drill and review their performance.
 *
 * @param data - Array of practice queue items containing tactic and position details.
 * @param includeFailedAttempt - Boolean indicating whether to include failed attempts in the queue.
 * @param onToggleIncludeFailedAttempt - Callback function triggered when the "Include failed attempts" checkbox is toggled.
 * @param loading - Boolean indicating whether the practice queue data is currently loading.
 *
 * Renders a table of tactics with details such as motif, result, best move, user's move, move number, and evaluation delta.
 * Shows a loading or empty state message when appropriate.
 */
export default function PracticeQueue({
  data,
  includeFailedAttempt,
  onToggleIncludeFailedAttempt,
  loading,
}: PracticeQueueProps) {
  const header = (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div>
        <h3 className="text-lg font-display text-sand">Practice queue</h3>
        <Text value="Missed tactics from your games, ready to drill." />
      </div>
      <label className="flex items-center gap-2 text-xs text-sand/70">
        <input
          type="checkbox"
          className="accent-teal"
          checked={includeFailedAttempt}
          onChange={(event) =>
            onToggleIncludeFailedAttempt(event.target.checked)
          }
          disabled={loading}
        />
        Include failed attempts
      </label>
    </div>
  );

  return (
    <BaseCard className="p-4" header={header} contentClassName="pt-3">
      {data.length ? (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="text-sand/60">
              <tr>
                <th className="text-left py-2">Motif</th>
                <th className="text-left">Result</th>
                <th className="text-left">Best</th>
                <th className="text-left">Your move</th>
                <th className="text-left">Move</th>
                <th className="text-left">Delta</th>
              </tr>
            </thead>
            <tbody className="text-sand/90">
              {data.map((row) => (
                <tr
                  key={`${row.tactic_id}-${row.position_id}`}
                  className="odd:bg-white/0 even:bg-white/5/5 border-b border-white/5"
                >
                  <td className="py-2 font-display text-sm uppercase tracking-wide">
                    {row.motif}
                  </td>
                  <td>
                    <Badge label={row.result} />
                  </td>
                  <td className="font-mono text-xs text-teal">
                    {row.best_uci || '--'}
                  </td>
                  <td className="font-mono text-xs">{row.user_uci}</td>
                  <td className="font-mono text-xs">
                    {row.move_number}.{row.ply}
                  </td>
                  <td className="font-mono text-xs text-rust">
                    {row.eval_delta}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <Text
          value={
            loading
              ? 'Loading practice queue…'
              : 'No missed tactics queued yet.'
          }
        />
      )}
    </BaseCard>
  );
}
