const PGADMIN_URL = process.env.TACTIX_PGADMIN_URL || 'http://localhost:5050';

async function checkLoginPage() {
  const response = await fetch(`${PGADMIN_URL}/login`);
  if (!response.ok) {
    throw new Error(`PgAdmin login page returned ${response.status}`);
  }
  const text = await response.text();
  if (!text.toLowerCase().includes('pgadmin')) {
    throw new Error('PgAdmin login page did not include expected branding');
  }
}

(async () => {
  await checkLoginPage();
  console.log('PgAdmin integration check passed');
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
