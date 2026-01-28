import { Client } from 'pg';

const getEnv = (key: string): string | undefined => {
  const value = process.env[key];
  return value && value.trim() ? value : undefined;
};

const buildConnectionString = (): string | undefined => {
  return (
    getEnv('TACTIX_POSTGRES_DSN') ||
    getEnv('TACTIX_POSTGRES_URL') ||
    getEnv('POSTGRES_URL') ||
    getEnv('DATABASE_URL')
  );
};

const buildConnectionConfig = () => {
  const host = getEnv('TACTIX_POSTGRES_HOST');
  const database = getEnv('TACTIX_POSTGRES_DB');
  if (!host || !database) {
    return undefined;
  }
  return {
    host,
    port: Number(getEnv('TACTIX_POSTGRES_PORT') ?? '5432'),
    database,
    user: getEnv('TACTIX_POSTGRES_USER'),
    password: getEnv('TACTIX_POSTGRES_PASSWORD'),
    ssl: getEnv('TACTIX_POSTGRES_SSLMODE') === 'require',
  };
};

const buildTableName = (): string => {
  const runId = Date.now();
  return `ts_smoke_${runId}`;
};

const run = async (): Promise<void> => {
  const connectionString = buildConnectionString();
  const config = connectionString ?? buildConnectionConfig();
  if (!config) {
    throw new Error('Missing Postgres connection info');
  }

  const client = new Client(
    typeof config === 'string' ? { connectionString: config } : config
  );

  await client.connect();

  const table = buildTableName();
  try {
    await client.query(
      `CREATE TEMP TABLE ${table} (id SERIAL PRIMARY KEY, name TEXT NOT NULL, created_at TIMESTAMPTZ DEFAULT now())`
    );

    const name = `ts-${table}`;
    const insertResult = await client.query(
      `INSERT INTO ${table} (name) VALUES ($1) RETURNING id`,
      [name]
    );
    const id = insertResult.rows[0]?.id as number;

    const countResult = await client.query(`SELECT COUNT(*) AS count FROM ${table}`);
    const count = Number(countResult.rows[0]?.count ?? 0);

    const updatedName = `ts-${table}-updated`;
    await client.query(`UPDATE ${table} SET name = $1 WHERE id = $2`, [
      updatedName,
      id,
    ]);

    const selectResult = await client.query(`SELECT name FROM ${table} WHERE id = $1`, [
      id,
    ]);
    const selectedName = selectResult.rows[0]?.name as string;

    await client.query(`DELETE FROM ${table} WHERE id = $1`, [id]);

    const remainingResult = await client.query(
      `SELECT COUNT(*) AS count FROM ${table}`
    );
    const remaining = Number(remainingResult.rows[0]?.count ?? 0);

    console.log(
      `TS CRUD ok: inserted=${count}, selected='${selectedName}', remaining=${remaining}`
    );
  } finally {
    await client.query(`DROP TABLE IF EXISTS ${table}`);
    await client.end();
  }
};

run().catch((error) => {
  console.error(`TS Postgres smoke test failed: ${error}`);
  process.exit(1);
});
