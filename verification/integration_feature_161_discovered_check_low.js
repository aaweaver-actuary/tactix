const apiBase = process.env.TACTIX_API_URL || 'http://localhost:8000';
const apiToken = process.env.TACTIX_API_TOKEN || 'local-dev-token';
const expectedGameId =
	process.env.TACTIX_DISCOVERED_CHECK_GAME_ID || '1610000001';

async function fetchDashboard() {
	const url = `${apiBase}/api/dashboard?source=chesscom&motif=discovered_check`;
	const res = await fetch(url, {
		headers: { Authorization: `Bearer ${apiToken}` },
	});
	if (!res.ok) {
		throw new Error(`Dashboard fetch failed: ${res.status}`);
	}
	return res.json();
}

(async () => {
	try {
		const data = await fetchDashboard();
		const tactics = Array.isArray(data?.tactics) ? data.tactics : [];
		const row = tactics.find(
			(item) =>
				item.motif === 'discovered_check' &&
				item.game_id === expectedGameId &&
				Number(item.severity) <= 1.0,
		);
		if (!row) {
			throw new Error('Expected discovered check tactic with low severity (<= 1.0)');
		}
		if (!row.best_uci || typeof row.best_uci !== 'string') {
			throw new Error('Expected best_uci to be persisted for discovered check');
		}
		if (!row.explanation || !String(row.explanation).includes('Best line')) {
			throw new Error('Expected explanation to include Best line');
		}
		if (!row.position_id) {
			throw new Error('Expected tactic to be linked to a position_id');
		}
		console.log('Feature 161 integration check ok');
	} catch (err) {
		console.error(err);
		process.exit(1);
	}
})();
