import { client } from '../api';

export default async function triggerMigrations(source?: string): Promise<{
  status: string;
  result: { source: string; schema_version: number };
}> {
  const res = await client.post('/api/jobs/migrations', null, {
    params: { source },
  });
  return res.data;
}
